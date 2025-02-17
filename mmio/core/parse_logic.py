"""Patterns for MMIO parsing."""

from collections import OrderedDict
from typing import Any

from pydantic import BaseModel

from mmio.core.logger import LoggerManager

logger = LoggerManager.get_logger(__name__)


class MMIOParseLogic(BaseModel):
    """Patterns for MMIO parsing.

    This class handles the parsing of MMIO log lines in the format:
    Operation Counter Timestamp Bar Address Value Value2 Final
    Example: W 2 298.823649 1 0xf70003fc 0x7a 0x0 0
    """

    @staticmethod
    def last_char_to_shift_amount(
        addr_hex: str,
        last_char: str,
    ) -> list[tuple[str, int]]:
        """Convert hex address last character to base address and shift amount."""
        char_to_base_map: dict[str, str] = {
            c: b
            for b, chars in {
                "0": "1230",
                "4": "5674",
                "8": "9ab8",
                "c": "defc",
            }.items()
            for c in chars
        }

        shift_map: dict[int, str] = {
            0: "048c",
            8: "159d",
            16: "26ae",
            24: "37bf",
        }

        last_char = last_char.lower()
        base_char = char_to_base_map.get(last_char)

        if not base_char:
            return [(addr_hex, 0)]

        base_addr = f"{addr_hex[:-1]}{base_char}"
        shift = next((k for k, v in shift_map.items() if last_char in v), 0)

        return [(base_addr, shift)]

    @classmethod
    def align_address_and_value(
        cls,
        addr: str,
        value: str,
    ) -> tuple[str, str]:
        """Aligns byte value based on address position."""
        last_char = addr[-1]
        base_addr, shift_amount = cls.last_char_to_shift_amount(addr[2:], last_char)[0]
        value_int = int(value, 16)
        hex_value = f"{(value_int << shift_amount) & 0xFFFFFFFF:08x}"
        return base_addr, hex_value

    @staticmethod
    def is_valid_hex(value: str) -> bool:
        """Check if a string is a valid hexadecimal value starting with 0x."""
        try:
            if not value.startswith("0x"):
                return False
            int(value, 16)
            return True
        except ValueError:
            return False

    @staticmethod
    def is_valid_line(line: str) -> bool:
        """Check if line starts with W or R and has the correct format."""
        return line.strip().startswith(("W", "R"))

    @staticmethod
    def is_write(line: str) -> bool:
        """Check if line is a write operation."""
        return line.strip().startswith("W")

    @staticmethod
    def is_read(line: str) -> bool:
        """Check if line is a read operation."""
        return line.strip().startswith("R")

    @staticmethod
    def bar_number(parts: list[str], base_addr: str, value: str) -> int:
        """Get the bar number from line parts with base address and value validation."""
        return int(parts[3])

    @staticmethod
    def validate_line_format(line: str) -> list[str]:
        """Validate line format and split into parts."""
        if not MMIOParseLogic.is_valid_line(line):
            raise ValueError("Invalid line format - must start with W or R")

        parts = line.strip().split()
        if len(parts) != 8:
            raise ValueError("Invalid line format - expected 8 fields")

        for hex_value in [parts[4], parts[5]]:
            if not MMIOParseLogic.is_valid_hex(hex_value):
                raise ValueError(f"Invalid hex value: {hex_value}")

        return parts

    @staticmethod
    def process_address(address_hex: str) -> tuple[str, str, int]:
        """Process address to get base address and shift amount."""
        address = address_hex[2:]
        if len(address) < 1:
            raise ValueError(f"Invalid address format: {address_hex}")

        last_char = address[-1]
        base_addr, shift_amount = MMIOParseLogic.last_char_to_shift_amount(
            address, last_char
        )[0]
        return base_addr, address, shift_amount

    @staticmethod
    def create_mmio_data(
        parts: list[str],
        operation: str,
        bar: int,
        address: str,
        value: str,
    ) -> OrderedDict[str, Any]:
        """Create MMIO data dictionary from parsed components."""
        try:
            return OrderedDict(
                [
                    ("operation", operation),
                    ("counter", int(parts[1])),
                    ("timestamp", float(parts[2])),
                    ("bar_number", bar),
                    ("address", address),
                    ("value", value),
                ]
            )
        except (ValueError, IndexError) as e:
            raise ValueError(f"Error creating MMIO data: {str(e)}")

    @staticmethod
    def parse_line(
        line: str,
    ) -> OrderedDict[str, Any]:
        """Parse a valid line into its components."""
        parts = MMIOParseLogic.validate_line_format(line)
        operation = "W" if MMIOParseLogic.is_write(line) else "R"

        base_addr, address, shift_amount = MMIOParseLogic.process_address(parts[4])
        bar = MMIOParseLogic.bar_number(parts, base_addr, parts[5])
        aligned_address, shifted_value = MMIOParseLogic.align_address_and_value(
            parts[4], parts[5]
        )

        return MMIOParseLogic.create_mmio_data(
            parts, operation, bar, aligned_address, shifted_value
        )
