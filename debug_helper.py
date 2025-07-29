# debug_helper.py - файл для интеграции с PyCharm Debugger

import inspect
import sys
from typing import Any


import inspect
def get_object_attributes(obj):
    class Result:
        pass

    result = Result()
    cls = obj.__class__
    mro = cls.mro()

    def get_method_signature(method):
        """Получает сигнатуру метода с типами параметров и возвращаемого значения"""
        try:
            sig = inspect.signature(method)

            # Формируем строку с параметрами
            params = []
            for param_name, param in sig.parameters.items():
                param_str = param_name

                # Добавляем аннотацию типа параметра
                if param.annotation != inspect.Parameter.empty:
                    param_str += f": {_format_annotation(param.annotation)}"

                # Добавляем значение по умолчанию
                if param.default != inspect.Parameter.empty:
                    param_str += f" = {repr(param.default)}"

                params.append(param_str)

            # Формируем строку возвращаемого типа
            return_annotation = ""
            if sig.return_annotation != inspect.Signature.empty:
                return_annotation = f" -> {_format_annotation(sig.return_annotation)}"

            # Получаем имя метода
            method_name = getattr(method, "__name__", "unknown")

            return f"{method_name}({', '.join(params)}){return_annotation}"

        except Exception as e:
            # Если не удалось получить сигнатуру, возвращаем базовую информацию
            method_name = getattr(method, "__name__", "unknown")
            return f"{method_name}(...) [signature unavailable: {e}]"

    def _format_annotation(annotation):
        """Форматирует аннотацию типа в читаемый вид"""
        if hasattr(annotation, "__name__"):
            return annotation.__name__
        elif hasattr(annotation, "__module__") and hasattr(annotation, "__qualname__"):
            return f"{annotation.__module__}.{annotation.__qualname__}"
        else:
            return str(annotation)

    for name in dir(obj):
        if name.startswith("__") and name.endswith("__"):
            continue  # пропускаем dunder

        try:
            attr = getattr(obj, name)
        except Exception:
            continue

        # Является ли это метод (ручная проверка для исключения property)
        is_method = (
            inspect.ismethod(attr)
            or inspect.isfunction(attr)
            or inspect.isroutine(attr)
        )

        # Проверяем на mangled приватный атрибут для всех классов из MRO
        unmangled_name = None
        for base in mro:
            prefix = f"_{base.__name__}__"
            if name.startswith(prefix):
                unmangled_name = "__" + name[len(prefix) :]
                break

        # Определяем значение для сохранения
        if is_method:
            value = get_method_signature(attr)
        else:
            value = attr

        if unmangled_name:
            postfix = "()_" if is_method else ""
            setattr(result, f"{unmangled_name}{postfix}", value)
        elif name.startswith("_") and not name.startswith("__"):
            postfix = "()_" if is_method else ""
            setattr(result, f"{name}{postfix}", value)
        else:
            postfix = "()_" if is_method else ""
            setattr(result, f"{name}{postfix}", value)

    return result


# Глобальная функция для быстрого доступа в дебаггере
def debug_object(obj_name_or_obj):
    """
    Функция для вызова из PyCharm Debugger Console
    Использование: debug_object(your_variable)
    """
    if isinstance(obj_name_or_obj, str):
        # Если передано имя переменной как строка, пытаемся найти её в frame
        frame = sys._getframe(1)
        if obj_name_or_obj in frame.f_locals:
            obj = frame.f_locals[obj_name_or_obj]
        elif obj_name_or_obj in frame.f_globals:
            obj = frame.f_globals[obj_name_or_obj]
        else:
            return f"Variable '{obj_name_or_obj}' not found"
    else:
        obj = obj_name_or_obj

    return get_object_attributes(obj)


# Альтернативная функция с сокращенным именем
def dobj(obj):
    """Сокращенная версия для быстрого вызова: dobj(your_variable)"""
    return debug_object(obj)




if __name__ == "__main__":
    # Пример использования
    class Example:
        def __init__(self, value: int):
            self.public_field = value
            self._protected_field = "protected"
            self.__private_field = "private"

        def public_method(self, x: int, y: str = "default") -> str:
            return f"{x}: {y}"

        def _protected_method(self, data: list) -> bool:
            return len(data) > 0

        def __private_method(self) -> None:
            pass

        @property
        def computed_property(self) -> int:
            return self.public_field * 2

    # Тестируем
    obj = Example(42)
    debug_info = debug_object(obj)
    print(debug_info)
