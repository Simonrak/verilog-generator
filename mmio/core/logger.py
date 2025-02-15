"""Centralized logging configuration for the MMIO application."""

import logging
import sys
from pathlib import Path

from pydantic import BaseModel, Field


class LogConfig(BaseModel):
    """Logging configuration settings.

    Attributes:
        level: The logging level to use
        format: The log message format
        date_format: The format for timestamps
        file_path: Optional path to log file

    """

    level: int = Field(default=logging.WARNING)
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    date_format: str = Field(default="%Y-%m-%d %H:%M:%S")
    file_path: Path | None = None


class LoggerManager:
    """Centralized logger management.

    This class handles the configuration and creation of loggers
    throughout the application, ensuring consistent logging behavior.
    """

    _config: LogConfig = LogConfig()
    _initialized: bool = False
    _loggers: dict[str, logging.Logger] = {}

    @classmethod
    def initialize(
        cls,
        level: int = logging.WARNING,
        file_path: Path | None = None,
        format_str: str | None = None,
        date_format: str | None = None,
    ) -> None:
        """Initialize the logging system.

        Args:
            level: The logging level to use
            file_path: Optional path to log file
            format_str: Optional custom format string
            date_format: Optional custom date format

        """
        if cls._initialized:
            return

        cls._config.level = level
        if file_path:
            cls._config.file_path = file_path
        if format_str:
            cls._config.format = format_str
        if date_format:
            cls._config.date_format = date_format

        formatter = logging.Formatter(cls._config.format, cls._config.date_format)

        root_logger = logging.getLogger()
        root_logger.setLevel(cls._config.level)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        if cls._config.file_path:
            try:
                file_handler = logging.FileHandler(cls._config.file_path)
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
            except Exception as e:
                cls.get_logger("LoggerManager").error(f"Failed to create file handler: {e}")
                console_handler.emit(
                    logging.LogRecord(
                        "LoggerManager",
                        logging.WARNING,
                        "",
                        0,
                        f"Failed to create file handler: {e}",
                        (),
                        None,
                    )
                )

        cls._initialized = True

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get a logger with the specified name.

        Args:
            name: The name for the logger (typically __name__)

        Returns:
            A configured logger instance

        """
        if not cls._initialized:
            cls.initialize()

        if name not in cls._loggers:
            logger = logging.getLogger(name)
            cls._loggers[name] = logger

        return cls._loggers[name]

    @classmethod
    def set_level(cls, level: int) -> None:
        """Set the logging level for all loggers.

        Args:
            level: The new logging level

        """
        cls._config.level = level
        for logger in cls._loggers.values():
            logger.setLevel(level)

    @classmethod
    def add_file_handler(cls, file_path: Path) -> None:
        """Add a file handler to all loggers.

        Args:
            file_path: Path to the log file

        """
        try:
            formatter = logging.Formatter(cls._config.format, cls._config.date_format)
            file_handler = logging.FileHandler(file_path)
            file_handler.setFormatter(formatter)

            for logger in cls._loggers.values():
                logger.addHandler(file_handler)

            cls._config.file_path = file_path
        except Exception as e:
            cls.get_logger("LoggerManager").error(f"Failed to add file handler: {e}")
