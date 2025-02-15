"""MMIO File Manager for handling MMIO log files."""

from pathlib import Path
from typing import ClassVar, Optional

from pydantic import BaseModel, Field

from mmio.core.logger import LoggerManager
from mmio.infrastructure.file_handling.base_input_manager import InputManager

logger = LoggerManager.get_logger(__name__)


class MMIOFileManager(BaseModel):
    """File Manager to handle MMIO log file operations.

    Specialized manager for handling MMIO log files input operations.
    Uses composition with InputManager for file operations.

    Attributes:
        input_manager: Input manager instance for file operations

    """

    _instance: ClassVar[Optional["MMIOFileManager"]] = None
    input_manager: InputManager = Field(default_factory=InputManager.get_instance)

    @classmethod
    def get_instance(cls) -> "MMIOFileManager":
        """Get the singleton instance of MMIOFileManager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def read_file(self) -> Path:
        """Validate and return the path to the specified MMIO log file."""
        return self.input_manager.read_file()

    def list_files(self) -> list[Path]:
        """List all files in the input directory."""
        return self.input_manager.list_files()
