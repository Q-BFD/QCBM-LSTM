import logging
import sys
from pathlib import Path

def setup_logger(log_dir: Path):
    """
    Sets up a centralized logger for the experiment.

    Args:
        log_dir (Path): The directory where the log file will be saved.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "experiment.log"

    logger = logging.getLogger("QCBM-LSTM")
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info("=" * 80)
    logger.info("Logger initialized. All output will be logged here.")
    logger.info(f"Log file available at: {log_file}")
    logger.info("=" * 80)

    return logger

def get_logger():
    """Returns the singleton logger instance."""
    return logging.getLogger("QCBM-LSTM") 