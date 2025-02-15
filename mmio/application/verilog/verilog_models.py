"""Verilog models for pre-generated Verilog code."""

from io import StringIO

from pydantic import BaseModel, ConfigDict, Field, field_validator

from mmio.core.logger import LoggerManager

logger = LoggerManager.get_logger(__name__)


class VerilogModelBase(BaseModel):
    """Base class for all Verilog models with bar number."""

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)


class VerilogGenerator(VerilogModelBase):
    """Enhanced base generator with dynamic content support."""

    bar_number: int

    @classmethod
    def get_available_bars(cls) -> list[int]:
        """Get list of BARs available for this generator.

        Returns:
            List[int]: List of available BAR numbers

        """
        return []

    def get_verilog_content(self, operation: str | None = None, field_type: str | None = None) -> StringIO:
        """Get Verilog content from a StringIO field.

        This method provides a generic way to access StringIO content from fields
        following the pattern verilog_[operation]_[field_type].

        Args:
            operation: Optional operation type ("read" or "write")
            field_type: Optional field type (e.g., "rom", "counter", "cases", etc.)
                        If None, looks for a field containing "header"

        Returns:
            StringIO content from the matching field

        Raises:
            ValueError: If operation is provided but invalid or if field not found

        """
        if operation and operation.lower() not in ["read", "write"]:
            raise ValueError("Operation must be 'read' or 'write' if provided")

        field_name = "verilog"
        if operation and field_type:
            field_name += f"_{operation.lower()}_{field_type}"
        elif not operation and not field_type:
            for name in self.model_fields:
                if "header" in name.lower():
                    field_name = name
                    break
                if "rom_init" in name.lower():
                    field_name = name
                    break
                if "state_machine" in name.lower():
                    field_name = name
                    break
                if "reset_counter" in name.lower():
                    field_name = name
                    break
        else:
            field_name += f"_{field_type}"

        logger.info(f"Looking for field: {field_name}")

        try:
            value = getattr(self, field_name)
            if isinstance(value, StringIO):
                logger.info(f"Found StringIO field {field_name} with content: {value.getvalue()}")
                result = StringIO()
                result.write(value.getvalue())
                result.seek(0)
                return result
            else:
                logger.warning(f"Field {field_name} exists but is not StringIO: {type(value)}")
        except AttributeError:
            logger.warning(f"Field {field_name} not found")

        logger.warning(f"Returning empty StringIO for {field_name}")
        return StringIO()

    def set_bar_data(
        self,
        addresses: list[str],
        bit_widths: dict[str, int],
        read_values: list[str],
        write_values: list[str],
        defaults: tuple[str, str],
    ) -> None:
        """Set BAR-specific data for the generator.

        Args:
            addresses: List of addresses for this BAR
            bit_widths: Dictionary mapping addresses to their required bit widths
            read_values: List of read values for this BAR
            write_values: List of write values for this BAR
            defaults: Tuple of (read_default, write_default) values

        """
        logger.info(f"Setting BAR {self.bar_number} data:")
        logger.info(f"Addresses: {addresses}")
        logger.info(f"Bit widths: {bit_widths}")
        logger.info(f"Read values: {read_values}")
        logger.info(f"Write values: {write_values}")
        logger.info(f"Defaults: {defaults}")

        self._addresses = addresses
        self._bit_widths = bit_widths
        self._read_values = read_values
        self._write_values = write_values
        self._defaults = defaults

    @property
    def addresses(self) -> list[str]:
        """Get addresses for current BAR."""
        return getattr(self, "_addresses", [])

    @property
    def bit_widths(self) -> dict[str, int]:
        """Get bit widths for current BAR."""
        return getattr(self, "_bit_widths", {})

    @property
    def read_values(self) -> list[str]:
        """Get read values for current BAR."""
        return getattr(self, "_read_values", [])

    @property
    def write_values(self) -> list[str]:
        """Get write values for current BAR."""
        return getattr(self, "_write_values", [])

    @property
    def defaults(self) -> tuple[str, str]:
        """Get default values (read, write) for current BAR."""
        return getattr(self, "_defaults", ("00000000", "00000000"))

    def get_unique_sorted_addresses(self, addresses: list[str]) -> list[str]:
        """Helper function to deduplicate and sort addresses."""
        return sorted(set(addresses))


class VerilogStatic(VerilogGenerator):
    """Data class with pre-generated static code for read/write operations."""

    verilog_header: StringIO = Field(default_factory=StringIO)
    verilog_state_machine_start: StringIO = Field(default_factory=StringIO)
    verilog_state_machine_end: StringIO = Field(default_factory=StringIO)

    @field_validator("verilog_header", "verilog_state_machine_start", "verilog_state_machine_end")
    @classmethod
    def validate_static(cls, value: StringIO) -> StringIO:
        """Validate static code format."""
        return value


class ROMEntry(VerilogGenerator):
    """Data class with pre-generated ROM entries for read/write operations."""

    verilog_read_rom: StringIO = Field(default_factory=StringIO)
    verilog_write_rom: StringIO = Field(default_factory=StringIO)
    verilog_read_rom_init: StringIO = Field(default_factory=StringIO)
    verilog_write_rom_init: StringIO = Field(default_factory=StringIO)

    @field_validator("verilog_read_rom", "verilog_write_rom", "verilog_read_rom_init", "verilog_write_rom_init")
    @classmethod
    def validate_rom(cls, value: StringIO) -> StringIO:
        """Validate ROM format."""
        return value

    def get_rom_name(self, address: str, operation: str) -> str:
        """Get ROM name for a specific address and operation."""
        return f"{operation.upper()}_{address}"


class AddressCheckEntry(VerilogGenerator):
    """Data class with pre-generated address checks for read/write operations."""

    verilog_read_addr_check: StringIO = Field(default_factory=StringIO)
    verilog_write_addr_check: StringIO = Field(default_factory=StringIO)

    @field_validator("verilog_read_addr_check", "verilog_write_addr_check")
    @classmethod
    def validate_address(cls, value: StringIO) -> StringIO:
        """Validate address format."""
        return value


class CounterEntry(VerilogGenerator):
    """Data class with pre-generated counters for read/write operations."""

    verilog_read_counter: StringIO = Field(default_factory=StringIO)
    verilog_write_counter: StringIO = Field(default_factory=StringIO)
    verilog_reset_read_counter: StringIO = Field(default_factory=StringIO)
    verilog_reset_write_counter: StringIO = Field(default_factory=StringIO)

    @field_validator(
        "verilog_read_counter",
        "verilog_write_counter",
        "verilog_reset_read_counter",
        "verilog_reset_write_counter",
    )
    @classmethod
    def validate_counter(cls, value: StringIO) -> StringIO:
        """Validate counter format."""
        return value

    def get_counter_name(self, address: str, operation: str) -> str:
        """Get counter name for a specific address and operation."""
        return f"{operation.upper()}_C_{address}"


class LogicEntries(VerilogGenerator):
    """Data class with pre-generated logic for read/write operations."""

    verilog_read_cases: StringIO = Field(default_factory=StringIO)
    verilog_write_cases: StringIO = Field(default_factory=StringIO)

    @field_validator("verilog_read_cases", "verilog_write_cases")
    @classmethod
    def validate_cases(cls, value: StringIO) -> StringIO:
        """Validate cases format."""
        return value
