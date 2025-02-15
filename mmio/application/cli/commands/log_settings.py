"""CLI interface for managing logging settings."""

from pathlib import Path
from typing import Any

import click
from click import Argument, Group, Option
from click import Command as ClickCommand
from pydantic import BaseModel, ConfigDict, Field

from mmio.config.log_settings import LOG_LEVELS, LogSettings
from mmio.core.logger import LoggerManager
from mmio.infrastructure.cli.base import CLIBase, CLICommand

logger = LoggerManager.get_logger(__name__)


class LogSettingsCLI(BaseModel):
    """CLI interface for managing logging settings."""

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)

    cli_base: CLIBase = Field(default_factory=CLIBase)
    cli_commands: CLICommand = Field(default_factory=lambda: CLICommand(name="log"))
    settings: LogSettings = Field(default_factory=LogSettings.load)

    def model_post_init(self, __context: Any) -> None:
        """Initialize after model creation."""
        self.cli_commands.group = self.log_group
        self.cli_commands.help = "Manage logging settings"
        self.cli_commands.epilog = "Configure logging behavior"
        self.cli_commands.short_help = "Logging settings"
        self.cli_commands.options_metavar = "[OPTIONS]"
        self.cli_commands.add_help_option = True
        self.cli_commands.no_args_is_help = False
        self.cli_commands.hidden = False
        self.cli_commands.deprecated = False
        self._setup_default_options()

    @property
    def log_group(self) -> Group:
        """Get the log settings group."""
        return Group(name="log")

    @property
    def log_name(self) -> str:
        """Get the log settings name."""
        return "log"

    def _setup_default_options(self) -> None:
        """Set up default CLI options."""
        self.add_option(
            param_decls=["--set-level"],
            type=click.Choice(list(LOG_LEVELS.keys()), case_sensitive=False),
            help="Set the logging level",
            callback=self._set_level_callback,
        )
        self.add_option(
            param_decls=["--enable-file-logging"],
            type=click.Path(dir_okay=False, path_type=Path),
            help="Enable logging to file",
            callback=self._set_file_callback,
        )
        self.add_option(
            param_decls=["--disable-file-logging"],
            is_flag=True,
            help="Disable file logging",
            callback=self._disable_file_callback,
        )
        self.add_option(
            param_decls=["--show-options"],
            is_flag=True,
            help="Show current logging settings",
            callback=self._show_settings_callback,
        )

    def add_command(self, command: ClickCommand) -> None:
        """Add a command to the CLI."""
        self.cli_base.add_group(group=self.log_group)
        self.cli_base.add_command(command=command)

    def add_argument(self, *args: Any, **kwargs: Any) -> None:
        """Add an argument to the CLI."""
        self.cli_commands.params.append(Argument(*args, **kwargs))

    def add_option(self, *args: Any, **kwargs: Any) -> None:
        """Add an option to the CLI."""
        option = Option(*args, **kwargs)
        self.cli_commands.add_parameter(option)

    def add_help_option(self) -> None:
        """Add a help option to the CLI."""
        self.cli_commands.add_help_option = True

    def add_group(self, group: Group) -> None:
        """Add a group to the CLI."""
        self.cli_base.add_group(group=group)

    def setup_commands(self) -> None:
        """Set up all commands for the CLI."""
        self.cli_base.setup_commands()

    def _set_level_callback(self, ctx: click.Context, param: click.Parameter, value: str) -> None:
        """Callback for setting the log level."""
        if not value:
            return
        try:
            self.settings.level = value.upper()
            self.settings.save()
            self.settings.apply()
            click.echo(f"Log level set to: {value.upper()}")
        except Exception as e:
            logger.error(f"Failed to set log level: {e}")
            click.echo(f"Error: {e}")

    def _set_file_callback(self, ctx: click.Context, param: click.Parameter, value: Path) -> None:
        """Callback for enabling file logging."""
        if not value:
            return
        try:
            self.settings.file_enabled = True
            self.settings.log_file = value
            self.settings.save()
            self.settings.apply()
            click.echo(f"File logging enabled: {value}")
        except Exception as e:
            logger.error(f"Failed to enable file logging: {e}")
            click.echo(f"Error: {e}")

    def _disable_file_callback(self, ctx: click.Context, param: click.Parameter, value: bool) -> None:
        """Callback for disabling file logging."""
        if not value:
            return
        try:
            self.settings.file_enabled = False
            self.settings.log_file = None
            self.settings.save()
            self.settings.apply()
            click.echo("File logging disabled")
        except Exception as e:
            logger.error(f"Failed to disable file logging: {e}")
            click.echo(f"Error: {e}")

    def _show_settings_callback(self, ctx: click.Context, param: click.Parameter, value: bool) -> None:
        """Callback for showing current settings."""
        if not value:
            return
        click.echo("\nCurrent Logging Settings:")
        click.echo(f"Level: {self.settings.level}")
        click.echo(f"File Logging: {'Enabled' if self.settings.file_enabled else 'Disabled'}")
        if self.settings.file_enabled and self.settings.log_file:
            click.echo(f"Log File: {self.settings.log_file}")
        click.echo(f"Format: {self.settings.format}")
        click.echo(f"Date Format: {self.settings.date_format}")

    def prompt_user(self) -> None:
        """Prompt the user for logging settings."""
        click.echo("\nLogging Settings Configuration")
        click.echo("===========================")

        levels = list(LOG_LEVELS.keys())
        click.echo("\nAvailable log levels:")
        for idx, level in enumerate(levels, 1):
            click.echo(f"{idx}. {level}")

        try:
            level_idx = click.prompt(
                "Select log level (number)",
                type=click.IntRange(1, len(levels)),
                default=levels.index(self.settings.level) + 1,
            )
            self.settings.level = levels[level_idx - 1]

            if click.confirm("Enable file logging?", default=self.settings.file_enabled):
                file_path = click.prompt(
                    "Log file path",
                    type=click.Path(dir_okay=False, path_type=Path),
                    default=self.settings.log_file or Path("mmio.log"),
                )
                self.settings.file_enabled = True
                self.settings.log_file = file_path
            else:
                self.settings.file_enabled = False
                self.settings.log_file = None

            self.settings.save()
            self.settings.apply()
            click.echo("\nLogging settings updated successfully")

        except click.Abort:
            click.echo("\nConfiguration cancelled")
        except Exception as e:
            logger.error(f"Error configuring logging: {e}")
            click.echo(f"\nError: {e}")
