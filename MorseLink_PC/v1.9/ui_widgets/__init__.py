"""Local, PySide6-only replacements for project UI components.

This module intentionally exposes the subset of APIs used by this project,
implemented with native Qt widgets for stability and simplicity.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QDoubleSpinBox,
    QLineEdit,
    QListWidget,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QProxyStyle,
    QSlider,
    QSpinBox,
    QStyle,
    QTableWidget,
    QTextEdit,
    QTimeEdit,
    QToolTip,
)


class _FluentIconValue(str):
    """Token type used to represent pseudo fluent icons."""


class _FluentIcon:
    """Dynamic icon token namespace, e.g. FluentIcon.PLAY."""

    def __getattr__(self, name: str) -> _FluentIconValue:
        return _FluentIconValue(name)


FluentIcon = _FluentIcon()


_ICON_MAP = {
    "PLAY": QStyle.StandardPixmap.SP_MediaPlay,
    "PAUSE": QStyle.StandardPixmap.SP_MediaPause,
    "SEARCH": QStyle.StandardPixmap.SP_FileDialogContentsView,
    "SYNC": QStyle.StandardPixmap.SP_BrowserReload,
    "SEND": QStyle.StandardPixmap.SP_ArrowForward,
    "SEND_FILL": QStyle.StandardPixmap.SP_ArrowForward,
    "CONNECT": QStyle.StandardPixmap.SP_DialogApplyButton,
    "BROOM": QStyle.StandardPixmap.SP_DialogResetButton,
}


def _to_qicon(icon: Any) -> QIcon:
    if isinstance(icon, QIcon):
        return icon
    if isinstance(icon, _FluentIconValue):
        app = QApplication.instance()
        if app is None:
            return QIcon()
        pix = _ICON_MAP.get(str(icon))
        if pix is None:
            return QIcon()
        return app.style().standardIcon(pix)
    return QIcon()


class PushButton(QPushButton):
    """Compatible replacement of fluent PushButton."""

    def __init__(self, *args: Any) -> None:
        icon = None
        text = ""
        parent = None

        if len(args) >= 2 and isinstance(args[0], (_FluentIconValue, QIcon)) and isinstance(args[1], str):
            icon = args[0]
            text = args[1]
            if len(args) >= 3:
                parent = args[2]
        elif len(args) >= 1 and isinstance(args[0], str):
            text = args[0]
            if len(args) >= 2:
                parent = args[1]
        elif len(args) >= 1:
            parent = args[0]

        super().__init__(text, parent)
        if icon is not None:
            self.setIcon(icon)

    def setIcon(self, icon: Any) -> None:  # type: ignore[override]
        super().setIcon(_to_qicon(icon))


class TransparentPushButton(PushButton):
    """Simple flat style button."""

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)
        self.setFlat(True)
        self.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                border: 1px solid rgba(0, 0, 0, 0.15);
                border-radius: 6px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background: rgba(0, 0, 0, 0.06);
            }
            """
        )


class Slider(QSlider):
    pass


class TextEdit(QTextEdit):
    pass


class ListWidget(QListWidget):
    pass


class ComboBox(QComboBox):
    pass


class LineEdit(QLineEdit):
    pass


class TableWidget(QTableWidget):
    pass


class ProgressBar(QProgressBar):
    pass


class ProgressRing(QProgressBar):
    """Fallback: linear progress bar with same value API."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0, 100)
        self.setTextVisible(True)


class RoundMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            """
            QMenu {
                border: 1px solid rgba(0, 0, 0, 0.15);
                border-radius: 8px;
                padding: 6px;
                background: white;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background: rgba(0, 0, 0, 0.08);
            }
            """
        )


class SpinBox(QSpinBox):
    pass


class CompactSpinBox(QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)


class DoubleSpinBox(QDoubleSpinBox):
    pass


class CompactDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)


class DateTimeEdit(QDateTimeEdit):
    pass


class CompactDateTimeEdit(QDateTimeEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)


class DateEdit(QDateEdit):
    pass


class CompactDateEdit(QDateEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)


class TimeEdit(QTimeEdit):
    pass


class CompactTimeEdit(QTimeEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)


class HollowHandleStyle(QProxyStyle):
    """Compatibility style object used by tests."""

    def __init__(self, _style: Any = None):
        super().__init__()


class Theme(Enum):
    LIGHT = "light"
    DARK = "dark"


def setTheme(_theme: Theme) -> None:
    """No-op theme hook for compatibility."""


class InfoBarPosition(Enum):
    TOP = "top"
    BOTTOM = "bottom"


class InfoBarIcon(Enum):
    INFORMATION = "information"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class InfoBar:
    """Lightweight info prompt compatible with project InfoBar API."""

    def __init__(
        self,
        *,
        icon: InfoBarIcon | None = None,
        title: str = "",
        content: str = "",
        orient: Qt.Orientation = Qt.Vertical,
        isClosable: bool = True,
        position: InfoBarPosition = InfoBarPosition.BOTTOM,
        duration: int = 2000,
        parent=None,
    ) -> None:
        self.icon = icon
        self.title = title
        self.content = content
        self.orient = orient
        self.isClosable = isClosable
        self.position = position
        self.duration = duration
        self.parent = parent

    def show(self) -> None:
        message = f"{self.title}: {self.content}" if self.title else self.content
        if self.parent is not None and hasattr(self.parent, "statusBar"):
            try:
                self.parent.statusBar().showMessage(message, self.duration)
                return
            except Exception:
                pass

        if self.parent is not None:
            rect = self.parent.rect()
            point = rect.topLeft() if self.position == InfoBarPosition.TOP else rect.bottomLeft()
            QToolTip.showText(self.parent.mapToGlobal(point), message, self.parent, rect, self.duration)
            return

        app = QApplication.instance()
        if app and app.activeWindow():
            win = app.activeWindow()
            QToolTip.showText(win.mapToGlobal(win.rect().bottomLeft()), message, win, win.rect(), self.duration)
            return

        QMessageBox.information(None, "Info", message)


__all__ = [
    "ComboBox",
    "CompactDateEdit",
    "CompactDateTimeEdit",
    "CompactDoubleSpinBox",
    "CompactSpinBox",
    "CompactTimeEdit",
    "DateEdit",
    "DateTimeEdit",
    "DoubleSpinBox",
    "FluentIcon",
    "HollowHandleStyle",
    "InfoBar",
    "InfoBarIcon",
    "InfoBarPosition",
    "LineEdit",
    "ListWidget",
    "ProgressBar",
    "ProgressRing",
    "PushButton",
    "RoundMenu",
    "Slider",
    "SpinBox",
    "TableWidget",
    "TextEdit",
    "Theme",
    "TimeEdit",
    "TransparentPushButton",
    "setTheme",
]
