# Daymark — Academic Task Manager

Daymark merges the Activity 1 To-Do application with Activity 2 accounts (registration, login, persistent sessions, profile, password change and recovery) and adds Activity 3 **user-based access control (UBAC)**: every user creates, views, updates, and deletes only their own tasks, plus tasks in collaborative lists they own or were added to.

The app uses **vanilla JavaScript and Vite**, **FastAPI**, **SQLAlchemy/Alembic**, and **PostgreSQL 16**. It retains task creation, editing, completion, filtering, sorting, deletion, and timed undo. After login the user lands directly on their personal To-Do list and can switch to collaborative lists.

Activity 3 work is on **`act3-ubac`** in the same public repository (Activity 2: `act2-accounts`). This is an individual submission.

## Activity 3: how Activities 1 and 2 were merged

- Activity 1 (CRUD) lives on `main`. Activity 2 was developed on `act2-accounts`, branched from that CRUD code, and merged back into `main` through pull request #10. That merge applied cleanly: Activity 2 changed the task code only to require a signed-in session (`dependencies=[Depends(get_current_user)]` on the task router), so Git reported no conflicts.
- `act3-ubac` was created from `act2-accounts` and `main` was merged into it with `git merge --no-ff main`, recording an explicit merge commit as the integration point. There were again no textual conflicts.
- The real integration work was **semantic**, not textual: the merged code authenticated users but did not know *who* owned a task. Activity 3 resolves that by adding `todos.user_id`, passing the signed-in user into every task route, and filtering every query by owner/membership. Each step is a separate commit on `act3-ubac`.

## Schema

```
users ─┬─< auth_sessions            (user_id FK, CASCADE)        Activity 2
       ├─< password_reset_tokens    (user_id FK, CASCADE)        Activity 2
       ├─< todos.user_id            (owner/creator, NOT NULL)    Activity 3
       ├─< task_lists.owner_id      (list owner, NOT NULL)       Activity 3
       └─< list_members.user_id     (added members)              Activity 3

task_lists ─┬─< list_members.list_id   PK (list_id, user_id)
            └─< todos.list_id          NULL = owner's personal list
```

| Table | Purpose | Key constraints |
|---|---|---|
| `users` | Accounts (Argon2id `password_hash`, never plaintext) | unique `email` |
| `todos` | Tasks | `user_id` → `users.id` NOT NULL; `list_id` → `task_lists.id` nullable; both `ON DELETE CASCADE`, indexed |
| `task_lists` | Collaborative lists | `owner_id` → `users.id` NOT NULL |
| `list_members` | Who was added to which list | composite primary key `(list_id, user_id)` prevents duplicates |

The schema is normalized: tasks store only the owner's ID, never their name or email, and a list's owner is stored once in `task_lists.owner_id` rather than duplicated as a member row. Migration `b23c45d67e89` adds `todos.user_id`; tasks created before it were shared by everyone and cannot be attributed to an owner, so that migration removes them instead of handing them to an arbitrary account. Migration `c34d56e78f90` adds the list tables.

## Access control (UBAC)

Authorization is enforced only on the backend; hiding buttons in the UI is a convenience, not a control.

1. `get_current_user` (`backend/app/api/dependencies.py`) turns the session cookie into a `User`, or answers 401.
2. Every task route receives that `user` and passes `user_id=user.id` to the service layer. The task router also keeps a router-level authentication dependency, so a route that forgot to ask for the user would still reject anonymous requests.
3. Every task query in `backend/app/services/todo_service.py` (list, detail, update, delete, restore) includes **one** filter, `_accessible_by(user_id)`:

   ```python
   or_(
       and_(Todo.list_id.is_(None), Todo.user_id == user_id),   # my personal tasks
       Todo.list_id.in_(accessible_list_ids(user_id)),          # lists I own or joined
   )
   ```

   `accessible_list_ids` (`backend/app/services/list_service.py`) is the single membership rule shared by list and task endpoints.
4. **IDOR prevention:** the ID in the URL is only ever looked up *together with* that filter. If account B requests account A's task `/todos/5`, the query matches no row and the route answers **404 "Todo not found"**, exactly as for a nonexistent ID, so B cannot even confirm the task exists. The same applies to `POST /todos/5/restore`.
5. Lists use **404** for lists you cannot see and **403** when a member attempts an owner-only action (adding/removing others, deleting the list).
6. A task's owner comes from the session, never from the request body. `list_id` can be set only at creation (after an access check) and cannot be changed by `PATCH`, so a task cannot be moved into someone else's list.
7. Access to collaborative-list tasks follows **membership, not authorship**: a removed member immediately loses access, including to tasks they created there.

`backend/tests/test_ubac.py` and `backend/tests/test_lists.py` sign in as two or three accounts and verify each rule above, including the Activity 3 "Nikko / Victor" scenario.

## Run with Docker

Requirements: Docker Engine and Docker Compose v2. For real recovery email, also prepare an SMTP account and an authorized sender address.

1. Copy `.env.example` to `.env`.
2. Set `POSTGRES_PASSWORD` and `DATABASE_URL`. The URL format is `postgresql+psycopg://USER:URL_ENCODED_PASSWORD@postgres:5432/DATABASE`; use the same user, password, and database as the PostgreSQL variables. URL-encode special characters in the password. `.env` is ignored by Git.
3. Start the app:

   ```bash
   docker compose up -d --build
   ```

   If your installed Compose version crashes in its Bake integration, use `COMPOSE_BAKE=false docker compose up -d --build`.
   If host port 5433 is already used by another project, choose a free one for this run, e.g. `POSTGRES_PORT=5434 docker compose up -d`. Inside Docker the backend always reaches PostgreSQL on port 5432.
4. Open <http://localhost:5173>. Register an account, then log in. Successful login opens that user's personal To-Do list.
5. Optional demo data: after registering the two demo accounts **through the registration page**, add sample personal tasks to them:

   ```bash
   docker compose exec backend python -m app.seed_tasks first@example.com second@example.com
   ```

   The seeder never creates accounts and skips tasks an account already has.

Other addresses: API documentation <http://localhost:8000/docs>, health check <http://localhost:8000/health>. The health check is public; account, task, and list routes enforce authentication and ownership on the server.

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
| `GET /todos` | Caller's personal tasks; `list_id` selects a collaborative list (404 unless owner/member); optional `tag`, `priority`, `sort_by`, `sort_order` |
| `GET /todos/{id}` | Task detail; 404 unless the task is accessible to the caller |
| `POST /todos` | `title`, optional `description`, `due_date`, `priority`, `tag`, `list_id`; owner is always the caller |
| `PATCH /todos/{id}` | Supported task fields, including `completed`; 404 unless accessible; `list_id` cannot be changed |
| `DELETE /todos/{id}` | Soft-delete, 204; 404 unless accessible; `X-Undo-Window-Seconds` reports the undo window |
| `POST /todos/{id}/restore` | Restore within the undo window; 404 unless accessible |
| `GET /lists` | Lists the caller owns or was added to, with `owner_name` and `is_owner` |
| `POST /lists` | `name` (1–100 characters); caller becomes owner |
| `DELETE /lists/{id}` | Owner only (403 for members, 404 for others); deletes its memberships and tasks |
| `GET /lists/{id}/members` | Owner and members (404 for others) |
| `POST /lists/{id}/members` | Owner only; `email` of a registered account; 404 unknown email, 409 already has access |
| `DELETE /lists/{id}/members/{user_id}` | Owner removes anyone; a member may remove only themselves (leave) |

Task priorities: `low`, `medium`, `high`. Sort fields: `date_added`, `due_date`, `priority`, `tag`; order: `asc` or `desc`. Expired soft-deleted tasks are purged during normal task access.

For example, after logging in with a CLI cookie jar:

```bash
curl -b /tmp/daymark-cookies http://localhost:8000/auth/me
curl -b /tmp/daymark-cookies 'http://localhost:8000/todos?sort_by=priority&sort_order=desc'
# Another account's task ID behaves exactly like a missing one:
curl -b /tmp/daymark-cookies -i http://localhost:8000/todos/999   # 404 {"detail":"Todo not found"}
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

UBAC tests (`test_ubac.py`, `test_lists.py`, `test_list_models.py`) act as several signed-in accounts against the same database and check that every task and list operation stays within the caller's own data.

PostgreSQL integration tests additionally cover migration upgrade/downgrade, removal of unattributable pre-ownership tasks, constraints, fresh-process session persistence, and concurrent reset consumption. They create and remove uniquely named temporary databases. Enable them with a PostgreSQL role allowed to create databases:

```bash
docker compose exec backend sh -c 'POSTGRES_TEST_URL="$DATABASE_URL" pytest tests -q'
```

Without `POSTGRES_TEST_URL`, those integration tests explicitly skip. Mock SMTP tests verify delivery boundaries without sending mail; a real-inbox test is still necessary before defense. GitHub Actions runs backend tests with PostgreSQL plus frontend tests/build for `main`, `act2-accounts`, and `act3-ubac`.

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

-- Tasks with their owner (joined; no password data selected)
SELECT t.id, t.title, t.completed, t.list_id, u.id AS owner_id, u.email AS owner
FROM todos t JOIN users u ON u.id = t.user_id
WHERE t.deleted_at IS NULL ORDER BY u.id, t.id;

-- Collaborative lists, owners, and members
SELECT l.id, l.name, o.email AS owner, m.email AS member
FROM task_lists l JOIN users o ON o.id = l.owner_id
LEFT JOIN list_members lm ON lm.list_id = l.id
LEFT JOIN users m ON m.id = lm.user_id ORDER BY l.id;
\q
```

The password representation begins with an Argon2 identifier; it is not reversible plaintext. Do not display raw session/reset tokens during defense. Re-run the account query after a browser refresh and backend restart to demonstrate persistence.

Use [the defense checklist](docs/DEFENSE_CHECKLIST.md) to rehearse the required live flows and source-code explanations. The final submission checkpoint uses the lab-prescribed commit message `cmsc128-Indiv-Act3-finalX`; normal development commits use Conventional Commits. Submit the public repository URL and the `act3-ubac` branch. The live defense and its deadline remain the student's responsibility.

## Project map

- `backend/app/api/`: account, task, and list routes and the authenticated-user dependency.
- `backend/app/services/`: account transactions, session lifecycle, SMTP delivery, reset consumption, owner-scoped task operations (`todo_service.py`), and list membership rules (`list_service.py`).
- `backend/app/seed_tasks.py`: optional demo-task seeder for already-registered accounts.
- `backend/app/core/`: settings, password/token helpers, request protection, throttling.
- `backend/app/db/models/` and `backend/migrations/`: durable data model and schema history.
- `frontend/src/accountApp.js`: navigation, account form orchestration, session restoration.
- `frontend/src/components/`: account views and task presentation.
- `frontend/src/handlers/`: task interactions (`taskHandlers.js`) and the list picker / member panel (`listHandlers.js`).
- `frontend/src/api/`: shared HTTP client and endpoint wrappers.
- `backend/tests/` and frontend `*.test.js`: behavior and regression coverage.

Design references: [OWASP Broken Access Control](https://owasp.org/Top10/A01_2021-Broken_Access_Control/), [OWASP IDOR prevention](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html), [FastAPI password hashing](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/), [OWASP sessions](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html), [OWASP CSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html), [OWASP password recovery](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html).
