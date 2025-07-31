from enum import Enum


class Status(Enum):
    WAITING_ROOT_AUTORIZATION = ("ROOT", "Ожидает ввода пароля")
    IDLE = ("🟢", "Готово")
    WORKING = ("🟡", "Инициализация")
    ERROR = ("🔴", "Ошибка")
    STARTED_RECORD = ("🎤", "Запись")
    PROCESSING_RECORD = ("🔇", "В процессе расшифровки")
    FINISHED_RECORD = ("🎯", "Распознано")
    WAITING_AGENT_RESPONSE = ("🟡", "Ожидает ответ агента")

    def __init__(self, icon, text):
        self.icon = icon
        self.text = text
