import atexit
from multiprocessing.connection import Listener
from threading import Thread, Lock
import queue
import time
import uuid
import traceback
import logging

import keyboard
import pyperclip

logging.basicConfig(level=logging.INFO, format='[server] %(message)s')
logger = logging.getLogger(__name__)


class HotKey(object):
    def __init__(self, keys: list, on_activate: bool, on_deactivate: bool):
        self.__state = set()
        self.keys = set(keys)
        self.__on_activate: bool = on_activate
        self.__on_deactivate: bool = on_deactivate

    def release(self, key):
        activated = False
        if self.__state == self.keys:
            activated = True

        if key.name in self.__state:
            self.__state.remove(key.name)

        if self.__on_deactivate and activated:
            return True
        return False

    def press(self, key):
        if key.name in self.keys and key.name not in self.__state:
            self.__state.add(key.name)
            if self.__state == self.keys:
                if self.__on_activate:
                    return True
        return False



class HotKeyHandlerServer:
    def __init__(self, address=('localhost', 6000), authkey=b'secret'):
        self.__address = address
        self.__authkey = authkey
        self.__listener = None
        self.__conn = None
        self.__running = True
        self.__event_queue = queue.Queue()
        self.__send_lock = Lock()
        self.__hotkeys: list[HotKey] = []
        atexit.register(self.cleanup)


    def run(self):
        try:
            self.__listener = Listener(self.__address, authkey=self.__authkey)
            logging.info(f"Listening on {self.__address}...")

            self.__conn = self.__listener.accept()
            logging.info("Client connected.")

            t_recv = Thread(target=self.__recv_loop, daemon=True)
            # t_event = Thread(target=self.__emit_event_loop, daemon=True)
            t_send = Thread(target=self.__send_queue_loop, daemon=True)

            t_recv.start()
            # t_event.start()
            t_send.start()

            while self.__running:
                time.sleep(0.5)

        except Exception as e:
            logging.error("Fatal error in server:\n" + traceback.format_exc())
        finally:
            self.cleanup()

    def keyboard_type_text(self, text):
        logger.info(f'keyboard_type_text {text}')
        pyperclip.copy(text)
        time.sleep(0.2)  # время на обновление буфера
        # keyboard.write(text)
        keyboard.press_and_release('ctrl+v')


    def add_hotkey(self, hotkey: list, on_press_callback=False, on_release_callback=False):
        logger.info(f'add hotkey {hotkey}')
        self.__hotkeys.append(HotKey(keys=hotkey, on_activate=on_press_callback, on_deactivate=on_release_callback))
        keyboard.on_press(callback=self.__on_press, suppress=True)
        keyboard.on_release(callback=self.__on_release, suppress=True)


    def __on_press(self, key):
        logger.debug(f'key {key.name} pressed')
        for hotkey in self.__hotkeys:
            if hotkey.press(key=key):
                logger.info(f'key {key.name} pressed')
                self.__event_queue.put({'event': 'on_press', 'key': hotkey.keys})

    def __on_release(self, key):
        logger.debug(f'key {key.name} released')
        for hotkey in self.__hotkeys:
            if hotkey.release(key=key):
                logger.info(f'key {key.name} released')
                self.__event_queue.put({'event': 'on_release', 'key': hotkey.keys})


    def __recv_loop(self):
        while self.__running:
            try:
                if self.__conn.poll(0.1):
                    request = self.__conn.recv()
                    if not isinstance(request, dict):
                        continue

                    logging.info(f"Received: {request}")
                    response = self.handle_request(request)
                    if response:
                        response['response_to'] = request.get('request_id')
                        self.__send(response)
            except (EOFError, OSError):
                logging.warning("Client disconnected.")
                self.__running = False
                break
            except Exception:
                logging.error("Error receiving data:\n" + traceback.format_exc())


    def __send(self, data: dict):
        try:
            with self.__send_lock:
                self.__conn.send(data)
                logger.info(f"Sent data: {data}")
        except (EOFError, BrokenPipeError, OSError):
            logging.warning("Lost connection during send.")
            self.__running = False
        except Exception:
            logging.error("Send failed:\n" + traceback.format_exc())


    def __send_queue_loop(self):
        while self.__running:
            try:
                data = self.__event_queue.get(timeout=1)
                logger.info(f"Received: {data}")
                self.__send(data)
            except queue.Empty:
                continue
            except Exception:
                logging.error("Event sender crashed:\n" + traceback.format_exc())


    # def __emit_event_loop(self):
    #     counter = 0
    #     while self.__running:
    #         try:
    #             time.sleep(3)
    #             self.__event_queue.put({'event': 'tick', 'data': counter})
    #             counter += 1
    #         except Exception:
    #             logging.error("Error in emitter:\n" + traceback.format_exc())


    def handle_request(self, req: dict):
        try:
            match req:
                case {"action": "add_hotkey"}:
                    self.add_hotkey(
                        hotkey=req.get('hotkey', []),
                        on_press_callback=req.get('on_press_callback', False),
                        on_release_callback=req.get('on_release_callback', False),
                    )
                    return {"status": "ok"}

                case {"action": "keyboard_type_text"}:
                    self.keyboard_type_text(text=req.get('text', ""))
                    return {"status": "ok"}

                case {"action": "status"}:
                    return {"status": "ok"}

                case {"action": "exit"}:
                    self.__running = False
                    return {"status": "bye"}

                case _:
                    return {"status": "error", "message": "unknown action"}

        except Exception:
            logging.error("Request handler error:\n" + traceback.format_exc())
            return {"status": "error", "message": "internal server error"}


    def cleanup(self):
        logging.info("Cleaning up...")
        self.__running = False
        try:
            if self.__conn:
                self.__conn.close()
        except Exception:
            pass
        try:
            if self.__listener:
                self.__listener.close()
        except Exception:
            pass
        logging.info("Server stopped.")


if __name__ == '__main__':
    HotKeyHandlerServer().run()
