"""Generator module for Verilog logic operations."""

from io import StringIO

from pydantic import Field

from mmio.application.verilog.verilog_models import (
    CounterEntry,
    LogicEntries,
    ROMEntry,
    VerilogGenerator,
)
from mmio.core.logger import LoggerManager
from mmio.domain.models.verilog_data import VerilogData

logger = LoggerManager.get_logger(__name__)


class ResponseLogicGenerator(VerilogGenerator):
    """Generate response logic for Verilog."""

    verilog_data: VerilogData = Field(default_factory=VerilogData)

    verilog_logic: LogicEntries = Field(
        default_factory=lambda: LogicEntries(
            bar_number=0,
            verilog_read_cases=StringIO(),
            verilog_write_cases=StringIO(),
        )
    )

    def generate_read_logic(self, bar_number: int, rom_entry: ROMEntry, counter_entry: CounterEntry) -> None:
        """Generate read operation logic."""
        read_addrs = {
            data.address: data.value
            for data in VerilogData.get_all_instances()
            if data.operation == "R" and data.address is not None and data.bar == bar_number
        }

        if not read_addrs:
            return

        sio = StringIO()
        sio.write("            if (drd_req_valid && read_addr_check(local_read_addr)) begin\n")
        sio.write("                case(local_read_addr)\n")

        default_value = self.verilog_data.get_default_values(bar_number)[0]
        for addr in sorted(read_addrs.keys()):
            rom_name = rom_entry.get_rom_name(addr, "R")
            counter_name = counter_entry.get_counter_name(addr, "R")

            count = sum(1 for data in VerilogData.get_all_instances() if data.address == addr and data.operation == "R")

            if count > 1:
                counter_width = (count).bit_length()
                sio.write(f"                    16'h{addr}: begin\n")
                sio.write(
                    f"                        {counter_name} <= ({counter_name} == {counter_width}'d{count - 1}) ? "
                )
                sio.write(f"{counter_width}'d0 : {counter_name} + 1;\n")
                sio.write(f"                        rd_rsp_data <= {rom_name}[{counter_name}];\n")
                sio.write("                    end\n")
            else:
                sio.write(f"                    16'h{addr}: rd_rsp_data <= {rom_name}[0];\n")

        sio.write(f"                    default: rd_rsp_data <= 32'h{default_value};\n")
        sio.write("                endcase\n")
        sio.write(f"                rd_rsp_data <= 32'h{default_value};\n")
        sio.write("            end\n")

        self.verilog_logic.verilog_read_cases = sio

    def generate_write_logic(self, bar_number: int, rom_entry: ROMEntry, counter_entry: CounterEntry) -> None:
        """Generate write operation logic."""
        write_addrs = {
            data.address: data.value
            for data in VerilogData.get_all_instances()
            if data.operation == "W" and data.address is not None and data.bar == bar_number
        }

        if not write_addrs:
            return

        sio = StringIO()
        sio.write("            if (dwr_valid && write_addr_check(local_write_addr)) begin\n")
        sio.write("                case(local_write_addr)\n")

        default_value = self.verilog_data.get_default_values(bar_number)[1]
        for addr in sorted(write_addrs.keys()):
            rom_name = rom_entry.get_rom_name(addr, "W")
            counter_name = counter_entry.get_counter_name(addr, "W")

            count = sum(1 for data in VerilogData.get_all_instances() if data.address == addr and data.operation == "W")

            if count > 1:
                counter_width = (count).bit_length()
                sio.write(f"                    16'h{addr}: begin\n")
                sio.write(
                    f"                        {counter_name} <= ({counter_name} == {counter_width}'d{count - 1}) ? "
                )
                sio.write(f"{counter_width}'d0 : {counter_name} + 1;\n")
                sio.write(f"                        {rom_name}[{counter_name}] <= dwr_data;\n")
                sio.write("                    end\n")
            else:
                sio.write(f"                    16'h{addr}: {rom_name}[0] <= dwr_data;\n")

        sio.write(f"                    default: wr_data_out <= 32'h{default_value};\n")
        sio.write("                endcase\n")
        sio.write("            end\n")
        sio.write("        end\n")
        sio.write("    end\n")
        self.verilog_logic.verilog_write_cases = sio

    def generate_verilog_logic(self, bar_number: int, rom_entry: ROMEntry, counter_entry: CounterEntry) -> LogicEntries:
        """Generate all Verilog logic for a specific BAR."""
        self.generate_read_logic(bar_number, rom_entry, counter_entry)
        self.generate_write_logic(bar_number, rom_entry, counter_entry)
        return self.verilog_logic
