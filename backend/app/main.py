from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from app.core.request_security import protect_requests, safe_validation_error
from app.api.routes.auth import router as auth_router
from app.api.routes.users import router as users_router
from app.api.routes.todos import router as todos_router

app = FastAPI(
    title="Academic Task Manager API",
    version="0.1.0",
)


app.middleware("http")(protect_requests)
app.add_exception_handler(RequestValidationError, safe_validation_error)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(todos_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}


