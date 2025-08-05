from enum import Enum


class Status(Enum):
    WAITING_ROOT_AUTORIZATION = ("🔴", "Ожидает ввода пароля ROOT")
    CONNECTED_HOTKEY_SERVER = ("🟡", "Подключено к серверу горячих клавиш")
    IDLE = ("🟢", "Готово")
    WORKING = ("🟡", "Инициализация")
    ERROR = ("🔴", "Ошибка")
    STARTED_RECORD = ("🎤", "Запись")
    FINISHED_RECORD = ("🎯", "Записано")
    PROCESSING_RECORD = ("🔇", "В процессе расшифровки")
    FINISHED_RECOGNITION = ("🎯", "Распознано")
    WAITING_AGENT_RESPONSE = ("🟡", "Ожидает ответ агента")

    def __init__(self, icon, text):
        self.icon = icon
        self.text = text
