from pydantic import BaseModel, ConfigDict, Field

from mmio.core.logger import LoggerManager

logger = LoggerManager.get_logger(__name__)


class CLIOptions(BaseModel):
    """CLI Options for controlling the Verilog generation process.

    Attributes:
        bar_selection: Optional list of BAR numbers to process; if None, process all.
        operation_filter: Either "R" (read only), "W" (write only), or "B" (both).
        include_address_checks: Whether to generate address check entries.
        include_counters: Whether to generate counter entries.
        include_default_values: Whether to calculate and include default values.
        include_logic: Whether to include logic structures.
        include_state_machines: Whether to include state machine structures.

    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    bar_selection: list[int] | None = Field(default=None, description="List of BARs to process")
    operation_filter: str = Field(default="B", description="Operation filter (R/W/B)")
    include_address_checks: bool = Field(default=True, description="Whether to include address check structures")
    include_counters: bool = Field(default=True, description="Whether to include counter structures")
    include_default_values: bool = Field(default=True, description="Whether to include default value structures")
    include_logic: bool = Field(default=True, description="Whether to include logic structures")
    include_state_machines: bool = Field(default=True, description="Whether to include state machine structures")
    init_roms: bool = Field(default=True, description="Whether to include ROM initialization structures")
