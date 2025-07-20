import logging

from business_logic.orchestration import Orchestration
from core.config import *
from view.main_window import MainWindow

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    orchestrator = Orchestration()
    app = MainWindow(orchestrator=orchestrator)
    app.mainloop()

