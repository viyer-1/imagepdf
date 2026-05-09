"""
Comprehensive logging system for the application.
Logs to both file and console with rotation.
"""

import logging
import logging.handlers
import sys
from pathlib import Path


class AppLogger:
    """Application logger with file and console output."""

    _instance = None
    _logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._logger is not None:
            return

        # Create logger
        self._logger = logging.getLogger("JPGPDFConverter")
        self._logger.setLevel(logging.DEBUG)

        # Prevent duplicate handlers
        if self._logger.handlers:
            return

        # Create logs directory
        log_dir = self._get_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)

        # File handler with rotation (max 10MB, keep 5 backups)
        log_file = log_dir / "app.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers
        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)

        # Log startup
        self._logger.info("=" * 80)
        self._logger.info("JPG PDF Converter Application Started")
        self._logger.info(f"Log file: {log_file}")
        self._logger.info("=" * 80)

    def _get_log_dir(self) -> Path:
        """Get the logs directory path."""
        # Use user's home directory for logs
        if sys.platform == "win32":
            base_dir = (
                Path.home() / "AppData" / "Local" / "ImagePDF Solutions" / "JPG PDF Converter"
            )
        elif sys.platform == "darwin":
            base_dir = Path.home() / "Library" / "Application Support" / "JPG PDF Converter"
        else:  # Linux and others
            base_dir = Path.home() / ".local" / "share" / "jpg-pdf-converter"

        return base_dir / "logs"

    def get_logger(self) -> logging.Logger:
        """Get the logger instance."""
        return self._logger

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self._logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._logger.warning(message, **kwargs)

    def error(self, message: str, exc_info=False, **kwargs):
        """Log error message."""
        self._logger.error(message, exc_info=exc_info, **kwargs)

    def critical(self, message: str, exc_info=False, **kwargs):
        """Log critical message."""
        self._logger.critical(message, exc_info=exc_info, **kwargs)

    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self._logger.exception(message, **kwargs)


# Singleton instance
_app_logger = None


def get_logger() -> AppLogger:
    """Get singleton logger instance."""
    global _app_logger
    if _app_logger is None:
        _app_logger = AppLogger()
    return _app_logger


def log_conversion_start(conversion_type: str, file_count: int):
    """Log conversion start."""
    logger = get_logger()
    logger.info(f"Starting {conversion_type} conversion with {file_count} file(s)")


def log_conversion_success(conversion_type: str, output_path: str):
    """Log successful conversion."""
    logger = get_logger()
    logger.info(f"{conversion_type} conversion completed successfully: {output_path}")


def log_conversion_error(conversion_type: str, error: Exception):
    """Log conversion error."""
    logger = get_logger()
    logger.error(f"{conversion_type} conversion failed: {str(error)}", exc_info=True)
