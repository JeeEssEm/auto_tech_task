import logging
from pathlib import Path


def build_file_logger(name: str, path: str = "llm.log") -> logging.Logger:
    log_path = Path(path)
    if log_path.parent and str(log_path.parent) != ".":
        log_path.parent.mkdir(parents=True, exist_ok=True)

    logger_name = f"{name}:{log_path.as_posix()}"
    logger = logging.getLogger(logger_name)

    if not logger.handlers:
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.propagate = False
    logger.setLevel(logging.DEBUG)
    return logger
