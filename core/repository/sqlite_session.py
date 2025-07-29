from contextlib import contextmanager

from typing import Generator, Type

from sqlalchemy import create_engine, text, select, func
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, Session
import logging

from application.interfaces.Idatabase_session import IDatabaseSession
from core.config.config import settings
from core.repository.base import Base
from core.repository.models import * #импорт всех моделей по умолчанию.


logger = logging.getLogger(__name__)


class SQLiteDatabaseSession(IDatabaseSession):
    def __init__(self, db_url: str = settings.SQLALCHEMY_DATABASE_URI):
        self.engine = create_engine(db_url, echo=True)
        self.Session = sessionmaker(bind=self.engine)
        self._init_db()

    def _init_db(self):
        Base.metadata.create_all(bind=self.engine)
        logging.info("Database initialized")

    @contextmanager
    def get_session(self) -> Generator[Session, any, None]:
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_next_id(self, model: Type[Base]) -> int:
        try:
            # Попытка получить из sqlite_sequence
            with self.get_session() as session:
                table_name = model.__tablename__
                result = session.execute(
                    text(f"SELECT seq FROM sqlite_sequence WHERE name = :table_name"),
                    {"table_name": table_name},
                ).scalar()
                return (result or 0) + 1
        except OperationalError:
            # Таблицы sqlite_sequence ещё нет
            pass

        # Fallback на MAX(id)
        result = session.execute(select(func.max(model.id))).scalar()
        return (result or 0) + 1