"""Configuration for Verilog code generation output."""

from pathlib import Path
from typing import Any, ClassVar, Optional

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from mmio.config.base_config import BaseConfig
from mmio.core.logger import LoggerManager

logger = LoggerManager.get_logger(__name__)


class VerilogSettings(BaseSettings):
    """Configuration for Verilog code generation output."""

    _instance: ClassVar[Optional["VerilogSettings"]] = None

    # From BaseConfig
    base_settings: BaseConfig = Field(default_factory=BaseConfig.get_instance)

    module_header: str | None = "cool_bar_controller"
    file_output_path: Path | None = Field(
        default_factory=lambda: BaseConfig.get_instance().workdir / "output" / "verilog"
    )
    file_output_name: str | None = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_ignore_empty=True,
        extra="allow",
        env_prefix="VERILOG_",
    )

    @classmethod
    def get_instance(cls) -> "VerilogSettings":
        """Get the singleton instance of VerilogSettings."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @field_validator("file_output_path", mode="before")
    @classmethod
    def validate_directory_exists(cls, value: Path | str, info: ValidationInfo) -> Path:
        """Ensure the Verilog output directory exists if a path is provided."""
        if not isinstance(value, Path):
            value = Path(value)
        if value.exists():
            return value
        value.mkdir(parents=True, exist_ok=True)
        logger.error(f"Verilog output directory did not exist, creating: {value}")
        return value

    @field_validator("file_output_name", mode="after")
    @classmethod
    def validate_file_exists(cls, value: str, info: ValidationInfo) -> str:
        """Ensure the Verilog output file exists."""
        directory: Any | None = info.data.get("file_output_path")
        if directory is None:
            raise ValueError("Verilog output directory path is not set.")
        if value is not None:
            path: Path = directory / value
            if not path.is_file():
                raise ValueError(f"Verilog output file does not exist: {path}")
        return value


settings: VerilogSettings = VerilogSettings.get_instance()
