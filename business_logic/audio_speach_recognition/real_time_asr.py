import logging
import multiprocessing
import platform
import queue
import threading
import time
from collections import deque

import numpy as np

from business_logic.audio_speach_recognition.speach_recognizer import SpeechRecognizer
from business_logic.hot_key_handler_service import HotkeyHandlerService

logger = logging.getLogger(__name__)


# Определяем доступные backend'ы
GSTREAMER_AVAILABLE = False
SOUNDDEVICE_AVAILABLE = False

try:
    import gi

    gi.require_version("Gst", "1.0")
    from gi.repository import GLib, Gst

    Gst.init(None)
    GSTREAMER_AVAILABLE = True
except ImportError:
    logger.warning("GStreamer not available")

try:
    import sounddevice as sd
    from scipy import signal

    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    logger.warning("SoundDevice not available")



class RealTimeASR:
    def __init__(
        self,
        target_sample_rate=16000,
        block_size=1024,
        hotkey: list = [],
        hot_key_handler_service: HotkeyHandlerService = None,
        queue_recognised_text: multiprocessing.Queue = None,
        speech_recognizer: SpeechRecognizer = None,
        preferred_backend=None,
    ):
        """
        Инициализация системы распознавания речи

        Args:
            target_sample_rate: частота дискретизации для модели
            block_size: размер блока аудио
            hotkey: комбинация клавиш для ручного режима
            preferred_backend: 'gstreamer' или 'sounddevice' или None (авто)
        """
        self.__target_sample_rate = target_sample_rate
        self.__block_size = block_size
        self.__audio_queue = queue.Queue()
        self.__queue_recognised_text: multiprocessing.Queue = queue_recognised_text
        self.__running: multiprocessing.Event = None
        self.__hotkey = hotkey
        self.__hot_key_handler_service = hot_key_handler_service
        self.__speech_recognizer: SpeechRecognizer = speech_recognizer

        # Выбираем backend
        self.__backend = self.__choose_backend(preferred_backend)
        logger.info(f"Используем audio backend: {self.__backend}")

        # Общие буферы
        self.__audio_buffer = deque()
        self.__speech_buffer = []
        self.__recording_speech = False
        self.__manual_recording = False
        self.__manual_start_time = None

        # Настройки для распознавания
        self.__min_speech_length = int(0.3 * target_sample_rate)
        self.__max_speech_length = int(60 * target_sample_rate)

        # Инициализация специфичных для backend компонентов
        if self.__backend == "gstreamer":
            self.__init_gstreamer()
        elif self.__backend == "sounddevice":
            self.__init_sounddevice()
        else:
            raise RuntimeError("Нет доступных audio backend'ов")

        self.__setup_hotkeys()

    def __choose_backend(self, preferred_backend):
        """Выбор наиболее подходящего backend'а"""
        system = platform.system().lower()

        if preferred_backend:
            if preferred_backend == "gstreamer" and GSTREAMER_AVAILABLE:
                return "gstreamer"
            elif preferred_backend == "sounddevice" and SOUNDDEVICE_AVAILABLE:
                return "sounddevice"
            else:
                logger.warning(
                    f"Предпочитаемый backend '{preferred_backend}' недоступен"
                )

        # Автоматический выбор на основе платформы
        if system == "linux":
            if GSTREAMER_AVAILABLE:
                return "gstreamer"
            elif SOUNDDEVICE_AVAILABLE:
                return "sounddevice"
        else:  # Windows, macOS
            if SOUNDDEVICE_AVAILABLE:
                return "sounddevice"
            elif GSTREAMER_AVAILABLE:
                return "gstreamer"

        return None

    def __init_gstreamer(self):
        """Инициализация GStreamer backend"""
        self.__pipeline = None
        self.__main_loop = None
        self.__bus = None
        self.__appsink = None
        self.__create_gst_pipeline()

    def __init_sounddevice(self):
        """Инициализация SoundDevice backend"""
        self.__device_sample_rate = self.__find_supported_sample_rate()
        logger.info(f"Устройство поддерживает: {self.__device_sample_rate} Hz")
        logger.info(f"Модель требует: {self.__target_sample_rate} Hz")

        if self.__device_sample_rate != self.__target_sample_rate:
            self.__need_resample = True
            self.__resample_ratio = (
                self.__target_sample_rate / self.__device_sample_rate
            )
            logger.warning(
                f"Будем ресэмплировать с {self.__device_sample_rate} Hz до {self.__target_sample_rate} Hz"
            )
        else:
            self.__need_resample = False

    def __create_gst_pipeline(self):
        """Создание GStreamer pipeline"""
        try:
            pipeline_str = (
                f"autoaudiosrc ! "
                f"audioconvert ! "
                f"audioresample ! "
                f"audio/x-raw,format=F32LE,channels=1,rate={self.__target_sample_rate} ! "
                f"appsink name=sink emit-signals=true max-buffers=1 drop=true"
            )

            self.__pipeline = Gst.parse_launch(pipeline_str)
            self.__appsink = self.__pipeline.get_by_name("sink")
            self.__appsink.connect("new-sample", self.__on_new_sample)

            self.__bus = self.__pipeline.get_bus()
            self.__bus.add_signal_watch()
            self.__bus.connect("message", self.__on_bus_message)

            logger.info(
                f"GStreamer pipeline создан для частоты {self.__target_sample_rate} Hz"
            )

        except Exception as e:
            logger.error(f"Ошибка создания GStreamer pipeline: {e}")
            raise

    def __find_supported_sample_rate(self):
        """Поиск поддерживаемой частоты для SoundDevice"""
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
                    device=default_device, channels=1, samplerate=sr, dtype=np.float32
                )
                return sr
            except:
                continue

        try:
            device_info = sd.query_devices(default_device)
            return int(device_info["default_samplerate"])
        except:
            return 44100

    def start(self, stop_event):
        """Запуск записи и обработки"""
        self.__running = stop_event

        processing_thread = threading.Thread(target=self.__process_audio)
        processing_thread.daemon = True
        processing_thread.start()

        logger.info(f"Начинаем запись с микрофона через {self.__backend}")

        try:
            if self.__backend == "gstreamer":
                self.__start_gstreamer()
            elif self.__backend == "sounddevice":
                self.__start_sounddevice()

        except KeyboardInterrupt:
            logger.info("\nОстанавливаем запись...")
        finally:
            self.stop()

    def __start_gstreamer(self):
        """Запуск GStreamer"""
        ret = self.__pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            raise Exception("Не удалось запустить GStreamer pipeline")

        self.__main_loop = GLib.MainLoop()
        loop_thread = threading.Thread(target=self.__run_main_loop)
        loop_thread.daemon = True
        loop_thread.start()

        while not (self.__running and self.__running.is_set()):
            time.sleep(0.1)

    def __start_sounddevice(self):
        """Запуск SoundDevice"""
        with sd.InputStream(
            channels=1,
            samplerate=self.__device_sample_rate,
            blocksize=self.__block_size,
            callback=self.__audio_callback,
            dtype=np.float32,
        ):
            while not (self.__running and self.__running.is_set()):
                time.sleep(0.1)

    def __run_main_loop(self):
        """Запуск GLib main loop"""
        try:
            self.__main_loop.run()
        except Exception as e:
            logger.error(f"Ошибка в main loop: {e}")

    def stop(self):
        """Остановка записи и обработки"""
        try:
            if self.__running:
                self.__running.set()

            if self.__backend == "gstreamer":
                if self.__pipeline:
                    self.__pipeline.set_state(Gst.State.NULL)
                if self.__main_loop and self.__main_loop.is_running():
                    self.__main_loop.quit()

        except Exception as e:
            logger.error(f"Ошибка при остановке: {e}")

        logger.info("Запись остановлена")

    def __on_new_sample(self, appsink):
        """Callback для GStreamer"""
        try:
            sample = appsink.emit("pull-sample")
            if not sample:
                return Gst.FlowReturn.ERROR

            buffer = sample.get_buffer()
            success, map_info = buffer.map(Gst.MapFlags.READ)
            if not success:
                return Gst.FlowReturn.ERROR

            try:
                audio_data = np.frombuffer(map_info.data, dtype=np.float32)
                self.__audio_queue.put(audio_data.copy())
            finally:
                buffer.unmap(map_info)

            return Gst.FlowReturn.OK

        except Exception as e:
            logger.error(f"Ошибка в GStreamer callback: {e}")
            return Gst.FlowReturn.ERROR

    def __audio_callback(self, indata, frames, time, status):
        """Callback для SoundDevice"""
        if status:
            logger.info(f"Аудио статус: {status}")

        if len(indata.shape) > 1:
            audio_data = indata[:, 0]
        else:
            audio_data = indata.flatten()

        self.__audio_queue.put(audio_data.copy())

    def __on_bus_message(self, bus, message):
        """Обработка сообщений GStreamer"""
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"GStreamer ошибка: {err}")
            if self.__main_loop:
                self.__main_loop.quit()

    def __resample_audio(self, audio_data):
        """Ресэмплирование для SoundDevice"""
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

    def __setup_hotkeys(self):
        """Настройка горячих клавиш"""
        logger.info(f"setup_hotkeys")
        try:
            self.__hot_key_handler_service.add_hotkey(
                hotkey=self.__hotkey,
                on_press_callback=self.__on_hotkey_press,
                on_release_callback=self.__on_hotkey_release,
            )
            logger.info(f"Горячие клавиши настроены: {self.__hotkey}")
        except Exception as e:
            logger.error(f"Ошибка настройки горячих клавиш: {e}")

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
            duration = (
                time.time() - self.__manual_start_time
                if self.__manual_start_time
                else 0
            )
            logger.info(
                f"🔇 РУЧНАЯ ЗАПИСЬ ОСТАНОВЛЕНА (отпущена {self.__hotkey}, длительность: {duration:.1f}с)"
            )

            if len(self.__speech_buffer) > 0:
                recognition_thread = threading.Thread(
                    target=self.__process_speech_segment, daemon=True
                )
                recognition_thread.start()

    def __process_speech_segment(self):
        """Обработка речевого сегмента"""
        if len(self.__speech_buffer) < self.__min_speech_length:
            logger.warning("Сегмент слишком короткий для распознавания")
            return

        logger.info(
            f"Распознаем речевой сегмент ({len(self.__speech_buffer) / self.__target_sample_rate:.1f}s)..."
        )

        speech_array = np.array(self.__speech_buffer, dtype=np.float32)
        text, language, confidence = self.__speech_recognizer.transcribe_audio(
            speech_array
        )

        if text:
            logger.info(
                f"🎯 РАСПОЗНАНО [{language.upper()}, уверенность: {confidence:.2f}]:"
            )
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

                # Ресэмплирование только для SoundDevice
                if self.__backend == "sounddevice":
                    audio_chunk = self.__resample_audio(audio_chunk)

                self.__audio_buffer.extend(audio_chunk)

                while len(self.__audio_buffer) >= 512:
                    chunk_data = np.array(
                        [self.__audio_buffer.popleft() for _ in range(512)]
                    )

                    if self.__manual_recording:
                        self.__speech_buffer.extend(chunk_data)
                        if len(self.__speech_buffer) > self.__max_speech_length:
                            self.__speech_buffer = self.__speech_buffer[
                                -self.__max_speech_length :
                            ]

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Ошибка обработки: {e}")

        logger.info("Процесс обработки аудио остановлен...")

    def __del__(self):
        """Деструктор"""
        try:
            self.stop()
        except:
            pass
