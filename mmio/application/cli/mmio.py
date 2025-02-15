"""MMIO CLI app."""

from pathlib import Path

import click
from pydantic import BaseModel, ConfigDict, Field

from mmio.application.cli.commands.mmio_select import SelectMMIOFileInputCLI
from mmio.config.mmio_settings import MMIOSettings
from mmio.core.logger import LoggerManager
from mmio.infrastructure.file_handling.mmio_filemanager import MMIOFileManager

logger = LoggerManager.get_logger(__name__)


class MMIOCLIManager(BaseModel):
    """MMIO CLI manager.

    This class is responsible for managing the MMIO CLI application.
    Handles the MMIO settings, file selection, and MMIO file operations.
    Coordinates between the CLI interface and file management components.

    Attributes:
        mmio_select: CLI component for MMIO file selection
        settings: MMIO configuration settings
        file_manager: Manager for MMIO file operations
        selected_file: Currently selected MMIO file path

    """

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)

    mmio_select: SelectMMIOFileInputCLI = Field(default_factory=SelectMMIOFileInputCLI)
    settings: MMIOSettings = Field(default_factory=MMIOSettings.get_instance)
    file_manager: MMIOFileManager = Field(default_factory=MMIOFileManager.get_instance)
    selected_file: Path | None = None

    def setup_cli(self) -> None:
        """Initialize MMIO CLI components and file manager."""
        self._initialize_file_manager()
        self._setup_cli_integration()
        self.mmio_select.setup_commands()

    def _initialize_file_manager(self) -> None:
        """Initialize the file manager with settings."""
        if self.settings.file_input_path:
            self.file_manager.input_manager.file_manager.path = self.settings.file_input_path
            logger.info(f"Initialized file manager with path: {self.settings.file_input_path}")

    def _setup_cli_integration(self) -> None:
        """Set up integration between CLI and file manager components."""
        self.mmio_select.set_list_files_callback(self.list_available_files)

        self.mmio_select.add_option(
            param_decls=["--path-to-mmio-files"],
            type=click.Path(exists=True, file_okay=False, dir_okay=True),
            help="Set the MMIO files directory path",
            callback=self._set_path_callback,
        )

    def _set_path_callback(self, ctx: click.Context, param: click.Parameter, value: str) -> None:
        """Callback for setting the MMIO files directory path."""
        if not value:
            return
        try:
            path = Path(value)
            self.file_manager.input_manager.file_manager.path = path
            self.settings.file_input_path = path
            click.echo(f"Set MMIO files directory to: {path}")
        except Exception as e:
            logger.error(f"Error setting path: {e}")
            click.echo(f"Error setting path: {e}")

    def list_available_files(self) -> list[Path]:
        """List all available MMIO log files."""
        try:
            files = self.file_manager.list_files()
            if not files:
                click.echo("No MMIO log files found in the input directory")
            return files
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            click.echo(f"Error listing files: {e}")
            return []

    def select_file(self, file_name: str) -> bool:
        """Select an MMIO file for processing."""
        try:
            logger.info(f"Attempting to select file: {file_name}")
            logger.info(
                f"Current file manager state - input_path: "
                f"{self.file_manager.input_manager.file_manager.path}, input_file_name: "
                f"{self.file_manager.input_manager.file_manager.file_name}"
            )

            self.file_manager.input_manager.file_manager.file_name = file_name
            logger.info(f"Set input_file_name to: {self.file_manager.input_manager.file_manager.file_name}")

            self.selected_file = self.file_manager.read_file()
            logger.info(f"Successfully read file: {self.selected_file}")

            self.mmio_select.selected_file = self.selected_file
            logger.info(f"Updated CLI selection state with file: {self.selected_file}")
            return True
        except (ValueError, FileNotFoundError) as e:
            logger.error(f"Error selecting file: {e}")
            logger.info(
                f"File manager state at error - input_path: "
                f"{self.file_manager.input_manager.file_manager.path}, input_file_name: "
                f"{self.file_manager.input_manager.file_manager.file_name}"
            )
            click.echo(f"Error selecting file: {e}")
            return False

    def process_cli_selection(self) -> Path | None:
        """Process file selection through CLI interface."""
        logger.info("Starting CLI file selection process")
        selected = self.mmio_select.prompt_user()

        if selected:
            logger.info(f"User selected file: {selected}")
            if self.select_file(selected.name):
                logger.info("File selection successful, proceeding with validation")
                if self.validate_and_process_file():
                    logger.info(f"File validation successful: {selected}")
                    return selected
                else:
                    logger.error("File validation failed")
            else:
                logger.error("File selection failed")
        else:
            logger.warning("No file was selected by user")

        return None

    def get_settings(self) -> MMIOSettings:
        """Get collected MMIO settings."""
        return self.settings

    def get_selected_file(self) -> Path | None:
        """Get the currently selected file path."""
        return self.selected_file

    def validate_and_process_file(self) -> bool:
        """Validate and prepare selected file for processing."""
        if not self.selected_file:
            click.echo("No file selected for processing")
            return False

        try:
            self.file_manager.input_manager.file_manager.validate_file(self.selected_file)
            logger.info(f"File validated successfully: {self.selected_file}")
            return True
        except Exception as e:
            logger.error(f"Error validating file: {e}")
            click.echo(f"Error validating file: {e}")
            return False
