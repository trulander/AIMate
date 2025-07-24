import inspect
import logging
import logging.config
import sys
import time
import os
from pythonjsonlogger import jsonlogger

from core.config.config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    project_dir = os.path.dirname(os.path.abspath(__file__))
    def get_caller_info(self):
        stack = inspect.stack()
        caller_chain = []

        for frame_info in stack:
            # Пропускаем фреймы, относящиеся к логгеру и форматтеру, а также системные и сторонние библиотеки
            if frame_info.function in ('format', 'get_caller_info', 'emit', 'add_fields'):
                continue
            if frame_info.filename.startswith(self.project_dir):
                caller_chain.append(f"{frame_info.function}, {frame_info.lineno}, {frame_info.filename}")
        # Обратный порядок, чтобы сначала была первая вызывающая функция
        caller_chain.reverse()
        return {i:val for i, val in enumerate(caller_chain)}

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        # Основные поля
        log_record["service"] = settings.SERVICE_NAME
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["message"] = record.getMessage()

        log_record["pid"] = os.getpid()
        log_record["thread_id"] = record.thread
        log_record["thread_name"] = record.threadName
        
        # Добавляем меток времени в секундах с начала эпохи
        log_record["timestamp_epoch"] = int(time.time())

        # # Если есть исключение, добавляем его информацию
        # if record.exc_info:
        #     log_record["exception"] = self.formatException(record.exc_info)
        #
        #     # Извлекаем номер строки из стектрейса
        #     tb_lines = traceback.format_exception(*record.exc_info)
        #     tb_str = ''.join(tb_lines)
        #     match = re.search(r'File ".*", line (\d+)', tb_str)
        #     if match:
        #         line_number = match.group(1)
        #         log_record["line_number"] = int(line_number)

        if settings.TRACE_CALLER:
            # Добавляем информацию о вызывающей функции
            log_record["called_by"] = self.get_caller_info()

def configure_logging():
    """Настройка JSON логирования"""
    log_level = getattr(logging, settings.LOG_LEVEL)
    log_handler = logging.StreamHandler(sys.stdout)
    
    # Используем JSON или обычный формат логирования в зависимости от настроек
    if settings.LOG_FORMAT.lower() == "json":
        formatter = CustomJsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(levelname)-8s | %(name)s | [%(filename)s:%(lineno)d] (%(funcName)s) | %(message)s"
        )
    
    log_handler.setFormatter(formatter)
    
    logging.basicConfig(
        level=log_level,
        handlers=[log_handler],
    )

    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.handlers = [log_handler]
