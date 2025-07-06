import logging
import os

from backend.code.paths import OUTPUTS_DIR

logger = logging.getLogger("rag_assistant")
logger.setLevel(logging.INFO)


def setup_logging() -> None:
    if logger.handlers:
        return

    file_path = os.path.join(OUTPUTS_DIR, "rag_assistant.log")
    file_handler = logging.FileHandler(file_path)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
