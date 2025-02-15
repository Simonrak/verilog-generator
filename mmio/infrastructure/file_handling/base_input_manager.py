"""Base Input File Manager for reading operations."""

from pathlib import Path
from typing import ClassVar, Optional, Self

from pydantic import BaseModel, Field, model_validator

from mmio.config.mmio_settings import MMIOSettings
from mmio.core.logger import LoggerManager
from mmio.infrastructure.file_handling.base_file_manager import BaseFileManager

logger = LoggerManager.get_logger(__name__)


class InputManager(BaseModel):
    """Input file manager for reading operations.

    Provides functionality for reading and managing input files.
    Uses Pydantic for validation and type checking.

    Attributes:
        mmio_settings: MMIO settings for input operations
        file_manager: Base file manager for file operations

    """

    model_config = BaseFileManager.model_config

    _instance: ClassVar[Optional["InputManager"]] = None

    mmio_settings: MMIOSettings = Field(default_factory=MMIOSettings.get_instance)
    file_manager: BaseFileManager = Field(default_factory=BaseFileManager)

    @classmethod
    def get_instance(cls) -> "InputManager":
        """Get the singleton instance of the input manager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @model_validator(mode="after")
    def set_default_paths(self) -> Self:
        """Set default paths from settings if not provided."""
        if self.file_manager.path is None:
            object.__setattr__(self.file_manager, "path", self.mmio_settings.file_input_path)
        if self.file_manager.file_name is None:
            object.__setattr__(self.file_manager, "file_name", self.mmio_settings.file_input_name)
        return self

    def get_full_input_path(self) -> Path | None:
        """Get the full input path combining directory and filename."""
        if self.file_manager.path and self.file_manager.file_name:
            logger.info(f"Constructing path from: {self.file_manager.path} and {self.file_manager.file_name}")
            return self.file_manager.path / self.file_manager.file_name
        logger.error(f"Cannot construct path - path: {self.file_manager.path}, filename: {self.file_manager.file_name}")
        return None

    def read_file(self) -> Path:
        """Read configured input file with validation.

        Returns:
            Path: Validated path to the input file

        Raises:
            ValueError: If input path or file name is not set
            FileNotFoundError: If file doesn't exist or isn't accessible

        """
        self.file_manager.validate_path()
        if self.file_manager.path is None:
            raise ValueError("Input path is not set")
        if self.file_manager.file_name is None:
            raise ValueError("Input file name is not set")

        file_path = self.get_full_input_path()
        if file_path is None:
            raise ValueError("Could not construct input file path")

        self.file_manager.validate_file(file_path)
        logger.info(f"Validated input file: {file_path}")
        return file_path

    def list_files(self, pattern: str = "*") -> list[Path]:
        """List files in the directory with optional pattern matching."""
        return self.file_manager.list_files(pattern)
