"""Custom exceptions for MMIO parser error handling.

This module provides a comprehensive set of exceptions for handling various
error scenarios in MMIO parsing operations.
"""

from mmio.core.logger import LoggerManager

logger = LoggerManager.get_logger(__name__)


class MMIOParserError(Exception):
    """Base exception class for MMIO parser errors.

    All other MMIO-related exceptions should inherit from this class.
    """

    def __init__(self, message: str, line_number: int | None = None) -> None:
        """Initialize the error with an optional line number.

        Args:
            message: Detailed error description
            line_number: Optional line number where the error occurred

        """
        self.line_number = line_number
        super().__init__(f"Line {line_number}: {message}" if line_number else message)


class ValidationError(MMIOParserError):
    """Raised when MMIO data validation fails.

    Examples:
        - Invalid address format
        - Invalid operation type
        - Out of range values

    """

    pass


class FileAccessError(MMIOParserError):
    """Raised when there are issues accessing MMIO files.

    Examples:
        - File not found
        - Permission denied
        - File is empty

    """

    pass
