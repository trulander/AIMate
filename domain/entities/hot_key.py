from typing import Iterable

from Cryptodome.Cipher.DES3 import key_size


class HotKey(object):
    def __init__(self, keys, on_activate, on_deactivate):
        self._state = set()
        self._keys = set(keys)
        self._on_activate = on_activate
        self._on_deactivate = on_deactivate

    def release(self, key: str | Iterable):
        if self._state == self._keys and self._on_deactivate:
            self._on_deactivate(self._keys)
        if isinstance(key, str):
            if key in self._state:
                self._state.remove(key)
        elif isinstance(key, Iterable):
            self._state = set()

    def press(self, key: str | Iterable):
        if isinstance(key, str):
            if key in self._keys and key not in self._state:
                self._state.add(key)
                if self._state == self._keys:
                    self._on_activate(self._keys)

        elif isinstance(key, Iterable):
            set_key = set(key)
            if self._state!= set_key and set_key == self._keys and self._on_activate:
                self._state = set_key
                self._on_activate(self._keys)