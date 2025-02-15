from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mmio.core.logger import LoggerManager
from mmio.core.mmio_parser import MMIOParser
from mmio.domain.models.verilog_data import VerilogData
from mmio.infrastructure.file_handling.mmio_filemanager import MMIOFileManager

logger = LoggerManager.get_logger(__name__)


class InputOrchestrator(BaseModel):
    """Handle the input operations.

    - Reading file(s) using MMIOFileManager.
    - Parsing the MMIO log content via MMIOParser.
    - Converting the parsed dictionaries into VerilogData instances.

    Returns a processed data structure (e.g., a dictionary of VerilogData) that will be used
    by the Verilog builder orchestrator.
    """

    mmio_file_manager: MMIOFileManager = Field(default_factory=MMIOFileManager.get_instance)
    parser: MMIOParser = Field(default_factory=MMIOParser)

    def execute(self) -> dict[int, list[VerilogData]]:
        """Execute the input processing.

        Process:
            1. Read the input file path using MMIOFileManager.
            2. Read file content.
            3. Parse file content using MMIOParser to get a list of dictionary data.
            4. Transform each parsed dictionary into VerilogData using from_dict.
            5. Aggregate the data into a structured format (e.g., keyed by BAR) and return.

        Returns:
            dict: A dictionary containing processed BAR data.

        """
        logger.info("Starting input processing")

        logger.info(f"Reading file from path: {self.mmio_file_manager.input_manager.file_manager.path}")
        if self.mmio_file_manager.input_manager.file_manager.file_name is not None:
            logger.info(f"Input file name: {self.mmio_file_manager.input_manager.file_manager.file_name}")
        else:
            logger.info("No input file name provided")

        file_path: Path = self.mmio_file_manager.read_file()
        logger.info(f"Successfully read file: {file_path}")

        content: str = file_path.read_text()

        logger.info("Parsing file content")
        parsed_results: list[dict[str, Any]] = self.parser.parse_content(content)

        logger.info("Transforming parsed data to VerilogData instances")
        processed_data: dict[int, list[VerilogData]] = {}
        success_count = 0
        error_count = 0

        for entry in parsed_results:
            try:
                verilog_data: VerilogData = VerilogData.from_dict(entry)
                logger.info(f"Created VerilogData instance: {verilog_data}")

                bar_number: int = verilog_data.bar if verilog_data.bar is not None else 0
                if bar_number not in processed_data:
                    processed_data[bar_number] = []
                    logger.info(f"Created new list for BAR {bar_number}")
                processed_data[bar_number].append(verilog_data)
                success_count += 1

                if success_count % 100 == 0:
                    logger.info(f"Processed {success_count} entries successfully")
            except Exception as e:
                error_count += 1
                logger.error(f"Error processing entry: {e}")
                logger.info(f"Problematic entry: {entry}")

        if error_count > 0:
            logger.warning(f"Failed to process {error_count} entries")

        logger.info(f"Final processed data contains {len(processed_data)} BARs")
        for bar_num, entries in processed_data.items():
            logger.info(f"BAR {bar_num}: {len(entries)} entries")

        return processed_data
