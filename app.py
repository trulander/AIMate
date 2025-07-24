import logging
from application.orchestration import Orchestration
from application.services.view_service import ViewService
from core.config.logging_config import configure_logging
from presentation.main_window import MainWindow


configure_logging()
logger = logging.getLogger(__name__)



if __name__ == "__main__":
    orchestrator = Orchestration()
    view_service = ViewService(orchestrator=orchestrator)
    app = MainWindow(view_service=view_service)
    app.run_app()

