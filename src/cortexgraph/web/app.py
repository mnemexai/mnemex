import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from ..storage.models import ErrorCode, ErrorContext, ErrorDetail, ErrorResponse
from .api import router as api_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # config = get_config()

    app = FastAPI(
        title="CortexGraph Memory Viewer",
        description="Web interface for viewing and managing CortexGraph memories",
        version="0.1.0",
    )

    # CORS middleware (useful for dev, though we serve static files from same origin)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(api_router, prefix="/api")

    # Mount static files
    # We assume the static directory is relative to this file
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
    else:
        logger.warning(f"Static directory not found: {static_dir}")

    # Rate limiting
    state = getattr(app, "state", None)
    if state:
        state.limiter = limiter

    def rate_limit_handler(request: Request, exc: Exception) -> Response:
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "detail": str(exc)},
        )

    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

    # Global error handling
    app.add_exception_handler(Exception, _global_exception_handler)

    return app


# Rate limiting configuration
limiter = Limiter(key_func=get_remote_address)


async def _global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            success=False,
            error=ErrorDetail(
                code=ErrorCode.INTERNAL_ERROR,
                message="An internal error occurred",
                remediation="Please try again later or contact support.",
                context=ErrorContext(details=str(exc)),
            ),
        ).model_dump(),
    )


app = create_app()
