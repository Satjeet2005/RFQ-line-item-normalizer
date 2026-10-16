import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from app.api.routes import router
from app.core.errors import APIError, format_error_response
from app.core.logging import logger
from app.db.seed import seed_catalog
from app.db.session import SessionLocal
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Idempotent catalog seeding on startup
    db = SessionLocal()
    try:
        seed_catalog(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title="RFQ Line-Item Normalizer API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Items-Excluded"],
)

@app.middleware("http")
async def request_id_and_logging_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = req_id

    start_time = time.time()
    try:
        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = req_id

        logger.info(
            f"{request.method} {request.url.path} {response.status_code}",
            extra={
                "request_id": req_id,
                "extra_data": {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                },
            },
        )
        return response
    except Exception as exc:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(
            f"Unhandled error processing {request.method} {request.url.path}: {exc}",
            exc_info=True,
            extra={
                "request_id": req_id,
                "extra_data": {
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            },
        )
        return format_error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="An internal server error occurred",
            request_id=req_id,
        )

@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return format_error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request_id=req_id,
        details=exc.details,
        extra_body=exc.extra_body,
    )

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    details: list[dict[str, Any]] = []
    for err in exc.errors():
        field_loc = " -> ".join([str(loc_item) for loc_item in err.get("loc", []) if loc_item != "body"])
        details.append({
            "field": field_loc,
            "code": "VALIDATION_ERROR",
            "message": err.get("msg", "Invalid value"),
        })

    return format_error_response(
        status_code=422,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        request_id=req_id,
        details=details,
    )

# Include API routes
app.include_router(router)
