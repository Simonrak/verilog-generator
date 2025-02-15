"""Base configuration class."""

from pathlib import Path
from typing import ClassVar, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    """Base configuration class."""

    _instance: ClassVar[Optional["BaseConfig"]] = None

    workdir: Path = Field(default=(Path.cwd()))
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    date_format: str = Field(default="%Y-%m-%d %H:%M:%S")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
        env_ignore_empty=True,
        env_prefix="BASE_",
    )

    @classmethod
    def get_instance(cls) -> "BaseConfig":
        """Get the singleton instance of BaseConfig."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


base_config_instance = BaseConfig()
base_config: BaseConfig = BaseConfig.get_instance()
