import tkinter as tk
import logging
from typing import Callable

from PIL import Image, ImageTk
import pystray
from chlorophyll import CodeView
from application.services.view_service import ViewService
from domain.enums.content_media_type import (
    ContentMediaType,
    EXTENSION_MAP,
    MIME_TYPE_MAP,
)
from domain.enums.lexers import Lexers
from presentation.main_menu import MainMenu
from presentation.selection_window import SelectionWindow
from presentation.status_bar import StatusBar
import base64
import io
from tkinter import filedialog, messagebox
from PIL import ImageGrab
import tempfile
import os



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

        self.create_editor(self.editor_frame, "editor", initial_data="", height=1)

        # Метка и поле ввода пользователя
        input_lbl = tk.Label(self.right_frame, text="Ваш запрос:", bg="white", anchor="w")
        input_lbl.pack(anchor="nw", padx=10, pady=(10, 0))

        self.input_frame = tk.Frame(self.right_frame, bg="white", height=1)
        self.input_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.create_editor(self.input_frame, "input_editor", initial_data="", height=1)

        # Область для отображения прикрепленных файлов
        self.attachments_frame = tk.Frame(self.right_frame, bg="white")
        self.attachments_frame.pack(fill="x", padx=10, pady=(0, 5))

        # Кнопки для работы с файлами
        buttons_frame = tk.Frame(self.right_frame, bg="white")
        buttons_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.attach_button = tk.Button(buttons_frame, text="📎 Прикрепить файл", command=self.attach_file)
        self.attach_button.pack(side="left", padx=(0, 10))

        self.clear_button = tk.Button(buttons_frame, text="🗑️ Очистить", command=self.clear_all_attachments)
        self.clear_button.pack(side="left", padx=(0, 10))

        self.send_button = tk.Button(buttons_frame, text="Отправить", command=self.send_message)
        self.send_button.pack(side="right")

        # Переменные для хранения прикрепленных медиафайлов
        self.attached_files = []  # Список файлов: [{'base64': ..., 'mime_type': ..., 'type': ..., 'name': ...}]
        self.status_bar = StatusBar(self)

    def run_app(self):
        self.mainloop()

    def update_chat_listbox(self):
        self.chat_listbox.delete(0, tk.END)  # Очищает список
        self.chat_sessions = self.view_service.get_chat_list()
        for name in self.chat_sessions:
            self.chat_listbox.insert(tk.END, name)

    def create_editor(self, container, attr_name, initial_data=None, height=10, expand: bool = True):
        # Удалить старый, если есть
        old = getattr(self, attr_name, None)
        if old:
            current_text = old.get("1.0", tk.END)
            old.destroy()
        else:
            current_text = ""

        editor = CodeView(
            container,
            lexer=self.default_lexer,
            color_scheme="monokai",
            autohide_scrollbar=False,
            background="white",
            wrap="word",
            height=height,
        )
        editor.pack(fill="both", pady=(0, 10), expand=expand)

        # Инициализируем хранилище изображений для предотвращения удаления сборщиком мусора
        if not hasattr(editor, '_images'):
            editor._images = []

        # Настройка стилей для сообщений
        if attr_name == "editor":
            # # Привязываем обработчики для главного редактора (чат)
            # editor.bind("<Button-3>", self.show_chat_context_menu)  # Правая кнопка мыши
            self.setup_message_styles(editor)
            # Если есть данные чата, заполняем по сообщениям
            if initial_data:
                self.load_chat_messages(editor, initial_data)

        if attr_name == "input_editor":
            # Привязываем обработчики для вставки из буфера обмена
            editor.bind("<Control-v>", self.paste_from_clipboard)
            editor.bind("<Button-3>", self.show_context_menu)  # Правая кнопка мыши

        if not initial_data and current_text:
            # Восстанавливаем текст в поле ввода
            if current_text.strip():
                editor.insert("1.0", current_text)

        setattr(self, attr_name, editor)

    def setup_message_styles(self, editor):
        """Настройка стилей для разных типов сообщений"""
        # Стиль для сообщений пользователя (справа, белый фон)
        editor.tag_config(
            "user_message",
            justify="right",
            # background="white",
            # foreground="black",
            # relief="solid",
            borderwidth=1,
            rmargin=20,
            lmargin1=100,
            lmargin2=100,
            spacing1=8,
            spacing3=8,
        )

        # Стиль для сообщений агента (слева, очень светло-серый фон)
        editor.tag_config(
            "agent_message",
            justify="left",
            # background="#F8F8F8",  # Светло-серый вместо зеленого
            # foreground="black",
            # relief="solid",
            borderwidth=1,
            lmargin1=20,
            lmargin2=20,
            rmargin=100,
            spacing1=8,
            spacing3=8,
        )

        # Стиль для меток пользователя - убираем фон, делаем только цветной текст
        editor.tag_config(
            "user_label",
            justify="right",
            foreground="#4472C4",  # Синий текст без фона
            font=("Arial", 10, "bold"),
            relief="flat",
            rmargin=20,
            lmargin1=100,
            lmargin2=100,
            spacing1=3,
            spacing3=3,
        )

        # Стиль для меток агента - убираем фон, делаем только цветной текст
        editor.tag_config(
            "agent_label",
            justify="left",
            foreground="#70AD47",  # Зеленый текст без фона
            font=("Arial", 10, "bold"),
            relief="flat",
            lmargin1=20,
            lmargin2=20,
            rmargin=100,
            spacing1=3,
            spacing3=3,
        )

        # Стиль для разделителей между сообщениями
        editor.tag_config(
            "separator",
            background="#E0E0E0",  # Серый разделитель
            justify="center",
            spacing1=5,
            spacing3=5,
        )

        # Стили для изображений
        editor.tag_config(
            "user_image",
            justify="right",
            rmargin=20,
            lmargin1=100,
            lmargin2=100,
            spacing1=5,
            spacing3=5,
        )

        editor.tag_config(
            "agent_image",
            justify="left",
            lmargin1=20,
            lmargin2=20,
            rmargin=100,
            spacing1=5,
            spacing3=5,
        )

    def base64_to_image(self, base64_string, max_width=300, max_height=200):
        """Конвертирует base64 строку в ImageTk.PhotoImage с ограничением размера"""
        try:
            # Декодируем base64
            image_data = base64.b64decode(base64_string)
            image = Image.open(io.BytesIO(image_data))

            # Изменяем размер если изображение слишком большое
            if image.width > max_width or image.height > max_height:
                image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            # Конвертируем в PhotoImage
            return ImageTk.PhotoImage(image)
        except Exception as e:
            logger.error(f"Ошибка при конвертации изображения: {e}")
            return None

    def add_message_to_editor(self, editor, message: str, sender: str, media_files: list = None):
        """Добавляет стилизованное сообщение в указанный редактор с поддержкой медиафайлов"""
        # Добавляем разделитель если чат не пустой
        current_content = editor.get("1.0", tk.END).strip()
        if current_content:
            # Добавляем пустую строку как разделитель
            separator_start = editor.index("end-1c")  # Позиция перед последним символом
            editor.insert("end-1c", "\n")
            separator_end = editor.index("end-1c")
            editor.tag_add("separator", separator_start, separator_end)

        if sender.lower() == "user":
            # Добавляем метку пользователя
            label_start = editor.index("end-1c")
            editor.insert("end-1c", " 👤 Пользователь ")
            label_end = editor.index("end-1c")
            editor.tag_add("user_label", label_start, label_end)

            # Переход на новую строку
            editor.insert("end-1c", "\n")

            # Добавляем медиафайлы если есть
            if media_files:
                for media_data in media_files:
                    self.add_media_to_editor(editor, media_data, "user")

            # Добавляем текстовое сообщение если есть
            if message:
                message_start = editor.index("end-1c")
                editor.insert("end-1c", message + "\n")
                message_end = editor.index("end-1c")
                editor.tag_add("user_message", message_start, message_end)

        elif sender.lower() == "agent":
            # Добавляем метку агента
            label_start = editor.index("end-1c")
            editor.insert("end-1c", " 🤖 AI Агент ")
            label_end = editor.index("end-1c")
            editor.tag_add("agent_label", label_start, label_end)

            # Переход на новую строку
            editor.insert("end-1c", "\n")

            # Добавляем медиафайлы если есть (хотя агент обычно не отправляет медиафайлы)
            if media_files:
                for media_data in media_files:
                    self.add_media_to_editor(editor, media_data, "agent")

            # Добавляем текстовое сообщение
            if message:
                message_start = editor.index("end-1c")
                editor.insert("end-1c", message + "\n")
                message_end = editor.index("end-1c")
                editor.tag_add("agent_message", message_start, message_end)

        # Прокручиваем к концу
        editor.see(tk.END)

    def add_media_to_editor(self, editor, media_data: dict, sender: str):
        """Добавляет медиафайл в редактор"""
        # {"mime_type": mime_type, "base64": base64_data, "type": "image"}
        if not media_data:
            return

        base64_data = media_data.get('base64', '')
        mime_type = media_data.get('mime_type', '')
        file_type: ContentMediaType = media_data.get('type', ContentMediaType.UNKNOWN)

        media_start = editor.index("end-1c")

        if file_type == ContentMediaType.IMAGE:
            # For images, show the actual image
            photo_image = self.base64_to_image(base64_data)
            if photo_image:
                # Сохраняем ссылку на изображение
                editor._images.append(photo_image)

                # Вставляем изображение
                editor.image_create("end-1c", image=photo_image)
                editor.insert("end-1c", "\n")
        elif file_type == ContentMediaType.AUDIO:
            # For audio, show a placeholder with file info
            icon = "🎵"
            audio_text = f"{icon} Аудио: ({mime_type}) [Нажмите для прикрепления]"
            editor.insert("end-1c", audio_text + "\n")

            # Создаем тег для клика по аудио
            audio_tag = f"audio_{len(getattr(editor, '_audio_data', []))}"
            if not hasattr(editor, '_audio_data'):
                editor._audio_data = []
            editor._audio_data.append(media_data.copy())

            # Применяем тег к тексту аудио
            line_start = f"{media_start} linestart"
            line_end = f"{media_start} lineend"
            editor.tag_add(audio_tag, line_start, line_end)
            editor.tag_config(audio_tag, foreground="blue", underline=True)
            editor.tag_bind(audio_tag, "<Button-1>",
                          lambda e, data=media_data: self.attach_media_from_chat(data))
        elif file_type == ContentMediaType.VIDEO:
            # For video, show a placeholder with file info
            icon = "🎥"
            video_text = f"{icon} Видео: ({mime_type}) [Нажмите для прикрепления]"
            editor.insert("end-1c", video_text + "\n")

            # Создаем тег для клика по видео
            video_tag = f"video_{len(getattr(editor, '_video_data', []))}"
            if not hasattr(editor, '_video_data'):
                editor._video_data = []
            editor._video_data.append(media_data.copy())

            # Применяем тег к тексту видео
            line_start = f"{media_start} linestart"
            line_end = f"{media_start} lineend"
            editor.tag_add(video_tag, line_start, line_end)
            editor.tag_config(video_tag, foreground="blue", underline=True)
            editor.tag_bind(video_tag, "<Button-1>",
                          lambda e, data=media_data: self.attach_media_from_chat(data))
        else:
            # For unknown files
            icon = "📎"
            file_text = f"{icon} Файл: ({mime_type}) [Нажмите для прикрепления]"
            editor.insert("end-1c", file_text + "\n")

            # Создаем кликабельный тег
            file_tag = f"file_{len(getattr(editor, '_file_data', []))}"
            if not hasattr(editor, '_file_data'):
                editor._file_data = []
            editor._file_data.append(media_data.copy())

            line_start = f"{media_start} linestart"
            line_end = f"{media_start} lineend"
            editor.tag_add(file_tag, line_start, line_end)
            editor.tag_config(file_tag, foreground="blue", underline=True)
            editor.tag_bind(file_tag, "<Button-1>",
                          lambda e, data=media_data: self.attach_media_from_chat(data))

        media_end = editor.index("end-1c")

        # Применяем соответствующий стиль
        if sender == "user":
            editor.tag_add("user_image", media_start, media_end)
        else:
            editor.tag_add("agent_image", media_start, media_end)

    def get_mime_type(self, file_path: str) -> tuple[str, ContentMediaType]:
        """Определяет MIME тип и категорию контента по расширению файла"""
        extension = file_path.lower().rsplit(".", 1)[-1]
        return EXTENSION_MAP.get(
            extension, ("application/octet-stream", ContentMediaType.UNKNOWN)
        )

    def get_media_type_by_mime(self, mime_type: str) -> ContentMediaType:
        """Возвращает тип контента (изображение, аудио, видео) по MIME"""
        return MIME_TYPE_MAP.get(mime_type, ContentMediaType.UNKNOWN)

    def attach_media_from_chat(self, media_data):
        """Прикрепляет медиафайл из чата к новому сообщению"""
        try:
            # Создаем копию данных медиафайла
            new_media = media_data.copy()

            # Добавляем к прикрепленным файлам
            self.attached_files.append(new_media)
            self.update_attachments_display()

            logger.info(f"Медиафайл из чата прикреплен: {new_media['name']}")

        except Exception as e:
            logger.error(f"Ошибка при прикреплении медиафайла из чата: {e}")
            messagebox.showerror("Ошибка", f"Не удалось прикрепить файл: {e}")

    def paste_from_clipboard(self, event=None):
        """Обработчик вставки из буфера обмена"""
        try:
            # Пробуем получить изображение из буфера обмена


            clipboard_image = ImageGrab.grabclipboard()
            self.attach_image(image=clipboard_image)

        except Exception as e:
            logger.error(f"Ошибка при вставке из буфера обмена: {e}")
            return None

    def attach_image(self, image: Image.Image):
        if image:
            # Создаем временный файл для изображения
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                image.save(tmp_file.name, "PNG")

                # Читаем как base64
                with open(tmp_file.name, "rb") as f:
                    base64_data = base64.b64encode(f.read()).decode("utf-8")

                # Удаляем временный файл
                os.unlink(tmp_file.name)

                # Добавляем к прикрепленным файлам
                file_data = {
                    "base64": base64_data,
                    "mime_type": "image/png",
                    "type": ContentMediaType.IMAGE,
                    "name": f"clipboard_image_{len(self.attached_files) + 1}.png",
                }
                self.attached_files.append(file_data)
                self.update_attachments_display()

                logger.info("Изображение вставлено из буфера обмена")
                return "break"  # Предотвращаем стандартную вставку
        else:
            # Если изображения нет, разрешаем стандартную вставку текста
            return None

    def show_chat_context_menu(self, event):
        """Показывает контекстное меню для чата"""
        try:
            # Получаем позицию курсора в тексте
            cursor_pos = self.editor.index(f"@{event.x},{event.y}")

            # Проверяем, есть ли в этой позиции изображение
            images_at_pos = self.editor.image_names()

            context_menu = tk.Menu(self, tearoff=0)

            # Если есть изображения, добавляем опции для работы с ними
            if images_at_pos:
                context_menu.add_command(label="Копировать изображение в буфер",
                                       command=lambda: self.copy_image_to_clipboard(cursor_pos))
                context_menu.add_command(label="Прикрепить это изображение",
                                       command=lambda: self.attach_image_from_chat(cursor_pos))
                context_menu.add_separator()

            context_menu.add_command(label="Копировать текст", command=self.copy_selected_text)
            context_menu.add_separator()
            context_menu.add_command(label="Прикрепить файл", command=self.attach_file)

            context_menu.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            logger.error(f"Ошибка при показе контекстного меню чата: {e}")

    def show_context_menu(self, event):
        """Показывает контекстное меню для поля ввода"""
        try:
            context_menu = tk.Menu(self, tearoff=0)
            context_menu.add_command(label="Вставить изображение из буфера", command=self.paste_from_clipboard)
            context_menu.add_separator()
            context_menu.add_command(label="Прикрепить файл", command=self.attach_file)
            context_menu.add_command(label="Очистить вложения", command=self.clear_all_attachments)

            context_menu.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            logger.error(f"Ошибка при показе контекстного меню: {e}")

    def copy_selected_text(self):
        """Копирует выделенный текст в буфер обмена"""
        try:
            selected_text = self.editor.selection_get()
            self.clipboard_clear()
            self.clipboard_append(selected_text)
        except tk.TclError:
            # Нет выделенного текста
            pass

    def copy_image_to_clipboard(self, position):
        """Копирует изображение из чата в буфер обмена"""
        try:
            # Находим изображение рядом с позицией курсора
            for i, image_ref in enumerate(getattr(self.editor, '_images', [])):
                # Пробуем найти соответствующее изображение в данных сообщений
                # Это упрощенная реализация - в реальности нужно отслеживать связь между изображениями и их данными
                logger.info(f"Попытка копирования изображения {i} в буфер обмена")

        except Exception as e:
            logger.error(f"Ошибка при копировании изображения: {e}")

    def attach_image_from_chat(self, position):
        """Прикрепляет изображение из чата к новому сообщению"""
        try:
            # Это упрощенная реализация
            # В реальности нужно найти base64 данные изображения по позиции
            logger.info("Функция прикрепления изображения из чата пока не реализована полностью")
            messagebox.showinfo("Информация", "Функция в разработке. Пока используйте кнопку 'Прикрепить файл' или вставку из буфера обмена.")

        except Exception as e:
            logger.error(f"Ошибка при прикреплении изображения из чата: {e}")

    def update_attachments_display(self):
        """Обновляет отображение прикрепленных файлов"""
        # Очищаем старые виджеты
        for widget in self.attachments_frame.winfo_children():
            widget.destroy()

        if not self.attached_files:
            return

        # Создаем заголовок если есть файлы
        header = tk.Label(self.attachments_frame, text="Прикрепленные файлы:",
                         bg="white", font=("Arial", 9, "bold"))
        header.pack(anchor="w", pady=(5, 2))

        # Отображаем каждый файл
        for i, file_data in enumerate(self.attached_files):
            file_frame = tk.Frame(self.attachments_frame, bg="#F0F0F0", relief="solid", bd=1)
            file_frame.pack(fill="x", pady=1, padx=5)

            # Иконка в зависимости от типа
            icon = "🖼️" if file_data['type'] == 'image' else "🎵" if file_data['type'] == 'audio' else "🎥" if file_data['type'] == 'video' else "📎"

            # Информация о файле
            info_text = f"{icon} {file_data['name']} ({file_data['mime_type']})"
            file_label = tk.Label(file_frame, text=info_text, bg="#F0F0F0", anchor="w")
            file_label.pack(side="left", fill="x", expand=True, padx=(5, 0), pady=2)

            # Кнопка удаления
            remove_btn = tk.Button(file_frame, text="❌", bg="#F0F0F0",
                                 command=lambda idx=i: self.remove_attachment(idx),
                                 font=("Arial", 8))
            remove_btn.pack(side="right", padx=5, pady=1)

            # Если это изображение, показываем превью
            if file_data['type'] == 'image':
                try:
                    preview_image = self.base64_to_image(file_data['base64'], max_width=100, max_height=60)
                    if preview_image:
                        preview_label = tk.Label(file_frame, image=preview_image, bg="#F0F0F0")
                        preview_label.image = preview_image  # Сохраняем ссылку
                        preview_label.pack(side="right", padx=5, pady=2)
                except Exception as e:
                    logger.error(f"Ошибка создания превью: {e}")

    def remove_attachment(self, index):
        """Удаляет прикрепленный файл по индексу"""
        if 0 <= index < len(self.attached_files):
            removed_file = self.attached_files.pop(index)
            logger.info(f"Удален прикрепленный файл: {removed_file['name']}")
            self.update_attachments_display()

    def clear_all_attachments(self):
        """Очищает все прикрепленные файлы"""
        self.attached_files.clear()
        self.update_attachments_display()
        logger.info("Все прикрепленные файлы очищены")


    def attach_file(self):
        """Прикрепляет медиафайл к сообщению"""
        file_path = filedialog.askopenfilename(
            title="Выберите файл",
            filetypes=[
                ("Все медиафайлы", "*.png *.jpg *.jpeg *.gif *.bmp *.webp *.mp3 *.wav *.ogg *.aac *.m4a *.flac *.mp4 *.avi *.mov *.wmv *.flv *.webm *.mkv"),
                ("Изображения", "*.png *.jpg *.jpeg *.gif *.bmp *.webp *.svg"),
                ("Аудио", "*.mp3 *.wav *.ogg *.aac *.m4a *.flac"),
                ("Видео", "*.mp4 *.avi *.mov *.wmv *.flv *.webm *.mkv"),
                ("Все файлы", "*.*")
            ]
        )

        if file_path:
            try:
                # Определяем MIME тип
                mime_type, file_type = self.get_mime_type(file_path)

                # Читаем и конвертируем в base64
                with open(file_path, "rb") as media_file:
                    file_data = {
                        'base64': base64.b64encode(media_file.read()).decode('utf-8'),
                        'name': file_path.split("/")[-1],  # Имя файла
                        'mime_type': mime_type,
                        'type': file_type
                    }

                self.attached_files.append(file_data)
                self.update_attachments_display()

                logger.info(f"Файл прикреплен: {file_data['name']} ({mime_type})")

            except Exception as e:
                logger.error(f"Ошибка при чтении файла: {e}")
                messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {e}")

    def parse_history_message(self, message: list | str) -> tuple[str, list]:
        textmessage = None
        media = []

        if isinstance(message, list):
            for i in message:
                if ContentMediaType.TEXT.value in i:
                    textmessage = i.get(ContentMediaType.TEXT.value, None)
                elif ContentMediaType.IMAGE.value in i:
                    try:
                        media_data = i.get("image_url")
                        prefix = media_data[len("data:") :]
                        mime_type, base64_data = prefix.split(";base64,", 1)
                        type = self.get_media_type_by_mime(mime_type=mime_type)
                    except ValueError:
                        raise ValueError("Invalid data URL format")
                    media.append(
                        {"mime_type": mime_type, "base64": base64_data, "type": type}
                    )

                elif ContentMediaType.MEDIA.value in i:
                    # {
                    #     "type": "media",
                    #     "data": encoded_audio,  # Use base64 string directly
                    #     "mime_type": audio_mime_type,
                    # }
                    mime_type = i.get("mime_type")
                    base64_data = i.get("data")
                    type = self.get_media_type_by_mime(mime_type=mime_type)
                    media.append(
                        {"mime_type": mime_type, "base64": base64_data, "type": type}
                    )
        elif isinstance(message, str):
            textmessage = message

        return textmessage, media

    def load_chat_messages(self, editor, messages_data):
        """Загружает список сообщений в редактор с правильной стилизацией"""
        for message_dict in messages_data:
            if "human" in message_dict:
                message, media_files = self.parse_history_message(message=message_dict["human"])
                self.add_message_to_editor(editor=editor, message=message, sender="user", media_files=media_files)
            elif "ai" in message_dict:
                message, media_files = self.parse_history_message(message=message_dict["ai"])
                self.add_message_to_editor(editor=editor, message=message, sender="agent", media_files=media_files)

    def change_language(self, event=None):
        logger.info(f"change_language: {event}")
        if event:
            self.default_lexer = Lexers[event].value
        # Пересоздаем редакторы
        self.create_editor(self.editor_frame, "editor", initial_data=None, height=1)
        self.create_editor(self.input_frame, "input_editor", height=1)

    def select_chat(self, event=None):
        selection = self.chat_listbox.curselection()
        if not selection:
            return
        chat_name = self.chat_listbox.get(selection[0])
        self.current_chat_id = chat_name

        # Получаем структурированные данные чата
        chat_data = self.view_service.get_chat(chat_id=self.current_chat_id)
        self.create_editor(self.editor_frame, "editor", initial_data=chat_data, height=1)

    def send_message(self):
        text = self.input_editor.get("1.0", tk.END).strip()

        # Проверяем что есть либо текст либо медиафайлы
        if not text and not self.attached_files:
            return

        logger.info(f"send_message Отправка запроса в чат id: {self.current_chat_id}, text: {text}, files_count: {len(self.attached_files)}")

        # Быстро добавляем сообщение пользователя с медиафайлами если есть
        self.add_message_to_editor(self.editor, text, "user", self.attached_files.copy())

        # Формируем данные для отправки в сервис в формате LangChain
        message_content = []

        # Добавляем текст если есть
        if text:
            message_content.append({"type": "text", "text": text})

        # Добавляем медиафайлы если есть
        for file_data in self.attached_files:
            if file_data['type'] == ContentMediaType.IMAGE:
                # Для изображений используем image_url формат
                image_url = f"data:{file_data['mime_type']};base64,{file_data['base64']}"
                message_content.append({
                    "type": "image_url",
                    "image_url": image_url
                })
            elif file_data['type'] == ContentMediaType.AUDIO:
                # Для аудио используем аналогичный формат
                message_content.append({
                    "type": "media",
                    "data": file_data['base64'],
                    "mime_type": file_data['mime_type'],
                })
            elif file_data['type'] == ContentMediaType.VIDEO:
                # Для видео используем аналогичный формат
                message_content.append(
                    {
                        "type": "media",
                        "data": file_data['base64'],
                        "mime_type": file_data['mime_type'],
                    }
                )

        # Формируем окончательное сообщение
        message_data = {
            "content": message_content
        }

        # Получаем ответ от сервиса (теперь это list[dict])
        result_data = self.view_service.send_message(message=message_data, chat_id=self.current_chat_id)

        # Добавляем новые сообщения из результата
        for message_dict in result_data:
            if "human" in message_dict:
                # Пропускаем, так как сообщение пользователя уже добавлено
                continue
            elif "ai" in message_dict:
                # Агент может вернуть медиафайл (хотя это редко)
                agent_media = message_dict.get("media", None)
                self.add_message_to_editor(self.editor, message_dict["ai"], "agent", agent_media)

        # Очищаем поле ввода и сбрасываем прикрепленный медиафайл
        self.input_editor.delete("1.0", tk.END)
        self.clear_all_attachments()

        self.update_chat_listbox()



    def show_screenshot(self):
        self.mark_area()
        frame = self.view_service.get_screenshot(coords=self.view_service.__coords)
        self.attach_image(image=frame)


    def mark_area(self, call_cack_func: Callable = lambda *args,**kwargs: None):
        if self.selection_window is None:
            self.selection_window = SelectionWindow(main_window=self, call_cack_func=call_cack_func)
        self.selection_window.wait_visibility()
        self.selection_window.attributes('-fullscreen', True)
        self.selection_window.attributes('-alpha', 0.5)
        self.selection_window.grab_set()
        self.selection_window.wait_window(self.selection_window)
        logger.info("mark_area finished")

    def callback_for_receive_coordinates(self, x1: int, y1: int, x2: int, y2: int, callback: Callable):
        self.selection_rect = (x1, y1, x2, y2)
        self.view_service.set_coords_area(coords=self.selection_rect)
        logger.info("Coordinates of selected area:")
        logger.info(f"Top-left corner: ({x1}, {y1})")
        logger.info(f"Bottom-right corner: ({x2}, {y2})")
        self.selection_window = None
        self.start_position = None
        self.update()
        callback(coords=self.selection_rect)

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