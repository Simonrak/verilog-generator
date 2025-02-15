import click
from pydantic import BaseModel, ConfigDict, Field

from mmio.application.cli.commands.mmio_select import SelectMMIOFileInputCLI
from mmio.application.cli.commands.output_select import OutputVerilogCLI
from mmio.config.cli_config import CLIOptions
from mmio.core.logger import LoggerManager

logger = LoggerManager.get_logger(__name__)


class CLICoordinator(BaseModel):
    """Central coordinator for CLI interactions.

    This class calls individual CLI modules sequentially and aggregates
    the responses into a CLIOptions object that can be passed to the orchestrators.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    mmio_select_cli: SelectMMIOFileInputCLI = Field(default_factory=SelectMMIOFileInputCLI)
    output_select_cli: OutputVerilogCLI = Field(default_factory=OutputVerilogCLI)

    def collect_options(self) -> CLIOptions:
        """Interactively collect CLI options from the user."""
        self.mmio_select_cli.prompt_user()
        self.output_select_cli.prompt_user()

        bar_input = click.prompt(
            "Enter BAR numbers separated by commas (or type 'all' to process all BARs)",
            default="all",
        )
        if bar_input.strip().lower() == "all":
            bar_selection = None
        else:
            try:
                bar_selection = list({int(b.strip()) for b in bar_input.split(",")})
            except ValueError:
                click.echo("Invalid input for BAR numbers. Processing all BARs by default.")
                bar_selection = None

        op_filter = click.prompt("Select operation type: R for Read, W for Write, B for Both", default="B").upper()

        include_address_checks = click.confirm("Generate Address Check functions?", default=True)
        include_counters = click.confirm("Generate Counter functions?", default=True)
        include_logic = click.confirm("Generate Logic functions?", default=True)
        include_state_machines = click.confirm("Generate State Machine functions?", default=True)
        init_roms = click.confirm("Generate ROM Initialization functions?", default=True)

        return CLIOptions(
            bar_selection=bar_selection,
            operation_filter=op_filter,
            include_address_checks=include_address_checks,
            include_counters=include_counters,
            include_logic=include_logic,
            include_state_machines=include_state_machines,
            init_roms=init_roms,
        )
