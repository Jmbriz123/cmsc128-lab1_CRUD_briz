from fastapi import FastAPI
from app.api.routes.todos import router as todos_router

app = FastAPI(
    title="Academic Task Manager API",
    version="0.1.0",
)


app,include_router(todos_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}


