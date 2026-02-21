"""Shared application context and dependency factories."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Callable

from utils.config_manager import ConfigManager
from utils.database_tool import DatabaseTool
from utils.sound import BuzzerSimulator
from .metadata import APP_NAME, APP_VERSION


DatabaseFactory = Callable[[], DatabaseTool]
BuzzerFactory = Callable[[], BuzzerSimulator]


@dataclass
class AppContext:
    """Holds cross-module dependencies for non-breaking DI."""

    app_name: str = APP_NAME
    app_version: str = APP_VERSION
    config_manager: ConfigManager = field(default_factory=ConfigManager)
    database_factory: DatabaseFactory = field(default=DatabaseTool)
    buzzer_factory: BuzzerFactory = field(default=BuzzerSimulator)
    _shared_buzzer: BuzzerSimulator | None = field(default=None, init=False, repr=False)
    _buzzer_lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def create_database_tool(self) -> DatabaseTool:
        return self.database_factory()

    def create_buzzer(self) -> BuzzerSimulator:
        with self._buzzer_lock:
            if self._shared_buzzer is None:
                self._shared_buzzer = self.buzzer_factory()
            return self._shared_buzzer

    def recreate_buzzer(self) -> BuzzerSimulator:
        old = None
        with self._buzzer_lock:
            old = self._shared_buzzer
            self._shared_buzzer = self.buzzer_factory()
            new = self._shared_buzzer
        if old and old is not new and hasattr(old, "close"):
            try:
                old.close()
            except Exception:
                pass
        return new

    def close_buzzer(self) -> None:
        with self._buzzer_lock:
            buzzer = self._shared_buzzer
            self._shared_buzzer = None
        if buzzer and hasattr(buzzer, "close"):
            try:
                buzzer.close()
            except Exception:
                pass
