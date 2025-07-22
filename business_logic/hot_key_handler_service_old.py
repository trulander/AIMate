import logging
from collections import defaultdict
from time import sleep
import time
import atexit
import keyboard
import pyperclip


logger = logging.getLogger(__name__)



class HotKey(object):
    def __init__(self, keys, on_activate, on_deactivate):
        self._state = set()
        self._keys = set(keys)
        self._on_activate = on_activate
        self._on_deactivate = on_deactivate


    def release(self, key):
        if self._state == self._keys:
            self._on_deactivate()
        if key.name in self._state:
            self._state.remove(key.name)


    def press(self, key):
        if key.name in self._keys and key.name not in self._state:
            self._state.add(key.name)
            if self._state == self._keys:
                self._on_activate()




class HotkeyHandlerService:
    def __init__(self):
        self.hotkeys = []

        atexit.register(self.cleanup)

    def keyboard_type_text(self, text):
        logger.info(f'keyboard_type_text {text}')
        pyperclip.copy(text)
        sleep(0.2)  # время на обновление буфера
        # keyboard.write(text)
        keyboard.press_and_release('ctrl+v')


    def add_hotkey(self, hotkey: list, on_press_callback=None, on_release_callback=None):
        logger.info(f'add hotkey {hotkey}')
        # keyboard.add_hotkey(hotkey=hotkey, callback=on_press_callback, suppress=True, trigger_on_release=False)
        # keyboard.add_hotkey(hotkey=hotkey, callback=on_release_callback, suppress=True, trigger_on_release=True)

        self.hotkeys.append(HotKey(keys=hotkey, on_activate=on_press_callback, on_deactivate=on_release_callback))
        keyboard.on_press(callback=self._on_press, suppress=True)
        keyboard.on_release(callback=self._on_release, suppress=True)


    def _on_press(self, key):
        logger.debug(f'key {key.name} pressed')
        for hotkey in self.hotkeys:
            hotkey.press(key=key)


    def _on_release(self, key):
        logger.debug(f'key {key.name} released')
        for hotkey in self.hotkeys:
            hotkey.release(key=key)


    def cleanup(self):
        try:
            keyboard.clear_all_hotkeys()
        except:
            pass


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # keyboard.add_hotkey(hotkey='ctrl+alt', callback=print, args=['space was pressed'], suppress=False, trigger_on_release=False)
    # keyboard.add_hotkey(hotkey='ctrl+alt', callback=print, args=['space was reliase'], suppress=False, trigger_on_release=True)
    service = HotkeyHandlerService()
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