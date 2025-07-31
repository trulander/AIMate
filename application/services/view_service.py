import logging
import threading
from typing import Callable

import numpy as np
from application.orchestration import Orchestration
from core.event_dispatcher import dispatcher
from domain.enums.signal import Signal
from domain.enums.status_statusbar import Status

logger = logging.getLogger(__name__)


class ViewService(object):
    def __init__(self, orchestrator: Orchestration):
        self.orchestrator: Orchestration = orchestrator

    def get_chat_list(self) -> dict:
        result = {id: message for (id, message) in self.orchestrator.get_list_chats()}
        return result

    def create_new_chat(self) -> int:
        self.orchestrator.create_ai_agent()
        return self.orchestrator.get_current_chat_id()

    def get_chat(self, chat_id: int):
        record = self.orchestrator.get_ai_chat(chat_id=chat_id)
        return record

    def __send_message_thread(self, message: list[dict[str, str]], callback: Callable):
        try:
            response = self.orchestrator.send_message(message=message)
            callback(messages=response)
            dispatcher.send(signal=Signal.set_status, status=Status.IDLE)
        except Exception as e:
            logger.critical(f"received exception: {e}")
            dispatcher.send(signal=Signal.set_status, status=Status.ERROR)
        finally:
            pass

    def send_message(self, message: list[dict[str, str]], callback: Callable):
        dispatcher.send(signal=Signal.set_status, status=Status.WAITING_AGENT_RESPONSE)
        threading.Thread(
            target=self.__send_message_thread,
            kwargs={
                "message":message,
                "callback": callback
            },
            daemon=True
        ).start()

    def get_screenshot(self, coords: tuple) -> np.ndarray:
        result = self.orchestrator.get_screenshot(coords=coords)
        return result

    def set_coords_area(self, coords: tuple):
        logger.info(f"set coords area: {coords} were set")
        self.coords = coords
