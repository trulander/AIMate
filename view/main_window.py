import threading
import tkinter as tk
from time import sleep
from tkinter import Toplevel
import logging
from PIL import Image, ImageTk
import pystray

from business_logic.orchestration import Orchestration
from view.selection_window import SelectionWindow

logger = logging.getLogger(__name__)


class MainWindow(tk.Tk):
    def __init__(self, orchestrator: Orchestration):
        super().__init__()
        self.orchestrator = orchestrator
        self.title("Main Window")
        self.geometry("300x200")
        self.selection_rect = None
        self.start_position = None
        self.selection_window = None
        self.protocol('WM_DELETE_WINDOW', self.minimize_to_tray)

        btn = tk.Button(self, text="Mark Area", command=self.mark_area)
        btn.pack(pady=20)

        btn = tk.Button(self, text="show screenshot", command=self.show_screenshot)
        btn.pack(pady=20)

        self.label = tk.Label(self)
        self.label.pack()

    def show_screenshot(self):
        self.mark_area()
        frame = self.orchestrator.get_screenshot(coords=self.orchestrator.coords)


        img_tk = ImageTk.PhotoImage(frame)
        self.label.config(image=img_tk)
        self.label.image = img_tk


    def mark_area(self):
        if self.selection_window is None:
            self.selection_window = SelectionWindow(self)
        self.selection_window.wait_visibility()
        self.selection_window.attributes('-fullscreen', True)
        self.selection_window.attributes('-alpha', 0.5)
        self.selection_window.grab_set()
        self.selection_window.wait_window(self.selection_window)
        logger.info("mark_area finished")

    def receive_coordinates(self, x1, y1, x2, y2):
        self.selection_rect = (x1, y1, x2, y2)
        self.orchestrator.set_coords_area(coords=self.selection_rect)
        logger.info(f"Coordinates of selected area:")
        logger.info(f"Top-left corner: ({x1}, {y1})")
        logger.info(f"Bottom-right corner: ({x2}, {y2})")
        self.selection_window = None
        self.start_position = None
        self.update()

    def minimize_to_tray(self):
        self.withdraw()

        # Используй PNG вместо ICO
        image = Image.open("app.ico")

        menu = pystray.Menu(
            pystray.MenuItem('Show', self.show_window),
            pystray.MenuItem('Quit', self.quit_window)
        )

        self.tray_icon = pystray.Icon("myapp", image, "My App", menu)
        self.tray_icon.run()

    def quit_window(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self.destroy()

    def show_window(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self.after(0, self.deiconify)