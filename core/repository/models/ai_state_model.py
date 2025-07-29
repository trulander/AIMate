from sqlalchemy import Column, Integer, Text, BINARY
from core.repository.base import Base


class AIStateModel(Base):
    __tablename__ = "ai_state"
    id = Column(Integer, primary_key=True, autoincrement=True)
    last_message = Column(Text, nullable=True)
    data_state = Column(BINARY, nullable=True)
    data_storage = Column(BINARY, nullable=True)
    data_writes = Column(BINARY, nullable=True)
    data_default = Column(BINARY, nullable=True)
