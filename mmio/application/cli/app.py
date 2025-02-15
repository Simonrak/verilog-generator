"""Application logic for the CLI interface."""

from pathlib import Path
from typing import Any

import click
from pydantic import BaseModel, Field
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from mmio.application.cli.commands.file_select import BaseFileSelectCLI
from mmio.application.cli.commands.log_settings import LogSettingsCLI
from mmio.application.cli.commands.mmio_select import SelectMMIOFileInputCLI
from mmio.application.cli.commands.output_select import OutputVerilogCLI
from mmio.application.cli.coordinator.cli_coordinator import CLICoordinator
from mmio.application.cli.coordinator.modular_orchestrator import ModularOrchestrator
from mmio.application.cli.mmio import MMIOCLIManager
from mmio.config.cli_config import CLIOptions
from mmio.config.log_settings import LogSettings
from mmio.config.mmio_settings import MMIOSettings
from mmio.config.verilog_settings import VerilogSettings
from mmio.core.logger import LoggerManager
from mmio.infrastructure.file_handling.verilog_filemanager import VerilogFileManager

logger = LoggerManager.get_logger(__name__)
console = Console()


class AppLogic(BaseModel):
    """Application logic for coordinating CLI components and orchestration.

    This class serves as the main coordinator between the CLI interface and the
    domain logic. It manages:
    1. CLI components for file selection and configuration
    2. Settings management
    3. Orchestration of the main application flow
    """

    file_select_cli: BaseFileSelectCLI = Field(default_factory=BaseFileSelectCLI)
    mmio_select_cli: SelectMMIOFileInputCLI = Field(default_factory=SelectMMIOFileInputCLI)
    output_select_cli: OutputVerilogCLI = Field(default_factory=OutputVerilogCLI)
    log_settings_cli: LogSettingsCLI = Field(default_factory=LogSettingsCLI)
    verilog_file_manager: VerilogFileManager = Field(default_factory=VerilogFileManager)

    mmio_cli_manager: MMIOCLIManager = Field(default_factory=MMIOCLIManager)

    mmio_settings: MMIOSettings = Field(
        default_factory=lambda: MMIOSettings.get_instance(), description="MMIO settings singleton instance"
    )
    verilog_settings: VerilogSettings = Field(
        default_factory=lambda: VerilogSettings.get_instance(), description="Verilog settings singleton instance"
    )
    log_instance: LogSettings = Field(
        default_factory=lambda: LogSettings.get_instance(), description="Log settings singleton instance"
    )
    log_settings: LogSettings = Field(
        default_factory=lambda: LogSettings.load(), description="Loaded log settings from file"
    )
    file_name: str = Field(default_factory=VerilogFileManager.get_instance().generate_output_filename)

    settings_path: Path | None = Field(
        default=None, description="Optional path to override mmio_settings.file_input_path"
    )
    settings_output_path: Path | None = Field(
        default=None, description="Optional path to override verilog_settings.file_output_path"
    )
    settings_module_header: str | None = Field(
        default=None, description="Optional value to override verilog_settings.module_header"
    )

    orchestrator: ModularOrchestrator = Field(default_factory=ModularOrchestrator)

    def model_post_init(self, __context: Any) -> None:
        """Initialize settings after model creation.

        This method is called automatically by Pydantic after the model is created.
        It applies any overrides to the settings singletons before they are used.
        """
        mmio = MMIOSettings.get_instance()
        verilog = VerilogSettings.get_instance()

        if self.settings_path is not None:
            mmio.file_input_path = self.settings_path
            logger.info(f"Overriding MMIO input path with: {self.settings_path}")

        if self.settings_output_path is not None:
            verilog.file_output_path = self.settings_output_path
            logger.info(f"Overriding Verilog output path with: {self.settings_output_path}")

        if self.settings_module_header is not None:
            verilog.module_header = self.settings_module_header
            logger.info(f"Overriding Verilog module header with: {self.settings_module_header}")

    def initialize(self) -> None:
        """Initialize the application components."""
        try:
            logger.info("Initializing application components...")
            self.log_settings.apply()
            self._initialize_cli_components()
            logger.info("Application components initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing application: {e}")
            raise

    def _initialize_cli_components(self) -> None:
        """Initialize CLI components and managers."""
        self.log_settings_cli.setup_commands()
        self._setup_cli_commands()

    def _setup_cli_commands(self) -> None:
        """Set up CLI commands and options."""
        self.file_select_cli.add_command(self.mmio_select_cli.cli_commands)
        self.file_select_cli.add_command(self.output_select_cli.cli_commands)
        self.file_select_cli.add_command(self.log_settings_cli.cli_commands)

        if self.settings_path:
            self.file_select_cli.add_command(click.Command(name=self.settings_path.name))
        if self.settings_output_path:
            self.file_select_cli.add_command(click.Command(name=self.settings_output_path.name))
        if self.settings_module_header:
            self.file_select_cli.add_command(click.Command(name=self.settings_module_header))

    def run(self) -> None:
        """Run the application flow."""
        try:
            logger.info("Starting application flow...")

            logger.info("Initializing components")
            self.initialize()

            logger.info("Displaying welcome message")
            self._show_welcome()

            logger.info("Processing MMIO file selection")
            mmio_file = self.mmio_cli_manager.process_cli_selection()
            if not mmio_file:
                logger.error("No MMIO file selected")
                return

            logger.info(f"Selected MMIO file: {mmio_file}")

            logger.info("Collecting CLI options")
            cli_options = self._collect_cli_options()
            logger.info(f"Collected CLI options: {cli_options}")

            logger.info("Setting up orchestrator with selected file")
            logger.info(f"Setting input path: {mmio_file.parent}")
            logger.info(f"Setting input file name: {mmio_file.name}")

            self.orchestrator.input_orch.mmio_file_manager.input_manager.file_manager.path = mmio_file.parent
            self.orchestrator.input_orch.mmio_file_manager.input_manager.file_manager.file_name = mmio_file.name

            logger.info(
                f"Orchestrator input manager state - input_path: "
                f"{self.orchestrator.input_orch.mmio_file_manager.input_manager.file_manager.path}, input_file_name: "
                f"{self.orchestrator.input_orch.mmio_file_manager.input_manager.file_manager.file_name}"
            )

            logger.info("Running orchestrator")
            self.orchestrator.run(which_steps=["input", "build", "output"], cli_options=cli_options)

            logger.info("Application flow completed successfully")

        except Exception as e:
            logger.error(f"Error in application flow: {e}", exc_info=True)
            click.echo(f"Error: {e}")

    def _show_welcome(self) -> None:
        """Display welcome message and initial menu."""
        logger.info("Showing welcome message and menu")

        title = Text("MMIO to Verilog Generator", style="bold blue")
        title.align("center", width=60)

        version = Text("v0.0.1", style="cyan")
        version.align("center", width=60)

        menu_text = Text()
        menu_text.append("\n📁 1. Select a file", style="green")
        menu_text.append("\n🔍 2. Configure logging", style="green")

        panel_content = Text()
        panel_content.append(title)
        panel_content.append("\n\n")
        panel_content.append(version)
        panel_content.append("\n\n")
        panel_content.append(menu_text)

        console.print(
            Panel(
                panel_content,
                box=box.ROUNDED,
                padding=(1, 2),
                title="https://simonrak.gay",
                title_align="center",
                width=60,
            )
        )

        try:
            choice = click.prompt("Enter your choice", type=int)
            logger.info(f"User selected option: {choice}")

            if choice == 1:
                logger.info("Initializing file selection")
                self.mmio_cli_manager.setup_cli()
                console.print("[green]File selection initialized.[/green]")
            elif choice == 2:
                logger.info("Configuring logging settings")
                self.log_settings_cli.prompt_user()
            else:
                logger.warning(f"Invalid choice: {choice}")
                console.print("[red]Invalid choice. Please try again.[/red]")
        except ValueError:
            logger.warning("Invalid input type provided")
            console.print("[red]Invalid input. Please enter a number.[/red]")

    def _collect_cli_options(self) -> CLIOptions:
        """Collect CLI options for Verilog generation."""
        console.print(
            Panel(
                "\n[bold blue]Verilog Generation Options[/bold blue]\n",
                box=box.ROUNDED,
                title="Configuration",
                title_align="center",
                width=60,
            )
        )

        console.print("[cyan]BAR Configuration[/cyan]")
        bar_input = click.prompt(
            "Enter BAR numbers separated by commas (or type 'all' to process all BARs)",
            default="all",
        )
        if bar_input.strip().lower() == "all":
            bar_selection = None
            console.print("[green]✓[/green] Processing all BARs")
        else:
            try:
                bar_selection = [int(b.strip()) for b in bar_input.split(",")]
                console.print(f"[green]✓[/green] Selected BARs: {bar_selection}")
            except ValueError:
                console.print("[yellow]⚠[/yellow] Invalid BAR input, processing all BARs")
                bar_selection = None

        console.print("\n[cyan]Operation Type[/cyan]")
        op_filter = click.prompt("Select operation type: [R]ead, [W]rite, [B]oth", default="B").upper()
        console.print(f"[green]✓[/green] Selected operation type: {op_filter}")

        console.print("\n[cyan]Function Generation Options[/cyan]")
        include_address_checks = click.confirm("🔍 Generate Address Check functions?", default=True)
        include_counters = click.confirm("🔢 Generate Counter functions?", default=True)
        include_logic = click.confirm("⚡ Generate Logic functions?", default=True)
        include_state_machines = click.confirm("🔄 Generate State Machine functions?", default=True)
        init_roms = click.confirm("💾 Generate ROM Initialization functions?", default=True)

        options = CLIOptions(
            bar_selection=bar_selection,
            operation_filter=op_filter,
            include_address_checks=include_address_checks,
            include_counters=include_counters,
            include_logic=include_logic,
            include_state_machines=include_state_machines,
            init_roms=init_roms,
        )

        console.print("\n[bold green]Configuration Complete![/bold green]")
        console.print(f"Selected BARs: {options.bar_selection}")
        console.print(f"Operation Type: {options.operation_filter}")
        console.print(f"Include Address Checks: {options.include_address_checks}")
        console.print(f"Include Counters: {options.include_counters}")
        console.print(f"Include Logic: {options.include_logic}")
        console.print(f"Include State Machines: {options.include_state_machines}")
        console.print(f"Include ROMs: {options.init_roms}")
        console.print(
            f"\n[bold green]File saved to: {self.verilog_settings.file_output_path}/{self.file_name}[/bold green]"
        )
        return options

    def get_settings(self) -> tuple[MMIOSettings, VerilogSettings]:
        """Get all collected settings."""
        return self.mmio_settings, self.verilog_settings

    def get_generator_options(self) -> CLIOptions:
        """Collect additional CLI options for Verilog generation."""
        bar_input = click.prompt(
            "Enter BAR numbers separated by commas (or type 'all' to process all BARs)",
            default="all",
        )
        if bar_input.strip().lower() == "all":
            bar_selection = None
        else:
            try:
                bar_selection = [int(b.strip()) for b in bar_input.split(",")]
            except ValueError:
                click.echo("Invalid input for BAR numbers. Processing all BARs by default.")
                bar_selection = None

        op_filter = click.prompt("Select operation type: R for Read, W for Write, B for Both", default="B").upper()

        include_address_checks = click.confirm("Generate Address Check functions?", default=True)
        include_counters = click.confirm("Generate Counter functions?", default=True)
        include_defaults = click.confirm("Generate Default Values?", default=True)

        return CLIOptions(
            bar_selection=bar_selection,
            operation_filter=op_filter,
            include_address_checks=include_address_checks,
            include_counters=include_counters,
            include_default_values=include_defaults,
        )

    def run_application(self) -> None:
        """Central method to run the full flow from CLI input to Verilog generation."""
        self._show_welcome()

        cli_coordinator = CLICoordinator()
        generator_options: CLIOptions = cli_coordinator.collect_options()

        modular_orch = ModularOrchestrator()

        modular_orch.run(which_steps=["input", "build", "output"], cli_options=generator_options)
