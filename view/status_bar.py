import logging
import tkinter as tk
from tkinter import ttk

from entities.lexers import Lexers

logger = logging.getLogger(__name__)

class StatusBar:
    def __init__(self, root):

        # === Статус бар ===
        status_bar = tk.Frame(root, relief=tk.SUNKEN, bd=1)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Пример: выпадающий список

        lang_menu = ttk.OptionMenu(
            status_bar,
            tk.StringVar(value=Lexers.python.name),
            Lexers.python.name,
            *[lexer.name for lexer in Lexers],
            command=root.change_language
        )
        lang_menu.pack(side=tk.LEFT, padx=5, pady=2)

        # Пример: текстовая метка
        status_label = tk.Label(status_bar, text="Готово", anchor="w")
        status_label.pack(side=tk.LEFT, padx=5)

        # Пример: кнопка
        settings_btn = ttk.Button(status_bar, text="⚙️ Настройки")
        settings_btn.pack(side=tk.RIGHT, padx=5)

