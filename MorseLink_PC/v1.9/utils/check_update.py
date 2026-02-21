import webbrowser
from datetime import datetime

import requests
from packaging.version import InvalidVersion, Version
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QMessageBox


def _tr(text: str) -> str:
    return QCoreApplication.translate("VersionChecker", text)


class VersionChecker:
    GITHUB_LATEST_RELEASE_API = "https://api.github.com/repos/TateLuo/MorseLink/releases/latest"
    REPO_URL = "https://github.com/TateLuo/MorseLink"
    REQUEST_HEADERS = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "MorseLink-UpdateChecker",
    }

    def __init__(self, current_version, release_api_url=None):
        self.current_version = self._safe_version(current_version)
        self.release_api_url = release_api_url or self.GITHUB_LATEST_RELEASE_API
        self.latest_version = None

    @staticmethod
    def _safe_version(raw_version):
        text = str(raw_version or "").strip()
        if text.lower().startswith("v"):
            text = text[1:]
        try:
            return Version(text)
        except InvalidVersion:
            return Version("0")

    @staticmethod
    def _format_published_time(raw):
        if not raw:
            return _tr("未知")
        try:
            # GitHub uses UTC ISO8601, e.g. 2025-08-18T03:30:00Z
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            return str(raw)

    @staticmethod
    def _format_release_notes(raw_notes, max_len=1500):
        notes = str(raw_notes or "").strip()
        if not notes:
            return _tr("（未提供更新日志）")
        if len(notes) > max_len:
            return notes[:max_len].rstrip() + _tr("\n\n...（更新日志过长，已截断）")
        return notes

    @staticmethod
    def _extract_download_url(release_data):
        assets = release_data.get("assets") or []
        exe_assets = [a for a in assets if str(a.get("name", "")).lower().endswith(".exe")]
        preferred = exe_assets[0] if exe_assets else (assets[0] if assets else None)
        if preferred:
            return preferred.get("browser_download_url")
        return release_data.get("html_url")

    def check_update(self):
        try:
            resp = requests.get(
                self.release_api_url,
                headers=self.REQUEST_HEADERS,
                timeout=8,
            )
            if resp.status_code != 200:
                return None

            data = resp.json()
            tag_name = data.get("tag_name") or data.get("name") or ""
            self.latest_version = self._safe_version(tag_name)
            if self.latest_version <= self.current_version:
                return None

            download_url = self._extract_download_url(data)
            detail_url = data.get("html_url") or self.REPO_URL
            release_time = self._format_published_time(data.get("published_at"))
            release_notes = self._format_release_notes(data.get("body"))

            action = self.ask_user_for_update(
                latest_version=self.latest_version,
                release_time=release_time,
                release_notes=release_notes,
            )

            if action == "download" and download_url:
                webbrowser.open(download_url)
                return "download"

            if action == "details" and detail_url:
                webbrowser.open(detail_url)
                return "details"

            return None
        except Exception:
            return None

    def ask_user_for_update(self, latest_version, release_time, release_notes):
        box = QMessageBox()
        box.setIcon(QMessageBox.Information)
        box.setWindowTitle(_tr("发现新版本"))
        box.setText(_tr("发现新版本：v{0}\n发布时间：{1}\n\n更新日志：\n{2}").format(latest_version, release_time, release_notes))

        btn_download = box.addButton(_tr("下载更新"), QMessageBox.AcceptRole)
        btn_details = box.addButton(_tr("查看详情"), QMessageBox.ActionRole)
        box.addButton(_tr("不更新"), QMessageBox.RejectRole)
        box.setDefaultButton(btn_download)
        box.exec()

        clicked = box.clickedButton()
        if clicked is btn_download:
            return "download"
        if clicked is btn_details:
            return "details"
        return "skip"
