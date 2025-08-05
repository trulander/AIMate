import base64
import io
import logging
import multiprocessing
import platform
import queue
import threading
import time
import wave
from collections import deque
from enum import Enum
import numpy as np
from core.audio_speach_recognition.speach_recognizer import SpeechRecognizer
from application.services.hot_key_service import HotkeyService
from core.event_dispatcher import dispatcher
from domain.enums.signal import Signal
from domain.enums.status_statusbar import Status


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

class AudioBackends(Enum):
    GSTREAMER = "GSTREAMER"
    SOUNDDEVICE = "SOUNDDEVICE"

class RealTimeASR:
    def __init__(
        self,
        hotkey: list,
        hot_key_handler_service: HotkeyService,
        queue_recognised_text: multiprocessing.Queue,
        speech_recognizer: SpeechRecognizer,
        target_sample_rate=16000,
        block_size=1024,
        preferred_backend=AudioBackends.GSTREAMER,
    ):
        """
        Инициализация системы распознавания речи

        Args:
            target_sample_rate: частота дискретизации для модели
            block_size: размер блока аудио
            hotkey: комбинация клавиш для ручного режима
            preferred_backend: AudioBackends.GSTREAMER или AudioBackends.SOUNDDEVICE или None (авто)
        """
        self.__target_sample_rate = target_sample_rate
        self.__block_size = block_size
        self.__queue_recognised_text: multiprocessing.Queue = queue_recognised_text
        self.__running: multiprocessing.Event = None
        self.__hotkey = hotkey
        self.__hot_key_handler_service = hot_key_handler_service
        self.__speech_recognizer: SpeechRecognizer = speech_recognizer

        # Выбираем backend
        self.__backend = self.__choose_backend(preferred_backend)
        logger.info(f"Используем audio backend: {self.__backend.value}")

        # Компоненты для управления аудиопотоком
        self.__stream_active = False
        self.__audio_stream = None  # Для SoundDevice
        self.__stream_thread = None  # Для GStreamer
        # Общие буферы
        self.__audio_buffer = deque()
        self.__audio_queue = queue.Queue()
        self.__speech_buffer = []
        self.__recording_speech = False
        self.__manual_recording = False
        self.__manual_start_time = None

        # Настройки для распознавания
        self.__min_speech_length = int(0.3 * target_sample_rate)
        self.__max_speech_length = int(60 * target_sample_rate)

        # Инициализация специфичных для backend компонентов
        if self.__backend == AudioBackends.GSTREAMER:
            self.__init_gstreamer()
        elif self.__backend == AudioBackends.SOUNDDEVICE:
            self.__init_sounddevice()
        else:
            raise RuntimeError("Нет доступных audio backend'ов")


    def __choose_backend(self, preferred_backend: AudioBackends) -> AudioBackends | None:
        """Выбор наиболее подходящего backend'а"""
        system = platform.system().lower()

        if preferred_backend:
            if preferred_backend == AudioBackends.GSTREAMER and GSTREAMER_AVAILABLE:
                return AudioBackends.GSTREAMER
            elif preferred_backend == AudioBackends.SOUNDDEVICE and SOUNDDEVICE_AVAILABLE:
                return AudioBackends.SOUNDDEVICE
            else:
                logger.warning(
                    f"Предпочитаемый backend '{preferred_backend}' недоступен"
                )

        # Автоматический выбор на основе платформы
        if system == "linux":
            if GSTREAMER_AVAILABLE:
                return AudioBackends.GSTREAMER
            elif SOUNDDEVICE_AVAILABLE:
                return AudioBackends.SOUNDDEVICE
        else:  # Windows, macOS
            if SOUNDDEVICE_AVAILABLE:
                return AudioBackends.SOUNDDEVICE
            elif GSTREAMER_AVAILABLE:
                return AudioBackends.GSTREAMER

        return None

    def __init_gstreamer(self):
        """Инициализация GStreamer backend"""
        self.__pipeline = None
        self.__glib_main_loop = None
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
            self.__resample_ratio = self.__target_sample_rate / self.__device_sample_rate
            logger.warning(f"Будем ресэмплировать с {self.__device_sample_rate} Hz до {self.__target_sample_rate} Hz")
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
            self.__appsink.connect("new-sample", self.__callback_gstream)

            self.__bus = self.__pipeline.get_bus()
            self.__bus.add_signal_watch()
            self.__bus.connect("message", self.__on_bus_message)

            logger.info(f"GStreamer pipeline создан для частоты {self.__target_sample_rate} Hz")

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
        """Запуск сервиса (но не записи - она начнется по горячим клавишам)"""
        self.__setup_hotkeys()
        self.__running = stop_event

        # Запускаем поток обработки аудио (он будет ждать данных)
        processing_thread = threading.Thread(target=self.__process_audio)
        processing_thread.daemon = True
        processing_thread.start()

        logger.info(f"Сервис запущен. Нажмите {self.__hotkey} для начала записи речи.")
        logger.info("В режиме ожидания - аудиопоток не активен.")

        try:
            dispatcher.send(signal=Signal.set_status, status=Status.IDLE)
            # Просто ждем сигнала остановки, не запуская аудиопоток
            while not (self.__running and self.__running.is_set()):
                time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("\nОстанавливаем сервис...")
        finally:
            self.stop()

    def __start_gstreamer_stream(self):
        """Запуск GStreamer потока"""
        if self.__stream_active:
            return
        logger.info("Запуск GStreamer потока")
        ret = self.__pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            raise Exception("Не удалось запустить GStreamer pipeline")

        self.__glib_main_loop = GLib.MainLoop()
        self.__stream_thread = threading.Thread(target=self.__run_glib_main_loop)
        self.__stream_thread.daemon = True
        self.__stream_thread.start()

        self.__stream_active = True
        logger.info("GStreamer поток запущен")

    def __stop_gstreamer_stream(self):
        """Остановка GStreamer потока"""
        if not self.__stream_active:
            return
        logger.info("Остановка GStreamer потока")
        if self.__pipeline:
            self.__pipeline.set_state(Gst.State.NULL)
        if self.__glib_main_loop and self.__glib_main_loop.is_running():
            self.__glib_main_loop.quit()

        self.__stream_active = False
        logger.info("GStreamer поток остановлен")

    def __start_sounddevice_stream(self):
        """Запуск SoundDevice потока"""
        if self.__stream_active:
            return
        logger.info("Запуск SoundDevice потока")
        self.__audio_stream = sd.InputStream(
            channels=1,
            samplerate=self.__device_sample_rate,
            blocksize=self.__block_size,
            callback=self.__callback_sounddevice,
            dtype=np.float32,
        )
        self.__audio_stream.start()
        self.__stream_active = True
        logger.info("SoundDevice поток запущен")

    def __stop_sounddevice_stream(self):
        """Остановка SoundDevice потока"""
        if not self.__stream_active:
            return
        logger.info("Остановка SoundDevice потока")
        if self.__audio_stream:
            self.__audio_stream.stop()
            self.__audio_stream.close()
            self.__audio_stream = None

        self.__stream_active = False
        logger.info("SoundDevice поток остановлен")

    def __run_glib_main_loop(self):
        """Запуск GLib main loop"""
        try:
            self.__glib_main_loop.run()
        except Exception as e:
            logger.error(f"Ошибка в main loop: {e}")

    def stop(self):
        """Остановка сервиса"""
        try:
            if self.__running:
                self.__running.set()

            # Останавливаем аудиопотоки если они активны
            if self.__stream_active:
                if self.__backend == AudioBackends.GSTREAMER:
                    self.__stop_gstreamer_stream()
                elif self.__backend == AudioBackends.SOUNDDEVICE:
                    self.__stop_sounddevice_stream()

        except Exception as e:
            logger.error(f"Ошибка при остановке: {e}")

        logger.info("Сервис остановлен")

    def __callback_gstream(self, appsink):
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

    def __callback_sounddevice(self, indata, frames, time, status):
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
            if self.__glib_main_loop:
                self.__glib_main_loop.quit()

    def __resample_audio_sounddevice(self, audio_data):
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
        """Обработка нажатия горячей клавиши - НАЧИНАЕМ запись"""
        self.start_recording_audio()

    def __on_hotkey_release(self, *args, **kwargs):
        """Обработка отпускания горячей клавиши - ОСТАНАВЛИВАЕМ запись"""
        self.stop_recording_audio()

        # Запускаем распознавание если есть данные
        if len(self.__speech_buffer) > 0:
            recognition_thread = threading.Thread(
                target=self.__process_speech_segment,
                daemon=True
            )
            recognition_thread.start()

    def start_recording_audio(self):
        if not self.__manual_recording:
            dispatcher.send(signal=Signal.set_status, status=Status.STARTED_RECORD)
            self.__manual_recording = True
            self.__manual_start_time = time.time()
            self.__speech_buffer = []

            # ЗАПУСКАЕМ аудиопоток
            try:
                if self.__backend == AudioBackends.GSTREAMER:
                    self.__start_gstreamer_stream()
                elif self.__backend == AudioBackends.SOUNDDEVICE:
                    self.__start_sounddevice_stream()
                logger.info(f"🎤 ЗАПИСЬ НАЧАЛАСЬ (нажата {self.__hotkey}) - аудиопоток активирован")
            except Exception as e:
                logger.error(f"Ошибка запуска аудиопотока: {e}")
                self.__manual_recording = False

    def stop_recording_audio(self):
        if self.__manual_recording:
            dispatcher.send(signal=Signal.set_status, status=Status.PROCESSING_RECORD)
            self.__manual_recording = False
            duration = (
                time.time() - self.__manual_start_time
                if self.__manual_start_time
                else 0
            )

            # ОСТАНАВЛИВАЕМ аудиопоток
            try:
                if self.__backend == AudioBackends.GSTREAMER:
                    self.__stop_gstreamer_stream()
                elif self.__backend == AudioBackends.SOUNDDEVICE:
                    self.__stop_sounddevice_stream()
                logger.info(
                    f"🔇 ЗАПИСЬ ОСТАНОВЛЕНА (отпущена {self.__hotkey}, длительность: {duration:.1f}с) - аудиопоток деактивирован"
                )
            except Exception as e:
                logger.error(f"Ошибка остановки аудиопотока: {e}")

            dispatcher.send(signal=Signal.set_status, status=Status.FINISHED_RECORD)
            return self.__speech_buffer


    def __process_speech_segment(self):
        """Обработка речевого сегмента"""
        if len(self.__speech_buffer) < self.__min_speech_length:
            logger.warning("Сегмент слишком короткий для распознавания")
            return

        logger.info(f"Распознаем речевой сегмент ({len(self.__speech_buffer) / self.__target_sample_rate:.1f}s)...")

        speech_array = np.array(self.__speech_buffer, dtype=np.float32)
        text, language, confidence = self.__speech_recognizer.transcribe_audio(speech_array)

        if text:
            logger.info(f"🎯 РАСПОЗНАНО [{language.upper()}, уверенность: {confidence:.2f}]:")
            logger.info(f"{text}")
            self.__queue_recognised_text.put(text)
        else:
            logger.warning("Речь не распознана или содержит только шум\n")
        dispatcher.send(signal=Signal.set_status, status=Status.FINISHED_RECOGNITION)

    def __process_audio(self):
        """Обработка аудио в отдельном потоке"""
        logger.info("Процесс обработки аудио запущен (в режиме ожидания)...")

        while not (self.__running and self.__running.is_set()):
            try:
                # Ждем данные только когда идет запись
                audio_chunk = self.__audio_queue.get(timeout=1.0)

                # Ресэмплирование только для SoundDevice
                if self.__backend == AudioBackends.SOUNDDEVICE:
                    audio_chunk = self.__resample_audio_sounddevice(audio_chunk)

                self.__audio_buffer.extend(audio_chunk)

                while len(self.__audio_buffer) >= 512:
                    chunk_data = np.array([self.__audio_buffer.popleft() for _ in range(512)])

                    # Сохраняем данные только во время записи
                    if self.__manual_recording:
                        self.__speech_buffer.extend(chunk_data)
                        if len(self.__speech_buffer) > self.__max_speech_length:
                            self.__speech_buffer = self.__speech_buffer[-self.__max_speech_length:]

            except queue.Empty:
                # Это нормально - просто нет данных (аудиопоток неактивен)
                continue
            except Exception as e:
                logger.error(f"Ошибка обработки: {e}")

        logger.info("Процесс обработки аудио остановлен...")


    def convert_to_wav_base64(self, audio_array) -> str:
        """Конвертация numpy array в WAV и кодирование в base64"""
        # Нормализуем и конвертируем в 16-bit PCM
        audio_normalized = np.clip(audio_array, -1.0, 1.0)
        audio_int16 = (audio_normalized * 32767).astype(np.int16)

        # Создаем WAV файл в памяти
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)  # моно
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.__target_sample_rate)
            wav_file.writeframes(audio_int16.tobytes())

        # Кодируем в base64
        buffer.seek(0)
        audio_base64 = base64.b64encode(buffer.read()).decode("utf-8")
        return audio_base64


    def __del__(self):
        """Деструктор"""
        try:
            self.stop()
        except:
            pass
