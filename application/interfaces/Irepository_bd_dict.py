from typing import Protocol

from domain.entities.ai_state import AIState


class IRepositoryDBDict(Protocol):

    def create(self, ai_state: AIState) -> None:
        pass

    def update(self, ai_state: AIState) -> None:
        pass

    def get_chat(self, record_id: int) -> AIState | None:
        pass

    def get_list_chats(self) -> (int, str):
        pass

    def get_next_id(self) -> int:
        pass

    def delete_chat(self, record_id: int):
        pass