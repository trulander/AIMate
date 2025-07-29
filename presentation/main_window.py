import tkinter as tk
import logging
from PIL import Image, ImageTk
import pystray
from chlorophyll import CodeView
from application.services.view_service import ViewService
from domain.enums.lexers import Lexers
from presentation.main_menu import MainMenu
from presentation.selection_window import SelectionWindow
from presentation.status_bar import StatusBar


logger = logging.getLogger(__name__)


class MainWindow(tk.Tk):
    def __init__(self, view_service: ViewService):
        super().__init__()
        self.view_service: ViewService = view_service
        self.title("Main Window")
        self.geometry("1045x642+1036+533")
        self.minsize(800, 1000)
        self.selection_rect = None
        self.start_position = None
        self.selection_window = None
        self.tray_icon = None
        self.protocol('WM_DELETE_WINDOW', self.minimize_to_tray)

        self.configure(background="white")
        self.configure(highlightbackground="white")
        self.configure(highlightcolor="black")

        self.main_menu = MainMenu(self)

        # Основной контент
        main_frame = tk.Frame(self, bg="white")
        main_frame.pack(fill="both", expand=True)

        self.editor = None
        self.input_editor = None

        # === Левая панель: список чатов ===
        self.chat_listbox = tk.Listbox(main_frame)
        self.chat_listbox.place(relx=0.01, rely=0.02, relwidth=0.22, relheight=0.96)
        self.chat_listbox.bind("<<ListboxSelect>>", self.select_chat)
        self.current_chat_id: int | None = None
        self.update_chat_listbox()


        # === Правая панель ===
        self.right_frame = tk.Frame(main_frame, bg="white")
        self.right_frame.place(relx=0.24, rely=0.02, relwidth=0.74, relheight=0.96)

        # Метка для AI-ответа
        lbl = tk.Label(self.right_frame, text="Ответ AI агента:", bg="white", anchor="w")
        lbl.pack(anchor="nw", padx=10, pady=5)

        # Выбор языка
        self.default_lexer = Lexers.python.value

        # === Контейнеры для редакторов ===
        self.editor_frame = tk.Frame(self.right_frame, bg="white", height=1)
        self.editor_frame.pack(fill="both", expand=True, padx=10, pady=(5, 5))

        self.create_editor(self.editor_frame, "editor", initial_text="", height=1)

        # Метка и поле ввода пользователя
        input_lbl = tk.Label(self.right_frame, text="Ваш запрос:", bg="white", anchor="w")
        input_lbl.pack(anchor="nw", padx=10, pady=(10, 0))

        self.input_frame = tk.Frame(self.right_frame, bg="white", height=1)
        self.input_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.create_editor(self.input_frame, "input_editor", initial_text="", height=1)

        # Кнопка отправки
        self.send_button = tk.Button(self.right_frame, text="Отправить", command=self.send_message)
        self.send_button.pack(anchor="e", padx=10, pady=(0, 10))
        self.status_bar = StatusBar(self)


    def run_app(self):
        self.mainloop()

    def update_chat_listbox(self):
        self.chat_listbox.delete(0, tk.END)  # Очищает список
        self.chat_sessions = self.view_service.get_chat_list()
        for name in self.chat_sessions:
            self.chat_listbox.insert(tk.END, name)

    def create_editor(self, container, attr_name, initial_text="", height=10, expand: bool = True):
        # Удалить старый, если есть
        old = getattr(self, attr_name, None)
        if old:
            current_text = old.get("1.0", tk.END)
            old.destroy()
        else:
            current_text = ""

        editor = CodeView(container,
                          lexer=self.default_lexer,
                          color_scheme="monokai",
                          autohide_scrollbar=False,
                          background="white",
                          wrap="none",
                          height=height)
        editor.pack(fill="both", pady=(0, 10), expand=expand)
        editor.insert("1.0", initial_text or current_text)
        setattr(self, attr_name, editor)

    def change_language(self, event=None):
        logger.info(f"change_language: {event}")
        if event:
            self.default_lexer = Lexers[event].value
        out_text = self.editor.get("1.0", tk.END)
        in_text = self.input_editor.get("1.0", tk.END)
        self.create_editor(self.editor_frame, "editor", initial_text=out_text, height=1)
        self.create_editor(self.input_frame, "input_editor", initial_text=in_text, height=1)

    def select_chat(self, event=None):
        selection = self.chat_listbox.curselection()
        if not selection:
            return
        chat_name = self.chat_listbox.get(selection[0])
        self.current_chat_id = chat_name

        chat_text = self.view_service.get_chat(chat_id=self.current_chat_id)
        self.create_editor(self.editor_frame, "editor", initial_text=chat_text, height=1)


    def send_message(self):
        text = self.input_editor.get("1.0", tk.END).strip()
        logger.info(f"send_message Отправка запроса в чат id: {self.current_chat_id}, text: {text}")
        result = self.view_service.send_message(message=text, chat_id=self.current_chat_id)
        self.create_editor(self.editor_frame, "editor", initial_text=result, height=15)
        self.update_chat_listbox()


    def show_screenshot(self):
        self.mark_area()
        frame = self.view_service.get_screenshot(coords=self.view_service.__coords)
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

        self.tray_icon = pystray.Icon("AIMate", image, "AIMate", menu)
        self.tray_icon.run()

    def quit_window(self, icon=None, item=None):
        self.view_service.orchestrator.stop_all()
        if self.tray_icon:
            self.tray_icon.stop()
        self.destroy()

    def show_window(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self.after(0, self.deiconify)