import os


def is_wayland():
    return os.environ.get('XDG_SESSION_TYPE') == 'wayland'


def detect_wayland_compositor():
    """
    Возвращает имя композитора на Wayland: 'kwin', 'sway' или None
    """
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    session = os.environ.get("DESKTOP_SESSION", "").lower()
    if "plasma" in desktop or "plasma" in session or "kde" in desktop:
        return "kwin"
    elif "sway" in session or "sway" in desktop:
        return "sway"
    return None