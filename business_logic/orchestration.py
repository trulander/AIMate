import logging
import cv2
import numpy as np
from business_logic.asr_service import ASRService
from business_logic.screenshot_service import ScreenshotService
from business_logic.hot_key_handler_service import HotkeyHandlerService


logger = logging.getLogger(__name__)


class Orchestration:
    def __init__(self):
        logger.info("init orchestration")
        self.__hot_key_handler_service = HotkeyHandlerService()
        self.__hot_key_handler_service.start()
        self.__screenshot_service = ScreenshotService()
        self.__asr_service = ASRService(
            whisper_model="medium",
            language="ru",
            target_sample_rate=16000,
            block_size=1024,
            hotkey=['ctrl', 'alt'],
            hot_key_handler_service=self.__hot_key_handler_service,
        )
        self.coords = (0, 0, 0, 0)

    def set_coords_area(self, coords: tuple):
        logger.info(f"set coords area: {coords} were set")
        self.coords = coords

    def get_screenshot(self, coords: tuple) -> np.ndarray:
        result = self.__screenshot_service.take_screenshot(bbox=coords)
        return result

    def save_screenshot(self, frame):
        cv2.namedWindow("test", cv2.WINDOW_NORMAL)
        cv2.imshow("test", frame)
        cv2.waitKey(1)

    def send_message(self, message: str):
        pass

    def get_chat_list(self) -> dict:
        return {
            "Chat 1": "print('Hello from Chat 1')",
            "Chat 2": "<h1>Hello from Chat 2</h1>",
            "Chat 3": "echo Hello from Chat 3",
        }

    def start_speach_service(self):
        self.__asr_service.start_speach_service()

    def stop_speach_service(self):
        self.__asr_service.stop()
        self.__hot_key_handler_service.stop()

