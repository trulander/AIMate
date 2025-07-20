import logging
from time import sleep

from pynput import keyboard
import atexit


logger = logging.getLogger(__name__)


class HotkeyHandler:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HotkeyHandler, cls).__new__(cls)
            cls._instance.hotkeys = {}
            cls._instance.combinations = {}
            cls._instance.listener = keyboard.Listener(
                on_press=cls._instance._on_press,
                on_release=cls._instance._on_release
            )
            cls._instance.listener.start()
            cls._instance.global_hotkeys = None
            atexit.register(cls._instance.cleanup)
        return cls._instance

    def add_hotkey(self, hotkey, on_press_callback=None, on_release_callback=None):
        logger.info(f'add hotkey {hotkey}')
        if isinstance(hotkey, str) and '+' in hotkey:
            self.combinations[hotkey] = on_press_callback
            self._update_global_hotkeys()
        else:
            key = keyboard.Key[hotkey] if isinstance(hotkey, str) and hotkey.isalnum() else hotkey
            self.hotkeys[key] = {
                'on_press': on_press_callback,
                'on_release': on_release_callback
            }

    def _update_global_hotkeys(self):
        if self.global_hotkeys:
            self.global_hotkeys.stop()
        if self.combinations:
            self.global_hotkeys = keyboard.GlobalHotKeys(self.combinations)
            self.global_hotkeys.start()

    def _on_press(self, key):
        if key in self.hotkeys and self.hotkeys[key]['on_press']:
            logger.info(f'hotkey {key} pressed')
            self.hotkeys[key]['on_press']()

    def _on_release(self, key):
        if key in self.hotkeys and self.hotkeys[key]['on_release']:
            logger.info(f'hotkey {key} released')
            self.hotkeys[key]['on_release']()

    def cleanup(self):
        if self.global_hotkeys:
            self.global_hotkeys.stop()
        if self.listener:
            self.listener.stop()
        self.hotkeys.clear()
        self.combinations.clear()

if __name__ == '__main__':
    import core.config
    def on_h_press():
        print("ctrl нажата!")


    def on_h_release():
        print("ctrl отпущена!")


    def on_ctrl_alt_h():
        print("Ctrl+Alt+z нажата!")


    # Получение singleton экземпляра
    handler = HotkeyHandler()

    # Одиночная клавиша
    handler.add_hotkey('ctrl', on_h_press, on_h_release)

    # Комбинация клавиш
    handler.add_hotkey('<ctrl>+<alt>+z', on_ctrl_alt_h)

    # input()  # Держит скрипт активным
    sleep(10)