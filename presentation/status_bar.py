import logging
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from core.event_dispatcher import dispatcher
from domain.enums.lexers import Lexers
from domain.enums.signal import Signal
from domain.enums.status_statusbar import Status

if TYPE_CHECKING:
    from presentation.main_window import MainWindow


logger = logging.getLogger(__name__)


class StatusBar:
    def __init__(self, root: "MainWindow"):

        self.root = root
        # === Статус бар ===
        self.status_bar = tk.Frame(root, relief=tk.SUNKEN, bd=1)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.lang_menu = ttk.OptionMenu(
            self.status_bar,
            tk.StringVar(value=Lexers.python.name),
            Lexers.python.name,
            *[lexer.name for lexer in Lexers],
            command=root.change_language
        )
        self.lang_menu.pack(side=tk.LEFT, padx=5, pady=2)

        self.status_label = tk.Label(self.status_bar, text="", anchor="w")
        self.status_label.pack(side=tk.LEFT, padx=5)
        self.set_status(Status.WORKING)

        self.settings_btn = ttk.Button(self.status_bar, text="⚙️ Настройки")
        self.settings_btn.pack(side=tk.RIGHT, padx=5)

        dispatcher.connect(sender=self, signal=Signal.set_status, receiver=self.set_status, weak=True)

    def set_status(self, status: Status):
        self.root.after(0, lambda: self.status_label.config(text=f"{status.icon} {status.text}"))

