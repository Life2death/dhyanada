import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.config import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Maharashtra Kisan AI",
    description="WhatsApp chatbot for mandi prices and MSP alerts",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
)


@app.on_event("startup")
async def startup() -> None:
    """Initialize DB pool and WhatsApp adapter on startup."""
    logging.basicConfig(level=settings.log_level)
    logger.info("Starting Maharashtra Kisan AI (env=%s)", settings.app_env)

    # Lazy import to avoid circular dependency during adapter init
    from src.adapters.whatsapp import wa_adapter
    await wa_adapter.start(app)


@app.get("/health", tags=["ops"])
async def health() -> JSONResponse:
    """Liveness probe."""
    return JSONResponse({"status": "ok"})


@app.get("/ready", tags=["ops"])
async def ready() -> JSONResponse:
    """Readiness probe — checks DB + Redis reachability."""
    from src.adapters.whatsapp import wa_adapter
    return JSONResponse({"status": "ok", "adapter": wa_adapter.is_ready})
