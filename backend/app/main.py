import json
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth_routes import router as auth_router
from app.api.v1.routes import router
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(
    title="AegisOps AI API",
    version="0.1.0",
    description="Local incident investigation API with operator and reviewer roles.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(auth_router)
app.include_router(router)

logger = logging.getLogger("aegisops.request")
logging.basicConfig(level=logging.INFO, format="%(message)s")


@app.middleware("http")
async def request_log(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    logger.info(
        json.dumps(
            {
                "event": "http_request",
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.monotonic() - start) * 1000, 1),
            }
        )
    )
    return response
