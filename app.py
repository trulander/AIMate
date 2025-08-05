import logging
from threading import Thread
from time import sleep

from application.interfaces.Idatabase_session import IDatabaseSession
from application.interfaces.Irepository_bd_dict import IRepositoryDBDict
from application.orchestration import Orchestration
from application.services.view_service import ViewService
from core.config.logging_config import configure_logging
from core.repository.repository_bd_dict import RepositoryDBDict
from core.repository.sqlite_session import SQLiteDatabaseSession
from presentation.main_window import MainWindow


configure_logging()
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    database: IDatabaseSession = SQLiteDatabaseSession()
    repository: IRepositoryDBDict = RepositoryDBDict(database=database)

    orchestrator = Orchestration(repository=repository)
    view_service = ViewService(orchestrator=orchestrator)

    def run_tk():
        app = MainWindow(view_service=view_service)
        app.run_app()

    tkinter = Thread(target=run_tk, daemon=True)
    tkinter.start()
    sleep(1)
    orchestrator.init_services()
    tkinter.join()



