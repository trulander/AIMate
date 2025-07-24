import logging

import numpy as np
from application.orchestration import Orchestration


logger = logging.getLogger(__name__)


class ViewService(object):
    def __init__(self, orchestrator: Orchestration):
        self.orchestrator: Orchestration = orchestrator

    def get_chat_list(self) -> dict:
        return {
            "Chat 1": "print('Hello from Chat 1')",
            "Chat 2": "<h1>Hello from Chat 2</h1>",
            "Chat 3": "echo Hello from Chat 3",
        }

    def send_message(self, message: str):
        pass

    def get_screenshot(self, coords: tuple) -> np.ndarray:
        result = self.orchestrator.__screenshot_service.take_screenshot(bbox=coords)
        return result

