"""Base Output File Manager for writing operations."""

from pathlib import Path
from typing import ClassVar, Optional, Self

from pydantic import BaseModel, Field, model_validator

from mmio.config.verilog_settings import VerilogSettings
from mmio.core.logger import LoggerManager
from mmio.infrastructure.file_handling.base_file_manager import BaseFileManager

logger = LoggerManager.get_logger(__name__)


class OutputManager(BaseModel):
    """Output file manager for writing operations.

    Provides functionality for writing and managing output files.
    Uses Pydantic for validation and type checking.

    Attributes:
        settings: Verilog settings for output operations
        file_manager: Base file manager for file operations
        folder_name: Name of the output folder

    """

    model_config = BaseFileManager.model_config

    _instance: ClassVar[Optional["OutputManager"]] = None

    settings: VerilogSettings = Field(default_factory=VerilogSettings.get_instance)
    file_manager: BaseFileManager = Field(default_factory=BaseFileManager)
    folder_name: str | None = Field(default=None)

    @classmethod
    def get_instance(cls) -> "OutputManager":
        """Get the singleton instance of the output manager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @model_validator(mode="after")
    def set_default_paths(self) -> Self:
        """Set default paths from settings if not provided."""
        if self.file_manager.path is None:
            object.__setattr__(self.file_manager, "path", self.settings.file_output_path)
        return self

    def get_full_output_path(self) -> Path | None:
        """Get the full output path combining directory and filename."""
        if self.file_manager.path and self.file_manager.file_name:
            return self.file_manager.path / self.file_manager.file_name
        return None

    def write_file(self, content: str) -> None:
        """Write content to output file."""
        self.file_manager.validate_path()
        if self.file_manager.path is None:
            raise ValueError("Output path is not set")
        if self.file_manager.file_name is None:
            raise ValueError("Output file name is not set")

        file_path = self.get_full_output_path()
        if file_path is None:
            raise ValueError("Could not construct output file path")

        logger.info(f"Writing file: {file_path}")
        file_path.write_text(content)
