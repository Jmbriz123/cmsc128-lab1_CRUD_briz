# Academic Task Manager

A full-stack todo application for managing academic tasks. It supports task creation, editing, completion tracking, due dates, priorities, tags, filtering, sorting, delete confirmation, and a timed Undo action.

## Technology Stack

- **Frontend:** Vite with vanilla JavaScript, HTML, and CSS. Vite keeps the client fast and lightweight while the application remains easy to run and inspect without a large UI framework.
- **Backend:** FastAPI with Python 3.12. FastAPI provides typed request validation, automatic OpenAPI documentation, and a small REST API suited to CRUD operations.
- **ORM and migrations:** SQLAlchemy and Alembic. SQLAlchemy keeps database access separate from HTTP routes, while Alembic version-controls schema changes.
- **Database:** PostgreSQL 16. PostgreSQL provides durable relational storage for tasks, indexed filtering fields, timestamps, and future expansion.
- **Local development:** Docker Compose runs the frontend, backend, and PostgreSQL together with consistent service names and health checks.
- **Testing:** pytest with an isolated SQLite test database, so the test suite does not modify development data.

## Requirements

For the recommended setup, install:

- Docker Engine
- Docker Compose v2

Node.js 22 and npm are only needed when developing the frontend outside Docker. Python 3.12 is only needed when running the backend outside Docker.

## Run Locally with Docker

1. Clone the repository and enter the project directory.

2. Create the environment file from the provided template:

	 ```bash
	 cp .env.example .env
	 ```

3. Build and start all services:

	 ```bash
	 docker compose up -d --build
	 ```

	 The backend applies pending Alembic migrations automatically before starting.

4. Open the application:

	 - Frontend: <http://localhost:5173>
	 - API documentation: <http://localhost:8000/docs>
	 - API health check: <http://localhost:8000/health>

5. View service logs when troubleshooting:

	 ```bash
	 docker compose logs -f backend
	 docker compose logs -f frontend
	 ```

6. Stop the services:

	 ```bash
	 docker compose down
	 ```

To remove the PostgreSQL volume and all stored development data, use `docker compose down -v`.

## Live Development in Docker

Both source directories are bind-mounted into their running containers. Saving frontend JavaScript, HTML, or CSS triggers Vite's browser updates; saving backend Python application files restarts Uvicorn automatically. Polling enables reliable file detection across Docker/WSL file systems. Frontend dependencies live in a separate Docker volume so host `node_modules` does not overwrite container dependencies.

To apply this configuration to existing containers once:

```bash
docker compose up -d --no-deps backend frontend
```

Subsequent source edits need no rebuild. Dependency and configuration changes may need an extra step:

- After changing backend requirements or its Dockerfile: `docker compose up -d --build --no-deps backend`.
- After changing frontend dependencies: `docker compose exec frontend npm ci`, then `docker compose restart frontend`.
- After adding database migrations: `docker compose exec backend alembic upgrade head`.
- After changing Compose settings: `docker compose up -d`.

## Authentication Security Foundation (Activity 2, Step 2)

The account database and security helpers are implemented. Registration/login/profile/recovery endpoints and screens are the next step; task endpoints are not yet login-gated.

- Password helpers use Argon2id through `pwdlib`. Registration validation accepts 15–128 characters, including spaces and Unicode, without trimming passwords. Emails are normalized and validated; display names are trimmed and limited to 100 characters. Public user responses expose only ID, email, and display name.
- Sessions use random 256-bit tokens, storing only SHA-256 token hashes in PostgreSQL. Helpers create, resolve, and revoke sessions; `get_current_user` rejects missing, expired, and revoked sessions. Sessions default to 30 days and survive process restarts because authentication state is stored in the database. The browser cookie is HttpOnly, SameSite=Lax, host-only, and scoped to `/`.
- `SESSION_COOKIE_SECURE=false` permits only localhost/loopback origins for development. For HTTPS deployment set it to `true` and set `ALLOWED_ORIGINS` to exact HTTPS origins (comma-separated, no paths or wildcards). Cookie security and allowed origins are validated together at startup.
- Every POST/PATCH/PUT/DELETE request must include `X-Requested-With: Daymark`. If an Origin header is present, it must match `ALLOWED_ORIGINS`. Nonempty request bodies must use `Content-Type: application/json`. The frontend sends the custom header automatically. No permissive credentialed CORS is enabled. Validation responses omit submitted input and account responses use `Cache-Control: no-store`.
- Login/recovery rate-limit dependencies are ready for the next step's endpoints: defaults are 10 login attempts and 3 recovery attempts per 60 seconds per peer IP. They return HTTP 429 with Retry-After. They do not yet apply to any route. Counters are bounded, in-memory, and reset on restart; multiple workers need shared storage. Requests through the Vite proxy share the proxy's peer IP; untrusted X-Forwarded-For headers are not used to identify clients.

Rebuild the backend after installing these dependencies:

```bash
docker compose up -d --build --no-deps backend
```

If the installed Compose version crashes in its Bake integration, use `COMPOSE_BAKE=false docker compose up -d --build --no-deps backend`.

Design references: [pwdlib](https://frankie567.github.io/pwdlib/reference/pwdlib/), [OWASP CSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).

## Run Tests

The backend test suite uses an isolated in-memory SQLite database and covers CRUD behavior, validation, filtering, sorting, and undo deletion.

Run it in the backend container:

```bash
docker compose exec backend pytest tests -q
```

The backend tests use SQLite and do not require PostgreSQL or Redis. Run the frontend workflow tests and production build locally:

```bash
cd frontend
npm ci
npm test
npm run build
```

## API Endpoints

The API is REST-based and uses JSON request and response bodies. The examples below assume the backend is available at `http://localhost:8000`.

### Create a task

```bash
curl -H "X-Requested-With: Daymark" -X POST http://localhost:8000/todos \
	-H 'Content-Type: application/json' \
	-d '{
		"title": "Finish literature review",
		"description": "Review and annotate three sources",
		"due_date": "2026-10-03T09:00:00",
		"priority": "high",
		"tag": "research"
	}'
```

`priority` accepts `low`, `medium`, or `high`. It defaults to `medium`. The backend records `created_at` automatically as the Date Added timestamp.

### List, filter, and sort tasks

```bash
# List all active tasks, newest added task last
curl 'http://localhost:8000/todos?sort_by=date_added&sort_order=asc'

# Filter by tag and priority
curl 'http://localhost:8000/todos?tag=research&priority=high'

# Sort by due date, priority, or tag
curl 'http://localhost:8000/todos?sort_by=due_date'
curl 'http://localhost:8000/todos?sort_by=priority&sort_order=desc'
curl 'http://localhost:8000/todos?sort_by=tag'
```

Supported `sort_by` values are `date_added`, `due_date`, `priority`, and `tag`. Supported `sort_order` values are `asc` and `desc`. Missing due dates and tags are placed last.

### Get one task

```bash
curl http://localhost:8000/todos/1
```

### Update a task

```bash
curl -H "X-Requested-With: Daymark" -X PATCH http://localhost:8000/todos/1 \
	-H 'Content-Type: application/json' \
	-d '{
		"completed": true,
		"priority": "medium"
	}'
```

PATCH updates only the supplied fields. The title cannot be blank, and an empty update is rejected.

### Delete and undo a task

```bash
# Soft-delete a task. The response is 204 and includes the undo duration header.
curl -i -H "X-Requested-With: Daymark" -X DELETE http://localhost:8000/todos/1

# Restore it during the undo window, currently 10 seconds.
curl -H "X-Requested-With: Daymark" -X POST http://localhost:8000/todos/1/restore
```

Deleted tasks are hidden from normal list and detail requests. After the undo window expires, the backend permanently purges them during normal todo access.

## Project Structure

```text
backend/
	app/              FastAPI application, routes, schemas, models, and services
	migrations/       Alembic migration scripts
	tests/            pytest API tests
frontend/
	src/              Vite application source and styles
docker-compose.yml  Local frontend, backend, and PostgreSQL services
```
