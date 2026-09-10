# cmsc128-lab1_CRUD_briz
Full-stack App for my individual software engineering laboratory project

## Run the app

Start the backend, database, and frontend with:

```bash
docker compose up -d --build
```

Open the task manager at <http://localhost:5173>. The API is available at <http://localhost:8000/docs>.

The frontend supports task creation and editing, completion toggles, tag and priority filters, sorting by date added, due date, priority, or tag, delete confirmation, and a timed Undo action after deletion.
