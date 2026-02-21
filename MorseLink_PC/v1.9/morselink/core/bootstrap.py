"""Process bootstrap for desktop app startup."""

from __future__ import annotations

import base64
import sys
from pathlib import Path
from typing import Sequence

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from morselink.application.startup import build_main_window
from morselink.core.context import AppContext
from morselink.core.i18n import build_translator
from utils.qq import img


def _set_high_dpi() -> None:
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)


def _set_app_version(context: AppContext) -> None:
    context.config_manager.set_current_version(context.app_version)


def _set_app_icon(app: QApplication) -> None:
    icon_path = Path("tmp.ico")
    icon_path.write_bytes(base64.b64decode(img))
    try:
        app.setWindowIcon(QIcon(str(icon_path)))
    finally:
        if icon_path.exists():
            icon_path.unlink()


def _install_language(app: QApplication, context: AppContext):
    translator = build_translator(context.config_manager.get_language())
    if translator is None:
        return None
    app.installTranslator(translator)
    return translator


def run(argv: Sequence[str] | None = None) -> int:
    context = AppContext()
    _set_high_dpi()
    _set_app_version(context)

    app = QApplication(list(argv) if argv is not None else sys.argv)
    app._ml_translator = _install_language(app, context)  # keep a strong reference
    _set_app_icon(app)

    window = build_main_window(context)
    window.show()
    try:
        return app.exec()
    finally:
        context.close_buzzer()
