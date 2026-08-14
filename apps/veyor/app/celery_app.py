import os
import sys
from celery import Celery

# Guarantee /container_root is first on sys.path before any app imports occur
CONTAINER_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if CONTAINER_ROOT not in sys.path:
    sys.path.insert(0, CONTAINER_ROOT)

REDIS_HOST = os.getenv("REDIS_HOST", "redis-service")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_BROKER = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"


celery_app = Celery(
    "tasks",
    broker=REDIS_BROKER,
    include=["app.tasks"]
)