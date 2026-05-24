from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import auth as auth_core
from audit_log import record_audit
from database import get_db
from rate_limit import admin_read_limit, admin_write_limit
from models import AuditEvent, User, UserRole
from schemas import AuditEventRead, FormAccessRead, FormAccessUpdate

router = APIRouter(prefix="/admin", tags=["admin"])


async def _shared_form_user(db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.role == UserRole.user).order_by(User.id))
    row = result.scalars().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shared form user not found")
    return row


async def _admin_user(db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.role == UserRole.admin).order_by(User.id))
    row = result.scalars().first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found")
    return row


async def _update_access_user(
    row: User,
    body: FormAccessUpdate,
    db: AsyncSession,
    *,
    actor: User | None = None,
    request: Request | None = None,
    audit_action: str | None = None,
) -> FormAccessRead:
    data = body.model_dump(exclude_unset=True)
    if not data:
        return FormAccessRead(username=row.username, is_active=row.is_active)

    next_username = data.get("username")
    if next_username is not None:
        next_username = next_username.strip()
        if not next_username:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username cannot be empty")
        existing = await db.execute(select(User).where(User.username == next_username, User.id != row.id))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username is already in use")
        row.username = next_username

    next_password = data.get("password")
    password_changed = False
    if next_password is not None:
        row.password_hash = auth_core.get_password_hash(next_password)
        row.token_version = (getattr(row, "token_version", 1) or 1) + 1
        password_changed = True

    if actor is not None and audit_action:
        await record_audit(
            db,
            user=actor,
            action=audit_action,
            resource_type="user",
            resource_id=str(row.id),
            detail={
                "username": row.username,
                "password_changed": password_changed,
                "username_changed": "username" in data,
            },
            request=request,
        )

    await db.commit()
    await db.refresh(row)
    return FormAccessRead(username=row.username, is_active=row.is_active)


@router.get("/form-access", response_model=FormAccessRead)
async def get_form_access(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_read_limit,
) -> FormAccessRead:
    row = await _shared_form_user(db)
    return FormAccessRead(username=row.username, is_active=row.is_active)


@router.patch("/form-access", response_model=FormAccessRead)
async def update_form_access(
    body: FormAccessUpdate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_write_limit,
) -> FormAccessRead:
    row = await _shared_form_user(db)
    return await _update_access_user(
        row,
        body,
        db,
        actor=admin,
        request=request,
        audit_action="update_form_access",
    )


@router.get("/admin-access", response_model=FormAccessRead)
async def get_admin_access(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_read_limit,
) -> FormAccessRead:
    row = await _admin_user(db)
    return FormAccessRead(username=row.username, is_active=row.is_active)


@router.patch("/admin-access", response_model=FormAccessRead)
async def update_admin_access(
    body: FormAccessUpdate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_write_limit,
) -> FormAccessRead:
    row = await _admin_user(db)
    return await _update_access_user(
        row,
        body,
        db,
        actor=admin,
        request=request,
        audit_action="update_admin_access",
    )


@router.get("/audit-events", response_model=list[AuditEventRead])
async def list_audit_events(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(auth_core.require_admin)],
    __rate: None = admin_read_limit,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[AuditEvent]:
    result = await db.execute(
        select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
