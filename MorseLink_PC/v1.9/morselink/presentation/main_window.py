"""Presentation layer entry point for the desktop main window."""

from gui.main_ui import MainUI
from morselink.core.context import AppContext


class MainWindow(MainUI):
    def __init__(self, context: AppContext):
        super().__init__(context=context)
