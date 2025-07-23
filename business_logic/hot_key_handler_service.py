import platform
import logging
from business_logic.hotkey_handler.Ihot_key_handler import IHotkeyHandler
from business_logic.hotkey_handler.hot_key_handler import HotkeyHandler
from business_logic.hotkey_handler.hot_key_handler_client import HotkeyHandlerClient


logger = logging.getLogger(__name__)


class HotkeyHandlerService():
    def __init__(self):
        if platform.system() == "Linux":
            self.hot_key_handler: IHotkeyHandler = HotkeyHandlerClient()
        else:
            self.hot_key_handler = HotkeyHandler()

    def stop(self):
        self.hot_key_handler.stop()

    def start(self):
        self.hot_key_handler.start()

    def keyboard_type_text(self, text):
        logger.info(f'keyboard_type_text {text}')
        self.hot_key_handler.keyboard_type_text(
            text=text
        )

    def add_hotkey(self, hotkey: list, on_press_callback=None, on_release_callback=None):
        logger.info(f'add hotkey {hotkey}')
        self.hot_key_handler.add_hotkey(
            hotkey=hotkey,
            on_press_callback=on_press_callback,
            on_release_callback=on_release_callback
        )

