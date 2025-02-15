"""Main entry point for the MMIO package."""

from mmio.config.log_settings import LogSettings
from mmio.core.logger import LoggerManager
from mmio.domain.services.orchestrators.main_orchestrator import MainOrchestrator

log_settings = LogSettings.load()
log_settings.apply()
logger = LoggerManager.get_logger(__name__)


def main() -> None:
    """Entry point for the MMIO package.

    This function initializes the application components and starts
    the main orchestration flow.
    """
    try:
        logger.info("Starting MMIO application")
        logger.info("Creating MainOrchestrator instance")

        orchestrator = MainOrchestrator()
        logger.info("MainOrchestrator instance created")

        logger.info("Initializing orchestrator")
        orchestrator.initialize()
        logger.info("Orchestrator initialization completed")

        logger.info("Starting main orchestration flow")
        orchestrator.run()
        logger.info("Main orchestration flow completed")

        logger.info("MMIO application completed successfully")
    except Exception as e:
        logger.error(f"Application failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
