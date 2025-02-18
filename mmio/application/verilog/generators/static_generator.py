"""Verilog module header generator."""

from io import StringIO

from pydantic import Field

from mmio.application.verilog.verilog_models import VerilogGenerator, VerilogStatic
from mmio.config.verilog_settings import VerilogSettings
from mmio.core.logger import LoggerManager

logger = LoggerManager.get_logger(__name__)


class StaticCodeGenerator(VerilogGenerator):
    """Verilog module static code generator.

    This class generates the Verilog module static code with all required ports
    for MMIO operations. It handles the generation of standard PCIe BAR
    implementation module static code.
    """

    static_code: VerilogStatic = Field(
        default_factory=lambda: VerilogStatic(
            bar_number=0,
            verilog_header=StringIO(),
            verilog_state_machine_start=StringIO(),
            verilog_state_machine_end=StringIO(),
        )
    )

    verilog_settings: VerilogSettings = Field(default_factory=lambda: VerilogSettings.get_instance())
    save_header: StringIO = Field(default_factory=StringIO)

    def generate_module_header(self) -> VerilogStatic:
        """Generate the Verilog module header with all ports."""
        self.save_header.seek(0)
        self.save_header.truncate()

        self.save_header.write(f"module pcileech_bar_impl_{self.verilog_settings.module_header}_{self.bar_number}(\n")
        self.save_header.write("    input               rst,\n")
        self.save_header.write("    input               clk,\n")
        self.save_header.write("    // incoming BAR writes:\n")
        self.save_header.write("    input [31:0]        wr_addr,\n")
        self.save_header.write("    input [3:0]         wr_be,\n")
        self.save_header.write("    input [31:0]        wr_data,\n")
        self.save_header.write("    input               wr_valid,\n")
        self.save_header.write("    // incoming BAR reads:\n")
        self.save_header.write("    input  [87:0]       rd_req_ctx,\n")
        self.save_header.write("    input  [31:0]       rd_req_addr,\n")
        self.save_header.write("    input               rd_req_valid,\n")
        self.save_header.write("    input  [31:0]       base_address_register,\n")
        self.save_header.write("    // outgoing BAR read replies:\n")
        self.save_header.write("    output logic [87:0] rd_rsp_ctx,\n")
        self.save_header.write("    output logic [31:0] rd_rsp_data,\n")
        self.save_header.write("    output logic        rd_rsp_valid\n")
        self.save_header.write(");\n\n")
        self.save_header.write("    bit [87:0]      drd_req_ctx;\n")
        self.save_header.write("    bit [31:0]      drd_req_addr;\n")
        self.save_header.write("    bit             drd_req_valid;\n")
        self.save_header.write("\n")
        self.save_header.write("    bit [31:0]      dwr_addr;\n")
        self.save_header.write("    bit [31:0]      dwr_data;\n")
        self.save_header.write("    bit             dwr_valid;\n")
        self.save_header.write("    bit [31:0]      wr_data_out;\n")
        self.save_header.write("\n")
        self.save_header.write("    wire [15:0]     local_read_addr;\n")
        self.save_header.write("    wire [15:0]     local_write_addr;\n")
        self.save_header.write("\n")
        self.save_header.write("    assign local_read_addr = ({drd_req_addr[31:24], drd_req_addr[23:16],\n")
        self.save_header.write("                                drd_req_addr[15:8], drd_req_addr[7:0]} -\n")
        self.save_header.write("                                (base_address_register & ~32'hFFF)) & 20'hFFFFF;\n")
        self.save_header.write("\n")
        self.save_header.write("    assign local_write_addr = ({dwr_addr[31:24], dwr_addr[23:16],\n")
        self.save_header.write("                                dwr_addr[15:8], dwr_addr[7:0]} -\n")
        self.save_header.write("                                (base_address_register & ~32'hFFF)) & 20'hFFFFF;\n")
        self.save_header.write("\n\n")

        self.static_code.verilog_header = StringIO(self.save_header.getvalue())
        return self.static_code

    save_state_machine: StringIO = Field(default_factory=StringIO)

    def generate_state_machine_start(self) -> VerilogStatic:
        """Generate the Verilog state machine with all ports."""
        self.save_state_machine.seek(0)
        self.save_state_machine.truncate()

        self.save_state_machine.write("    always_ff @(posedge clk) begin\n")
        self.save_state_machine.write("        if (rst) begin\n")
        self.save_state_machine.write("            rd_rsp_valid <= 1'b0;\n")

        self.static_code.verilog_state_machine_start = StringIO(self.save_state_machine.getvalue())
        return self.static_code

    def generate_state_machine_end(self) -> VerilogStatic:
        """Generate the Verilog state machine end."""
        self.save_state_machine.seek(0)
        self.save_state_machine.truncate()

        self.save_state_machine.write("    end else begin\n")
        self.save_state_machine.write("        drd_req_ctx     <= rd_req_ctx;\n")
        self.save_state_machine.write("        drd_req_valid   <= rd_req_valid;\n")
        self.save_state_machine.write("        dwr_valid       <= wr_valid;\n")
        self.save_state_machine.write("        drd_req_addr    <= rd_req_addr;\n")
        self.save_state_machine.write("        rd_rsp_ctx      <= drd_req_ctx;\n")
        self.save_state_machine.write("        rd_rsp_valid    <= drd_req_valid;\n")
        self.save_state_machine.write("        dwr_addr        <= wr_addr;\n")
        self.save_state_machine.write("        dwr_data        <= wr_data;\n")

        self.static_code.verilog_state_machine_end = StringIO(self.save_state_machine.getvalue())
        return self.static_code
