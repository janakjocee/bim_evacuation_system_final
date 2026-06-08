"""
Logging utility using Loguru.
"""
import sys
from pathlib import Path
from loguru import logger as _logger

# Remove default handler
_logger.remove()

# Add console handler
_logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}",
    level="INFO",
    colorize=True
)

# Create logs directory
log_dir = Path("./outputs")
log_dir.mkdir(parents=True, exist_ok=True)

# Add file handler
_logger.add(
    log_dir / "bim_evacuation.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="7 days"
)


def get_logger(name: str = None):
    """Get logger instance."""
    if name:
        return _logger.bind(name=name)
    return _logger
