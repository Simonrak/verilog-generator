"""Base file manager with common functionality."""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from mmio.core.logger import LoggerManager

logger = LoggerManager.get_logger(__name__)


class BaseFileManager(BaseModel):
    """Base class for all file managers with common Pydantic configuration.

    This class provides common functionality for file operations and path management.
    It uses Pydantic for validation and type checking.

    Attributes:
        path: Base path for file operations
        file_name: Name of the file to process

    """

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True, extra="forbid")

    path: Path | None = Field(default=None)
    file_name: str | None = Field(default=None)

    def validate_path(self) -> None:
        """Validate the base path."""
        if self.path is None:
            raise ValueError("Path is not set")
        if not self.path.exists():
            self.path.mkdir(parents=True, exist_ok=True)
        if not self.path.is_dir():
            raise ValueError(f"Path is not a directory: {self.path}")

    def validate_file(self, file_path: Path) -> None:
        """Validate a file path."""
        if not file_path.exists():
            raise ValueError(f"File does not exist: {file_path}")
        if not file_path.is_file():
            raise ValueError(f"Path exists but is not a file: {file_path}")

    def list_files(self, pattern: str = "*") -> list[Path]:
        """List files in the directory with optional pattern matching."""
        self.validate_path()
        if self.path is None:
            return []
        try:
            files = list(self.path.glob(pattern))
            logger.info(f"Found {len(files)} files matching pattern '{pattern}' in {self.path}")
            return files
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
