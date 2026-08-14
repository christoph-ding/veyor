import logging
from prometheus_fastapi_instrumentator import Instrumentator

logger = logging.getLogger(__name__)


def init_api_metrics(app, endpoint: str = "/metrics"):
    """Instruments FastAPI to expose /metrics on port 8000."""
    Instrumentator().instrument(app).expose(app, endpoint=endpoint)