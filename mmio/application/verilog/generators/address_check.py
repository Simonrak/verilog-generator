"""Generator module for Verilog ROM address checking functions."""

from io import StringIO

from pydantic import Field

from mmio.application.verilog.verilog_models import AddressCheckEntry, VerilogGenerator
from mmio.core.logger import LoggerManager
from mmio.domain.models.verilog_data import VerilogData

logger = LoggerManager.get_logger(__name__)


class AddressCheckGenerator(VerilogGenerator):
    """Generate ROM address checking functions and save them in an AddressCheckEntry."""

    verilog_data: VerilogData = Field(default_factory=VerilogData)

    verilog_address_check: AddressCheckEntry = Field(
        default_factory=lambda: AddressCheckEntry(
            bar_number=0,
            verilog_read_addr_check=StringIO(),
            verilog_write_addr_check=StringIO(),
        )
    )

    def generate_read_address_check(self, bar_number: int) -> None:
        """Generate read address check function for specific BAR."""
        read_addrs = [
            data.address
            for data in VerilogData.get_all_instances()
            if data.operation == "R" and data.address is not None and data.bar == bar_number
        ]
        sorted_read = self.get_unique_sorted_addresses(read_addrs)

        sio_read = StringIO()
        if sorted_read:
            sio_read.write("    function read_addr_check;\n")
            sio_read.write("        input [19:0] addr;\n")
            sio_read.write("        begin\n")
            sio_read.write("            case (addr)\n")
            for i in range(0, len(sorted_read), 8):
                addr_group = sorted_read[i : i + 8]
                sio_read.write("                ")
                sio_read.write(", ".join(f"20'h{addr.zfill(4)}" for addr in addr_group))
                if i + 8 < len(sorted_read):
                    sio_read.write(",\n")
                else:
                    sio_read.write(":\n")
            sio_read.write("                    read_addr_check = 1'b1;\n")
            sio_read.write("                default: read_addr_check = 1'b0;\n")
            sio_read.write("            endcase\n")
            sio_read.write("        end\n")
            sio_read.write("    endfunction\n\n")

        self.verilog_address_check.verilog_read_addr_check = StringIO(sio_read.getvalue())
        self.verilog_address_check.verilog_read_addr_check.seek(0)

    def generate_write_address_check(self, bar_number: int) -> None:
        """Generate write address check function for specific BAR."""
        write_addrs = [
            data.address
            for data in VerilogData.get_all_instances()
            if data.operation == "W" and data.address is not None and data.bar == bar_number
        ]
        sorted_write = self.get_unique_sorted_addresses(write_addrs)

        sio_write = StringIO()
        if sorted_write:
            sio_write.write("    function write_addr_check;\n")
            sio_write.write("        input [19:0] addr;\n")
            sio_write.write("        begin\n")
            sio_write.write("            case (addr)\n")
            for i in range(0, len(sorted_write), 8):
                addr_group = sorted_write[i : i + 8]
                sio_write.write("                ")
                sio_write.write(", ".join(f"20'h{addr.zfill(4)}" for addr in addr_group))
                if i + 8 < len(sorted_write):
                    sio_write.write(",\n")
                else:
                    sio_write.write(":\n")
            sio_write.write("                    write_addr_check = 1'b1;\n")
            sio_write.write("                default: write_addr_check = 1'b0;\n")
            sio_write.write("            endcase\n")
            sio_write.write("        end\n")
            sio_write.write("    endfunction\n\n")

        self.verilog_address_check.verilog_write_addr_check = StringIO(sio_write.getvalue())
        self.verilog_address_check.verilog_write_addr_check.seek(0)

    def generate_address_check_entry(self, bar_number: int) -> AddressCheckEntry:
        """Generate a consolidated AddressCheckEntry with one read and one write function per BAR."""
        self.verilog_address_check.bar_number = bar_number
        self.generate_read_address_check(bar_number)
        self.generate_write_address_check(bar_number)

        return self.verilog_address_check
