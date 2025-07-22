import logging

from business_logic.orchestration import Orchestration
from core.config import settings
from core.logging_config import configure_logging

from view.main_window import MainWindow


configure_logging()
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    orchestrator = Orchestration()
    app = MainWindow(orchestrator=orchestrator)
    app.mainloop()

