from typing import Callable, Protocol


class IHotkeyHandler(Protocol):

    def keyboard_type_text(self, text: str):
        pass

    def add_hotkey(self, hotkey: list, on_press_callback: Callable[[tuple], None] = None, on_release_callback: Callable[[tuple], None] = None):
        pass

    def start(self):
        pass

    def stop(self):
        pass