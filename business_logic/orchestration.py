import logging
import cv2
import numpy as np
from business_logic.screenshoter import Screenshoter
from business_logic.speach_recognition import RealTimeASR



logger = logging.getLogger(__name__)



class Orchestration:
    def __init__(self):
        logger.info("init orchestration")
        self.screenshot_service = Screenshoter()
        self.audio_speach_recognition = RealTimeASR(
            target_sample_rate=16000,
            block_size=1024,
            whisper_model='small',
            language='ru',
            hotkey='ctrl'
        )
        # self.audio_speach_recognition.start()


        self.coords = (0,0,0,0)

    def set_coords_area(self, coords: tuple):
        logger.info(f"set coords area: {coords} were set")
        self.coords = coords

    def get_screenshot(self, coords: tuple) -> np.ndarray:
        result = self.screenshot_service.take_screenshot(bbox=coords)
        return result

    def save_screenshot(self, frame):
        cv2.namedWindow("test", cv2.WINDOW_NORMAL)
        cv2.imshow("test", frame)
        cv2.waitKey(1)