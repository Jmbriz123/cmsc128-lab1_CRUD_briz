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

## Run Tests

The backend test suite uses an isolated in-memory SQLite database and covers CRUD behavior, validation, filtering, sorting, and undo deletion.

Run it in the backend container:

```bash
docker compose exec backend pytest tests -q
```

Run the frontend production build locally:

```bash
cd frontend
npm install
npm run build
```

## API Endpoints

The API is REST-based and uses JSON request and response bodies. The examples below assume the backend is available at `http://localhost:8000`.

### Create a task

```bash
curl -X POST http://localhost:8000/todos \
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
curl -X PATCH http://localhost:8000/todos/1 \
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
curl -i -X DELETE http://localhost:8000/todos/1

# Restore it during the undo window, currently 10 seconds.
curl -X POST http://localhost:8000/todos/1/restore
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
