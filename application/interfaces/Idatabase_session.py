from contextlib import contextmanager
from typing import Protocol, Generator, Type
from sqlalchemy.orm import Session
from core.repository.base import Base


class IDatabaseSession(Protocol):
    @contextmanager
    def get_session(self) -> Generator[Session, any, None]:
        pass

    def get_next_id(self, model: Type[Base]) -> int:
        pass