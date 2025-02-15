"""Base class for CLI."""

from typing import Any

import click
from click import Argument, Command, Group, Option
from pydantic import BaseModel, ConfigDict

from mmio.core.logger import LoggerManager

logger = LoggerManager.get_logger(__name__)


class CLIBase(BaseModel):
    """Base class for CLI."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str | None = None
    group: Group | Command | None = None

    click_group: Group = Group(name=None)
    click_command: Command = Command(name=None)
    click_argument: Argument = Argument(
        param_decls=["argument_name"],
        required=False,
    )
    click_option: Option = Option(
        param_decls=["--option_name"],
        required=False,
    )

    def setup_commands(self) -> None:
        """Set up all commands for the CLI."""
        if self.name is not None:
            self.click_group.add_command(cmd=Command(name=self.name))
        if self.group is not None:
            self.click_group.add_command(cmd=self.group)

    def add_command(self, command: Command) -> None:
        """Add a command to the CLI."""
        self.click_group.add_command(cmd=command)

    def add_group(self, group: Group) -> None:
        """Add a group to the CLI."""
        self.click_group.add_command(cmd=group)

    def add_argument(self, *args: Any, **kwargs: Any) -> None:
        """Add an argument to the CLI."""
        self.click_command.params.append(Argument(*args, **kwargs))

    def add_option(self, *args: Any, **kwargs: Any) -> None:
        """Add an option to the CLI."""
        self.click_command.params.append(Option(*args, **kwargs))


class CLICommand(click.Command):
    """Command class."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the command with a name."""
        self.group = kwargs.pop("group", None)
        params = kwargs.pop("params", [])
        self.help = kwargs.pop("help", "")
        self.epilog = kwargs.pop("epilog", "")
        self.short_help = kwargs.pop("short_help", None)
        self.options_metavar = kwargs.pop("options_metavar", "[OPTIONS]")
        self.add_help_option = kwargs.pop("add_help_option", True)
        self.no_args_is_help = kwargs.pop("no_args_is_help", False)
        self.hidden = kwargs.pop("hidden", False)
        self.deprecated = kwargs.pop("deprecated", False)

        if "name" not in kwargs:
            kwargs["name"] = "default_name"

        kwargs["params"] = []
        super().__init__(*args, **kwargs)

        for param in params:
            self.params.append(param)

    def add_parameter(self, param: click.Parameter) -> None:
        """Add a parameter to the command while checking for name conflicts.

        Args:
            param: The Click parameter to add

        Raises:
            ValueError: If a parameter with the same name or short form already exists

        """
        existing_names = {p.name for p in self.params}
        if param.name in existing_names:
            raise ValueError(f"Parameter with name '{param.name}' already exists")

        if isinstance(param, click.Option):
            new_shorts = {opt[1:] for opt in param.opts if len(opt) == 2 and opt.startswith("-")}
            existing_shorts = {
                opt[1:]
                for p in self.params
                if isinstance(p, click.Option)
                for opt in p.opts
                if len(opt) == 2 and opt.startswith("-")
            }

            conflicts = new_shorts & existing_shorts
            if conflicts:
                raise ValueError(f"Short form(s) '-{', -'.join(conflicts)}' already in use by another option")

        self.params.append(param)

    def to_info_dict(self, ctx: click.Context) -> dict[str, Any]:
        """Convert the command to a dictionary."""
        info_dict: dict[str, Any] = super().to_info_dict(ctx)
        info_dict.update(
            params=[param.to_info_dict() for param in self.params],
        )
        return info_dict


model_config = ConfigDict(arbitrary_types_allowed=True)
