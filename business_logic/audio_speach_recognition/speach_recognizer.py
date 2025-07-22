import logging

import numpy as np
from faster_whisper import WhisperModel


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
        logger.info(f"Загружаем модель Faster-Whisper: {model_size}")
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
                # "initial_prompt": "Это русский текст с возможными английскими словами и терминами. Deployment процесс проходит после merge в master ветку."
            }
        else:
            # Автоопределение языка
            self.transcribe_options = {
                "task": "transcribe",
                "temperature": 0.0,
                "best_of": 3,
                "beam_size": 5
            }

        logger.info("Модель распознавания загружена!")

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
            logger.error(f"Ошибка распознавания: {e}")
            return "", "unknown", 0.0
