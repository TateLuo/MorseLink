from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class TrainingTrendWidget(QWidget):
    """Lightweight trend chart for latest training snapshots."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._points: list[dict[str, float]] = []
        self.setMinimumHeight(150)

    def set_points(self, points: Iterable[dict[str, float]]) -> None:
        normalized: list[dict[str, float]] = []
        for row in points:
            normalized.append(
                {
                    "wpm": float(row.get("wpm", 0.0)),
                    "accuracy": float(row.get("accuracy", 0.0)),
                    "rhythm": float(row.get("rhythm", 0.0)),
                }
            )
        self._points = normalized[-7:]
        self.update()

    def _to_plot_points(self, key: str, rect, y_min: float, y_max: float) -> list[QPointF]:
        if not self._points:
            return []

        width = float(rect.width())
        height = float(rect.height())
        count = len(self._points)
        span = max(1, count - 1)
        points: list[QPointF] = []

        for idx, row in enumerate(self._points):
            x = float(rect.left()) + width * (idx / span)
            value = float(row.get(key, 0.0))
            if y_max <= y_min:
                y_ratio = 0.0
            else:
                y_ratio = (value - y_min) / (y_max - y_min)
            y_ratio = max(0.0, min(1.0, y_ratio))
            y = float(rect.bottom()) - height * y_ratio
            points.append(QPointF(x, y))

        return points

    @staticmethod
    def _draw_series(painter: QPainter, points: list[QPointF], color: QColor, width: int = 2) -> None:
        if not points:
            return
        pen = QPen(color)
        pen.setWidth(width)
        painter.setPen(pen)

        path = QPainterPath(points[0])
        for point in points[1:]:
            path.lineTo(point)
        painter.drawPath(path)

        point_pen = QPen(color)
        point_pen.setWidth(max(2, width))
        painter.setPen(point_pen)
        for point in points:
            painter.drawEllipse(point, 2.5, 2.5)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(12, 10, -10, -22)
        painter.fillRect(self.rect(), QColor(250, 251, 253))

        axis_pen = QPen(QColor(205, 210, 218))
        axis_pen.setWidth(1)
        painter.setPen(axis_pen)
        painter.drawRect(rect)

        if not self._points:
            painter.setPen(QColor(120, 120, 120))
            painter.drawText(rect, Qt.AlignCenter, self.tr("暂无训练数据"))
            return

        accuracy_points = self._to_plot_points("accuracy", rect, 0.0, 100.0)
        rhythm_points = self._to_plot_points("rhythm", rect, 0.0, 100.0)

        wpm_values = [row.get("wpm", 0.0) for row in self._points]
        wpm_min = min(min(wpm_values), 5.0)
        wpm_max = max(max(wpm_values), wpm_min + 1.0)
        wpm_points = self._to_plot_points("wpm", rect, wpm_min, wpm_max)

        self._draw_series(painter, wpm_points, QColor(24, 119, 242), 2)
        self._draw_series(painter, accuracy_points, QColor(26, 166, 95), 2)
        self._draw_series(painter, rhythm_points, QColor(245, 137, 34), 2)

        legend_y = self.rect().bottom() - 8
        painter.setPen(QColor(24, 119, 242))
        painter.drawText(14, legend_y, self.tr("WPM"))
        painter.setPen(QColor(26, 166, 95))
        painter.drawText(62, legend_y, self.tr("准确率"))
        painter.setPen(QColor(245, 137, 34))
        painter.drawText(132, legend_y, self.tr("节奏分"))
