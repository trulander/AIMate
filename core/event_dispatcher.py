# from pydispatch import dispatcher
import logging
import traceback
from collections import defaultdict
from typing import Callable
from domain.enums.signal import Signal
import weakref


logger = logging.getLogger(__name__)


class EventDispatcher:
    def __init__(self):
        self._listeners: dict[Signal, dict] = {}

    def connect(self, signal: Signal, receiver: Callable, sender: object, weak: bool) -> None:
        """Подписывает receiver на сигнал."""
        ref = weakref.ref(sender)
        if signal not in self._listeners:
            self._listeners[signal] = {
                'receiver': [],
                'sender': ref,
            }
        self._listeners[signal]['receiver'].append(receiver)

    def send(self, signal: Signal, **kwargs) -> None:
        """Отправляет сигнал всем подписчикам."""
        try:
            if signal in self._listeners:
                sender = self._listeners[signal]['sender']()
                if sender:
                    for receiver in self._listeners[signal]['receiver']:
                        receiver(**kwargs)
        except Exception as e:
            logger.error(traceback.format_exc())

# Создаем глобальный экземпляр диспетчера
dispatcher = EventDispatcher()
