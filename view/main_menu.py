import logging
import sys
import tkinter as tk

_debug = True
_bgcolor = 'white'
_fgcolor = 'black'
_tabfg1 = 'black'
_tabfg2 = 'white'
_bgmode = 'light'
_tabbg1 = '#d9d9d9'
_tabbg2 = 'gray40'

logger = logging.getLogger(__name__)

class MainMenu:
    def __init__(self, top=None):
        self.top = top

        self.menubar = tk.Menu(top,font="TkMenuFont",bg='white',fg=_fgcolor)
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
        self.sub_menu12 = tk.Menu(self.menubar, activebackground='#d9d9d9'
                ,activeforeground='black', background='white'
                ,disabledforeground='#bfbfbf', font="-family {Noto Sans} -size 10"
                ,foreground='black', tearoff=0)
        self.menubar.add_cascade(compound='left'
                ,font="-family {Noto Sans} -size 10", label='Распознавание голоса'
                ,menu=self.sub_menu12, )
        self.sub_menu12.add_command(command=self.start_speach_service
                ,compound='left', font="-family {Noto Sans} -size 10"
                ,label='Запустить агента транскрипции')
        self.sub_menu12.add_command(command=self.stop_speach_service
                ,compound='left', font="-family {Noto Sans} -size 10"
                ,label='Остановить агента транскрипции')

    def close_app(self, *args):
        self.top.quit_window()


    def minimize_to_tray(self, *args):
        self.top.minimize_to_tray()

    def pic_answer_question(self, *args):
        if _debug:
            print('test_support.pic_answer_question')
            for arg in args:
                print('    another arg:', arg)
            sys.stdout.flush()

    def pic_solve_problem(self, *args):
        if _debug:
            print('test_support.pic_solve_problem')
            for arg in args:
                print('    another arg:', arg)
            sys.stdout.flush()

    def pic_to_text(self, *args):
        if _debug:
            print('test_support.pic_to_text')
            for arg in args:
                print('    another arg:', arg)
            sys.stdout.flush()

    def start_speach_service(self, *args):
        logger.info(f'start_speach_service')
        self.top.orchestrator.start_speach_service()

    def stop_speach_service(self, *args):
        logger.info(f'stop_speach_service')
        self.top.orchestrator.stop_speach_service()

