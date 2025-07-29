import logging
import pickle
from collections import defaultdict

from application.interfaces.Irepository_bd_dict import IRepositoryDBDict
from core.repository.models.ai_state_model import AIStateModel
from domain.entities.ai_state import AIState

logger = logging.getLogger(__name__)


class SQLAlchemyDBDict(defaultdict):
    @classmethod
    def db_dict_factory(cls, repository: IRepositoryDBDict, record_id: str | int = None, col_name: str = None):
        if not record_id:
            record_id = repository.get_next_id()

        def create_db_dict(default_factory=None):
            if col_name:
                _col_name = col_name
            else:
                if default_factory is None:
                    _col_name = AIStateModel.data_state.key
                elif default_factory is dict:
                    _col_name = AIStateModel.data_writes.key
                elif callable(default_factory) and default_factory() == defaultdict(dict):
                    _col_name = AIStateModel.data_storage.key
                else:
                    _col_name = AIStateModel.data_default.key
            instance = cls(default_factory=default_factory, col_name=_col_name, record_id=record_id, repository=repository)
            return instance

        return create_db_dict, record_id

    def __init__(self, default_factory, col_name, record_id: str | int, repository: IRepositoryDBDict):
        super().__init__(default_factory)
        self.col_name = col_name
        self.record_id: str | int = record_id
        self.bd_repository: IRepositoryDBDict = repository

        try:
            self.load_from_db()
        except Exception as e:
            logger.error(f"Error: {e}")

    def load_from_db(self):
        try:
            ai_state = self.bd_repository.get_chat(record_id=self.record_id)
            if ai_state:
                data = pickle.loads(getattr(ai_state, self.col_name, None))
                super().update(data)
        except Exception as e:
            logger.error(f"load_from_db error, {e}")
        logger.info(f"Loaded from {self.record_id}")

    def sync_data(self):
        try:
            logger.info(f"Syncing from {self.record_id}")
            data = dict(self)
            pickled_data = pickle.dumps(data)
            if data:
                ai_state = self.bd_repository.get_chat(record_id=self.record_id)
                if ai_state is None:
                    ai_state = AIState(**{"id":self.record_id, self.col_name:pickled_data})
                    self.bd_repository.create(ai_state=ai_state)
                elif getattr(ai_state, self.col_name, None) != pickled_data:
                    setattr(ai_state, self.col_name, pickled_data)
                    self.bd_repository.update(ai_state=ai_state)

        except Exception as e:
            logger.error(f"Sync error: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        logger.info("Выход из контекстного менеджера и вызов метода синхронизации")
        self.sync_data()

    def __del__(self):
        try:
            logger.info("Удаление обьекта SQLAlchemyDBDict и вызов метода синхронизации")
            self.sync_data()
        except AttributeError as e:
            logger.error(f"Error: {e}")

