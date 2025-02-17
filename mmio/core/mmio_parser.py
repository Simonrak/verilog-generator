"""MMIO Parser module."""

from collections import OrderedDict
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from mmio.core.exceptions import (
    FileAccessError,
    MMIOParserError,
)
from mmio.core.logger import LoggerManager
from mmio.core.parse_logic import MMIOParseLogic

logger = LoggerManager.get_logger(__name__)


class MMIOParser(BaseModel):
    """Parser for MMIO logs.

    This class handles parsing of MMIO log content, converting raw log lines into structured data.
    Each line represents either a read or write operation with associated metadata.

    Attributes:
        parse_logic: Logic for parsing MMIO log lines

    """

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)
    parse_logic: MMIOParseLogic = Field(default_factory=MMIOParseLogic)

    def parse_content(self, content: str) -> list[dict[str, Any]]:
        """Parse MMIO content and return a list of parsed data as dictionaries.

        Args:
            content: MMIO log content to parse

        Returns:
            List of dictionaries containing parsed MMIO operations, including:
            - All original fields from parse_line
            - read_value/write_value: Operation-specific values
            - read_address/write_address: Operation-specific addresses (shifted)

        Raises:
            FileAccessError: If content is empty
            MMIOParserError: For unexpected errors

        """
        try:
            if not content.strip():
                logger.info("Skipping empty content")
                return []

            lines: list[str] = content.splitlines()
            parsed_data: list[dict[str, Any]] = []

            for line_number, line in enumerate(iterable=lines, start=1):
                if not (line.startswith("R") or line.startswith("W")):
                    logger.info(f"Skipped non-R/W line {line_number}: {line[:40]}...")
                    continue

                try:
                    parsed_line_dict: OrderedDict[str, Any] = (
                        self.parse_logic.parse_line(line)
                    )
                    logger.info(
                        f"Parsed line: {parsed_line_dict['operation']}, {parsed_line_dict['address']}, {parsed_line_dict['value']}"
                    )
                    value = parsed_line_dict["value"]
                    num = int(value, 16)
                    value = f"{num:08X}"
                    logger.info(f"Parsed value: {value}")

                    parsed_data.append(
                        {
                            "operation": parsed_line_dict["operation"],
                            "counter": parsed_line_dict["counter"],
                            "timestamp": float(parsed_line_dict["timestamp"]),
                            "bar": int(parsed_line_dict["bar_number"]),
                            "address": parsed_line_dict["address"],
                            "value": value,
                        }
                    )
                    logger.info(f"Parsed data: {parsed_data[-1]}")
                except (ValueError, KeyError) as e:
                    logger.info(f"Skipped invalid line {line_number}: {str(e)}")
                    continue

            return parsed_data
        except FileAccessError:
            raise
        except Exception as e:
            raise MMIOParserError(f"Unexpected error: {str(e)}")
