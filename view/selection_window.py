import threading
import tkinter as tk
from time import sleep
from tkinter import Toplevel
import logging
from PIL import Image
import pystray
from core.config import *


logger = logging.getLogger(__name__)


class SelectionWindow(Toplevel):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.title("Select Area")
        self.selection_started = False
        self.start_position = None

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Button-1>", self.handle_click)

    def handle_click(self, event):
        if not self.selection_started:
            self.selection_started = True
            self.start_position = (event.x, event.y)
        else:
            x1, y1 = self.start_position
            x2, y2 = event.x, event.y
            self.main_window.receive_coordinates(x1, y1, x2, y2)
            self.selection_started = False
            sleep(0.3)
            self.destroy()