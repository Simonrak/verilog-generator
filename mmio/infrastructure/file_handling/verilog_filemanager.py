"""Verilog File Manager for handling Verilog file generation."""

from datetime import datetime
from pathlib import Path
from typing import ClassVar, Optional

from pydantic import BaseModel, Field

from mmio.core.logger import LoggerManager
from mmio.infrastructure.file_handling.base_output_manager import OutputManager

logger = LoggerManager.get_logger(__name__)


class VerilogFileManager(BaseModel):
    """File Manager to handle Verilog file operations.

    Specialized manager for handling Verilog file output operations.
    Uses composition with OutputManager for file operations.

    Attributes:
        output_manager: Output manager instance for file operations

    """

    _instance: ClassVar[Optional["VerilogFileManager"]] = None
    output_manager: OutputManager = Field(default_factory=OutputManager.get_instance)

    @classmethod
    def get_instance(cls) -> "VerilogFileManager":
        """Get the singleton instance of VerilogFileManager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def write_file(self, content: str) -> None:
        """Write generated Verilog content to an output file."""
        if not self.output_manager.file_manager.file_name:
            self.generate_output_filename()
        self.output_manager.write_file(content)

    def generate_output_filename(self) -> str:
        """Generate output filename with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"generated_verilog_{timestamp}.v"
        self.output_manager.file_manager.file_name = filename
        logger.info(f"Generated output filename: {filename}")
        return filename


verilog_filemanager: VerilogFileManager = VerilogFileManager.get_instance()
