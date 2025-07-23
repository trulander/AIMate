import atexit
import logging
import multiprocessing
import threading
from queue import Empty
from business_logic.audio_speach_recognition.real_time_asr import RealTimeASR
from business_logic.audio_speach_recognition.speach_recognizer import SpeechRecognizer
from business_logic.hot_key_handler_service import HotkeyHandlerService

logger = logging.getLogger(__name__)


class ASRService:
    def __init__(self,
                 whisper_model="small",
                 language="ru",
                 target_sample_rate: int = 16000,
                 block_size: int = 1024,
                 hotkey: list = [],
                 hot_key_handler_service: HotkeyHandlerService = None
                 ):
        logger.info(f"Initial speach recognition service ")

        self.__whisper_model = whisper_model
        self.__language = language
        self.__target_sample_rate = target_sample_rate
        self.__block_size = block_size
        self.__hotkey = hotkey
        self.__hot_key_handler_service = hot_key_handler_service

        self.__process_speach_recognition: threading.Thread = None
        self.__stop_event_process_speach_recognition: multiprocessing.Event = None
        self.__loop_calback_thread: threading.Thread = None

        self.__queue_recognised_text = multiprocessing.Queue()

        atexit.register(self.stop)


    def start_speach_service(self):
        if self.__process_speach_recognition is None or not self.__process_speach_recognition.is_alive():
            self.__stop_event_process_speach_recognition = multiprocessing.Event()
            self.__process_speach_recognition = threading.Thread(
                target=self.__initial_speach_recognition_service
            )
            self.__process_speach_recognition.start()

            self.__loop_calback_thread = threading.Thread(target=self.__loop_calback)
            self.__loop_calback_thread.daemon = True
            self.__loop_calback_thread.start()

            logger.info("Процесс для RealTimeASR запущен")

    def stop(self):
        logger.info(f'stop_speach_service')
        if self.__process_speach_recognition is not None:
            self.__stop_event_process_speach_recognition.set()
            # self.__process_speach_recognition.terminate()
            self.__process_speach_recognition.join()
            logger.info("Сервис распознавания аудио текста остановлен")

        if self.__loop_calback_thread is not None:
            self.__loop_calback_thread.join()

    def __loop_calback(self):
        while not (
                self.__stop_event_process_speach_recognition and self.__stop_event_process_speach_recognition.is_set()):
            try:
                msg = self.__queue_recognised_text.get(timeout=0.5)
                self.__callback_text_recognition(text=msg)
                logger.info(f"loop_calback received message: {msg}")
            except Empty:
                continue  # просто ждём дальше
        logger.info(f"loop_calback остановлен")

    def __initial_speach_recognition_service(self):
        # hot_key_handler_service = HotkeyHandlerService()
        # hot_key_handler_service.run()
        real_time_asr = RealTimeASR(
            target_sample_rate=self.__target_sample_rate,
            block_size=self.__block_size,
            hotkey=self.__hotkey,
            hot_key_handler_service=self.__hot_key_handler_service,
            queue_recognised_text=self.__queue_recognised_text,
            speech_recognizer=SpeechRecognizer(
                model_size=self.__whisper_model,
                language=self.__language
            ),
        )
        real_time_asr.start(
            stop_event=self.__stop_event_process_speach_recognition
        )

    def __callback_text_recognition(self, text):
        logger.info(f"__callback_text_recognition - Распознанный текст: {text}")
        self.__hot_key_handler_service.keyboard_type_text(text=text)

