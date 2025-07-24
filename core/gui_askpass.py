#!/usr/bin/env python3
import getpass
import tkinter as tk
from tkinter import ttk
import sys
import webbrowser

class AuthDialog:
    def __init__(self):
        self.password = None
        self.details_visible = False

        # Создаем главное окно
        self.root = tk.Tk()
        self.root.title("Требуется аутентификация")
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)

        # Устанавливаем иконку и делаем окно модальным
        self.root.transient()
        self.root.grab_set()

        # Настраиваем стиль
        self.setup_styles()

        # Создаем интерфейс
        self.create_widgets()

        # Центрируем окно после создания виджетов
        self.center_window()

        # Привязываем события
        self.bind_events()

    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_reqwidth()
        height = self.root.winfo_reqheight()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def setup_styles(self):
        # Настраиваем цветовую схему в стиле системных диалогов
        self.root.configure(bg='#f0f0f0')

        style = ttk.Style()
        style.theme_use('clam')

    def create_widgets(self):
        # Основной фрейм
        main_frame = tk.Frame(self.root, bg='#f0f0f0', padx=20, pady=15)
        main_frame.pack(fill='both', expand=True)

        # Верхняя часть с иконкой и текстом
        top_frame = tk.Frame(main_frame, bg='#f0f0f0')
        top_frame.pack(fill='x', pady=(0, 15))

        # Иконка замка (эмуляция)
        icon_frame = tk.Frame(top_frame, bg='#f0f0f0', width=48, height=48)
        icon_frame.pack(side='left', padx=(0, 15))
        icon_frame.pack_propagate(False)

        # Создаем простую иконку замка
        canvas = tk.Canvas(icon_frame, width=48, height=48, bg='#f0f0f0', highlightthickness=0)
        canvas.pack()

        # Рисуем замок
        canvas.create_rectangle(16, 20, 32, 35, outline='#333', width=2, fill='#ddd')
        canvas.create_arc(18, 12, 30, 24, start=0, extent=180, outline='#333', width=2, style='arc')
        canvas.create_oval(22, 26, 26, 30, fill='#333')
        canvas.create_rectangle(23, 28, 25, 32, fill='#333')

        # Текстовая часть
        text_frame = tk.Frame(top_frame, bg='#f0f0f0')
        text_frame.pack(side='left', fill='both', expand=True)

        # Заголовок
        title_label = tk.Label(
            text_frame,
            text="Authentication is needed to run '/bin/bash' as the super user",
            font=('Sans', 11, 'bold'),
            bg='#f0f0f0',
            fg='#333',
            anchor='w'
        )
        title_label.pack(fill='x')
        user = getpass.getuser()
        # Подзаголовок
        subtitle_label = tk.Label(
            text_frame,
            text=f"Аутентификация пользователя {user} ({user})",
            font=('Sans', 9),
            bg='#f0f0f0',
            fg='#666',
            anchor='w'
        )
        subtitle_label.pack(fill='x', pady=(5, 0))

        # Фрейм для ввода пароля
        password_frame = tk.Frame(main_frame, bg='#f0f0f0')
        password_frame.pack(fill='x', pady=(0, 15))

        # Поле ввода пароля
        self.password_entry = tk.Entry(
            password_frame,
            font=('Sans', 10),
            show='*',
            width=40,
            relief='solid',
            borderwidth=1
        )
        self.password_entry.pack(side='left', fill='x', expand=True)
        self.password_entry.insert(0, "Введите пароль...")
        self.password_entry.configure(fg='#999')

        # Кнопка показать/скрыть пароль
        self.show_password_var = tk.BooleanVar()
        self.show_btn = tk.Button(
            password_frame,
            text="👁",
            width=3,
            command=self.toggle_password_visibility,
            relief='solid',
            borderwidth=1,
            bg='white'
        )
        self.show_btn.pack(side='right', padx=(5, 0))

        # Фрейм для кнопок
        button_frame = tk.Frame(main_frame, bg='#f0f0f0')
        button_frame.pack(fill='x')

        # Кнопка "Подробные сведения"
        self.details_btn = tk.Button(
            button_frame,
            text="ⓘ Подробные сведения",
            command=self.toggle_details,
            relief='flat',
            bg='#f0f0f0',
            fg='#0066cc',
            font=('Sans', 9),
            cursor='hand2',
            anchor='w'
        )
        self.details_btn.pack(side='left')

        # Правые кнопки
        right_buttons = tk.Frame(button_frame, bg='#f0f0f0')
        right_buttons.pack(side='right')

        # Кнопка "Отмена"
        cancel_btn = tk.Button(
            right_buttons,
            text="Отмена",
            command=self.cancel,
            width=10,
            relief="solid",
            borderwidth=1,
            bg="white",
            font=("Sans", 9, "bold"),
        )
        cancel_btn.pack(side='right', padx=(5, 0))

        # Кнопка "OK"
        ok_btn = tk.Button(
            right_buttons,
            text="OK",
            command=self.ok,
            width=10,
            relief='solid',
            borderwidth=1,
            bg='#e3f2fd',
            fg='#1976d2',
            font=('Sans', 9, 'bold')
        )
        ok_btn.pack(side='right')

        # Фрейм для подробностей (скрыт по умолчанию)
        self.details_frame = tk.Frame(main_frame, bg='#f9f9f9', relief='solid', borderwidth=1)

        self.details_text = tk.Text(
            self.details_frame,
            height=9,
            wrap='word',
            bg='#f9f9f9',
            fg='#333',
            font=('Sans', 9),
            relief='flat',
            padx=10,
            pady=10,
            cursor='arrow'
        )
        self.details_text.pack(fill='both', expand=True, padx=5, pady=5)

        # Настраиваем тег для ссылок
        self.details_text.tag_configure("link", foreground="#0066cc", underline=True)
        self.details_text.tag_bind("link", "<Button-1>", self.open_link)
        self.details_text.tag_bind("link", "<Enter>", lambda e: self.details_text.configure(cursor="hand2"))
        self.details_text.tag_bind("link", "<Leave>", lambda e: self.details_text.configure(cursor="arrow"))

        # Заглушка для подробностей с ссылкой
        details_content = """Приложение 'AIMate' запрашивает права суперпользователя для запуска отдельного микросервиса. Для его работы библиотека keyboard требуются root прав, без них назначение горячих клавиш будет не возможно.

Это действие требует ввода пароля администратора для подтверждения разрешения на выполнение привилегированных операций в системе.

Дополнительная информация доступна на """

        link_text = "pypi.org/project/keyboard/"
        link_url = "https://pypi.org/project/keyboard/"

        end_content = "."

        self.details_text.insert('1.0', details_content)

        # Вставляем ссылку
        link_start = self.details_text.index('end-1c')
        self.details_text.insert('end', link_text)
        link_end = self.details_text.index('end-1c')
        self.details_text.tag_add("link", link_start, link_end)

        # Сохраняем URL для ссылки
        self.details_text.tag_add(link_url, link_start, link_end)

        self.details_text.insert('end', end_content)
        self.details_text.configure(state='disabled')

    def bind_events(self):
        # Обработка фокуса для placeholder
        self.password_entry.bind('<FocusIn>', self.on_entry_focus_in)
        self.password_entry.bind('<FocusOut>', self.on_entry_focus_out)

        # Enter для подтверждения
        self.root.bind('<Return>', lambda e: self.ok())
        self.root.bind('<Escape>', lambda e: self.cancel())

        # Устанавливаем фокус на поле ввода
        self.password_entry.focus_set()

    def on_entry_focus_in(self, event):
        if self.password_entry.get() == "Введите пароль..." and self.password_entry.cget('fg') == '#999':
            self.password_entry.delete(0, 'end')
            self.password_entry.configure(fg='black')

    def on_entry_focus_out(self, event):
        if not self.password_entry.get():
            self.password_entry.insert(0, "Введите пароль...")
            self.password_entry.configure(fg='#999')

    def toggle_password_visibility(self):
        if self.show_password_var.get():
            self.password_entry.configure(show='')
            self.show_btn.configure(text="🙈")
            self.show_password_var.set(False)
        else:
            self.password_entry.configure(show='*')
            self.show_btn.configure(text="👁")
            self.show_password_var.set(True)

    def toggle_details(self):
        if self.details_visible:
            self.details_frame.pack_forget()
            self.details_visible = False
        else:
            self.details_frame.pack(fill='x', pady=(10, 0))
            self.details_visible = True

        # Пересчитываем размер окна и центрируем
        self.root.update_idletasks()
        self.center_window()

    def open_link(self, event):
        # Получаем позицию клика
        index = self.details_text.index("@%s,%s" % (event.x, event.y))

        # Получаем все теги в этой позиции
        tags = self.details_text.tag_names(index)

        # Ищем тег с URL (который начинается с http)
        for tag in tags:
            if tag.startswith('http'):
                webbrowser.open(tag)
                break

    def ok(self):
        password = self.password_entry.get()
        if password and password != "Введите пароль...":
            self.password = password
            self.root.quit()

    def cancel(self):
        self.password = None
        self.root.quit()

    def show(self):
        self.root.mainloop()
        return self.password

if __name__ == "__main__":
    dialog = AuthDialog()
    password = dialog.show()

    if password:
        print(password)
    else:
        sys.exit(1)