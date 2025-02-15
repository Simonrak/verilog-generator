"""ROM module."""

from io import StringIO

from pydantic import Field

from mmio.application.verilog.verilog_models import ROMEntry, VerilogGenerator
from mmio.core.logger import LoggerManager
from mmio.domain.models.verilog_data import VerilogData

logger = LoggerManager.get_logger(__name__)


class ROMGenerator(VerilogGenerator):
    """ROM module.

    This class generates ROM structures for MMIO operations.
    Each unique address in a BAR gets its own ROM with a bit width determined by
    the maximum value seen at that address.

    ROM definitions and value assignments are stored separately:
    - Definitions go into ROMEntry.verilog_read_rom/verilog_write_rom
    - Value assignments can be accessed via get_rom_assignments()
    """

    verilog_data: VerilogData = Field(default_factory=VerilogData)

    verilog_rom: ROMEntry = Field(
        default_factory=lambda: ROMEntry(
            bar_number=0,
            verilog_read_rom=StringIO(),
            verilog_write_rom=StringIO(),
            verilog_read_rom_init=StringIO(),
            verilog_write_rom_init=StringIO(),
        )
    )

    read_assignments: StringIO = Field(default_factory=StringIO)
    write_assignments: StringIO = Field(default_factory=StringIO)
    read_rom_init: StringIO = Field(default_factory=StringIO)
    write_rom_init: StringIO = Field(default_factory=StringIO)

    def get_rom_values_for_address(self, bar: int, address: str, operation: str) -> list[str]:
        """Get all values for a specific address and operation.

        Args:
            bar: BAR number
            address: Address to get values for
            operation: "R" for read values, "W" for write values

        Returns:
            List of values seen at this address for this operation

        """
        return [
            data.value
            for data in VerilogData.get_all_instances()
            if (data.bar == bar and data.address == address and data.operation == operation and data.value is not None)
        ]

    def generate_read_roms(self, bar_number: int) -> None:
        """Generate read ROM declarations for a specific BAR."""
        logger.info("Creating new read ROM")
        self.verilog_rom.verilog_read_rom.seek(0)
        self.verilog_rom.verilog_read_rom.truncate()
        self.read_assignments = StringIO()

        address_widths = self.verilog_data.get_bar_address_bit_widths(bar_number)
        read_addrs = [
            data.address
            for data in VerilogData.get_all_instances()
            if data.operation == "R" and data.address is not None and data.bar == bar_number
        ]
        unique_read_addrs = self.get_unique_sorted_addresses(read_addrs)

        for address in unique_read_addrs:
            bit_width = address_widths.get(address, 0)
            values = self.get_rom_values_for_address(bar_number, address, "R")
            if not values:
                continue

            rom_name = f"R_{address}"
            size = len(values)

            self.verilog_rom.verilog_read_rom.write(f"    bit [{bit_width - 1}:0] {rom_name} [0:{size - 1}];\n")

    def generate_write_roms(self, bar_number: int) -> None:
        """Generate write ROM declarations for a specific BAR."""
        logger.info("Creating new write ROM")
        self.verilog_rom.verilog_write_rom.seek(0)
        self.verilog_rom.verilog_write_rom.truncate()
        self.write_assignments = StringIO()

        address_widths = self.verilog_data.get_bar_address_bit_widths(bar_number)
        write_addrs = [
            data.address
            for data in VerilogData.get_all_instances()
            if data.operation == "W" and data.address is not None and data.bar == bar_number
        ]
        unique_write_addrs = self.get_unique_sorted_addresses(write_addrs)

        for address in unique_write_addrs:
            bit_width = address_widths.get(address, 0)
            values = self.get_rom_values_for_address(bar_number, address, "W")
            if not values:
                continue

            rom_name = f"W_{address}"
            size = len(values)

            self.verilog_rom.verilog_write_rom.write(f"    bit [{bit_width - 1}:0] {rom_name} [0:{size - 1}];\n")

    def get_address_value_pairs(self, bar_number: int, operation: str) -> dict[str, list[str]]:
        """Get all address-value pairs for a given BAR and operation.

        Args:
            bar_number: BAR number to get values for
            operation: 'R' for read values, 'W' for write values

        Returns:
            Dictionary mapping addresses to their values (including duplicates)

        """
        address_values: dict[str, list[str]] = {}
        for data in VerilogData.get_all_instances():
            if (
                data.bar == bar_number
                and data.operation == operation
                and data.address is not None
                and data.value is not None
            ):
                if data.address not in address_values:
                    address_values[data.address] = []
                address_values[data.address].append(data.value)
        return address_values

    def initialize_read_roms(self, bar_number: int) -> None:
        """Initialize read ROM values."""
        logger.info("Creating new read ROM initialization")
        self.verilog_rom.verilog_read_rom_init.seek(0)
        self.verilog_rom.verilog_read_rom_init.truncate()

        address_values = self.get_address_value_pairs(bar_number, "R")
        logger.info(f"Found values for addresses in BAR {bar_number}: {address_values.keys()}")

        for address, values in address_values.items():
            rom_name = f"R_{address}"
            logger.debug(f"Initializing read ROM {rom_name} with {len(values)} values")
            for i, value in enumerate(values):
                self.verilog_rom.verilog_read_rom_init.write(f"            {rom_name}[{i}] <= 32'h{value};\n")
        self.verilog_rom.verilog_read_rom_init.write("\n")
        self.verilog_rom.verilog_read_rom_init.seek(0)

    def initialize_write_roms(self, bar_number: int) -> None:
        """Initialize write ROM values."""
        logger.info("Creating new write ROM initialization")
        self.verilog_rom.verilog_write_rom_init.seek(0)
        self.verilog_rom.verilog_write_rom_init.truncate()

        address_values = self.get_address_value_pairs(bar_number, "W")
        logger.info(f"Found values for addresses in BAR {bar_number}: {address_values.keys()}")

        for address, values in address_values.items():
            rom_name = f"W_{address}"
            logger.debug(f"Initializing write ROM {rom_name} with {len(values)} values")
            for i, value in enumerate(values):
                self.verilog_rom.verilog_write_rom_init.write(f"            {rom_name}[{i}] <= 32'h{value};\n")
        self.verilog_rom.verilog_write_rom_init.write("\n")
        self.verilog_rom.verilog_write_rom_init.seek(0)

    def generate_rom_structure(self, bar_number: int) -> None:
        """Generate all ROM declarations and assignments for a specific BAR."""
        logger.info("Generating ROM structure")
        self.generate_read_roms(bar_number)
        self.generate_write_roms(bar_number)

    def generate_rom_init(self, bar_number: int) -> None:
        """Generate all ROM initializations for a specific BAR."""
        logger.info("Generating ROM initialization")
        self.initialize_read_roms(bar_number)
        self.initialize_write_roms(bar_number)

    def get_rom_assignments(self, operation: str = "R") -> str:
        """Get ROM value assignments for use in state machine.

        Args:
            operation: "R" for read assignments, "W" for write assignments

        Returns:
            String containing all ROM value assignments

        """
        if operation == "R":
            return self.read_assignments.getvalue()
        elif operation == "W":
            return self.write_assignments.getvalue()
        else:
            raise ValueError("Operation must be 'R' or 'W'")
