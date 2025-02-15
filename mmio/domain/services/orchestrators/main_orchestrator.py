"""Orchestrator to manage all modules."""

from pydantic import BaseModel, ConfigDict, Field

from mmio.application.cli.app import AppLogic
from mmio.application.cli.mmio import MMIOCLIManager
from mmio.config.mmio_settings import MMIOSettings
from mmio.config.verilog_settings import VerilogSettings
from mmio.core.logger import LoggerManager
from mmio.domain.models.verilog_data import VerilogData
from mmio.infrastructure.file_handling.mmio_filemanager import MMIOFileManager
from mmio.infrastructure.file_handling.verilog_filemanager import VerilogFileManager

logger = LoggerManager.get_logger(__name__)


class MainOrchestrator(BaseModel):
    """Main Orchestration.

    This class coordinates all application components and manages the main
    application flow. It handles initialization of components and ensures
    proper interaction between them.

    Attributes:
        verilog_settings: VerilogSettings to configure Verilog output
        mmio_settings: MMIOSettings to configure MMIO input
        app_logic: AppLogic to handle CLI interactions
        mmio_cli_manager: MMIOCLIManager to handle MMIO CLI interactions
        verilog_data: VerilogData to handle Verilog data
        mmio_file_manager: MMIOFileManager to handle MMIO file input
        verilog_file_manager: VerilogFileManager to handle Verilog file output

    """

    model_config = ConfigDict(arbitrary_types_allowed=True, validate_assignment=True)

    verilog_data: VerilogData = Field(default_factory=VerilogData)

    verilog_settings: VerilogSettings = Field(default_factory=VerilogSettings.get_instance)
    mmio_settings: MMIOSettings = Field(default_factory=MMIOSettings.get_instance)

    app_logic: AppLogic = Field(default_factory=AppLogic)
    mmio_cli_manager: MMIOCLIManager = Field(default_factory=MMIOCLIManager)

    mmio_file_manager: MMIOFileManager = Field(default_factory=MMIOFileManager.get_instance)
    verilog_file_manager: VerilogFileManager = Field(default_factory=VerilogFileManager.get_instance)

    results: list[dict[str, str | int | float | None]] = Field(default_factory=list)

    def _init_mmio_file_manager(self) -> None:
        logger.info(f"MMIO settings - file_input_path: {self.mmio_settings.file_input_path}")
        if self.mmio_settings.file_input_path:
            logger.info(f"Setting MMIO file manager input path: {self.mmio_settings.file_input_path}")
            self.mmio_file_manager.input_manager.file_manager.path = self.mmio_settings.file_input_path
        else:
            logger.warning("No MMIO input path set in settings")
        logger.info(
            f"Verilog settings - output_path: "
            f"{self.verilog_settings.file_output_path}, "
            f"output_name: {self.verilog_settings.file_output_name}"
        )

    def _init_verilog_file_manager(self) -> None:
        """Initialize Verilog file manager with current settings."""
        logger.info(
            f"Verilog settings - output_path: "
            f"{self.verilog_settings.file_output_path}, "
            f"output_name: {self.verilog_settings.file_output_name}"
        )
        if self.verilog_settings.file_output_path:
            logger.info(f"Setting Verilog file manager output path: {self.verilog_settings.file_output_path}")
            self.verilog_file_manager.output_manager.file_manager.path = self.verilog_settings.file_output_path
        else:
            logger.warning("No Verilog output path set in settings")

    def _generate_output_filename(self) -> None:
        """Generate output filename if not already set."""
        if self.verilog_settings.file_output_name:
            logger.info(f"Setting Verilog file manager output name: {self.verilog_settings.file_output_name}")
            self.verilog_file_manager.output_manager.file_manager.file_name = self.verilog_settings.file_output_name
        else:
            logger.info("Generating default Verilog output filename")
            self.verilog_file_manager.generate_output_filename()

    def _log_file_managers_state(self) -> None:
        """Log the state of the file managers."""
        logger.info(
            f"Final MMIO file manager state - input_path: "
            f"{self.mmio_file_manager.input_manager.file_manager.path}, "
            f"input_file_name: {self.mmio_file_manager.input_manager.file_manager.file_name}"
        )
        logger.info(
            f"Final Verilog file manager state - output_path: "
            f"{self.verilog_file_manager.output_manager.file_manager.path}, "
            f"output_file_name: {self.verilog_file_manager.output_manager.file_manager.file_name}"
        )
        logger.info("File managers initialized")

    def _initialize_file_managers(self) -> None:
        """Initialize file managers with current settings."""
        logger.info("Initializing file managers")

        self._init_mmio_file_manager()
        self._init_verilog_file_manager()
        self._generate_output_filename()
        self._log_file_managers_state()

    def initialize(self) -> None:
        """Initialize all application components.

        This method ensures all components are properly initialized and
        configured before the main application flow starts.
        """
        try:
            logger.info("Initializing application components")

            self.app_logic.initialize()

            self.mmio_settings, self.verilog_settings = self.app_logic.get_settings()

            self._initialize_file_managers()

            logger.info("Application components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise

    def _run_cli_interface(self) -> None:
        """Run the CLI interface through AppLogic."""
        self.app_logic.run()

    def _write_verilog_to_file(self) -> None:
        """Write the Verilog code to file."""
        if self.verilog_settings.file_output_path:
            self.verilog_file_manager.output_manager.file_manager.path = self.verilog_settings.file_output_path
            logger.info(f"Writing Verilog output to {self.verilog_file_manager.output_manager.file_manager.path}")

    def generate_output(self) -> None:
        """Generate Verilog output from processed results."""
        try:
            logger.info("Generating Verilog output")

            if not self.verilog_settings.file_output_name:
                self._generate_output_filename()

            self._write_verilog_to_file()

            logger.info("Verilog output generated successfully")
        except Exception as e:
            logger.error(f"Failed to generate output: {e}")
            raise

    def _process_generated_verilog(self) -> None:
        """Process the generated Verilog code."""
        if self.app_logic.orchestrator:
            self.generate_output()

    def run(self) -> None:
        """Execute the complete application workflow.

        This method coordinates the main application flow:
        1. Runs the CLI interface for user interaction
        2. Processes selected files
        3. Generates output
        """
        try:
            logger.info("Starting application workflow")

            self._run_cli_interface()

            self._process_generated_verilog()

            logger.info("Application workflow completed successfully")
        except Exception as e:
            logger.error(f"Application workflow failed: {e}")
            raise
