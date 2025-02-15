from typing import Any

from pydantic import BaseModel, Field

from mmio.application.verilog.verilog_builder_orchestrator import VerilogBuilderOrchestrator
from mmio.config.cli_config import CLIOptions
from mmio.core.logger import LoggerManager
from mmio.domain.models.verilog_data import VerilogData
from mmio.domain.services.orchestrators.input_orchestrator import InputOrchestrator
from mmio.domain.services.orchestrators.output_orchestrator import OutputOrchestrator

logger = LoggerManager.get_logger(__name__)


class ModularOrchestrator(BaseModel):
    """Master orchestrator that integrates Input, Verilog build, and Output operations."""

    input_orch: InputOrchestrator = Field(default_factory=InputOrchestrator)
    verilog_orch: VerilogBuilderOrchestrator = Field(default_factory=VerilogBuilderOrchestrator)
    output_orch: OutputOrchestrator = Field(default_factory=OutputOrchestrator)
    verilog_code: str = Field(default="")

    def run(
        self,
        which_steps: list[str] | None = None,
        cli_options: CLIOptions | None = None,
    ) -> None:
        """Execute orchestrated operations."""
        steps = set(which_steps) if which_steps is not None else {"input", "build", "output"}
        options: CLIOptions = cli_options or CLIOptions()
        logger.info(f"Starting orchestration with steps: {steps}")
        logger.info(f"CLI options: {options}")

        bar_data = self.input(steps=list(steps))

        self.build(bar_data=bar_data, steps=list(steps), options=options, include_logic=options.include_logic)
        self.output(verilog_code=self.verilog_code, steps=list(steps))

    def input(self, steps: list[str]) -> dict[Any, Any] | None:
        """Input the data."""
        if "input" in steps:
            logger.info("Starting input step")
            bar_data = self._execute_input_step()
            if bar_data:
                self._process_bar_data(bar_data)
            return bar_data
        return None

    def _execute_input_step(self) -> dict[Any, Any] | None:
        """Execute the input step and handle any errors."""
        logger.debug(
            f"Input orchestrator file manager state - input_path: "
            f"{self.input_orch.mmio_file_manager.input_manager.file_manager.path}, "
            f"input_file_name: {self.input_orch.mmio_file_manager.input_manager.file_manager.file_name}"
        )
        try:
            bar_data = self.input_orch.execute()
            if not bar_data:
                logger.warning("No data received from input orchestrator")
                logger.debug("Input orchestrator returned empty or None result")
            return bar_data
        except Exception as e:
            logger.error(f"Error during input step: {e}", exc_info=True)
            logger.error(
                "Input orchestrator state at error - "
                f"input_path: {self.input_orch.mmio_file_manager.input_manager.file_manager.path}, "
                f"input_file_name: {self.input_orch.mmio_file_manager.input_manager.file_manager.file_name}"
            )
            raise

    def _process_bar_data(self, bar_data: dict[Any, Any]) -> None:
        """Process and log BAR data."""
        logger.debug(f"Processed data for {len(bar_data)} BARs")
        logger.debug(f"Available BAR numbers: {list(bar_data.keys())}")
        for bar_num, entries in bar_data.items():
            logger.debug(f"BAR {bar_num}: {len(entries)} entries")
            if entries:
                logger.debug(f"First entry in BAR {bar_num}: {entries[0]}")
                logger.debug(
                    f"Sample fields from first entry: address={entries[0].address}, operation={entries[0].operation}"
                )

    def build(
        self,
        bar_data: dict[Any, Any] | None,
        steps: list[str],
        options: CLIOptions,
        include_logic: bool = True,
    ) -> None:
        """Build the Verilog code."""
        if "build" in steps:
            logger.info("Starting build step")
            if bar_data is None:
                logger.warning("No input data available, using empty dict")
                logger.debug("Bar data is None, this might indicate an issue with the input step")
                bar_data = {}

            logger.info("Generating Verilog code")
            logger.debug(f"Passing bar_data to build_verilog: {list(bar_data.keys()) if bar_data else 'empty'}")
            self.verilog_code = self.build_verilog(
                processed_data=bar_data, cli_options=options, include_logic=include_logic
            )
            if self.verilog_code:
                logger.debug(f"Generated Verilog code (size: {len(self.verilog_code)} bytes)")
                logger.debug(f"First 100 chars of generated code: {self.verilog_code[:100]}")
            else:
                logger.warning("No Verilog code was generated")
                logger.error("build_verilog returned empty string")

    def output(self, verilog_code: str, steps: list[str]) -> None:
        """Output the generated Verilog code."""
        if "output" in steps:
            logger.info("Starting output step")
            if self.verilog_code:
                logger.info("Passing generated Verilog code to output orchestrator")
                try:
                    self.output_orch.output(self.verilog_code)
                    logger.info("Successfully passed code to output orchestrator")
                except Exception as e:
                    logger.error(f"Error in output step: {e}", exc_info=True)
                    raise
            else:
                logger.warning("No Verilog code available for output step")
                logger.info("verilog_code is empty or None")

    def _get_first_bar_entry(self, processed_data: dict[Any, Any]) -> Any | None:
        """Get the first entry from any BAR in the processed data."""
        logger.info(f"Input data contains {len(processed_data)} BARs")
        for entries in processed_data.values():
            if entries:
                return entries[0]
        return None

    def _initialize_verilog_data(self, first_entry: Any) -> bool:
        """Initialize VerilogData with the first entry."""
        if not first_entry:
            logger.warning("No VerilogData available")
            return False

        logger.info("Setting VerilogData in orchestrator")
        self.verilog_orch.set_verilog_data(first_entry)
        logger.info(f"Total VerilogData instances: {len(VerilogData.get_all_instances())}")
        logger.info(f"Available addresses: {VerilogData.addresses()}")
        logger.info(f"Address bit widths: {VerilogData.get_address_bit_widths()}")
        return True

    def _get_operation_flags(self, operation_filter: str) -> tuple[bool, bool]:
        """Determine which operations to generate based on operation filter."""
        generate_read = operation_filter in ["R", "B"]
        generate_write = operation_filter in ["W", "B"]
        logger.info(f"Operation filter: {operation_filter}, Generating read: {generate_read}, write: {generate_write}")
        return generate_read, generate_write

    def _generate_headers(
        self,
        bar_numbers: list[Any],
        processed_data: dict[Any, Any],
        include_logic: bool = True,
    ) -> list[str]:
        """Generate headers for each BAR."""
        lines: list[str] = []
        for bar_number in bar_numbers:
            if bar_number not in processed_data:
                continue
            lines.append(self.verilog_orch.build_verilog(operation="read", bar_number=bar_number, field_type="header"))
            lines.append("")
        return lines

    def _generate_state_machine_structures(
        self,
        bar_number: Any,
        processed_data: dict[Any, Any],
        field_type: str,
    ) -> list[str]:
        """Generate state machine structures for a BAR."""
        lines: list[str] = []
        if field_type == "state_machine_start":
            lines.append(
                self.verilog_orch.build_verilog(
                    operation=None,
                    bar_number=bar_number,
                    field_type=field_type,
                )
            )
            lines.append("")

        elif field_type == "state_machine_end":
            lines.append(
                self.verilog_orch.build_verilog(
                    operation=None,
                    bar_number=bar_number,
                    field_type=field_type,
                )
            )
            lines.append("")

        return lines

    def _append_code_block(
        self,
        lines: list[str],
        code: str,
        bar_number: Any,
        block_type: str,
        operation: str,
    ) -> None:
        """Append a code block with appropriate comments if it contains content."""
        if code.strip():
            lines.append(code)
            lines.append("")

    def _generate_rom_structures(
        self,
        bar_number: Any,
        generate_read: bool,
        generate_write: bool,
    ) -> list[str]:
        """Generate ROM structures for a BAR."""
        lines: list[str] = []
        logger.info("Generating ROM structure")
        if generate_read:
            rom_code = self.verilog_orch.build_verilog(operation="read", bar_number=bar_number, field_type="rom")
            self._append_code_block(lines, rom_code, bar_number, "ROM", "Read")
        if generate_write:
            rom_code = self.verilog_orch.build_verilog(operation="write", bar_number=bar_number, field_type="rom")
            self._append_code_block(lines, rom_code, bar_number, "ROM", "Write")
        return lines

    def _generate_rom_init_structures(
        self,
        bar_number: Any,
        generate_read: bool,
        generate_write: bool,
    ) -> list[str]:
        """Generate ROM init structures for a BAR."""
        lines: list[str] = []
        logger.info("Generating ROM init structure")
        if generate_read:
            rom_init_code = self.verilog_orch.build_verilog(
                operation="read", bar_number=bar_number, field_type="rom_init"
            )
            self._append_code_block(lines, rom_init_code, bar_number, "ROM Init", "Read")
        if generate_write:
            rom_init_code = self.verilog_orch.build_verilog(
                operation="write", bar_number=bar_number, field_type="rom_init"
            )
            self._append_code_block(lines, rom_init_code, bar_number, "ROM Init", "Write")
        return lines

    def _generate_verilog_logic(
        self,
        bar_number: Any,
        generate_read: bool,
        generate_write: bool,
    ) -> list[str] | None:
        """Generate Verilog logic for a BAR."""
        lines: list[str] = []
        logger.info("Generating Verilog logic")
        if generate_read:
            logic_code = self.verilog_orch.build_verilog(operation="read", bar_number=bar_number, field_type="logic")
            self._append_code_block(lines, logic_code, bar_number, "Logic", "Read")
        if generate_write:
            logic_code = self.verilog_orch.build_verilog(operation="write", bar_number=bar_number, field_type="logic")
            self._append_code_block(lines, logic_code, bar_number, "Logic", "Write")
        return lines

    def _generate_counter_structures(
        self,
        bar_number: Any,
        generate_read: bool,
        generate_write: bool,
    ) -> list[str]:
        """Generate counter structures for a BAR."""
        lines: list[str] = []
        logger.info("Generating counter structure")
        if generate_read:
            counter_code = self.verilog_orch.build_verilog(
                operation="read", bar_number=bar_number, field_type="counter"
            )
            self._append_code_block(lines, counter_code, bar_number, "Counter", "Read")
        if generate_write:
            counter_code = self.verilog_orch.build_verilog(
                operation="write", bar_number=bar_number, field_type="counter"
            )
            self._append_code_block(lines, counter_code, bar_number, "Counter", "Write")
        return lines

    def _generate_reset_counter_structures(
        self,
        bar_number: Any,
        generate_read: bool,
        generate_write: bool,
    ) -> list[str]:
        """Generate reset counter structures for a BAR."""
        lines: list[str] = []
        logger.info("Generating reset counter structure")
        if generate_read:
            reset_counter_code = self.verilog_orch.build_verilog(
                operation="read", bar_number=bar_number, field_type="reset_counter"
            )
            self._append_code_block(lines, reset_counter_code, bar_number, "Reset Counter", "Read")
        if generate_write:
            reset_counter_code = self.verilog_orch.build_verilog(
                operation="write", bar_number=bar_number, field_type="reset_counter"
            )
            self._append_code_block(lines, reset_counter_code, bar_number, "Reset Counter", "Write")
        return lines

    def _generate_address_check_structures(
        self,
        bar_number: Any,
        generate_read: bool,
        generate_write: bool,
    ) -> list[str]:
        """Generate address check structures for a BAR."""
        lines: list[str] = []
        logger.info("Generating address check structure")
        if generate_read:
            addr_check_code = self.verilog_orch.build_verilog(
                operation="read", bar_number=bar_number, field_type="addr_check"
            )
            self._append_code_block(lines, addr_check_code, bar_number, "Address Check", "Read")
        if generate_write:
            addr_check_code = self.verilog_orch.build_verilog(
                operation="write", bar_number=bar_number, field_type="addr_check"
            )
            self._append_code_block(lines, addr_check_code, bar_number, "Address Check", "Write")
        return lines

    def _generate_bar_structures(
        self,
        bar_numbers: list[Any],
        processed_data: dict[Any, Any],
        cli_options: CLIOptions,
        generate_read: bool,
        generate_write: bool,
    ) -> list[str]:
        """Generate all structures for each BAR."""
        lines: list[str] = []
        for bar_number in bar_numbers:
            if bar_number not in processed_data:
                logger.warning(f"BAR {bar_number} not found in processed data, skipping")
                continue

            logger.info(f"Generating structures for BAR {bar_number}")

            lines.extend(
                self._generate_rom_structures(
                    bar_number,
                    generate_read,
                    generate_write,
                )
            )

            if cli_options.include_counters:
                lines.extend(
                    self._generate_counter_structures(
                        bar_number,
                        generate_read,
                        generate_write,
                    )
                )

            if cli_options.include_address_checks:
                lines.extend(
                    self._generate_address_check_structures(
                        bar_number,
                        generate_read,
                        generate_write,
                    )
                )

            if cli_options.include_state_machines:
                lines.extend(
                    self._generate_state_machine_structures(
                        bar_number,
                        processed_data,
                        "state_machine_start",
                    )
                )

            if cli_options.include_counters:
                lines.extend(
                    self._generate_reset_counter_structures(
                        bar_number,
                        generate_read,
                        generate_write,
                    )
                )

            if cli_options.init_roms:
                lines.extend(
                    self._generate_rom_init_structures(
                        bar_number,
                        generate_read,
                        generate_write,
                    )
                )

            if cli_options.include_state_machines:
                lines.extend(
                    self._generate_state_machine_structures(
                        bar_number,
                        processed_data,
                        "state_machine_end",
                    )
                )

            if cli_options.include_logic:
                logger.info("Including logic structures")
                logic_lines = self._generate_verilog_logic(
                    bar_number,
                    generate_read,
                    generate_write,
                )
                if logic_lines:
                    lines.extend(logic_lines)

        return lines

    def build_verilog(
        self,
        processed_data: dict[Any, Any],
        cli_options: CLIOptions,
        include_logic: bool = True,
    ) -> str:
        """Build Verilog code from processed data based on CLI options."""
        logger.info("Starting Verilog code generation")

        first_entry = self._get_first_bar_entry(processed_data)
        if not self._initialize_verilog_data(first_entry):
            return ""

        lines: list[str] = []
        bar_numbers = cli_options.bar_selection or list(processed_data.keys())
        generate_read, generate_write = self._get_operation_flags(cli_options.operation_filter)

        for bar_number in bar_numbers:
            if bar_number not in processed_data:
                logger.warning(f"BAR {bar_number} not found in processed data, skipping")
                continue

            logger.info(f"Generating complete module for BAR {bar_number}")

            bar_lines = []
            bar_lines.extend(self._generate_headers([bar_number], processed_data))

            bar_lines.extend(
                self._generate_bar_structures([bar_number], processed_data, cli_options, generate_read, generate_write)
            )

            if bar_lines:
                while bar_lines and not bar_lines[-1].strip():
                    bar_lines.pop()
                bar_lines.append("endmodule\n")
                lines.extend(bar_lines)

                if bar_number != bar_numbers[-1]:
                    lines.append("")

        result = "\n".join(line for line in lines if line.strip())
        logger.info(f"Completed Verilog code generation, total size: {len(result)} bytes")
        return result
