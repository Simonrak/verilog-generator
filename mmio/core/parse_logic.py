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
    def last_char_to_shift_amount(addr_hex: str, last_char: str) -> list[tuple[str, int]]:
        """Calculate base address and shift amount based on last character of address.

        Args:
        addr_hex: Hex address string
        last_char: Last character of address

        Returns:
        Tuple of base address and shift amount

        """
        last_char = last_char.lower()

        if last_char in "1230":
            base_addr: str = addr_hex[:-1] + "0"
            if last_char == "0":
                return [(base_addr, 0)]
            elif last_char == "1":
                return [(base_addr, 8)]
            elif last_char == "2":
                return [(base_addr, 16)]
            elif last_char == "3":
                return [(base_addr, 24)]

        elif last_char in "5674":
            base_addr = addr_hex[:-1] + "4"
            if last_char == "4":
                return [(base_addr, 0)]
            elif last_char == "5":
                return [(base_addr, 8)]
            elif last_char == "6":
                return [(base_addr, 16)]
            elif last_char == "7":
                return [(base_addr, 24)]

        elif last_char in "9ab8":
            base_addr = addr_hex[:-1] + "8"
            if last_char == "8":
                return [(base_addr, 0)]
            elif last_char == "9":
                return [(base_addr, 8)]
            elif last_char == "a":
                return [(base_addr, 16)]
            elif last_char == "b":
                return [(base_addr, 24)]

        elif last_char in "defc":
            base_addr = addr_hex[:-1] + "c"
            if last_char == "c":
                return [(base_addr, 0)]
            elif last_char == "d":
                return [(base_addr, 8)]
            elif last_char == "e":
                return [(base_addr, 16)]
            elif last_char == "f":
                return [(base_addr, 24)]

        return [(addr_hex, 0)]

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
    def bar_number(line: str) -> int:
        """Get the bar number from the line."""
        return int(line.strip().split()[1])

    @staticmethod
    def parse_line(line: str) -> OrderedDict[str, Any]:
        """Parse a valid line into its components."""
        parts = line.strip().split()
        if len(parts) != 8:
            raise ValueError("Invalid line format - expected 8 fields")

        if parts[0] not in ("W", "R"):
            raise ValueError(f"Invalid operation {parts[0]} - expected W or R")

        for hex_value in [parts[4], parts[5]]:
            if not MMIOParseLogic.is_valid_hex(hex_value):
                raise ValueError(f"Invalid hex value: {hex_value}")

        address = parts[4][2:]
        if len(address) < 1:
            raise ValueError(f"Invalid address format: {parts[4]}")

        shifted_address = MMIOParseLogic.last_char_to_shift_amount(parts[4], address[-1])[0][0]

        try:
            return OrderedDict(
                [
                    ("operation", parts[0]),
                    ("counter", int(parts[1])),
                    ("timestamp", float(parts[2])),
                    ("bar_number", int(parts[3])),
                    ("address", shifted_address),
                    ("value", parts[5][2:]),
                ]
            )
        except (ValueError, IndexError) as e:
            raise ValueError(f"Error parsing line values: {str(e)}")
