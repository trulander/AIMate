import atexit
from multiprocessing.connection import Listener
from threading import Thread, Lock
import queue
import time
import traceback
import logging
from application.interfaces.Ihot_key_handler import IHotkeyHandler
from core.config.logging_config import configure_logging
from core.hotkey_handler.hot_key_handler import HotkeyHandler


configure_logging()
logger = logging.getLogger(__name__)


class HotKeyHandlerServer:
    def __init__(self, address=('localhost', 6000), authkey=b'secret'):
        self.__address = address
        self.__authkey = authkey
        self.__listener = None
        self.__conn = None
        self.__running = True
        self.__event_queue = queue.Queue()
        self.__send_lock = Lock()
        atexit.register(self.cleanup)
        self.hot_key_handler: IHotkeyHandler = HotkeyHandler()

    def run(self):
        try:
            self.__listener = Listener(self.__address, authkey=self.__authkey)
            logging.info(f"Listening on {self.__address}...")

            self.__conn = self.__listener.accept()
            logging.info("Client connected.")

            t_recv = Thread(target=self.__recv_loop, daemon=True)
            t_send = Thread(target=self.__send_queue_loop, daemon=True)

            t_recv.start()
            t_send.start()

            while self.__running:
                time.sleep(0.5)

        except Exception as e:
            logging.error("Fatal error in server:\n" + traceback.format_exc())
        finally:
            self.cleanup()

    def add_hotkey(self, hotkey: list, on_press_callback=False, on_release_callback=False):
        logger.info(f'add hotkey {hotkey}')
        self.hot_key_handler.add_hotkey(
            hotkey=hotkey,
            on_press_callback=self.__on_press,
            on_release_callback=self.__on_release
        )

    def __on_press(self, keys):
        logger.debug(f'key {keys} pressed')
        self.__event_queue.put({'event': 'on_press', 'key': keys})

    def __on_release(self, keys):
        logger.debug(f'key {keys} released')
        self.__event_queue.put({'event': 'on_release', 'key': keys})

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
                    self.hot_key_handler.keyboard_type_text(text=req.get('text', ""))
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
