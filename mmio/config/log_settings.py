"""Logging settings configuration."""

import json
import logging
from pathlib import Path
from typing import Any, ClassVar, Optional, Self

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import SettingsConfigDict

from mmio.config.base_config import BaseConfig

LOG_LEVELS: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


class LogSettings(BaseModel):
    """Logging settings configuration.

    This class manages logging settings and their persistence between sessions.
    Settings are stored in a temporary file and loaded on startup.

    Attributes:
        level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        file_enabled: Whether to enable file logging
        log_file: Optional path to the log file
        format: Log message format string
        date_format: Date format for log messages

    """

    _instance: ClassVar[Optional["LogSettings"]] = None

    # From BaseConfig
    base_settings: BaseConfig = Field(default_factory=BaseConfig.get_instance)
    workdir: Path = Field(default_factory=lambda: BaseConfig.get_instance().workdir)
    format: str = Field(default_factory=lambda: BaseConfig.get_instance().format)
    date_format: str = Field(default_factory=lambda: BaseConfig.get_instance().date_format)

    level: str = Field(default="WARNING")
    file_enabled: bool = Field(default=True)
    log_file: Path | None = Field(default_factory=lambda: BaseConfig.get_instance().workdir / "mmio.log")
    settings_file: Path = Field(default_factory=lambda: BaseConfig.get_instance().workdir / "mmio_log_settings.json")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_ignore_empty=True,
        extra="allow",
        env_prefix="LOG_",
    )

    @classmethod
    def get_instance(cls) -> "LogSettings":
        """Get the singleton instance of LogSettings."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def get_workdir(cls) -> Path:
        """Get the workspace directory."""
        return BaseConfig.get_instance().workdir

    @model_validator(mode="after")
    def validate_settings(self) -> Self:
        """Validate the settings after model creation."""
        if self.level not in LOG_LEVELS:
            raise ValueError(f"Invalid log level. Must be one of: {', '.join(LOG_LEVELS.keys())}")
        return self

    @property
    def level_value(self) -> int:
        """Get the numeric value for the current log level."""
        return LOG_LEVELS[self.level]

    def save(self, file_path: Path | None = None) -> None:
        """Save settings to a file.

        Args:
            file_path: Optional custom path to save settings

        """
        save_path: Path = file_path or self.settings_file

        data: dict[str, Any] = self.model_dump()
        if data.get("log_file"):
            data["log_file"] = str(data["log_file"])

        try:
            save_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to save log settings: {e}")

    @classmethod
    def load(cls, file_path: Path | None = None) -> "LogSettings":
        """Load settings from a file.

        Args:
            file_path: Optional custom path to load settings from

        Returns:
            LogSettings instance with loaded values or defaults

        """
        load_path: Path = file_path or cls.get_workdir() / "log_settings.json"

        if not load_path.exists():
            return cls()

        try:
            data: dict[str, Any] = json.loads(load_path.read_text())
            if data.get("log_file"):
                data["log_file"] = Path(data["log_file"])
            return cls(**data)
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to load log settings: {e}")
            return cls()

    def apply(self) -> None:
        """Apply these settings to the LoggerManager."""
        from mmio.core.logger import LoggerManager

        LoggerManager.initialize(level=self.level_value, format_str=self.format, date_format=self.date_format)

        if self.file_enabled and self.log_file:
            LoggerManager.add_file_handler(self.log_file)


log_settings: LogSettings = LogSettings.get_instance()
