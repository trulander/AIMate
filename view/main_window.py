import threading
import tkinter as tk
from time import sleep
from tkinter import Toplevel, ttk
import logging
from PIL import Image, ImageTk
import pystray
from chlorophyll import CodeView
from pygments import lexers

from business_logic.orchestration import Orchestration
from view.main_menu import MainMenu
from view.selection_window import SelectionWindow

logger = logging.getLogger(__name__)


LEXERS = {
    "text": lexers.TextLexer,
    "python": lexers.PythonLexer,
    "javascript": lexers.JavascriptLexer,
    "html": lexers.HtmlLexer,
    "bash": lexers.BashLexer,
    "json": lexers.JsonLexer,
    "css": lexers.CssLexer,
}


class MainWindow(tk.Tk):
    def __init__(self, orchestrator: Orchestration):
        super().__init__()
        self.orchestrator = orchestrator
        self.title("Main Window")
        self.geometry("1045x642+1036+533")
        self.minsize(800, 800)
        self.selection_rect = None
        self.start_position = None
        self.selection_window = None
        self.protocol('WM_DELETE_WINDOW', self.minimize_to_tray)

        self.configure(background="white")
        self.configure(highlightbackground="white")
        self.configure(highlightcolor="black")
        MainMenu(self)

        self.editor = None
        self.input_editor = None

        # === Левая панель: список чатов ===
        self.chat_listbox = tk.Listbox(self)
        self.chat_listbox.place(relx=0.01, rely=0.02, relwidth=0.22, relheight=0.96)
        self.chat_listbox.bind("<<ListboxSelect>>", self.select_chat)

        self.chat_sessions = {
            "Chat 1": "print('Hello from Chat 1')",
            "Chat 2": "<h1>Hello from Chat 2</h1>",
            "Chat 3": "echo Hello from Chat 3",
        }
        for name in self.chat_sessions:
            self.chat_listbox.insert(tk.END, name)

        # === Правая панель ===
        self.right_frame = tk.Frame(self, bg="white")
        self.right_frame.place(relx=0.24, rely=0.02, relwidth=0.74, relheight=0.96)

        # Метка для AI-ответа
        lbl = tk.Label(self.right_frame, text="Ответ AI агента:", bg="white", anchor="w")
        lbl.pack(anchor="nw", padx=10, pady=5)

        # Выбор языка
        self.lang_var = tk.StringVar(value="python")
        self.lang_combo = ttk.Combobox(self.right_frame, values=list(LEXERS.keys()),
                                       textvariable=self.lang_var, state='readonly')
        self.lang_combo.pack(anchor="nw", padx=10, pady=(0, 5))
        self.lang_combo.bind("<<ComboboxSelected>>", self.change_language)

        # === Контейнеры для редакторов ===
        self.editor_frame = tk.Frame(self.right_frame, bg="white")
        self.editor_frame.pack(fill="both", expand=True, padx=10, pady=(5, 5))

        self.create_editor(self.editor_frame, "editor", initial_text="", height=None)

        # Метка и поле ввода пользователя
        input_lbl = tk.Label(self.right_frame, text="Ваш запрос:", bg="white", anchor="w")
        input_lbl.pack(anchor="nw", padx=10, pady=(10, 0))

        self.input_frame = tk.Frame(self.right_frame, bg="white")
        self.input_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.create_editor(self.input_frame, "input_editor", initial_text="", height=7)

        # Кнопка отправки
        self.send_button = tk.Button(self.right_frame, text="Отправить", command=self.send_message)
        self.send_button.pack(anchor="e", padx=10, pady=(0, 10))

        # btn = tk.Button(self, text="Mark Area", command=self.mark_area)
        # btn.pack(pady=20)
        #
        # btn = tk.Button(self, text="show screenshot", command=self.show_screenshot)
        # btn.pack(pady=20)
        #
        # self.label = tk.Label(self)
        # self.label.pack()

    def create_editor(self, container, attr_name, initial_text="", height=None, expand: bool = True):
        # Удалить старый, если есть
        old = getattr(self, attr_name, None)
        if old:
            current_text = old.get("1.0", tk.END)
            old.destroy()
        else:
            current_text = ""

        lexer_cls = LEXERS.get(self.lang_var.get())
        editor = CodeView(container,
                          lexer=lexer_cls,
                          color_scheme="monokai",
                          autohide_scrollbar=False,
                          background="white",
                          wrap="none",
                          height=height)
        editor.pack(fill="both", pady=(0, 10), expand=expand)
        editor.insert("1.0", initial_text or current_text)
        setattr(self, attr_name, editor)

    def change_language(self, event=None):
        out_text = self.editor.get("1.0", tk.END)
        in_text = self.input_editor.get("1.0", tk.END)
        self.create_editor(self.editor_frame, "editor", initial_text=out_text, height=None)
        self.create_editor(self.input_frame, "input_editor", initial_text=in_text, height=7)

    def select_chat(self, event=None):
        selection = self.chat_listbox.curselection()
        if not selection:
            return
        chat_name = self.chat_listbox.get(selection[0])
        chat_text = self.chat_sessions.get(chat_name, "")
        self.create_editor(self.editor_frame, "editor", initial_text=chat_text, height=15)

    def send_message(self):
        text = self.input_editor.get("1.0", tk.END).strip()
        print("Отправка запроса:", text)
        # result = ai_model.generate(text)
        # self.create_editor(self.editor_frame, "editor", initial_text=result, height=15)


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