# MMIO to Verilog Generator

This package generates Verilog code from MMIO logs.

## Usage

### Run the script

- run.bat will install the dependencies and create a .venv folder, and then run the script after activating the venv.

### Adding your own generator and Verilog block

- Make a new data class in `mmio/application/verilog/verilog_models.py` if you want to add a new type of Verilog "Entry class" (Your own read/write response logic, ROM, counter, etc).

```py
"""mmio/application/verilog/verilog_models.py"""

# Might have to add your field types to the if statement below (depends on what you named your fields)
    def get_verilog_content(self, operation: str | None = None, field_type: str | None = None) -> StringIO:
        """Get Verilog content from a StringIO field."""
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

...
...

# Make a new data class in `mmio/application/verilog/verilog_models.py`:
class YourNewEntry(VerilogGenerator):
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
```

---

## Building the generated Verilog code

- Make a new file in `mmio/application/verilog/generators/` and a new class if you want to add a new type of Verilog block (ROM, counter, address check, logic). Look at the other files in the folder for examples.

- Existing generators:

```txt
mmio/application/verilog/generators/address_check.py
mmio/application/verilog/generators/counter_generator.py
mmio/application/verilog/generators/response_logic.py
mmio/application/verilog/generators/rom.py
mmio/application/verilog/generators/static_generator.py
```

- The class `StaticCodeGenerator` is already implemented, and can be used as a template for new generators.

```py
class StaticCodeGenerator(VerilogGenerator):
    """Verilog module static code generator."""

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
```

```py
"""Example of a simple start of a state machine."""

# Your StringIO object is built here, and is saved to the data class:
    def generate_state_machine_start(self) -> VerilogStatic:
        """Generate the Verilog state machine with all ports."""
        self.save_state_machine.seek(0)
        self.save_state_machine.truncate()

        self.save_state_machine.write("    always_ff @(posedge clk) begin\n")
        self.save_state_machine.write("        if (rst) begin\n")
        self.save_state_machine.write("            rd_rsp_valid <= 1'b0;\n")

        self.static_code.verilog_state_machine_start = StringIO(self.save_state_machine.getvalue())
        return self.static_code
```

---

- Add your new class and generator to the `mmio/application/verilog/verilog_builder_orchestrator.py` file.

```py
"""mmio/application/verilog/verilog_builder_orchestrator.py"""

class GeneratorType(Enum):
    """Enum for generator types."""

# Add your new generator type here:
    ROM = "rom"
    COUNTER = "counter"
    ADDRESS_CHECK = "addr_check"
    HEADER = "header"
    STATE_MACHINE_START = "state_machine_start"
    STATE_MACHINE_END = "state_machine_end"
    LOGIC = "logic"
    RESET_COUNTER = "reset_counter"
    ROM_INIT = "rom_init"

# Initialize your new StringIO objects here:
    verilog_rom: ROMEntry = Field(
        default_factory=lambda: ROMEntry(
            bar_number=0,
            verilog_read_rom=StringIO(),
            verilog_write_rom=StringIO(),
            verilog_read_rom_init=StringIO(),
            verilog_write_rom_init=StringIO(),
        )
    )

# Add your new generator initialization here:
    def __init__(self, **data: Any):
        """Initialize the VerilogBuilderOrchestrator with registered generators."""
        super().__init__(**data)
        logger.info("Initializing VerilogBuilderOrchestrator")

        # Register default generators
        self.register_generator(GeneratorType.ROM.value, ROMGenerator)
        self.register_generator(GeneratorType.ADDRESS_CHECK.value, AddressCheckGenerator)
        self.register_generator(GeneratorType.COUNTER.value, CounterGenerator)
        self.register_generator(GeneratorType.RESET_COUNTER.value, CounterGenerator)
        self.register_generator(GeneratorType.HEADER.value, StaticCodeGenerator)
        self.register_generator(GeneratorType.STATE_MACHINE_START.value, StaticCodeGenerator)
        self.register_generator(GeneratorType.STATE_MACHINE_END.value, StaticCodeGenerator)
        self.register_generator(GeneratorType.LOGIC.value, ResponseLogicGenerator)
        self.register_generator(GeneratorType.ROM_INIT.value, ROMGenerator)

...
...

# Add your new generator function here:
    def _handle_rom(self, generator: ROMGenerator, operation: str | None) -> str:
        """Handle ROM field type generation."""
        generator.generate_rom_structure(self.bar_number)
        self.verilog_rom = generator.verilog_rom
        return self._get_operation_value(
            operation, self.verilog_rom.verilog_read_rom, self.verilog_rom.verilog_write_rom
        )

...
...

# Add your new generator function to the match case:
        try:
            generator = self._get_generator_instance(field_type, bar_number)

            match field_type:
                case "header" if isinstance(generator, StaticCodeGenerator):
                    return self._handle_header(generator)

                case "state_machine_start" if isinstance(generator, StaticCodeGenerator):
                    return self._handle_state_machine_start(generator)

                case "state_machine_end" if isinstance(generator, StaticCodeGenerator):
                    return self._handle_state_machine_end(generator)

                case "rom" if isinstance(generator, ROMGenerator):
                    return self._handle_rom(generator, operation)

                case "rom_init" if isinstance(generator, ROMGenerator):
                    return self._handle_rom_init(generator, operation)

                case "counter" if isinstance(generator, CounterGenerator):
                    return self._handle_counter(generator, operation)

                case "reset_counter" if isinstance(generator, CounterGenerator):
                    return self._handle_reset_counter(generator, operation)

                case "addr_check" if isinstance(generator, AddressCheckGenerator):
                    return self._handle_addr_check(generator, operation)

                case "logic" if isinstance(generator, ResponseLogicGenerator):
                    return self._handle_logic(generator, operation)

                case _:
                    logger.warning(f"No handler found for field type: {field_type}")
                    return ""
```

---

**Add a new function and build the `mmio/application/cli/coordinator/modular_orchestrator.py` file.**

```py
"""mmio/application/verilog/modular_orchestrator.py"""

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

...
...

# Add your function to the bar structure generation (what/where does it need to be?):
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
```

---

## Add the new object to the CLI Base class

**Add the new object to the variable initialization:**

```py
"""mmio/config/cli_config.py"""

# Add shit here:
class CLIOptions(BaseModel):
    """CLI Options for controlling the Verilog generation process."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    bar_selection: list[int] | None = Field(default=None, description="List of BARs to process")
    operation_filter: str = Field(default="B", description="Operation filter (R/W/B)")
    include_address_checks: bool = Field(default=True, description="Whether to include address check structures")
    include_counters: bool = Field(default=True, description="Whether to include counter structures")
    include_default_values: bool = Field(default=True, description="Whether to include default value structures")
    include_logic: bool = Field(default=True, description="Whether to include logic structures")
    include_state_machines: bool = Field(default=True, description="Whether to include state machine structures")
    init_roms: bool = Field(default=True, description="Whether to include ROM initialization structures").py"""
```

---

## I don't want to write anymore, you can figure out the rest yourself :D
