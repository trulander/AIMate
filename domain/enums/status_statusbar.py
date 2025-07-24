from enum import Enum


class Status(Enum):
    WAITING_ROOT_AUTORIZATION = ("ROOT", "Ожидает ввода пароля")
    IDLE = ("🟢", "Готово")
    WORKING = ("🟡", "Инициализация")
    ERROR = ("🔴", "Ошибка")
    STARTED_RECORD = ("🎤", "Запись")
    PROCESSING_RECORD = ("🔇", "В процессе расшифровки")
    FINISHED_RECORD = ("🎯", "Распознано")

    def __init__(self, icon, text):
        self.icon = icon
        self.text = text
