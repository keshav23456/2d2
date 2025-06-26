"""
Logging configuration using loguru
"""
import sys
from loguru import logger
from app.core.config import settings


def setup_logger():
    """Configure logger with proper formatting and levels"""
    
    # Remove default handler
    logger.remove()
    
    # Add console handler with custom format
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # Console logging
    logger.add(
        sys.stdout,
        format=log_format,
        level="DEBUG" if settings.debug else "INFO",
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # File logging
    logger.add(
        "logs/app.log",
        format=log_format,
        level="INFO",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        backtrace=True,
        diagnose=True
    )
    
    # Error file logging
    logger.add(
        "logs/errors.log",
        format=log_format,
        level="ERROR",
        rotation="5 MB",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True
    )
    
    return logger


# Initialize logger
setup_logger()

# Export logger instance
__all__ = ["logger"]