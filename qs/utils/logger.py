from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "qs",
    level: int = logging.INFO,
    log_file: Optional[str | Path] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with both console and file handlers.
    
    Parameters:
    -----------
    name : str
        Logger name
    level : int
        Logging level (default: INFO)
    log_file : str or Path, optional
        Path to log file. If None, only logs to console.
    format_string : str, optional
        Custom format string. Default includes timestamp, level, name, and message.
    
    Returns:
    --------
    logging.Logger
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Default format
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "qs") -> logging.Logger:
    """Get or create a logger instance."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Setup default logger if not already configured
        setup_logger(name)
    return logger

