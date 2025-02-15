"""MMIO select CLI."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import click
from click import Argument, Group, Option
from click import Command as ClickCommand
from pydantic import BaseModel, ConfigDict, Field
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from mmio.core.logger import LoggerManager
from mmio.infrastructure.cli.base import CLIBase, CLICommand

logger = LoggerManager.get_logger(__name__)
console = Console()


class SelectMMIOFileInputCLI(BaseModel):
    """Select MMIO file input CLI.

    This class provides the CLI interface for selecting and managing MMIO input files.
    It handles file listing, selection, and validation through user interaction.

    Available options:
        --retrieve-list: Retrieve all available MMIO files
        --select-file: Select an MMIO file by name
        --validate-file: Validate the currently selected file
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)

    cli_base: CLIBase = Field(default_factory=CLIBase)
    cli_commands: CLICommand = Field(default_factory=lambda: CLICommand(name="mmio"))
    selected_file: Path | None = None
    _list_files_callback: Callable[[], list[Path]] | None = None

    def model_post_init(self, __context: Any) -> None:
        """Initialize after model creation."""
        self.cli_commands.group = self.mmio_group
        self.cli_commands.help = "Select and manage MMIO input files"
        self.cli_commands.epilog = "Use this command to select MMIO log files for processing"
        self.cli_commands.short_help = "MMIO file selection"
        self.cli_commands.options_metavar = "[OPTIONS]"
        self.cli_commands.add_help_option = True
        self.cli_commands.no_args_is_help = False
        self.cli_commands.hidden = False
        self.cli_commands.deprecated = False
        self._setup_default_options()

    @property
    def mmio_group(self) -> Group:
        """Get the mmio group."""
        return Group(name="mmio")

    @property
    def mmio_name(self) -> str:
        """Get the mmio name."""
        return "mmio"

    def set_list_files_callback(self, callback: Callable[[], list[Path]]) -> None:
        """Set the callback for listing files.

        Args:
            callback: Function that returns a list of available files

        """
        self._list_files_callback = callback

    def _setup_default_options(self) -> None:
        """Set up default CLI options."""
        self.cli_commands.params = [
            click.Option(
                ["--retrieve-list"],
                is_flag=True,
                help="Retrieve all available MMIO files",
                callback=self._list_files_option_callback,
            ),
            click.Option(
                param_decls=["--select-file"],
                type=str,
                help="Select an MMIO file by name",
                callback=self._select_file_callback,
            ),
            click.Option(
                param_decls=["--validate-file"],
                is_flag=True,
                help="Validate the currently selected file",
                callback=self._validate_file_callback,
            ),
        ]

    def add_command(self, command: ClickCommand) -> None:
        """Add a command to the CLI."""
        self.cli_base.add_group(group=self.mmio_group)
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

    def prompt_user(self) -> Path | None:
        """Prompt the user to select an MMIO file."""
        logger.info("Starting interactive file selection")

        title = Text("MMIO File Selection", style="bold blue")
        title.align("center", width=60)

        files = self._list_files()
        logger.info(f"Found {len(files)} available files")

        if not files:
            logger.warning("No MMIO files available")
            console.print(
                Panel(
                    "[yellow]No MMIO files available in the current directory.[/yellow]",
                    title="File Selection",
                    title_align="center",
                    box=box.ROUNDED,
                    width=60,
                )
            )
            return None

        table = Table(
            show_header=True,
            header_style="bold cyan",
            box=box.SIMPLE,
            title="Available Files",
            title_style="bold blue",
            width=56,
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("File Name", style="green")

        for idx, file in enumerate(files, 1):
            logger.info(f"File option {idx}: {file}")
            table.add_row(str(idx), file.name)

        console.print(
            Panel(title, box=box.DOUBLE, padding=(1, 2), title="File Selection", title_align="center", width=60)
        )

        console.print(Panel(table, box=box.ROUNDED, padding=(1, 1), width=60))

        try:
            selection = click.prompt("\nSelect a file (enter number or full name)", type=str, default="1")
            logger.info(f"User entered selection: {selection}")

            if selection.isdigit():
                idx = int(selection) - 1
                logger.info(f"Numeric selection: index {idx}")
                if 0 <= idx < len(files):
                    selected_file = files[idx]
                    logger.info(f"Selected file by index: {selected_file}")
                else:
                    logger.error(f"Invalid selection number: {selection}")
                    console.print("[red]❌ Invalid selection number[/red]")
                    return None
            else:
                logger.info(f"Name selection: {selection}")
                matching_files = [f for f in files if f.name == selection]
                if matching_files:
                    selected_file = matching_files[0]
                    logger.info(f"Selected file by name: {selected_file}")
                else:
                    logger.error(f"File not found: {selection}")
                    console.print("[red]❌ File not found[/red]")
                    return None

            self.selected_file = selected_file
            logger.info(f"Successfully set selected file: {self.selected_file}")
            console.print(f"\n[green]✓ Selected:[/green] {selected_file.name}")
            return selected_file

        except click.Abort:
            logger.warning("User cancelled selection")
            console.print("\n[yellow]Selection cancelled[/yellow]")
            return None
        except Exception as e:
            logger.error(f"Error during selection: {e}", exc_info=True)
            console.print(f"\n[red]Error during selection: {e}[/red]")
            return None

    def _list_files(self) -> list[Path]:
        """List available MMIO files."""
        logger.info("Attempting to list files")
        if self._list_files_callback:
            logger.info("Using list_files_callback")
            files = self._list_files_callback()
            logger.info(f"Found {len(files)} files using callback")
            return files
        logger.warning("No list_files_callback set")
        return []

    def _list_files_option_callback(self, ctx: click.Context, param: click.Parameter, value: bool) -> None:
        """Callback for --retrieve-list option."""
        if not value:
            return
        files = self._list_files()
        if files:
            click.echo("\nAvailable MMIO files:")
            for file in files:
                click.echo(f"- {file.name}")
        else:
            click.echo("No MMIO files available")

    def _select_file_callback(self, ctx: click.Context, param: click.Parameter, value: str) -> None:
        """Callback for --select option."""
        if not value:
            return
        files = self._list_files()
        matching_files = [f for f in files if f.name == value]
        if matching_files:
            self.selected_file = matching_files[0]
            click.echo(f"Selected file: {self.selected_file.name}")
        else:
            click.echo(f"File not found: {value}")

    def _validate_file_callback(self, ctx: click.Context, param: click.Parameter, value: bool) -> None:
        """Callback for --validate option."""
        if not value:
            return
        if not self.selected_file:
            click.echo("No file selected to validate")
            return
        click.echo(f"Validating file: {self.selected_file.name}")
