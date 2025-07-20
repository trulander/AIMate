import logging

import numpy as np
import sounddevice as sd
import onnxruntime as ort
import threading
import queue
import time
from collections import deque
from scipy import signal
from faster_whisper import WhisperModel
import keyboard
import argparse


logger = logging.getLogger(__name__)


class SpeechRecognizer:
    def __init__(self, model_size="small", language="ru", device="cpu", compute_type="int8"):
        """
        Инициализация Faster-Whisper для распознавания речи

        Args:
            model_size: размер модели ("tiny", "base", "small", "medium", "large-v2", "large-v3")
            language: основной язык ("ru", "en", "auto")
            device: устройство ("cpu", "cuda")
            compute_type: тип вычислений ("int8", "int16", "float16", "float32")
        """
        print(f"Загружаем модель Faster-Whisper: {model_size}")
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            download_root="models"
        )
        self.language = language
        self.sample_rate = 16000

        # Настройки для двуязычного распознавания
        if language == "ru":
            # Для русского с англицизмами
            self.transcribe_options = {
                "language": "ru",
                "task": "transcribe",
                "temperature": 0.0,
                "best_of": 5,
                "beam_size": 5,
                "patience": 1,
                "length_penalty": 1,
                "suppress_tokens": [-1],
                # "multilingual": True,
                "initial_prompt": "Это русский текст с возможными английскими словами и терминами. Deployment процесс проходит после merge в master ветку."
            }
        else:
            # Автоопределение языка
            self.transcribe_options = {
                "task": "transcribe",
                "temperature": 0.0,
                "best_of": 3,
                "beam_size": 5
            }

        print("Модель распознавания загружена!")

    def transcribe_audio(self, audio_data):
        """
        Распознавание речи из аудио данных

        Args:
            audio_data: numpy array с аудио данными (16kHz, float32)

        Returns:
            tuple: (text, language, confidence)
        """
        try:
            # Нормализуем аудио
            if np.max(np.abs(audio_data)) > 0:
                audio_data = audio_data / np.max(np.abs(audio_data)) * 0.95

            # Минимальная длина для распознавания (0.3 секунды)
            min_length = int(0.3 * self.sample_rate)
            if len(audio_data) < min_length:
                return "", "unknown", 0.0

            # Распознаем речь
            segments, info = self.model.transcribe(
                audio_data,
                **self.transcribe_options
            )

            # Собираем текст из сегментов
            text_parts = []
            for segment in segments:
                if segment.text.strip():
                    text_parts.append(segment.text.strip())

            full_text = " ".join(text_parts).strip()

            # Информация о языке
            detected_language = info.language if hasattr(info, 'language') else "unknown"
            confidence = info.language_probability if hasattr(info, 'language_probability') else 0.0

            return full_text, detected_language, confidence

        except Exception as e:
            print(f"Ошибка распознавания: {e}")
            return "", "unknown", 0.0


class RealTimeASR:
    def __init__(self,
                 target_sample_rate=16000,
                 block_size=1024,
                 whisper_model="small",
                 language="ru",
                 hotkey="ctrl+space"):
        """
        Инициализация системы распознавания речи

        Args:
            target_sample_rate: частота дискретизации для модели
            block_size: размер блока аудио
            whisper_model: размер модели Whisper
            language: язык распознавания
            hotkey: комбинация клавиш для ручного режима
        """
        self.target_sample_rate = target_sample_rate
        self.block_size = block_size
        self.audio_queue = queue.Queue()
        self.running = False
        self.hotkey = hotkey

        # Определяем поддерживаемую частоту устройства
        self.device_sample_rate = self.find_supported_sample_rate()
        print(f"Устройство поддерживает: {self.device_sample_rate} Hz")
        print(f"Модель требует: {self.target_sample_rate} Hz")

        # Инициализируем распознаватель речи
        self.speech_recognizer = SpeechRecognizer(
            model_size=whisper_model,
            language=language
        )

        # Буфер для накопления данных
        self.audio_buffer = deque()

        # Буфер для записи речевых сегментов
        self.speech_buffer = []
        self.recording_speech = False

        # Состояние для ручного режима
        self.manual_recording = False
        self.manual_start_time = None

        # Параметры для ресэмплинга
        if self.device_sample_rate != self.target_sample_rate:
            self.need_resample = True
            self.resample_ratio = self.target_sample_rate / self.device_sample_rate
            print(f"Будем ресэмплировать с {self.device_sample_rate} Hz до {self.target_sample_rate} Hz")
        else:
            self.need_resample = False

        # Настройки для распознавания
        self.min_speech_length = int(0.3 * target_sample_rate)  # минимум 0.3 секунды
        self.max_speech_length = int(60 * target_sample_rate)  # максимум 60 секунд

        # Настройка горячих клавиш для ручного режима
        self.setup_hotkeys()

    def setup_hotkeys(self):
        """Настройка горячих клавиш для ручного режима"""
        try:
            keyboard.on_press_key(self.hotkey, self.on_hotkey_press, suppress=False)
            keyboard.on_release_key(self.hotkey, self.on_hotkey_release, suppress=False)
            print(f"Горячие клавиши настроены: {self.hotkey}")
        except Exception as e:
            print(f"Ошибка настройки горячих клавиш: {e}")
            print("Попробуйте запустить с правами администратора или используйте автоматический режим")

    def on_hotkey_press(self, event):
        """Обработка нажатия горячей клавиши"""
        if not self.manual_recording:
            self.manual_recording = True
            self.manual_start_time = time.time()
            self.speech_buffer = []
            print(f"🎤 РУЧНАЯ ЗАПИСЬ НАЧАЛАСЬ (нажата {self.hotkey})")

    def on_hotkey_release(self, event):
        """Обработка отпускания горячей клавиши"""
        if self.manual_recording:
            self.manual_recording = False
            duration = time.time() - self.manual_start_time if self.manual_start_time else 0
            print(f"🔇 РУЧНАЯ ЗАПИСЬ ОСТАНОВЛЕНА (отпущена {self.hotkey}, длительность: {duration:.1f}с)")

            # Запускаем распознавание в отдельном потоке
            if len(self.speech_buffer) > 0:
                recognition_thread = threading.Thread(
                    target=self.process_speech_segment,
                    daemon=True
                )
                recognition_thread.start()

    def find_supported_sample_rate(self):
        """Находим поддерживаемую частоту дискретизации для входного устройства"""
        sample_rates = [16000, 44100, 48000, 22050, 8000]

        try:
            default_device = sd.default.device[0]
            device_info = sd.query_devices(default_device)
            print(f"Используем устройство: {device_info['name']}")
        except:
            print("Используем устройство по умолчанию")
            default_device = None

        for sr in sample_rates:
            try:
                sd.check_input_settings(device=default_device, channels=1,
                                        samplerate=sr, dtype=np.float32)
                return sr
            except:
                continue

        try:
            device_info = sd.query_devices(default_device)
            return int(device_info['default_samplerate'])
        except:

            return 44100

    def resample_audio(self, audio_data):
        """Ресэмплирование аудио до целевой частоты"""
        if not self.need_resample:
            return audio_data

        original_length = len(audio_data)
        target_length = int(original_length * self.resample_ratio)

        if target_length == 0:
            return np.array([], dtype=np.float32)

        try:
            resampled = signal.resample(audio_data, target_length)
            return resampled.astype(np.float32)
        except:
            indices = np.linspace(0, original_length - 1, target_length)
            resampled = np.interp(indices, np.arange(original_length), audio_data)
            return resampled.astype(np.float32)

    def process_speech_segment(self):
        """Обработка накопленного речевого сегмента"""
        if len(self.speech_buffer) < self.min_speech_length:
            print("Сегмент слишком короткий для распознавания")
            return

        print(f"Распознаем речевой сегмент ({len(self.speech_buffer) / self.target_sample_rate:.1f}s)...")

        # Конвертируем в numpy array
        speech_array = np.array(self.speech_buffer, dtype=np.float32)

        # Распознаем речь
        text, language, confidence = self.speech_recognizer.transcribe_audio(speech_array)

        if text:
            print(f"\n{'=' * 60}")
            print(f"🎯 РАСПОЗНАНО [{language.upper()}, уверенность: {confidence:.2f}]:")
            print(f"   {text}")
            print(f"{'=' * 60}\n")
        else:
            print("Речь не распознана или содержит только шум\n")

    def process_audio(self):
        """Обработка аудио в отдельном потоке"""
        print("Начинаем обработку аудио...")

        while self.running:
            try:
                audio_chunk = self.audio_queue.get(timeout=1.0)

                if self.need_resample:
                    audio_chunk = self.resample_audio(audio_chunk)

                self.audio_buffer.extend(audio_chunk)

                while len(self.audio_buffer) >= 512:
                    chunk_data = np.array([self.audio_buffer.popleft() for _ in range(512)])


                    if self.manual_recording:
                        self.speech_buffer.extend(chunk_data)
                        # Ограничиваем максимальную длину
                        if len(self.speech_buffer) > self.max_speech_length:
                            self.speech_buffer = self.speech_buffer[-self.max_speech_length:]

                        # Показываем статус записи
                        duration = len(self.speech_buffer) / self.target_sample_rate
                        print(f"🎙️  ЗАПИСЬ... {duration:.1f}s (удерживайте {self.hotkey})", end="\r")

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Ошибка обработки: {e}")

    def audio_callback(self, indata, frames, time, status):
        """Callback для sounddevice"""
        if status:
            print(f"Аудио статус: {status}")

        if len(indata.shape) > 1:
            audio_data = indata[:, 0]
        else:
            audio_data = indata.flatten()

        self.audio_queue.put(audio_data.copy())

    def start(self):
        """Запуск записи и обработки"""
        self.running = True

        processing_thread = threading.Thread(target=self.process_audio)
        processing_thread.daemon = True
        processing_thread.start()

        print(f"Начинаем запись с микрофона (устройство: {self.device_sample_rate} Hz → модель: {self.target_sample_rate} Hz)")
        print("Нажмите Ctrl+C для остановки\n")


        print(f"📋 ИНСТРУКЦИЯ:")
        print(f"   • Нажмите и удерживайте {self.hotkey} во время говорения")
        print(f"   • Отпустите {self.hotkey} чтобы запустить распознавание")
        print(f"   • Речь будет распознана автоматически после отпускания клавиши\n")


        try:
            with sd.InputStream(
                    channels=1,
                    samplerate=self.device_sample_rate,
                    blocksize=self.block_size,
                    callback=self.audio_callback,
                    dtype=np.float32
            ):
                while self.running:
                    time.sleep(0.1)

        except KeyboardInterrupt:
            print("\nОстанавливаем запись...")
        finally:
            self.stop()

    def stop(self):
        """Остановка записи и обработки"""
        self.running = False
        try:
            keyboard.unhook_all()
        except:
            pass
        print("Запись остановлена")


def main():
    """Основная функция с поддержкой аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description="Real-time Voice Activity Detection + Speech Recognition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python script.py                                    # автоматический режим
  python script.py --mode manual                      # ручной режим (Ctrl+Space)
  python script.py --mode manual --hotkey "ctrl+r"    # ручной режим (Ctrl+R)
  python script.py --model medium --language en       # английский с моделью medium
        """
    )


    parser.add_argument(
        "--hotkey",
        default="ctrl",
        help="Комбинация клавиш для ручного режима (по умолчанию: ctrl)"
    )

    parser.add_argument(
        "--model",
        choices=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
        default="medium",
        help="Размер модели Whisper (по умолчанию: small)"
    )

    parser.add_argument(
        "--language",
        default="ru",
        help="Язык распознавания (по умолчанию: ru)"
    )

    parser.add_argument(
        "--device",
        choices=["cpu", "cuda"],
        default="cpu",
        help="Устройство для вычислений (по умолчанию: cpu)"
    )

    args = parser.parse_args()

    print("=== Real-time Voice Activity Detection + Speech Recognition ===")

    # Проверяем доступные аудио устройства
    print("\nДоступные аудио устройства:")
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            print(f"  {i}: {device['name']} (входы: {device['max_input_channels']})")

    print(f"\n{'=' * 70}")
    print(f"НАСТРОЙКИ:")

    print(f"  Горячие клавиши:     {args.hotkey}")
    print(f"  Модель Whisper:      {args.model}")
    print(f"  Язык:                {args.language}")
    print(f"  Устройство:          {args.device}")
    print(f"{'=' * 70}\n")

    # Создаем и запускаем систему
    try:
        vad_asr = RealTimeASR(
            target_sample_rate=16000,
            block_size=1024,
            whisper_model=args.model,
            language=args.language,
            hotkey=args.hotkey
        )
        vad_asr.start()
    except Exception as e:
        print(f"Ошибка: {e}")
        if "keyboard" in str(e):
            print("Попробуйте:")
            print("1. Запустить с правами администратора")
            print("2. Использовать автоматический режим: python script.py --mode auto")


if __name__ == "__main__":
    # Установка зависимостей:
    # pip install faster-whisper onnxruntime sounddevice numpy scipy keyboard
    #
    # Для CUDA поддержки (опционально):
    # pip install faster-whisper[gpu]

    main()