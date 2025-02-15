from pydantic import BaseModel, Field

from mmio.core.logger import LoggerManager
from mmio.infrastructure.file_handling.verilog_filemanager import VerilogFileManager

logger = LoggerManager.get_logger(__name__)


class OutputOrchestrator(BaseModel):
    """Handle output operations.

    - Accepts generated verilog code.
    - Uses VerilogFileManager to write the code to disk.
    """

    verilog_file_manager: VerilogFileManager = Field(default_factory=VerilogFileManager.get_instance)

    def output(self, verilog_code: str) -> None:
        """Write the generated verilog code to a file.

        Args:
            verilog_code (str): The verilog code to be written.

        """
        if not self.verilog_file_manager.output_manager.file_manager.file_name:
            self.verilog_file_manager.generate_output_filename()

        self.verilog_file_manager.write_file(verilog_code)
