import logging
import pickle

import numpy as np
from application.orchestration import Orchestration
from domain.entities.ai_state import AIState

logger = logging.getLogger(__name__)


class ViewService(object):
    def __init__(self, orchestrator: Orchestration):
        self.orchestrator: Orchestration = orchestrator

    def get_chat_list(self) -> dict:
        result = {id: message for (id, message) in self.orchestrator.get_list_chats()}
        return result
        # return {
        #     "Chat 1": "print('Hello from Chat 1')",
        #     "Chat 2": "<h1>Hello from Chat 2</h1>",
        #     "Chat 3": "echo Hello from Chat 3",
        # }

    def get_chat(self, chat_id: int):
        record = self.orchestrator.get_ai_chat(chat_id=chat_id)
        return record

    def send_message(self, message: str, chat_id: str | int | None = None):
        return self.orchestrator.send_message(message=message, chat_id=chat_id)

    def get_screenshot(self, coords: tuple) -> np.ndarray:
        result = self.orchestrator.__screenshot_service.take_screenshot(bbox=coords)
        return result

