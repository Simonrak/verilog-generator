"""Output select CLI."""

from typing import Any

from click import Argument, Command, Group, Option
from pydantic import BaseModel, ConfigDict, Field

from mmio.core.logger import LoggerManager
from mmio.infrastructure.cli.base import CLIBase, CLICommand

logger = LoggerManager.get_logger(__name__)


class OutputVerilogCLI(BaseModel):
    """Output Verilog CLI."""

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)

    cli_base: CLIBase = Field(default_factory=CLIBase)
    cli_commands: CLICommand = Field(default_factory=CLICommand)

    @property
    def output_group(self) -> Group:
        """Get the output group."""
        return Group(name=self.output_name)

    @property
    def output_name(self) -> str:
        """Get the output name."""
        return "output"

    def __init__(self) -> None:
        """Initialize the output select CLI."""
        super().__init__()
        self.cli_commands.name = self.output_name
        self.cli_commands.group = self.output_group
        self.cli_commands.help = "Output select CLI."
        self.cli_commands.epilog = "Output select CLI."
        self.cli_commands.short_help = "Output select CLI."
        self.cli_commands.options_metavar = "[OPTIONS]"
        self.cli_commands.add_help_option = True
        self.cli_commands.no_args_is_help = False
        self.cli_commands.hidden = False
        self.cli_commands.deprecated = False

    def add_command(self, command: Command) -> None:
        """Add a command to the CLI."""
        self.cli_base.add_command(command=command)

    def add_argument(self, *args: Any, **kwargs: Any) -> None:
        """Add an argument to the CLI."""
        self.cli_commands.params.append(Argument(*args, **kwargs))

    def add_option(self, *args: Any, **kwargs: Any) -> None:
        """Add an option to the CLI."""
        self.cli_commands.params.append(Option(*args, **kwargs))

    def add_help_option(self) -> None:
        """Add a help option to the CLI."""
        self.cli_commands.add_help_option = True

    def add_group(self, group: Group) -> None:
        """Add a group to the CLI."""
        self.cli_base.add_group(group=group)

    def prompt_user(self) -> None:
        """Prompt the user for input."""
        print("Please select an output format ...")
