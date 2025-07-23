from abc import ABC
from typing import Callable


class IHotkeyHandler(ABC):

    def keyboard_type_text(self, text: str):
        raise NotImplementedError()

    def add_hotkey(self, hotkey: list, on_press_callback: Callable[[tuple], None] = None, on_release_callback: Callable[[tuple], None] = None):
        raise NotImplementedError()

    def start(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()