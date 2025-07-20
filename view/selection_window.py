import tkinter as tk
from tkinter import Toplevel
import logging


logger = logging.getLogger(__name__)


class SelectionWindow(Toplevel):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.title("Select Area")
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.canvas.bind('<Button-1>', self.start_selection)
        self.canvas.bind('<B1-Motion>', self.update_selection)
        self.canvas.bind('<ButtonRelease-1>', self.end_selection)


    def start_selection(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y, outline='red', width=2, fill='blue', stipple='gray50'
        )

    def update_selection(self, event):
        if self.rect and self.start_x is not None:
            curr_x = self.canvas.canvasx(event.x)
            curr_y = self.canvas.canvasy(event.y)
            x1, x2 = min(self.start_x, curr_x), max(self.start_x, curr_x)
            y1, y2 = min(self.start_y, curr_y), max(self.start_y, curr_y)
            self.canvas.coords(self.rect, x1, y1, x2, y2)

    def end_selection(self, event):
        if self.start_x is not None and self.rect:
            curr_x = self.canvas.canvasx(event.x)
            curr_y = self.canvas.canvasy(event.y)
            x1, x2 = min(self.start_x, curr_x), max(self.start_x, curr_x)
            y1, y2 = min(self.start_y, curr_y), max(self.start_y, curr_y)
            self.start_x = None
            self.rect = None
            self.main_window.receive_coordinates(x1, y1, x2, y2)
            # sleep(0.3)
            self.destroy()
