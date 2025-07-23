import logging
import os
import subprocess
import sys
import uuid
from collections import defaultdict
from queue import Queue, Empty
import time
import atexit
from multiprocessing.connection import Client
from threading import Thread, Lock
import traceback
import socket
import _pickle

from business_logic.hotkey_handler.Ihot_key_handler import IHotkeyHandler
from entities.hot_key import HotKey

logger = logging.getLogger(__name__)


class HotkeyHandlerClient(IHotkeyHandler):
    def __init__(self,
                 address=('localhost', 6000),
                 authkey=b'secret',
                 retry_interval=2,
                 max_retries=5):

        self.__address = address
        self.__authkey = authkey
        self.__retry_interval = retry_interval
        self.__max_retries = max_retries
        self.__conn = None
        self.__running = True
        self.__send_lock = Lock()
        self.__recv_lock = Lock()

        self.__response_waiters: dict[str, Queue] = {}
        self.__event_queue = Queue()

        self.__hotkeys = []

        atexit.register(self.stop)

    def keyboard_type_text(self, text):
        logger.info(f'keyboard_type_text {text}')
        self.__send_request(
            action='keyboard_type_text',
            text=text
        )

    def add_hotkey(self, hotkey: list, on_press_callback=None, on_release_callback=None):
        logger.info(f'add hotkey {hotkey}')
        self.__hotkeys.append(
            HotKey(
                keys=hotkey,
                on_activate=on_press_callback,
                on_deactivate=on_release_callback,
            )
        )

        self.__send_request(
            action='add_hotkey',
            hotkey=hotkey,
            on_press_callback=True if on_press_callback else None,
            on_release_callback=True if on_release_callback else None,
        )

    def start(self):
        self.__start_hot_key_server()
        self.__connection_thread = Thread(target=self.__run, daemon=True)
        self.__connection_thread.start()
        logger.info(f"HotkeyHandlerService running")

    def stop(self):
        logging.info("Shutting down client...")
        self.__running = False
        try:
            if self.__conn:
                self.__conn.close()
            self.__connection_thread.join()
        except Exception:
            pass
        logging.info("Client stopped.")

    def __start_hot_key_server(self):
        # Определим корень проекта как директорию этого скрипта
        project_root = os.path.abspath(".")

        # Пути относительные к корню проекта
        script = os.path.join(project_root, "hot_key_handler_server.py")
        askpass = os.path.join(project_root, "entities", "gui_askpass.py")
        python_venv_path = os.path.join(project_root, ".venv", "bin", "python")

        # Подготовка окружения
        env = os.environ.copy()
        env["SUDO_ASKPASS"] = askpass
        env["PYTHONPATH"] = project_root

        cmd = ["sudo", "-A", python_venv_path, script]

        try:
            subprocess.Popen(cmd, env=env, cwd=project_root)  # Указываем cwd для надежности
        except Exception as e:
            print("Ошибка:", e)
            sys.exit(1)

    def _on_press(self, key: tuple):
        logger.debug(f'key {key} pressed')
        for hotkey in self.__hotkeys:
            hotkey.press(key=key)

    def _on_release(self, key: tuple):
        logger.debug(f'key {key} released')
        for hotkey in self.__hotkeys:
            hotkey.release(key=key)

    def __connect(self):
        retries = 0
        # while retries < self.__max_retries:
        while self.__running:
            try:
                logging.info(f"Trying to connect to {self.__address} (attempt {retries + 1})...")
                self.__conn = Client(self.__address, authkey=self.__authkey)
                logging.info("Connected to server.")
                return
            except (ConnectionRefusedError, socket.error):
                retries += 1
                time.sleep(self.__retry_interval)
        raise ConnectionError("Failed to connect to server after retries.")

    def __handle_response(self, response: dict):
        match response:
            case {"event": "on_press"}:
                key = response.get("key", [])
                self._on_press(key=tuple(key))

            case {"event": "on_release"}:
                key = response.get("key", [])
                self._on_release(key=tuple(key))

    def _reader_loop(self):
        while self.__running:
            try:
                with self.__recv_lock:
                    if self.__conn.poll(0.1):
                        try:
                            msg = self.__conn.recv()
                            logger.info(f"Received message: {msg}")
                        except (_pickle.UnpicklingError, EOFError, OSError):
                            logging.warning("Connection lost or corrupted data.")
                            self.__running = False
                            break

                        if isinstance(msg, dict) and 'response_to' in msg:
                            logger.info(f"Received response: {msg}")
                            req_id = msg['response_to']
                            if req_id in self.__response_waiters:
                                self.__response_waiters[req_id].put(msg)
                        elif isinstance(msg, dict) and 'event' in msg:
                            logger.info(f"Received event: {msg}")
                            self.__event_queue.put(msg)
                        else:
                            logging.warning(f"Unknown message from server: {msg}")
            except Exception:
                logging.error(traceback.format_exc())
                self.__running = False
                break

    def __send_request(self, action: str, timeout=3, **kwargs):
        if not self.__conn:
            logging.error("Not connected.")
            return None

        req_id = str(uuid.uuid4())
        payload = {'action': action, 'request_id': req_id, **kwargs}

        response_queue = Queue()
        self.__response_waiters[req_id] = response_queue

        try:
            with self.__send_lock:
                self.__conn.send(payload)
        except Exception:
            logging.error("Failed to send request.")
            del self.__response_waiters[req_id]
            return None

        try:
            response = response_queue.get(timeout=timeout)
            return response
        except Empty:
            logging.warning("Timeout waiting for response.")
            return None
        finally:
            del self.__response_waiters[req_id]

    def __process_event_queue(self):
            while self.__running:
                try:
                    event = self.__event_queue.get(timeout=0.2)
                    self.__handle_response(response=event)
                    logging.info(f"Event received: {event}")
                except Empty:
                    pass

    def __run(self):
        try:
            self.__connect()
        except ConnectionError as e:
            logging.error(str(e))
            return

        self.reader = Thread(target=self._reader_loop, daemon=True)
        self.event_queue = Thread(target=self.__process_event_queue, daemon=True)
        self.reader.start()
        self.event_queue.start()
        self.reader.join()
        self.event_queue.join()





if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    def on_press_callback():
        logger.info(f"on_press_callback called.")

    def on_release_callback():
        logger.info(f"on_release_callback called.")

    service = HotkeyHandlerClient()
    service.start()



    service.__send_request('status')
    time.sleep(1)

    service.add_hotkey(
        hotkey=['ctrl', 'alt'],
        on_press_callback=on_press_callback,
        on_release_callback=on_release_callback
    )

    time.sleep(1)

    for _ in range(2):
        time.sleep(4)

    input()

    service.__send_request('exit')
    service.__running = False
    service.cleanup()

