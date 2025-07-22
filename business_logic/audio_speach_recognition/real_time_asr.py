import logging
import multiprocessing
import queue
import threading
import time
from collections import deque

import numpy as np
import sounddevice as sd
from scipy import signal

from business_logic.audio_speach_recognition.speach_recognizer import SpeechRecognizer
from business_logic.hot_key_handler_service import HotkeyHandlerService


logger = logging.getLogger(__name__)


class RealTimeASR:
    def __init__(self,
                 target_sample_rate=16000,
                 block_size=1024,
                 hotkey: list=[],
                 hot_key_handler_service: HotkeyHandlerService = None,
                 queue_recognised_text: multiprocessing.Queue = None,
                 speech_recognizer: SpeechRecognizer = None,):
        """
        Инициализация системы распознавания речи

        Args:
            target_sample_rate: частота дискретизации для модели
            block_size: размер блока аудио
            hotkey: комбинация клавиш для ручного режима
        """
        self.__target_sample_rate = target_sample_rate
        self.__block_size = block_size
        self.__audio_queue = queue.Queue()
        self.__queue_recognised_text: multiprocessing.Queue = queue_recognised_text
        self.__running: multiprocessing.Event = None
        self.__hotkey = hotkey

        self.__hot_key_handler_service = hot_key_handler_service

        # Определяем поддерживаемую частоту устройства
        self.__device_sample_rate = self.__find_supported_sample_rate()
        logger.info(f"Устройство поддерживает: {self.__device_sample_rate} Hz")
        logger.info(f"Модель требует: {self.__target_sample_rate} Hz")

        # Инициализируем распознаватель речи
        self.__speech_recognizer: SpeechRecognizer = speech_recognizer

        # Буфер для накопления данных
        self.__audio_buffer = deque()

        # Буфер для записи речевых сегментов
        self.__speech_buffer = []
        self.__recording_speech = False

        # Состояние для ручного режима
        self.__manual_recording = False
        self.__manual_start_time = None

        # Параметры для ресэмплинга
        if self.__device_sample_rate != self.__target_sample_rate:
            self.__need_resample = True
            self.__resample_ratio = self.__target_sample_rate / self.__device_sample_rate
            logger.warning(f"Будем ресэмплировать с {self.__device_sample_rate} Hz до {self.__target_sample_rate} Hz")
        else:
            self.__need_resample = False

        # Настройки для распознавания
        self.__min_speech_length = int(0.3 * target_sample_rate)  # минимум 0.3 секунды
        self.__max_speech_length = int(60 * target_sample_rate)  # максимум 60 секунд

        # Настройка горячих клавиш для ручного режима
        self.__setup_hotkeys()


    def start(self, stop_event):
        """Запуск записи и обработки"""
        self.__running = stop_event

        processing_thread = threading.Thread(target=self.__process_audio)
        processing_thread.daemon = True
        processing_thread.start()

        logger.info(f"Начинаем запись с микрофона (устройство: {self.__device_sample_rate} Hz → модель: {self.__target_sample_rate} Hz)")

        try:
            with sd.InputStream(
                    channels=1,
                    samplerate=self.__device_sample_rate,
                    blocksize=self.__block_size,
                    callback=self.__audio_callback,
                    dtype=np.float32
            ):
                while not (self.__running and self.__running.is_set()):
                    time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("\nОстанавливаем запись...")
        finally:
            self.stop()

    def stop(self):
        """Остановка записи и обработки"""
        try:
            self.__running.set()
        except:
            pass
        logger.info("Запись остановлена")


    def __setup_hotkeys(self):
        """Настройка горячих клавиш для ручного режима"""
        logger.info(f"setup_hotkeys")
        try:
            self.__hot_key_handler_service.add_hotkey(
                hotkey=self.__hotkey,
                on_press_callback=self.__on_hotkey_press,
                on_release_callback=self.__on_hotkey_release
            )
            logger.info(f"Горячие клавиши настроены: {self.__hotkey}")
        except Exception as e:
            logger.error(f"Ошибка настройки горячих клавиш: {e}")
            logger.error("Попробуйте запустить с правами администратора или используйте автоматический режим")

    def __on_hotkey_press(self, *args, **kwargs):
        """Обработка нажатия горячей клавиши"""
        if not self.__manual_recording:
            self.__manual_recording = True
            self.__manual_start_time = time.time()
            self.__speech_buffer = []
            logger.info(f"🎤 РУЧНАЯ ЗАПИСЬ НАЧАЛАСЬ (нажата {self.__hotkey})")

    def __on_hotkey_release(self, *args, **kwargs):
        """Обработка отпускания горячей клавиши"""
        if self.__manual_recording:
            self.__manual_recording = False
            duration = time.time() - self.__manual_start_time if self.__manual_start_time else 0
            logger.info(f"🔇 РУЧНАЯ ЗАПИСЬ ОСТАНОВЛЕНА (отпущена {self.__hotkey}, длительность: {duration:.1f}с)")

            # Запускаем распознавание в отдельном потоке
            if len(self.__speech_buffer) > 0:
                recognition_thread = threading.Thread(
                    target=self.__process_speech_segment,
                    daemon=True
                )
                recognition_thread.start()

    def __find_supported_sample_rate(self):
        """Находим поддерживаемую частоту дискретизации для входного устройства"""
        sample_rates = [16000, 44100, 48000, 22050, 8000]

        try:
            default_device = sd.default.device[0]
            device_info = sd.query_devices(default_device)
            logger.info(f"Используем устройство: {device_info['name']}")
        except:
            logger.info("Используем устройство по умолчанию")
            default_device = None

        for sr in sample_rates:
            try:
                sd.check_input_settings(
                    device=default_device,
                    channels=1,
                    samplerate=sr,
                    dtype=np.float32
                )
                return sr
            except:
                continue

        try:
            device_info = sd.query_devices(default_device)
            return int(device_info['default_samplerate'])
        except:

            return 44100

    def __resample_audio(self, audio_data):
        """Ресэмплирование аудио до целевой частоты"""
        if not self.__need_resample:
            return audio_data

        original_length = len(audio_data)
        target_length = int(original_length * self.__resample_ratio)

        if target_length == 0:
            return np.array([], dtype=np.float32)

        try:
            resampled = signal.resample(audio_data, target_length)
            return resampled.astype(np.float32)
        except:
            indices = np.linspace(0, original_length - 1, target_length)
            resampled = np.interp(indices, np.arange(original_length), audio_data)
            return resampled.astype(np.float32)

    def __process_speech_segment(self):
        """Обработка накопленного речевого сегмента"""
        if len(self.__speech_buffer) < self.__min_speech_length:
            logger.warning("Сегмент слишком короткий для распознавания")
            return

        logger.info(f"Распознаем речевой сегмент ({len(self.__speech_buffer) / self.__target_sample_rate:.1f}s)...")

        # Конвертируем в numpy array
        speech_array = np.array(self.__speech_buffer, dtype=np.float32)

        # Распознаем речь
        text, language, confidence = self.__speech_recognizer.transcribe_audio(speech_array)

        if text:
            logger.info(f"🎯 РАСПОЗНАНО [{language.upper()}, уверенность: {confidence:.2f}]:")
            logger.info(f"{text}")
            self.__queue_recognised_text.put(text)
        else:
            logger.warning("Речь не распознана или содержит только шум\n")

    def __process_audio(self):
        """Обработка аудио в отдельном потоке"""
        logger.info("Процесс обработки аудио запущен...")

        while not (self.__running and self.__running.is_set()):
            try:
                audio_chunk = self.__audio_queue.get(timeout=1.0)

                if self.__need_resample:
                    audio_chunk = self.__resample_audio(audio_chunk)

                self.__audio_buffer.extend(audio_chunk)

                while len(self.__audio_buffer) >= 512:
                    chunk_data = np.array([self.__audio_buffer.popleft() for _ in range(512)])

                    if self.__manual_recording:
                        self.__speech_buffer.extend(chunk_data)
                        # Ограничиваем максимальную длину
                        if len(self.__speech_buffer) > self.__max_speech_length:
                            self.__speech_buffer = self.__speech_buffer[-self.__max_speech_length:]

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Ошибка обработки: {e}")

        logger.info("Процесс обработки аудио остановлен...")

    def __audio_callback(self, indata, frames, time, status):
        """Callback для sounddevice"""
        if status:
            logger.info(f"Аудио статус: {status}")

        if len(indata.shape) > 1:
            audio_data = indata[:, 0]
        else:
            audio_data = indata.flatten()

        self.__audio_queue.put(audio_data.copy())

