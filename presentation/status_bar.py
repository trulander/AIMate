import logging
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from domain.enums.lexers import Lexers
from domain.enums.status_statusbar import Status

if TYPE_CHECKING:
    from presentation.main_window import MainWindow


logger = logging.getLogger(__name__)


class StatusBar:
    def __init__(self, root: "MainWindow"):

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

    def set_status(self, status: Status):
        self.status_label.config(text=f"{status.icon} {status.text}")


if __name__ == "__main__":
    def change_language(self, event=None):
        logger.info(f"change_language: {event}")
        if event:
            self.default_lexer = Lexers[event].value
        out_text = self.editor.get("1.0", tk.END)
        in_text = self.input_editor.get("1.0", tk.END)
        self.create_editor(self.editor_frame, "editor", initial_text=out_text, height=1)
        self.create_editor(self.input_frame, "input_editor", initial_text=in_text, height=1)

    self = tk.Tk()
    self.change_language = change_language
    StatusBar(root=self)
    self.mainloop()

