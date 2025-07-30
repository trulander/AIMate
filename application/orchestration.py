import logging
import cv2
import numpy as np

from application.interfaces.Idatabase_session import IDatabaseSession
from application.interfaces.Irepository_bd_dict import IRepositoryDBDict
from application.services.ai_service import AIService
from application.services.asr_service import ASRService
from application.services.screenshot_service import ScreenshotService
from application.services.hot_key_service import HotkeyService
from core.repository.repository_bd_dict import RepositoryDBDict
from core.repository.sqlite_session import SQLiteDatabaseSession
from domain.enums.ai_model import AIModels

logger = logging.getLogger(__name__)


class Orchestration:
    def __init__(self):
        logger.info("init orchestration")


        self.__hot_key_handler_service = HotkeyService()
        self.__hot_key_handler_service.start()
        self.screenshot_service = ScreenshotService()

        self.__database: IDatabaseSession = SQLiteDatabaseSession()
        self.__repository: IRepositoryDBDict = RepositoryDBDict(database=self.__database)


        self.__asr_service = ASRService(
            whisper_model="medium",
            language="ru",
            target_sample_rate=16000,
            block_size=1024,
            hotkey=['ctrl', 'alt'],
            hot_key_handler_service=self.__hot_key_handler_service,
        )
        self.coords = (0, 0, 0, 0)

        self.__ai_service: AIService = self.create_ai_agent()


    def create_ai_agent(self, chat_id: int | None = None) -> AIService:
        return AIService(
            model=AIModels.GEMINI_2_5_FLASH_LITE_PREVIEW_06_17,
            repository=self.__repository,
            chat_id=chat_id,
        )

    def get_list_chats(self) -> (int, str):
        return self.__repository.get_list_chats()


    def send_message(self, message: list[dict[str, str]], chat_id: str | int | None = None):
        result = self.__ai_service.invoke(human_message=message)
        logger.info(f"send_message result: {result}")
        return result

    def get_ai_chat(self, chat_id: int):
        self.__ai_service = self.create_ai_agent(chat_id=chat_id)
        result = self.__ai_service.get_chat_messages()
        return result




    def get_screenshot(self, coords: tuple) -> np.ndarray:
        result = self.screenshot_service.take_screenshot(bbox=coords)
        return result

    def save_screenshot(self, frame):
        cv2.namedWindow("test", cv2.WINDOW_NORMAL)
        cv2.imshow("test", frame)
        cv2.waitKey(1)


    def stop_all(self):
        self.stop_speach_service()

    def start_speach_service(self):
        self.__asr_service.start_speach_service()

    def stop_speach_service(self):
        self.__asr_service.stop()
        self.__hot_key_handler_service.stop()



