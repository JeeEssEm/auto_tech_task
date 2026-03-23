import logging
import os
import sys
import warnings
from pathlib import Path

import structlog

try:
    from requests.exceptions import RequestsDependencyWarning
except Exception:  # pragma: no cover
    RequestsDependencyWarning = None


def setup_logging(debug: bool = False):
    if RequestsDependencyWarning is not None:
        warnings.filterwarnings("ignore", category=RequestsDependencyWarning)

    log_level = logging.DEBUG if debug else logging.INFO
    logs_dir = Path(os.getenv("APP_LOG_DIR", "logs"))
    logs_dir.mkdir(parents=True, exist_ok=True)
    app_log_file = Path(os.getenv("APP_LOG_FILE", str(logs_dir / "backend.log")))
    langgraph_log_file = Path(os.getenv("LANGGRAPH_LOG_FILE", str(logs_dir / "langgraph-full.log")))

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if debug:
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    file_handler = logging.FileHandler(app_log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(log_level)

    # Dedicated full-fidelity file for LangGraph/LangChain internals.
    plain_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    langgraph_handler = logging.FileHandler(langgraph_log_file, encoding="utf-8")
    langgraph_handler.setLevel(logging.DEBUG)
    langgraph_handler.setFormatter(plain_formatter)

    for name in ("langgraph", "langchain", "langchain_core"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.addHandler(langgraph_handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

    noisy_loggers = (
        # S3 / boto
        "aiobotocore",
        "botocore",
        "boto3",
        # HTTP
        "urllib3",
        "httpcore",
        "httpx",
        # Redis
        "redis",
        "redis.asyncio",
        # RabbitMQ
        "aio_pika",
        "aiormq",
        # Taskiq
        "taskiq",
        "taskiq_aio_pika",
        "taskiq_redis",
        # ORM
        "prisma",
        # DI
        "dishka",
        # Uvicorn internals
        "uvicorn.access",
        "uvicorn.error",
        # Async / misc
        "asyncio",
        "watchfiles",
    )
    for name in noisy_loggers:
        logging.getLogger(name).setLevel(logging.WARNING)
