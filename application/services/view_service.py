import logging
import numpy as np
from application.orchestration import Orchestration


logger = logging.getLogger(__name__)


class ViewService(object):
    def __init__(self, orchestrator: Orchestration):
        self.orchestrator: Orchestration = orchestrator

    def get_chat_list(self) -> dict:
        result = {id: message for (id, message) in self.orchestrator.get_list_chats()}
        return result

    def get_chat(self, chat_id: int):
        record = self.orchestrator.get_ai_chat(chat_id=chat_id)
        return record

    def send_message(self, message: dict, chat_id: str | int | None = None):
        return self.orchestrator.send_message(message=message, chat_id=chat_id)

    def get_screenshot(self, coords: tuple) -> np.ndarray:
        result = self.orchestrator.screenshot_service.take_screenshot(bbox=coords)
        return result

    def set_coords_area(self, coords: tuple):
        logger.info(f"set coords area: {coords} were set")
        self.coords = coords
