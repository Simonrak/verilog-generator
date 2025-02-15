"""Configuration from .env file and paths."""

import os
from pathlib import Path
from typing import ClassVar, Optional

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from mmio.config.base_config import BaseConfig
from mmio.core.logger import LoggerManager

logger = LoggerManager.get_logger(__name__)


class MMIOSettings(BaseSettings):
    """Configuration for MMIO log file input handling."""

    _instance: ClassVar[Optional["MMIOSettings"]] = None

    # From BaseConfig
    base_settings: BaseConfig = Field(default_factory=BaseConfig.get_instance)
    workdir: Path = Field(default_factory=lambda: BaseConfig.get_instance().workdir)
    file_input_path: Path | None = Field(default_factory=lambda: BaseConfig.get_instance().workdir / "input" / "mmio")
    file_input_name: str | None = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_ignore_empty=True,
        extra="allow",
        env_prefix="MMIO_",
    )

    @classmethod
    def get_instance(cls) -> "MMIOSettings":
        """Get the singleton instance of MMIOSettings."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @field_validator("workdir", mode="before")
    @classmethod
    def ensure_workdir(cls, value: Path | str) -> Path:
        """Ensure workdir is a Path and exists."""
        if not isinstance(value, Path):
            value = Path(str(value))
        if not value.exists():
            value.mkdir(parents=True, exist_ok=True)
        return value

    @field_validator("file_input_path", mode="after")
    @classmethod
    def resolve_input_path(cls, value: Path, info: ValidationInfo) -> Path:
        """Resolve the input path relative to workdir if it's not absolute."""
        if not value.is_absolute():
            workdir = info.data.get("workdir")
            if workdir is None:
                workdir = BaseConfig.get_instance().workdir
            value = workdir / value
        if not value.exists():
            value.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created input directory: {value}")
        return value

    @field_validator("file_input_name", mode="before")
    @classmethod
    def validate_file_exists(cls, value: str, info: ValidationInfo) -> str:
        """Ensure the input log file exists."""
        directory: Path | None = info.data.get("file_input_path")
        if directory is None:
            raise ValueError("Input directory path is not set.")
        if value is not None:
            path: Path = directory / value
            if not path.is_file():
                raise ValueError(f"Input log file does not exist: {path}")
        return value


settings: MMIOSettings = MMIOSettings.get_instance()
