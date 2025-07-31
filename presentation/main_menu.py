import logging
import sys
import tkinter as tk
from typing import TYPE_CHECKING
from core.event_dispatcher import dispatcher
from domain.enums.signal import Signal
from domain.enums.status_statusbar import Status

if TYPE_CHECKING:
    from presentation.main_window import MainWindow


logger = logging.getLogger(__name__)


class MainMenu:
    def __init__(self, top:"MainWindow" =None):
        self.top = top

        self.menubar = tk.Menu(top,font="TkMenuFont",bg='white',fg='black')
        top.configure(menu = self.menubar)

        self.sub_menu = tk.Menu(self.menubar, activebackground='#d9d9d9'
                ,activeforeground='black', background='white'
                ,disabledforeground='#bfbfbf', font="-family {Noto Sans} -size 10"
                ,foreground='black', tearoff=0)
        self.menubar.add_cascade(compound='left'
                ,font="-family {Noto Sans} -size 10", label='File'
                ,menu=self.sub_menu, )
        self.sub_menu.add_command(command=self.minimize_to_tray
                ,compound='left', font="-family {Noto Sans} -size 10"
                ,label='Свернуть в трей')
        self.sub_menu.add_command(command=self.close_app, compound='left'
                ,font="-family {Noto Sans} -size 10", label='Exit')
        self.sub_menu1 = tk.Menu(self.menubar, activebackground='#d9d9d9'
                ,activeforeground='black', background='white'
                ,disabledforeground='#bfbfbf', font="-family {Noto Sans} -size 10"
                ,foreground='black', tearoff=0)
        self.menubar.add_cascade(compound='left'
                ,font="-family {Noto Sans} -size 10", label='AI комманды'
                ,menu=self.sub_menu1, )
        self.sub_menu1.add_command(command=self.pic_to_text
                ,compound='left', font="-family {Noto Sans} -size 10"
                ,label='Выделить текст с скриншота')
        self.sub_menu1.add_command(command=self.pic_solve_problem
                ,compound='left', font="-family {Noto Sans} -size 10"
                ,label='Решить задачу на скриншете')
        self.sub_menu1.add_command(command=self.pic_answer_question
                ,compound='left', font="-family {Noto Sans} -size 10"
                ,label='Ответить на вопрос на скриншете')
        self.sub_menu2 = tk.Menu(self.menubar, activebackground='#d9d9d9'
                ,activeforeground='black', background='white'
                ,disabledforeground='#bfbfbf', font="-family {Noto Sans} -size 10"
                ,foreground='black', tearoff=0)
        self.menubar.add_cascade(compound='left'
                ,font="-family {Noto Sans} -size 10", label='Распознавание голоса'
                ,menu=self.sub_menu2, )
        self.sub_menu2.add_command(command=self.start_speach_service
                ,compound='left', font="-family {Noto Sans} -size 10"
                ,label='Запустить агента транскрипции')
        self.sub_menu2.add_command(command=self.stop_speach_service
                ,compound='left', font="-family {Noto Sans} -size 10"
                ,label='Остановить агента транскрипции')

    def close_app(self, *args):
        self.top.quit_window()

    def minimize_to_tray(self, *args):
        self.top.minimize_to_tray()

    def pic_answer_question(self, *args):
        self.top.mark_area()

    def pic_solve_problem(self, *args):
        self.top.mark_area()

    def pic_to_text(self, *args):
        self.top.pic_to_text()



    def start_speach_service(self, *args):
        logger.info('start_speach_service')
        dispatcher.send(signal=Signal.set_status, status=Status.WORKING)
        self.top.view_service.orchestrator.start_speach_service()

    def stop_speach_service(self, *args):
        logger.info('stop_speach_service')
        self.top.view_service.orchestrator.stop_speach_service()

