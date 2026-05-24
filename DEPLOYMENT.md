# Deployment checklist

## Before go-live

- [ ] Run database migration: `alembic upgrade head` (includes login lockouts table `20260523_0009`)
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `SECRET_KEY` to a unique 32+ character random value (never use Docker defaults)
- [ ] Set `CORS_ORIGINS` to your real frontend URL(s) only
- [ ] Set `ALLOW_DEFAULT_USER_SEED=false`
- [ ] Change admin and form shared passwords via the admin UI
- [ ] Run `alembic upgrade head` on the production database
- [ ] Terminate TLS (HTTPS) at your reverse proxy or load balancer
- [ ] Enable HSTS in `frontend/nginx.conf` when HTTPS is active
- [ ] Configure Postgres backups (`pg_dump` schedule or managed DB backups)
- [ ] Restrict Postgres port (do not expose 5433 publicly)
- [ ] Run `npm audit` and `pip audit` / review dependency advisories
- [ ] Point monitoring at `GET /health` (expect `database: ok`)

## Docker production example

Copy `.env.production.example` and set real values, then:

```bash
export SECRET_KEY="$(openssl rand -hex 32)"
export ENVIRONMENT=production
export CORS_ORIGINS=https://forms.example.org
export ALLOW_DEFAULT_USER_SEED=false

docker compose up -d --build
```

**Local dev with Postgres on host port 5433** (optional):

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

Production compose does **not** publish Postgres to the host by default.

## Backups

Example daily backup (adjust paths and credentials):

```bash
pg_dump -h localhost -p 5433 -U postgres hatecrime | gzip > hatecrime-$(date +%F).sql.gz
```

Store backups off-server with retention (e.g. 30 days).

## Monitoring

- Health: `GET /health` → `{"status":"ok","database":"ok"}`
- Application logs: `docker compose logs -f api`
- Optional: forward logs to your platform (CloudWatch, Datadog, etc.)

## Logging

The API does **not** write log files inside the app. All logs go to **stdout** as structured JSON in production (or plain text in development).

| Variable | Default (dev) | Production suggestion |
|----------|---------------|------------------------|
| `LOG_LEVEL` | `DEBUG` | `INFO` |
| `LOG_FORMAT` | `text` | `json` |

Each HTTP request gets an **`X-Request-ID`** header (or pass your own). The same ID appears in every log line for that request, so you can trace a single submission end-to-end.

Example JSON access log line:

```json
{"timestamp":"2026-05-16T12:00:00+00:00","level":"INFO","logger":"hatecrime.access","message":"request completed","request_id":"a1b2c3d4-...","method":"POST","path":"/responses/submit","status_code":200,"duration_ms":42.5,"client_ip":"172.18.0.1","environment":"production"}
```

View logs:

```bash
docker compose logs -f api
docker compose logs -f web
```

### Docker log rotation

`docker-compose.yml` configures the **json-file** driver with `max-size: 10m` and `max-file: 5` (~50 MB per service on the host). Logs remain on the Docker host under `/var/lib/docker/containers/…`; they are not inside the application image.

For centralized logging, point your platform at container stdout or use a logging driver such as `awslogs`, `gcplogs`, or Fluent Bit.

Sensitive fields in log messages (passwords, Bearer tokens) are **redacted** when detected in the message text.

## Phase 2+ features (in application)

- **Analytics** uses batched queries (`analytics_aggregate.py`) instead of per-question DB round-trips.
- **Audit log:** Admin → **Audit log** tab, or `GET /admin/audit-events`. Logs form edits (create/update/reorder/delete), credentials, exports, and response deletes.
- **Export:** Admin → Data actions → Export all responses (JSON), or `GET /responses/export`.
- **Token revocation:** Changing a password increments `token_version`; old JWTs are rejected.
- **Consent:** Set `CONSENT_REQUIRED=true` and build frontend with `VITE_CONSENT_REQUIRED=true`.
- **Retention:** `python backend/scripts/purge_retention.py --dry-run` then `--commit`.
- **Backups:** `scripts/backup-db.ps1` (host with Docker access to Postgres).
- **Load smoke test:** `k6 run scripts/load-test/k6_submit.js` (optional k6 install).
- **Redis rate limits (optional):** set `REDIS_URL` when running multiple API replicas.
- **Production compose:** `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`

## Security notes

- JWTs are stored in `localStorage` on the client; protect against XSS in any custom scripts you add.
- Rate limits apply to login, form submit, `/form/flow`, `/form/pages*`, and admin read/write endpoints (in-memory per server instance; use `REDIS_URL` for multiple replicas).
- **Login lockout:** After `LOGIN_MAX_FAILURES` (default 5) failed attempts per username, login is blocked for `LOGIN_LOCKOUT_MINUTES` (default 15). Run migration `20260523_0009`.
- **Login audit:** Success and failure events appear in the audit log (`login_success`, `login_failed`).
- **Submit audit:** Each submission logs `submit_response` (metadata only, not answer text).
- **Request body cap:** API rejects bodies over `MAX_REQUEST_BODY_BYTES` (default 1 MiB); nginx `client_max_body_size 1m`.
- **Least-privilege DB (optional):** `scripts/postgres-app-user.sql` — create `hatecrime_app` and point `DATABASE_URL` at it.
- API `/docs` and OpenAPI schema are disabled when `ENVIRONMENT=production`.
- No file uploads are implemented; if added later, validate type and size server-side.
- CI runs `pytest`, `npm audit`, `pip audit`, and `gitleaks` (see `.github/workflows/ci.yml`).

## Phase 2 — cookie sessions, MFA, refresh (application)

- **HttpOnly cookies** for access (`hc_access`) and refresh (`hc_refresh`) when `USE_COOKIE_AUTH=true`.
- **CSRF:** mutating requests with a session cookie require header `X-CSRF-Token` matching cookie `hc_csrf`.
- **Admin MFA (TOTP):** required when `ADMIN_MFA_REQUIRED=true` (default in production). First login returns a provisioning URI; confirm with `POST /auth/admin/mfa/confirm`. Later logins use `POST /auth/admin/mfa/verify`.
- **Shorter admin JWT:** `ACCESS_TOKEN_EXPIRE_MINUTES_ADMIN` (default 15).
- **Refresh rotation:** `POST /auth/refresh` revokes the previous refresh token and issues new cookies.
- **Logout:** `POST /auth/logout` clears cookies and revokes refresh tokens (`token_version` incremented).
- **New IP alert:** audit event `admin_login_new_ip` and optional `ADMIN_LOGIN_WEBHOOK_URL`.
- **Admin IP allowlist (optional):** `ADMIN_IP_ALLOWLIST=ip1,ip2` blocks other IPs on admin login and admin APIs.
- Run migration `20260524_0010` after deploy.
