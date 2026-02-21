"""Application layer startup assembly."""

from morselink.core.context import AppContext
from morselink.presentation.main_window import MainWindow


def build_main_window(context: AppContext) -> MainWindow:
    return MainWindow(context)
