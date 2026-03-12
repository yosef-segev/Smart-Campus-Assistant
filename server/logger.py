import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Root logger for the application
logger = logging.getLogger("smart_campus")
logger.setLevel(logging.DEBUG)

# Avoid adding duplicate handlers if the module is reloaded (e.g. pytest)
if not logger.handlers:
    # Rotating file handler
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    # Console / stdout handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that wraps every HTTP request and logs:
      - Incoming: method + URL path
      - Outgoing: status code + response time (ms)

    The log entry is written at INFO level so it appears in both the file
    and the console handler defined above.
    """

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()

        # Log the incoming request
        logger.info("→ %s %s  (client: %s)",
                    request.method,
                    request.url.path,
                    request.client.host if request.client else "unknown")

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000

        # Log the outgoing response with timing
        logger.info("← %s %s  status=%d  time=%.2f ms",
                    request.method,
                    request.url.path,
                    response.status_code,
                    elapsed_ms)

        return response
