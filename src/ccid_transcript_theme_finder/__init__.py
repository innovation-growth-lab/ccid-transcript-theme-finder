"""CCID Transcript Theme Finder package.

This package provides tools for checking transcripts for themes using
Gemini models.
"""

import logging
from pathlib import Path


def setup_logging(log_file: str = "processing.log", log_level: int = logging.INFO) -> None:
    """Configure package-wide logging.

    Args:
        log_file: Path to the log file. Defaults to "processing.log"
        log_level: Logging level. Defaults to logging.INFO
    """
    # Create log directory if needed
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file),
        ],
        force=True,
    )


# set up default logging configuration when package is imported
setup_logging()

# Version info
__version__ = "0.1.0"
