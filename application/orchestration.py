import logging
import cv2
import numpy as np
from application.services.asr_service import ASRService
from application.services.screenshot_service import ScreenshotService
from application.services.hot_key_service import HotkeyService


logger = logging.getLogger(__name__)


class Orchestration:
    def __init__(self):
        logger.info("init orchestration")


        self.__hot_key_handler_service = HotkeyService()
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





    def start_speach_service(self):
        self.__asr_service.start_speach_service()

    def stop_speach_service(self):
        self.__asr_service.stop()
        self.__hot_key_handler_service.stop()



