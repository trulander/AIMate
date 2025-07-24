import logging
from time import sleep
import atexit
import keyboard
import pyperclip

from application.interfaces.Ihot_key_handler import IHotkeyHandler
from domain.entities.hot_key import HotKey

logger = logging.getLogger(__name__)


class HotkeyHandler(IHotkeyHandler):
    def __init__(self):
        self.hotkeys = []
        atexit.register(self.stop)

    def keyboard_type_text(self, text):
        logger.info(f'keyboard_type_text {text}')
        pyperclip.copy(text)
        sleep(0.2)  # время на обновление буфера
        # keyboard.write(text)
        keyboard.press_and_release('ctrl+v')

    def add_hotkey(self, hotkey: list, on_press_callback=None, on_release_callback=None):
        logger.info(f'add hotkey {hotkey}')
        self.hotkeys.append(HotKey(keys=hotkey, on_activate=on_press_callback, on_deactivate=on_release_callback))
        keyboard.on_press(callback=self._on_press, suppress=True)
        keyboard.on_release(callback=self._on_release, suppress=True)

    def stop(self):
        try:
            keyboard.clear_all_hotkeys()
        except:
            pass

    def start(self):
        pass

    def _on_press(self, key):
        logger.debug(f'key {key.name} pressed')
        for hotkey in self.hotkeys:
            hotkey.press(key=key.name)

    def _on_release(self, key):
        logger.debug(f'key {key.name} released')
        for hotkey in self.hotkeys:
            hotkey.release(key=key.name)





if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # keyboard.add_hotkey(hotkey='ctrl+alt', callback=print, args=['space was pressed'], suppress=False, trigger_on_release=False)
    # keyboard.add_hotkey(hotkey='ctrl+alt', callback=print, args=['space was reliase'], suppress=False, trigger_on_release=True)
    service = HotkeyHandler()
    def on_hotkey_press(*args, **kwargs):
        print("press")
        service.keyboard_type_text(text='Редактор субтитров О.Голубкина Корректор А.Егорова')


    def on_hotkey_release(*args, **kwargs):
        print("relise")
    # keyboard.on_press_key('ctrl', on_hotkey_press, suppress=False)
    # keyboard.on_release_key('ctrl', on_hotkey_release, suppress=False)

    service.add_hotkey(hotkey=['ctrl', 'alt'], on_press_callback=on_hotkey_press, on_release_callback=on_hotkey_release)
    logger.info("___")
    input()