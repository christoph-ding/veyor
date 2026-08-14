# app/utils/logger.py

import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logger(service_name: str) -> logging.Logger:
    """
    Configures and returns a structured JSON logger.
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.INFO)

    # Avoid adding handlers multiple times if logger already exists
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        
        # Define JSON format fields
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            timestamp=True
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger