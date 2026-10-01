from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import settings


async def protect_requests(request: Request, call_next):
    account_path = request.url.path.split("/")[1] in {"auth", "users"}
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if ((origin is not None and origin not in settings.trusted_origins)
                or request.headers.get("x-requested-with") != "Daymark"):
            return JSONResponse({"detail": "Request origin or security header is invalid"},
                                status_code=403, headers={"Cache-Control": "no-store"})
        # Bodyless DELETE/logout/restore requests are allowed; any body must be JSON.
        if await request.body() and request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
            return JSONResponse({"detail": "Request body must be JSON"}, status_code=415,
                                headers={"Cache-Control": "no-store"})
    response = await call_next(request)
    if account_path:
        response.headers["Cache-Control"] = "no-store"
    return response


async def safe_validation_error(request: Request, exc: RequestValidationError):
    # Pydantic's default error includes the submitted input (possibly passwords).
    errors = [{"loc": error["loc"], "msg": error["msg"], "type": error["type"]}
              for error in exc.errors()]
    return JSONResponse({"detail": errors}, status_code=422,
                        headers={"Cache-Control": "no-store"})
