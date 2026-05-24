import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

import auth as auth_core
import config as app_config
import mfa as mfa_core
from audit_log import record_audit
from cookie_auth import (
    clear_mfa_cookies,
    clear_session_cookies,
    decode_mfa_pending_token,
    get_mfa_pending_token,
    get_mfa_setup_token,
    get_refresh_token_from_request,
    set_mfa_pending_cookie,
    set_mfa_setup_cookie,
)
from database import get_db
from ip_allowlist import assert_admin_ip_allowed
from login_alerts import record_admin_login
from login_lockout import assert_not_locked, clear_login_lockout, record_failed_login
from models import User, UserRole, normalize_user_role
from rate_limit import auth_login_limit
from refresh_store import (
    create_refresh_session,
    get_active_session,
    new_family_id,
    new_jti,
    revoke_all_for_user,
    revoke_family,
    revoke_jti,
)
from schemas import LoginRequest, MfaCodeRequest, SessionResponse
from session_issue import issue_user_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _raise_service_unavailable(exc: BaseException, *, log_message: str) -> None:
    logger.exception(log_message)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=app_config.public_service_unavailable_detail(exc),
    ) from exc


async def _audit_login(
    db: AsyncSession,
    *,
    request: Request,
    action: str,
    login_kind: str,
    username: str,
    user: User | None = None,
    detail: dict | None = None,
) -> None:
    payload = {"login_kind": login_kind, "username": username}
    if detail:
        payload.update(detail)
    await record_audit(
        db,
        user=user,
        action=action,
        resource_type="auth",
        resource_id=login_kind,
        detail=payload,
        request=request,
    )


async def _verify_credentials(
    body: LoginRequest,
    db: AsyncSession,
    request: Request,
    *,
    expected_role: UserRole,
    login_kind: str,
    wrong_role_detail: str,
) -> User:
    await assert_not_locked(db, body.username)

    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if user is None or not auth_core.verify_password(body.password, user.password_hash):
        await record_failed_login(db, body.username)
        await _audit_login(
            db,
            request=request,
            action="login_failed",
            login_kind=login_kind,
            username=body.username,
            detail={"reason": "invalid_credentials"},
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        await _audit_login(
            db,
            request=request,
            action="login_failed",
            login_kind=login_kind,
            username=body.username,
            user=user,
            detail={"reason": "inactive"},
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    nr = normalize_user_role(user.role)
    if nr != expected_role:
        await record_failed_login(db, body.username)
        await _audit_login(
            db,
            request=request,
            action="login_failed",
            login_kind=login_kind,
            username=body.username,
            user=user,
            detail={"reason": "wrong_role"},
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=wrong_role_detail)

    await clear_login_lockout(db, body.username)
    return user


@router.get("/session", response_model=SessionResponse)
async def get_session(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(auth_core.require_authenticated)],
) -> SessionResponse:
    nr = normalize_user_role(user.role)
    role = nr.value if nr else "user"
    return SessionResponse(role=role, username=user.username)


@router.post("/login", response_model=SessionResponse)
async def login_user(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    _rate: None = auth_login_limit,
) -> SessionResponse:
    try:
        user = await _verify_credentials(
            body,
            db,
            request,
            expected_role=UserRole.user,
            login_kind="form_user",
            wrong_role_detail="This login is for form users only",
        )
        await _audit_login(
            db,
            request=request,
            action="login_success",
            login_kind="form_user",
            username=user.username,
            user=user,
        )
        session = await issue_user_session(db, response, user, role=UserRole.user)
        await db.commit()
        return session
    except HTTPException:
        raise
    except (SQLAlchemyError, ConnectionError, TimeoutError) as exc:
        _raise_service_unavailable(exc, log_message="Database error during form login")
    except Exception as exc:
        _raise_service_unavailable(exc, log_message="Unexpected error during form login")


@router.post("/admin/login", response_model=SessionResponse)
async def login_admin(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    _rate: None = auth_login_limit,
) -> SessionResponse:
    assert_admin_ip_allowed(request)
    try:
        user = await _verify_credentials(
            body,
            db,
            request,
            expected_role=UserRole.admin,
            login_kind="admin",
            wrong_role_detail="This login is for administrators only",
        )

        if app_config.admin_mfa_required():
            if not getattr(user, "mfa_enabled", False) or not user.mfa_secret_enc:
                secret = mfa_core.generate_totp_secret()
                setup_token = auth_core.create_mfa_setup_token(
                    username=user.username,
                    uid=user.id,
                    setup_secret=secret,
                )
                set_mfa_setup_cookie(response, setup_token)
                await db.commit()
                return SessionResponse(
                    role=UserRole.admin.value,
                    username=user.username,
                    mfa_setup_required=True,
                    provisioning_uri=mfa_core.provisioning_uri(secret=secret, username=user.username),
                )

            pending = auth_core.create_mfa_pending_token(username=user.username, uid=user.id)
            set_mfa_pending_cookie(response, pending)
            await db.commit()
            return SessionResponse(
                role=UserRole.admin.value,
                username=user.username,
                mfa_required=True,
            )

        await record_admin_login(db, user=user, request=request)
        session = await issue_user_session(db, response, user, role=UserRole.admin)
        await db.commit()
        return session
    except HTTPException:
        raise
    except (SQLAlchemyError, ConnectionError, TimeoutError) as exc:
        _raise_service_unavailable(exc, log_message="Database error during admin login")
    except Exception as exc:
        _raise_service_unavailable(exc, log_message="Unexpected error during admin login")


@router.post("/admin/mfa/verify", response_model=SessionResponse)
async def verify_admin_mfa(
    body: MfaCodeRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    _rate: None = auth_login_limit,
) -> SessionResponse:
    assert_admin_ip_allowed(request)
    token = get_mfa_pending_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MFA session expired")

    try:
        payload = decode_mfa_pending_token(token)
        if payload.get("typ") != "mfa_pending":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA session")
        uid = int(payload["uid"])
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA session") from exc

    user = await db.get(User, uid)
    if user is None or not getattr(user, "mfa_enabled", False) or not user.mfa_secret_enc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MFA not configured")

    secret = mfa_core.decrypt_mfa_secret(user.mfa_secret_enc)
    if not mfa_core.verify_totp(secret, body.code):
        await _audit_login(
            db,
            request=request,
            action="login_failed",
            login_kind="admin",
            username=user.username,
            user=user,
            detail={"reason": "invalid_mfa"},
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication code")

    clear_mfa_cookies(response)
    await record_admin_login(db, user=user, request=request)
    session = await issue_user_session(db, response, user, role=UserRole.admin)
    await db.commit()
    return session


@router.post("/admin/mfa/confirm", response_model=SessionResponse)
async def confirm_admin_mfa_setup(
    body: MfaCodeRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    _rate: None = auth_login_limit,
) -> SessionResponse:
    assert_admin_ip_allowed(request)
    token = get_mfa_setup_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MFA setup session expired")

    try:
        payload = auth_core.decode_token(token)
        if payload.get("typ") != "mfa_setup":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA setup session")
        uid = int(payload["uid"])
        setup_secret = str(payload.get("mfa_secret") or "")
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA setup session") from exc

    if not setup_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing MFA secret")

    user = await db.get(User, uid)
    if user is None or normalize_user_role(user.role) != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin account required")

    if not mfa_core.verify_totp(setup_secret, body.code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication code")

    user.mfa_secret_enc = mfa_core.encrypt_mfa_secret(setup_secret)
    user.mfa_enabled = True
    clear_mfa_cookies(response)
    await record_admin_login(db, user=user, request=request)
    session = await issue_user_session(db, response, user, role=UserRole.admin)
    await db.commit()
    return session


@router.post("/refresh", response_model=SessionResponse)
async def refresh_session(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionResponse:
    token = get_refresh_token_from_request(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required")

    try:
        payload = auth_core.decode_token(token)
        if payload.get("typ") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        jti = str(payload.get("jti") or "")
        family_id = str(payload.get("fid") or "")
        uid = int(payload["uid"])
        role = str(payload.get("role") or "")
        tv = int(payload.get("tv") or 1)
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    row = await get_active_session(db, jti)
    if row is None:
        if family_id:
            await revoke_family(db, family_id)
            await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

    user = await db.get(User, uid)
    if user is None or (getattr(user, "token_version", 1) or 1) != tv:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

    await revoke_jti(db, jti)
    new_jti_value = new_jti()
    access = auth_core.create_access_token(
        username=user.username,
        uid=user.id,
        role=role,
        token_version=tv,
    )
    refresh = auth_core.create_refresh_token(
        username=user.username,
        uid=user.id,
        role=role,
        token_version=tv,
        jti=new_jti_value,
        family_id=family_id or row.family_id,
    )
    await create_refresh_session(
        db,
        user=user,
        refresh_token=refresh,
        jti=new_jti_value,
        family_id=family_id or row.family_id,
    )
    if app_config.use_cookie_auth():
        from cookie_auth import set_session_cookies

        set_session_cookies(response, access_token=access, refresh_token=refresh, role=role)
    await db.commit()
    return SessionResponse(role=role, username=user.username, access_token=access)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(auth_core.require_authenticated)],
) -> dict[str, bool]:
    await revoke_all_for_user(db, user.id)
    user.token_version = (getattr(user, "token_version", 1) or 1) + 1
    clear_session_cookies(response)
    clear_mfa_cookies(response)
    await db.commit()
    return {"logged_out": True}
