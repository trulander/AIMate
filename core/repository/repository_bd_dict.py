import logging

from sqlalchemy import select

from application.interfaces.Idatabase_session import IDatabaseSession
from application.interfaces.Irepository_bd_dict import IRepositoryDBDict
from core.repository.models.ai_state_model import AIStateModel
from domain.entities.ai_state import AIState


logger = logging.getLogger(__name__)


class RepositoryDBDict(IRepositoryDBDict):
    def __init__(self, database: IDatabaseSession):
        self.database = database

    def create(self, ai_state: AIState) -> None:
        with self.database.get_session() as session:
            record= AIStateModel(**ai_state.model_dump())
            session.add(record)
            session.commit()
        logging.info("Saved data to database")

    def update(self, ai_state: AIState) -> None:
        with self.database.get_session() as session:
            session.query(AIStateModel).filter(AIStateModel.id == ai_state.id).update(
                ai_state.model_dump(exclude=['id'], exclude_none=True, exclude_unset=True)
            )
            session.commit()

    def get_chat(self, record_id: int) -> AIState | None:
        with self.database.get_session() as session:
            db_data = session.get(AIStateModel, record_id)
            if db_data:
                logger.info("Retrieved data from database")
                return AIState.model_validate(db_data) # ORM -> Домен
            logger.info("Retrieved data from database")
            return None

    def get_next_id(self) -> int:
        return self.database.get_next_id(model=AIStateModel)

    def get_list_chats(self) -> (int, str):
        with self.database.get_session() as session:
            #session.query(AIStateModel).with_entities(AIStateModel.id).all()
            #session.execute(select(AIStateModel.id)).scalars().all()
            return session.execute(select(AIStateModel.id, AIStateModel.last_message).order_by(AIStateModel.id.desc())).all()

    def delete_chat(self, record_id: int):
        with self.database.get_session() as session:
            session.query(AIStateModel).filter(AIStateModel.id == record_id).delete()
            session.commit()