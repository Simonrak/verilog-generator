"""Generate Verilog code for counters."""

from io import StringIO

from pydantic import Field

from mmio.application.verilog.verilog_models import CounterEntry, VerilogGenerator
from mmio.core.logger import LoggerManager
from mmio.domain.models.verilog_data import VerilogData

logger = LoggerManager.get_logger(__name__)


class CounterGenerator(VerilogGenerator):
    """Generate Verilog code for counters."""

    verilog_data: VerilogData = Field(default_factory=VerilogData)

    verilog_counter: CounterEntry = Field(
        default_factory=lambda: CounterEntry(
            bar_number=0,
            verilog_read_counter=StringIO(),
            verilog_write_counter=StringIO(),
            verilog_reset_read_counter=StringIO(),
            verilog_reset_write_counter=StringIO(),
        )
    )

    def generate_read_counters(self, bar_number: int) -> None:
        """Generate read counter declarations for a specific BAR."""
        read_addrs = [
            data.address
            for data in VerilogData.get_all_instances()
            if data.operation == "R" and data.address is not None and data.bar == bar_number
        ]

        if not read_addrs:
            return

        sio = StringIO()
        unique_read_addrs = self.get_unique_sorted_addresses(read_addrs)
        for addr in unique_read_addrs:
            counter_name = f"R_C_{addr}"
            width = self.calculate_counter_width(addr, "R")
            sio.write(f"    bit [{width - 1}:0] {counter_name};\n")

        self.verilog_counter.verilog_read_counter = sio

    def generate_write_counters(self, bar_number: int) -> None:
        """Generate write counter declarations for a specific BAR."""
        write_addrs = [
            data.address
            for data in VerilogData.get_all_instances()
            if data.operation == "W" and data.address is not None and data.bar == bar_number
        ]

        if not write_addrs:
            return

        sio = StringIO()
        unique_write_addrs = self.get_unique_sorted_addresses(write_addrs)
        for addr in unique_write_addrs:
            counter_name = f"W_C_{addr}"
            width = self.calculate_counter_width(addr, "W")
            sio.write(f"    bit [{width - 1}:0] {counter_name};\n")

        self.verilog_counter.verilog_write_counter = sio

    def calculate_counter_width(self, address: str, operation: str) -> int:
        """Calculate required bit width for counter at a specific address."""
        count = sum(
            1 for data in VerilogData.get_all_instances() if data.address == address and data.operation == operation
        )
        return max(1, (count).bit_length())

    def reset_read_counters(self, bar_number: int) -> None:
        """Generate reset logic for read counters."""
        read_addrs: list[str] = [
            data.address
            for data in VerilogData.get_all_instances()
            if data.operation == "R" and data.address is not None and data.bar == bar_number
        ]

        if not read_addrs:
            return

        sio = StringIO()

        unique_read_addrs = self.get_unique_sorted_addresses(read_addrs)
        for addr in unique_read_addrs:
            counter_name = f"R_C_{addr}"
            sio.write(f"            {counter_name} <= '0;\n")
        self.verilog_counter.verilog_reset_read_counter = sio

    def reset_write_counters(self, bar_number: int) -> None:
        """Generate reset logic for write counters."""
        write_addrs: list[str] = [
            data.address
            for data in VerilogData.get_all_instances()
            if data.operation == "W" and data.address is not None and data.bar == bar_number
        ]

        if not write_addrs:
            return

        sio = StringIO()
        unique_write_addrs = self.get_unique_sorted_addresses(write_addrs)
        for addr in unique_write_addrs:
            counter_name = f"W_C_{addr}"
            sio.write(f"            {counter_name} <= '0;\n")
        self.verilog_counter.verilog_reset_write_counter = sio

    def generate_verilog_counter(self, bar_number: int) -> CounterEntry:
        """Generate Verilog code for counter module for a specific BAR."""
        self.generate_read_counters(bar_number)
        self.generate_write_counters(bar_number)

        return self.verilog_counter

    def generate_reset_counter(self, bar_number: int) -> CounterEntry:
        """Generate reset logic for counters."""
        self.reset_read_counters(bar_number)
        self.reset_write_counters(bar_number)

        return self.verilog_counter
