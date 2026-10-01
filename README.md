# Daymark — Academic Task Manager

Daymark extends the Activity 1 To-Do application with Activity 2 accounts: registration, login, persistent sessions, logout, profile editing, password changes, and password recovery through real SMTP email.

The app uses **vanilla JavaScript and Vite**, **FastAPI**, **SQLAlchemy/Alembic**, and **PostgreSQL 16**. It retains task creation, editing, completion, filtering, sorting, deletion, and timed undo. All task operations require login. Tasks are currently **shared among signed-in users**; owner-based access control belongs to the next activity.

Activity 2 work is on **`act2-accounts`** in the same public Activity 1 repository. This is an individual submission.

## Run with Docker

Requirements: Docker Engine and Docker Compose v2. For real recovery email, also prepare an SMTP account and an authorized sender address.

1. Copy `.env.example` to `.env`.
2. Set `POSTGRES_PASSWORD` and `DATABASE_URL`. The URL format is `postgresql+psycopg://USER:URL_ENCODED_PASSWORD@postgres:5432/DATABASE`; use the same user, password, and database as the PostgreSQL variables. URL-encode special characters in the password. `.env` is ignored by Git.
3. Start the app:

   ```bash
   docker compose up -d --build
   ```

   If your installed Compose version crashes in its Bake integration, use `COMPOSE_BAKE=false docker compose up -d --build`.
4. Open <http://localhost:5173>. Register an account, then log in. Successful login opens Profile with `Hello, <display name>`.

Other addresses: API documentation <http://localhost:8000/docs>, health check <http://localhost:8000/health>. The health check is public; account data and task routes enforce authentication on the server.

The backend applies Alembic migrations automatically before starting. PostgreSQL stores its data in the `postgres_data` Docker volume, which survives backend restarts and `docker compose down`. No account seeding is necessary; register through the UI. Do not remove that volume if you want to retain data.

```bash
# Inspect logs or stop services
docker compose logs -f backend frontend
docker compose down

# Run an added migration without rebuilding
docker compose exec backend alembic upgrade head
```

## Live development

Both source folders are bind-mounted into their running containers. Frontend saves trigger Vite updates; backend Python saves trigger Uvicorn reloads. File polling supports Docker/WSL. Frontend dependencies reside in a separate Docker volume.

- Backend dependency/Dockerfile changes: `docker compose up -d --build --no-deps backend`.
- Frontend dependency changes: `docker compose exec frontend npm ci`, then `docker compose restart frontend`.
- Compose or `.env` changes: `docker compose up -d` to recreate affected containers. A simple restart does not reload Compose environment values.

## Authentication design

**Passwords:** `pwdlib` hashes passwords with Argon2id and a random salt. New passwords contain 15–128 characters; spaces and Unicode are allowed and passwords are never trimmed. Email addresses are trimmed, lowercased, validated, and database-unique. Display names contain 1–100 trimmed characters. Public user responses contain only ID, email, and display name. Validation responses omit the submitted input, and secret fields use Pydantic `SecretStr`.

**Sessions:** login generates a random 256-bit token. The database stores only its SHA-256 hash and expiry; the browser receives the raw token in a host-only, `HttpOnly`, `SameSite=Lax` cookie scoped to `/`. The default lifetime is 30 days. Refreshing, browser history, browser reopening, and backend restarts do not invalidate an unexpired session. Logout deletes its database record and clears the cookie. Password changes/resets revoke every session belonging to that user. Ordinary profile changes preserve the session.

**Request protection:** every POST/PATCH/PUT/DELETE needs `X-Requested-With: Daymark`; any supplied Origin must match the configured allowlist, and nonempty bodies must be JSON. The frontend adds the header automatically. CLI clients may omit Origin but still need the custom header. No permissive credentialed CORS is enabled. Account responses and authentication failures use `Cache-Control: no-store`.

**Deployment:** local defaults allow only loopback origins with `SESSION_COOKIE_SECURE=false`. HTTPS deployment requires `SESSION_COOKIE_SECURE=true` and exact HTTPS `ALLOWED_ORIGINS`, comma-separated without paths or wildcards. `PUBLIC_FRONTEND_URL` must match an allowed origin when SMTP is configured. Serve frontend and `/api` through the same origin; Vite's development proxy is not production hosting.

**Rate limits:** login defaults to 10 attempts and recovery to 3 attempts per 60 seconds per peer IP. Limits return HTTP 429 and `Retry-After`. Counters are bounded, per-process, and reset on restart; multiple workers require a shared rate-limit store. Vite-proxied clients share the proxy's peer IP. Caller-supplied forwarding headers are not used by the limiter.

**Frontend:** startup checks `/auth/me` before displaying protected content. History restoration and returning to the page recheck the session. Network errors offer retry without pretending the user logged out. Logout clears task/account state and timers. Profile navigation warns about unsaved changes. Saving profile details preserves any unsaved password-form input.

## Configure real password-reset email

Set these values in `.env` using your provider's SMTP documentation:

| Variable | Purpose |
|---|---|
| `SMTP_HOST` | Provider's SMTP hostname |
| `SMTP_PORT` | Usually 587 for STARTTLS or 465 for implicit TLS |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | SMTP credentials; use a provider-issued credential/app password where required |
| `SMTP_FROM` | Sender email address authorized by the provider |
| `SMTP_TLS_MODE` | `starttls` or `ssl`; plaintext transport is unsupported |
| `SMTP_TIMEOUT_SECONDS` | Bounded connection/operation timeout; default 10 |
| `PUBLIC_FRONTEND_URL` | Address the email recipient can open; default `http://localhost:5173` |
| `RESET_TOKEN_TTL_MINUTES` | Reset lifetime; default 30 |

Recreate the backend with `docker compose up -d --no-deps backend`. Use **Forgot password**, enter the account's email, and open the received link on a device that can reach `PUBLIC_FRONTEND_URL`. A localhost link works only on the machine running the app.

For existing and unknown addresses, the request returns the same acknowledgment. A background task creates a random reset token, stores only its SHA-256 hash, and sends the link over SMTP. The token appears in a URL fragment, is removed from the address bar after capture, and is submitted only in the reset request body. It is never returned in an API response, persisted in browser storage, or printed in application logs.

Reset consumption, password update, and session revocation happen in one transaction. User row locks plus conditional token consumption prevent simultaneous reuse. A successful reset invalidates all other reset links, and a new password must differ from the current one. Changing the account email invalidates links previously sent to the old address.

Without SMTP settings, recovery returns an explicit 503 instead of pretending to send email. SMTP delivery failures are logged without sensitive exception details, and undelivered tokens are removed where possible. Delivery uses an in-process background task, not a durable queue: a process interruption may lose delivery. Check spam/configuration and request another link if needed. No console-token or demo-inbox fallback is enabled.

## API reference

The browser calls these paths with an `/api` prefix through Vite. Direct backend calls omit `/api`. Authentication uses cookies, not bearer headers.

| Method and path | Request / result |
|---|---|
| `POST /auth/register` | `email`, `display_name`, `password`; returns public user, 201; then log in |
| `POST /auth/login` | `email`, `password`; sets session cookie and returns public user |
| `GET /auth/me` | Current public user; 401 without a valid session |
| `POST /auth/logout` | Revokes current session; idempotent 204 |
| `PATCH /users/me` | `display_name` and/or `email`; `current_password` required when email changes |
| `POST /auth/change-password` | `current_password`, `new_password`; revokes all sessions; 204 |
| `POST /auth/forgot-password` | `email`; generic acknowledgment, 202 |
| `POST /auth/reset-password` | `token`, `new_password`; consumes link and revokes sessions; 204 |
| `GET /todos` | Authenticated shared tasks; optional `tag`, `priority`, `sort_by`, `sort_order` |
| `GET /todos/{id}` | Authenticated task detail |
| `POST /todos` | `title`, optional `description`, `due_date`, `priority`, `tag` |
| `PATCH /todos/{id}` | Any supported task fields, including `completed` |
| `DELETE /todos/{id}` | Soft-delete, 204; `X-Undo-Window-Seconds` reports the undo window |
| `POST /todos/{id}/restore` | Restore within the undo window |

Task priorities: `low`, `medium`, `high`. Sort fields: `date_added`, `due_date`, `priority`, `tag`; order: `asc` or `desc`. Expired soft-deleted tasks are purged during normal task access.

For example, after logging in with a CLI cookie jar:

```bash
curl -b /tmp/daymark-cookies http://localhost:8000/auth/me
curl -b /tmp/daymark-cookies 'http://localhost:8000/todos?sort_by=priority&sort_order=desc'
curl -b /tmp/daymark-cookies -X POST http://localhost:8000/auth/logout \
  -H 'X-Requested-With: Daymark'
```

When using curl to log in, use `-c /tmp/daymark-cookies`, the custom header above, `Content-Type: application/json`, and a JSON body containing your registered email/password. Avoid putting real credentials or cookie jars in the repository or screenshots. Direct Swagger mutations also require the custom header; the browser UI or a configured API client is the simplest demonstration.

## Tests and CI

```bash
# Backend unit/API tests (SQLite; isolated from development data)
docker compose exec backend pytest tests -q

# Frontend behavior tests and production build
docker compose exec frontend npm test
docker compose exec frontend npm run build
```

PostgreSQL integration tests additionally cover migration upgrade/downgrade, task preservation, constraints, fresh-process session persistence, and concurrent reset consumption. They create and remove uniquely named temporary databases. Enable them with a PostgreSQL role allowed to create databases:

```bash
docker compose exec backend sh -c 'POSTGRES_TEST_URL="$DATABASE_URL" pytest tests -q'
```

Without `POSTGRES_TEST_URL`, those integration tests explicitly skip. Mock SMTP tests verify delivery boundaries without sending mail; a real-inbox test is still necessary before defense. GitHub Actions runs backend tests with PostgreSQL plus frontend tests/build for `main` and `act2-accounts`.

## Database inspection and defense

The PostgreSQL image includes **psql**, so the required inspection tool is available without installing another service:

```bash
docker compose exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Inside psql:

```sql
\dt
SELECT id, email, display_name, left(password_hash, 10) || '…' AS hash_prefix,
       created_at, updated_at
FROM users ORDER BY id;
SELECT user_id, created_at, expires_at FROM auth_sessions ORDER BY id;
SELECT user_id, expires_at, consumed_at FROM password_reset_tokens ORDER BY id;
\q
```

The password representation begins with an Argon2 identifier; it is not reversible plaintext. Do not display raw session/reset tokens during defense. Re-run the account query after a browser refresh and backend restart to demonstrate persistence.

Use [the defense checklist](docs/DEFENSE_CHECKLIST.md) to rehearse the required live flows and source-code explanations. The final submission checkpoint must use the lab-prescribed commit message `cmsc128-Indiv-Act2`; normal development commits use Conventional Commits. Submit the public repository URL and the `act2-accounts` branch. The live defense and its deadline remain the student's responsibility.

## Project map

- `backend/app/api/`: account/task routes and authenticated-user dependency.
- `backend/app/services/`: account transactions, session lifecycle, SMTP delivery, reset consumption, task operations.
- `backend/app/core/`: settings, password/token helpers, request protection, throttling.
- `backend/app/db/models/` and `backend/migrations/`: durable data model and schema history.
- `frontend/src/accountApp.js`: navigation, account form orchestration, session restoration.
- `frontend/src/components/`: account views and task presentation.
- `frontend/src/api/`: shared HTTP client and endpoint wrappers.
- `backend/tests/` and frontend `*.test.js`: behavior and regression coverage.

Design references: [FastAPI password hashing](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/), [OWASP sessions](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [OWASP CSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html), [OWASP password recovery](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html).
