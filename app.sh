#!/usr/bin/env bash

# Абсолютные пути к нашим скриптам:
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKER="$BASE_DIR/app.py"
PYTHON_VENV_PATH="$BASE_DIR/.venv/bin/python"

# Передаём sudo свой GUI-askpass
export SUDO_ASKPASS="$ASKPASS"

# Запускаем в фоне, перенаправляем логи в файл, отвязываемся от терминала
nohup "$PYTHON_VENV_PATH" "$WORKER" &

# Отвязываем от терминала (чтобы даже если nohup не помог)
disown

echo "🔹 app.py запущен в фоне"
