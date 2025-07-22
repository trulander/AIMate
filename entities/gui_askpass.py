#!/usr/bin/env python3
import tkinter as tk
from tkinter import simpledialog

root = tk.Tk()
root.withdraw()

pwd = simpledialog.askstring(
    title="Root‑пароль",
    prompt="Введите пароль root:",
    show="*"
)
if pwd:
    print(pwd)
