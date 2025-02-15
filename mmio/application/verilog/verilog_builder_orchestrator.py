from enum import Enum
from io import StringIO
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from mmio.application.verilog.generators.address_check import AddressCheckGenerator
from mmio.application.verilog.generators.counter_generator import CounterGenerator
from mmio.application.verilog.generators.response_logic import ResponseLogicGenerator
from mmio.application.verilog.generators.rom import ROMGenerator
from mmio.application.verilog.generators.static_generator import StaticCodeGenerator
from mmio.application.verilog.verilog_models import (
    AddressCheckEntry,
    CounterEntry,
    LogicEntries,
    ROMEntry,
    VerilogGenerator,
    VerilogStatic,
)
from mmio.core.logger import LoggerManager
from mmio.domain.models.verilog_data import VerilogData

logger = LoggerManager.get_logger(__name__)


class GeneratorType(Enum):
    """Enum for generator types."""

    ROM = "rom"
    COUNTER = "counter"
    ADDRESS_CHECK = "addr_check"
    HEADER = "header"
    STATE_MACHINE_START = "state_machine_start"
    STATE_MACHINE_END = "state_machine_end"
    LOGIC = "logic"
    RESET_COUNTER = "reset_counter"
    ROM_INIT = "rom_init"


class VerilogBuilderOrchestrator(BaseModel):
    """Enhanced Verilog Builder with dynamic generator support."""

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)

    generator_classes: dict[str, type[VerilogGenerator]] = Field(default_factory=dict)
    generator_instances: dict[str, VerilogGenerator] = Field(default_factory=dict)
    verilog_data: VerilogData = Field(default_factory=VerilogData)

    bar_number: int = Field(default=0)

    verilog_header: VerilogStatic = Field(
        default_factory=lambda: VerilogStatic(
            bar_number=0,
            verilog_header=StringIO(),
            verilog_state_machine_start=StringIO(),
            verilog_state_machine_end=StringIO(),
        )
    )

    verilog_rom: ROMEntry = Field(
        default_factory=lambda: ROMEntry(
            bar_number=0,
            verilog_read_rom=StringIO(),
            verilog_write_rom=StringIO(),
            verilog_read_rom_init=StringIO(),
            verilog_write_rom_init=StringIO(),
        )
    )

    verilog_counter: CounterEntry = Field(
        default_factory=lambda: CounterEntry(
            bar_number=0,
            verilog_read_counter=StringIO(),
            verilog_write_counter=StringIO(),
            verilog_reset_read_counter=StringIO(),
            verilog_reset_write_counter=StringIO(),
        )
    )

    verilog_address_check: AddressCheckEntry = Field(
        default_factory=lambda: AddressCheckEntry(
            bar_number=0,
            verilog_read_addr_check=StringIO(),
            verilog_write_addr_check=StringIO(),
        )
    )

    verilog_logic: LogicEntries = Field(
        default_factory=lambda: LogicEntries(
            bar_number=0,
            verilog_read_cases=StringIO(),
            verilog_write_cases=StringIO(),
        )
    )

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

        logger.info(f"Registered generators: {list(self.generator_classes.keys())}")

    def set_verilog_data(self, mmio_data: VerilogData) -> None:
        """Set VerilogData for all generators."""
        logger.info("Setting VerilogData in orchestrator")

        # Set the current VerilogData instance
        self.verilog_data = mmio_data

        # Update all generator instances with the data
        for generator in self.generator_instances.values():
            addresses = VerilogData.addresses(bar=generator.bar_number)
            bit_widths = VerilogData.get_bar_address_bit_widths(generator.bar_number)
            read_values = VerilogData.read_values(bar=generator.bar_number)
            write_values = VerilogData.write_values(bar=generator.bar_number)
            defaults = VerilogData.get_default_values(generator.bar_number)

            generator.set_bar_data(
                addresses=addresses,
                bit_widths=bit_widths,
                read_values=read_values,
                write_values=write_values,
                defaults=defaults,
            )

    @property
    def available_bars(self) -> list[int]:
        """Get list of available BAR numbers."""
        return sorted(bar for generator in self.generator_instances.values() for bar in generator.get_available_bars())

    @property
    def supported_generators(self) -> list[str]:
        """Get list of supported generator types."""
        return [e.value for e in GeneratorType]

    def register_generator(self, generator_type: str, generator_class: type[VerilogGenerator]) -> None:
        """Register a new generator type."""
        if generator_type not in [e.value for e in GeneratorType]:
            raise ValueError(f"Invalid generator type: {generator_type}")
        self.generator_classes[generator_type] = generator_class

    def _validate_verilog_data(self, bar_number: int) -> bool:
        """Validate VerilogData and required fields for generation."""
        if not self.verilog_data:
            logger.warning("No VerilogData set, cannot generate code")
            return False

        bar_addresses = self.verilog_data.addresses(bar=bar_number)
        address_bit_widths = self.verilog_data.get_bar_address_bit_widths(bar_number)

        logger.info(f"Found addresses for BAR: {bar_number}: {bar_addresses}")
        logger.info(f"Address bit widths: {address_bit_widths}")

        if not bar_addresses:
            logger.warning(f"No addresses found for BAR: {bar_number}")
            return False

        if not address_bit_widths:
            logger.warning(f"No bit width information for BAR: {bar_number}")
            return False

        return True

    def _get_generator_instance(self, field_type: str, bar_number: int) -> VerilogGenerator:
        """Get or create a generator instance for the given field type."""
        if field_type not in self.generator_classes:
            raise ValueError(f"Unknown field type: {field_type}")

        generator = self.generator_classes[field_type](bar_number=bar_number)
        self.generator_instances[field_type] = generator

        if hasattr(generator, "set_bar_data"):
            generator.set_bar_data(
                addresses=self.verilog_data.addresses(bar=bar_number),
                bit_widths=self.verilog_data.get_bar_address_bit_widths(bar_number),
                read_values=self.verilog_data.read_values(bar=bar_number),
                write_values=self.verilog_data.write_values(bar=bar_number),
                defaults=self.verilog_data.get_default_values(bar_number),
            )

        return generator

    def _get_rom_entry(self, bar_number: int) -> ROMEntry:
        """Get or create a ROM entry for the given BAR number."""
        rom_gen = self.generator_instances.get("rom")
        rom_entry = ROMEntry(bar_number=bar_number)
        if isinstance(rom_gen, ROMGenerator):
            rom_gen.generate_rom_structure(bar_number)
            if rom_gen.verilog_rom is not None:
                rom_entry = rom_gen.verilog_rom
        return rom_entry

    def _get_counter_entry(self, bar_number: int) -> CounterEntry:
        """Get or create a counter entry for the given BAR number."""
        counter_gen = self.generator_instances.get("counter")
        counter_entry = CounterEntry(bar_number=bar_number)
        if isinstance(counter_gen, CounterGenerator):
            counter_gen.generate_verilog_counter(bar_number)
            if counter_gen.verilog_counter is not None:
                counter_entry = counter_gen.verilog_counter
        return counter_entry

    def _get_operation_value(self, operation: str | None, read_value: StringIO, write_value: StringIO) -> str:
        """Get the appropriate value based on the operation."""
        return str(read_value.getvalue() if operation == "read" else write_value.getvalue())

    def _handle_header(self, generator: StaticCodeGenerator) -> str:
        """Handle header field type generation."""
        header = generator.generate_module_header()
        self.verilog_header = header
        return str(self.verilog_header.verilog_header.getvalue())

    def _handle_state_machine_start(self, generator: StaticCodeGenerator) -> str:
        """Handle state machine start field type generation."""
        start = generator.generate_state_machine_start()
        self.verilog_header = start
        return str(self.verilog_header.verilog_state_machine_start.getvalue())

    def _handle_state_machine_end(self, generator: StaticCodeGenerator) -> str:
        """Handle state machine end field type generation."""
        end = generator.generate_state_machine_end()
        self.verilog_header = end
        return str(self.verilog_header.verilog_state_machine_end.getvalue())

    def _handle_rom(self, generator: ROMGenerator, operation: str | None) -> str:
        """Handle ROM field type generation."""
        generator.generate_rom_structure(self.bar_number)
        self.verilog_rom = generator.verilog_rom
        return self._get_operation_value(
            operation, self.verilog_rom.verilog_read_rom, self.verilog_rom.verilog_write_rom
        )

    def _handle_rom_init(self, generator: ROMGenerator, operation: str | None) -> str:
        """Handle ROM init field type generation."""
        generator.generate_rom_init(self.bar_number)
        self.verilog_rom = generator.verilog_rom

        return str(
            self.verilog_rom.verilog_read_rom_init.getvalue()
            if operation == "read"
            else self.verilog_rom.verilog_write_rom_init.getvalue()
        )

    def _handle_reset_counter(self, generator: CounterGenerator, operation: str | None) -> str:
        """Handle reset counter field type generation."""
        generator.generate_reset_counter(self.bar_number)
        self.verilog_counter = generator.verilog_counter

        return str(
            self.verilog_counter.verilog_reset_read_counter.getvalue()
            if operation == "read"
            else self.verilog_counter.verilog_reset_write_counter.getvalue()
        )

    def _handle_counter(self, generator: CounterGenerator, operation: str | None) -> str:
        """Handle counter field type generation."""
        self.verilog_counter = generator.generate_verilog_counter(self.bar_number)
        return self._get_operation_value(
            operation,
            self.verilog_counter.verilog_read_counter,
            self.verilog_counter.verilog_write_counter,
        )

    def _handle_addr_check(self, generator: AddressCheckGenerator, operation: str | None) -> str:
        """Handle address check field type generation."""
        self.verilog_address_check = generator.generate_address_check_entry(self.bar_number)
        return self._get_operation_value(
            operation,
            self.verilog_address_check.verilog_read_addr_check,
            self.verilog_address_check.verilog_write_addr_check,
        )

    def _handle_logic(self, generator: ResponseLogicGenerator, operation: str | None) -> str:
        """Handle logic field type generation."""
        rom_entry = self._get_rom_entry(self.bar_number)
        counter_entry = self._get_counter_entry(self.bar_number)
        self.verilog_logic = generator.generate_verilog_logic(self.bar_number, rom_entry, counter_entry)
        return self._get_operation_value(
            operation,
            self.verilog_logic.verilog_read_cases,
            self.verilog_logic.verilog_write_cases,
        )

    def build_verilog(self, operation: str | None, bar_number: int, field_type: str) -> str:
        """Generate Verilog code using the class's BAR number."""
        self.bar_number = bar_number
        logger.info(f"Building for BAR: {self.bar_number} with {len(VerilogData.get_all_instances())} entries")

        for generator in self.generator_instances.values():
            generator.bar_number = self.bar_number
            logger.info(f"Updated {type(generator).__name__} to BAR: {self.bar_number}")

        if not self._validate_verilog_data(bar_number):
            return ""

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

        except ValueError as e:
            logger.warning(str(e))
            return ""
