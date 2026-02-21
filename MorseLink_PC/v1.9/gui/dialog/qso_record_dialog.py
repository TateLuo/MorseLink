# -*- coding: utf-8 -*-
"""QSO record management dialog."""

from __future__ import annotations

import csv
import math
from datetime import datetime
from typing import Any, Dict, List, Sequence, Tuple

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHeaderView,
)

from utils.database_tool import DatabaseTool
from utils.translator import MorseCodeTranslator


class QsoRecordDialog(QDialog):
    """QSO records page with filtering, pagination, details and batch actions."""

    EXPORT_FIELDS = [
        "id",
        "time",
        "direction",
        "sender",
        "duration_sec",
        "message_text",
        "message_morse",
        "has_timeline",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("QSO 记录"))
        self.resize(1220, 760)

        self.db_tool = DatabaseTool()
        self.translator = MorseCodeTranslator()

        self.current_page = 1
        self.page_size = 50
        self.total_count = 0
        self.page_records: List[Dict[str, Any]] = []
        self.last_deleted_batch: List[Dict[str, Any]] = []

        self._setup_ui()
        self._bind_signals()
        self._reload_records(reset_page=True)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)

        self.label_top_hint = QLabel("")
        self.label_top_hint.setStyleSheet("color:#c56a00;")
        self.label_top_hint.setVisible(False)
        main_layout.addWidget(self.label_top_hint)

        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setChildrenCollapsible(False)

        left_panel = self._build_left_panel()
        right_panel = self._build_right_panel()
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter, 1)

    def _build_left_panel(self) -> QFrame:
        panel = QFrame(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        filter_layout = QGridLayout()
        filter_layout.setHorizontalSpacing(8)
        filter_layout.setVerticalSpacing(6)

        self.edit_keyword = QLineEdit(self)
        self.edit_keyword.setPlaceholderText(self.tr("关键词（呼号/译文/原码）"))

        self.combo_direction = QComboBox(self)
        self.combo_direction.addItem(self.tr("全部方向"), "")
        self.combo_direction.addItem(self.tr("发送"), "send")
        self.combo_direction.addItem(self.tr("接收"), "receive")

        self.date_from = QDateEdit(self)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))

        self.date_to = QDateEdit(self)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())

        self.check_use_date_range = QCheckBox(self.tr("启用时间范围"), self)
        self.check_use_date_range.setChecked(False)
        self.date_from.setEnabled(False)
        self.date_to.setEnabled(False)

        self.combo_page_size = QComboBox(self)
        self.combo_page_size.addItem("50", 50)
        self.combo_page_size.addItem("100", 100)
        self.combo_page_size.addItem("200", 200)

        self.btn_reset_filters = QPushButton(self.tr("重置"), self)
        self.btn_refresh = QPushButton(self.tr("刷新"), self)

        filter_layout.addWidget(QLabel(self.tr("关键词")), 0, 0)
        filter_layout.addWidget(self.edit_keyword, 0, 1, 1, 3)
        filter_layout.addWidget(QLabel(self.tr("方向")), 0, 4)
        filter_layout.addWidget(self.combo_direction, 0, 5)

        filter_layout.addWidget(self.check_use_date_range, 1, 0)
        filter_layout.addWidget(self.date_from, 1, 1)
        filter_layout.addWidget(QLabel(self.tr("结束日期")), 1, 2)
        filter_layout.addWidget(self.date_to, 1, 3)
        filter_layout.addWidget(QLabel(self.tr("每页条数")), 1, 4)
        filter_layout.addWidget(self.combo_page_size, 1, 5)

        filter_layout.addWidget(self.btn_reset_filters, 2, 4)
        filter_layout.addWidget(self.btn_refresh, 2, 5)
        layout.addLayout(filter_layout)

        self.table = QTableWidget(0, 6, self)
        self.table.setHorizontalHeaderLabels(
            [
                self.tr("时间"),
                self.tr("时长"),
                self.tr("方向"),
                self.tr("呼号"),
                self.tr("译文预览"),
                self.tr("原码长度"),
            ]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        layout.addWidget(self.table, 1)

        batch_layout = QHBoxLayout()
        self.btn_delete_selected = QPushButton(self.tr("删除选中"), self)
        self.btn_undo_delete = QPushButton(self.tr("撤销删除"), self)
        self.btn_export_csv = QPushButton(self.tr("导出 CSV"), self)
        self.btn_undo_delete.setEnabled(False)
        batch_layout.addWidget(self.btn_delete_selected)
        batch_layout.addWidget(self.btn_undo_delete)
        batch_layout.addWidget(self.btn_export_csv)
        batch_layout.addStretch(1)
        layout.addLayout(batch_layout)

        pagination_layout = QHBoxLayout()
        self.btn_prev_page = QPushButton(self.tr("上一页"), self)
        self.btn_next_page = QPushButton(self.tr("下一页"), self)
        self.label_pagination = QLabel("", self)
        pagination_layout.addWidget(self.btn_prev_page)
        pagination_layout.addWidget(self.btn_next_page)
        pagination_layout.addStretch(1)
        pagination_layout.addWidget(self.label_pagination)
        layout.addLayout(pagination_layout)

        return panel

    def _build_right_panel(self) -> QFrame:
        panel = QFrame(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        summary_grid = QGridLayout()
        self.value_time = QLabel("--", self)
        self.value_duration = QLabel("--", self)
        self.value_direction = QLabel("--", self)
        self.value_sender = QLabel("--", self)

        summary_grid.addWidget(QLabel(self.tr("时间")), 0, 0)
        summary_grid.addWidget(self.value_time, 0, 1)
        summary_grid.addWidget(QLabel(self.tr("时长")), 1, 0)
        summary_grid.addWidget(self.value_duration, 1, 1)
        summary_grid.addWidget(QLabel(self.tr("方向")), 2, 0)
        summary_grid.addWidget(self.value_direction, 2, 1)
        summary_grid.addWidget(QLabel(self.tr("呼号")), 3, 0)
        summary_grid.addWidget(self.value_sender, 3, 1)
        layout.addLayout(summary_grid)

        layout.addWidget(QLabel(self.tr("译文全文"), self))
        self.edit_text = QPlainTextEdit(self)
        self.edit_text.setReadOnly(True)
        layout.addWidget(self.edit_text, 1)

        layout.addWidget(QLabel(self.tr("原始电码全文"), self))
        self.edit_morse = QPlainTextEdit(self)
        self.edit_morse.setReadOnly(True)
        layout.addWidget(self.edit_morse, 1)

        button_layout = QHBoxLayout()
        self.btn_copy_text = QPushButton(self.tr("复制译文"), self)
        self.btn_copy_morse = QPushButton(self.tr("复制原码"), self)
        self.btn_view_timeline = QPushButton(self.tr("查看时序"), self)
        button_layout.addWidget(self.btn_copy_text)
        button_layout.addWidget(self.btn_copy_morse)
        button_layout.addWidget(self.btn_view_timeline)
        layout.addLayout(button_layout)

        self.label_detail_hint = QLabel("", self)
        self.label_detail_hint.setStyleSheet("color:#888;")
        layout.addWidget(self.label_detail_hint)

        self._clear_detail()
        return panel

    def _bind_signals(self) -> None:
        self.edit_keyword.returnPressed.connect(lambda: self._reload_records(reset_page=True))
        self.combo_direction.currentIndexChanged.connect(lambda: self._reload_records(reset_page=True))
        self.combo_page_size.currentIndexChanged.connect(self._on_page_size_changed)
        self.check_use_date_range.toggled.connect(self._on_date_range_toggled)
        self.date_from.dateChanged.connect(lambda _d: self._reload_records(reset_page=True))
        self.date_to.dateChanged.connect(lambda _d: self._reload_records(reset_page=True))
        self.btn_refresh.clicked.connect(lambda: self._reload_records(reset_page=False))
        self.btn_reset_filters.clicked.connect(self._reset_filters)
        self.table.itemSelectionChanged.connect(self._refresh_detail_from_selection)
        self.btn_prev_page.clicked.connect(self._go_prev_page)
        self.btn_next_page.clicked.connect(self._go_next_page)
        self.btn_delete_selected.clicked.connect(self._delete_selected_rows)
        self.btn_undo_delete.clicked.connect(self._undo_last_delete)
        self.btn_export_csv.clicked.connect(self._export_csv)
        self.btn_copy_text.clicked.connect(lambda: self._copy_to_clipboard(self.edit_text.toPlainText()))
        self.btn_copy_morse.clicked.connect(lambda: self._copy_to_clipboard(self.edit_morse.toPlainText()))
        self.btn_view_timeline.clicked.connect(self._show_selected_timeline)

    def _reset_filters(self) -> None:
        self.edit_keyword.clear()
        self.combo_direction.setCurrentIndex(0)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_to.setDate(QDate.currentDate())
        self.check_use_date_range.setChecked(False)
        self.combo_page_size.setCurrentIndex(0)
        self.current_page = 1
        self._reload_records(reset_page=True)

    def _on_date_range_toggled(self, enabled: bool) -> None:
        self.date_from.setEnabled(enabled)
        self.date_to.setEnabled(enabled)
        self._reload_records(reset_page=True)

    def _on_page_size_changed(self) -> None:
        value = self.combo_page_size.currentData()
        self.page_size = int(value) if value else 50
        self.current_page = 1
        self._reload_records(reset_page=True)

    def _current_filters(self) -> Dict[str, Any]:
        if self.check_use_date_range.isChecked():
            date_from = self.date_from.date().toString("yyyy-MM-dd")
            date_to = self.date_to.date().toString("yyyy-MM-dd")
        else:
            date_from = None
            date_to = None

        return {
            "keyword": self.edit_keyword.text().strip(),
            "direction": str(self.combo_direction.currentData() or "").strip(),
            "date_from": date_from,
            "date_to": date_to,
        }

    def _direction_to_label(self, direction: str) -> str:
        mapping = {"Send": self.tr("发送"), "Receive": self.tr("接收")}
        return mapping.get(direction, direction or "--")

    @staticmethod
    def _format_duration(duration_sec: Any) -> str:
        try:
            value = float(duration_sec)
        except (TypeError, ValueError):
            return "--"
        if value <= 0:
            return "--"
        minutes = int(value // 60)
        seconds = value - (minutes * 60)
        return f"{minutes:02d}:{seconds:04.1f}"

    def _safe_translate(self, morse: str) -> str:
        if not morse:
            return ""
        try:
            return self.translator.morse_to_text(morse)
        except Exception:
            return ""

    def _reload_records(self, reset_page: bool) -> None:
        if reset_page:
            self.current_page = 1

        filters = self._current_filters()
        records, total_count, ignored_count = self.db_tool.query_qso_records(
            keyword=filters["keyword"],
            direction=filters["direction"],
            date_from=filters["date_from"],
            date_to=filters["date_to"],
            page=self.current_page,
            page_size=self.page_size,
            sort_desc=True,
        )

        max_page = max(1, math.ceil(total_count / self.page_size)) if total_count else 1
        if self.current_page > max_page:
            self.current_page = max_page
            records, total_count, ignored_count = self.db_tool.query_qso_records(
                keyword=filters["keyword"],
                direction=filters["direction"],
                date_from=filters["date_from"],
                date_to=filters["date_to"],
                page=self.current_page,
                page_size=self.page_size,
                sort_desc=True,
            )

        self.total_count = total_count
        self.page_records = records
        self._populate_table(records)
        self._update_pagination()
        self._update_ignored_hint(ignored_count)

    def _populate_table(self, records: Sequence[Dict[str, Any]]) -> None:
        self.table.clearContents()
        self.table.setRowCount(len(records))

        for row_index, record in enumerate(records):
            time_text = record.get("created_at") or "--"
            duration_text = self._format_duration(record.get("duration_sec"))
            direction_text = self._direction_to_label(str(record.get("direction") or ""))
            sender = str(record.get("sender") or "").strip() or "--"

            message_text = str(record.get("message_text") or "").strip()
            if not message_text:
                message_text = self._safe_translate(str(record.get("message_morse") or ""))
            preview = message_text.replace("\n", " ").strip()
            if len(preview) > 120:
                preview = preview[:117] + "..."

            morse_value = str(record.get("message_morse") or "")
            morse_len = str(len(morse_value))

            values = [time_text, duration_text, direction_text, sender, preview, morse_len]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col in (1, 2, 5):
                    item.setTextAlignment(Qt.AlignCenter)
                if col == 0:
                    item.setData(Qt.UserRole, int(record.get("id") or 0))
                self.table.setItem(row_index, col, item)

        if records:
            self.table.selectRow(0)
        else:
            self._clear_detail()

    def _update_pagination(self) -> None:
        total_pages = max(1, math.ceil(self.total_count / self.page_size)) if self.total_count else 1
        self.label_pagination.setText(
            self.tr("第 {0}/{1} 页，共 {2} 条").format(self.current_page, total_pages, self.total_count)
        )
        self.btn_prev_page.setEnabled(self.current_page > 1)
        self.btn_next_page.setEnabled(self.current_page < total_pages)

    def _update_ignored_hint(self, ignored_count: int) -> None:
        if ignored_count > 0:
            self.label_top_hint.setText(self.tr("有 {0} 条损坏记录已忽略。").format(ignored_count))
            self.label_top_hint.setVisible(True)
        else:
            self.label_top_hint.clear()
            self.label_top_hint.setVisible(False)

    def _go_prev_page(self) -> None:
        if self.current_page <= 1:
            return
        self.current_page -= 1
        self._reload_records(reset_page=False)

    def _go_next_page(self) -> None:
        total_pages = max(1, math.ceil(self.total_count / self.page_size)) if self.total_count else 1
        if self.current_page >= total_pages:
            return
        self.current_page += 1
        self._reload_records(reset_page=False)

    def _selected_row_indexes(self) -> List[int]:
        indexes = self.table.selectionModel().selectedRows()
        unique_rows = sorted({index.row() for index in indexes})
        return [row for row in unique_rows if 0 <= row < len(self.page_records)]

    def _selected_records(self) -> List[Dict[str, Any]]:
        return [self.page_records[row] for row in self._selected_row_indexes()]

    def _current_detail_record(self) -> Dict[str, Any] | None:
        records = self._selected_records()
        if not records:
            return None
        return records[0]

    def _clear_detail(self) -> None:
        self.value_time.setText("--")
        self.value_duration.setText("--")
        self.value_direction.setText("--")
        self.value_sender.setText("--")
        self.edit_text.clear()
        self.edit_morse.clear()
        self.label_detail_hint.setText(self.tr("请选择一条记录查看详情"))
        self.btn_copy_text.setEnabled(False)
        self.btn_copy_morse.setEnabled(False)
        self.btn_view_timeline.setEnabled(False)
        self.btn_view_timeline.setToolTip(self.tr("该记录无时序数据"))

    def _refresh_detail_from_selection(self) -> None:
        record = self._current_detail_record()
        if record is None:
            self._clear_detail()
            return

        time_text = str(record.get("created_at") or "--")
        duration_text = self._format_duration(record.get("duration_sec"))
        direction_text = self._direction_to_label(str(record.get("direction") or ""))
        sender = str(record.get("sender") or "").strip() or "--"
        message_morse = str(record.get("message_morse") or "")
        message_text = str(record.get("message_text") or "").strip()
        if not message_text:
            message_text = self._safe_translate(message_morse)

        self.value_time.setText(time_text)
        self.value_duration.setText(duration_text)
        self.value_direction.setText(direction_text)
        self.value_sender.setText(sender)
        self.edit_text.setPlainText(message_text)
        self.edit_morse.setPlainText(message_morse)

        timeline_ok, _lengths, _gaps = self._timeline_from_record(record)
        if timeline_ok:
            self.label_detail_hint.setText(self.tr("可查看时序回放"))
            self.btn_view_timeline.setEnabled(True)
            self.btn_view_timeline.setToolTip("")
        else:
            self.label_detail_hint.setText(self.tr("该记录无时序数据"))
            self.btn_view_timeline.setEnabled(False)
            self.btn_view_timeline.setToolTip(self.tr("该记录无时序数据"))

        self.btn_copy_text.setEnabled(bool(message_text))
        self.btn_copy_morse.setEnabled(bool(message_morse))

    @staticmethod
    def _parse_timeline_value(value: Any) -> List[float]:
        if isinstance(value, (list, tuple)):
            raw_tokens = value
        else:
            text = str(value or "").strip()
            if not text:
                return []
            raw_tokens = text.split(",")

        result: List[float] = []
        for token in raw_tokens:
            try:
                number = float(token)
            except (TypeError, ValueError):
                continue
            if number >= 0:
                result.append(number)
        return result

    def _timeline_from_record(self, record: Dict[str, Any]) -> Tuple[bool, List[float], List[float]]:
        data = record.get("data") if isinstance(record.get("data"), dict) else {}
        lengths = self._parse_timeline_value(data.get("play_time"))
        gaps = self._parse_timeline_value(data.get("play_time_interval"))

        if not lengths:
            return False, [], []
        if not gaps:
            gaps = [0.0] + [80.0] * max(0, len(lengths) - 1)
        if len(gaps) < len(lengths):
            gaps.extend([80.0] * (len(lengths) - len(gaps)))

        return True, lengths, gaps

    def _show_selected_timeline(self) -> None:
        record = self._current_detail_record()
        if not record:
            return

        timeline_ok, lengths, gaps = self._timeline_from_record(record)
        if not timeline_ok:
            QMessageBox.information(self, self.tr("提示"), self.tr("该记录无时序数据"))
            return

        dialog = WaterfallGraph(lengths, gaps, self)
        dialog.exec()

    def _delete_selected_rows(self) -> None:
        selected_records = self._selected_records()
        if not selected_records:
            QMessageBox.information(self, self.tr("提示"), self.tr("请先选择要删除的记录"))
            return

        count = len(selected_records)
        reply = QMessageBox.question(
            self,
            self.tr("确认删除"),
            self.tr("确认删除选中的 {0} 条记录吗？").format(count),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        ids = [int(record.get("id") or 0) for record in selected_records]
        deleted_records = self.db_tool.delete_qso_records_by_ids(ids)
        if not deleted_records:
            QMessageBox.warning(self, self.tr("删除失败"), self.tr("未找到可删除的记录"))
            return

        self.last_deleted_batch = deleted_records
        self.btn_undo_delete.setEnabled(True)
        self._reload_records(reset_page=False)

    def _undo_last_delete(self) -> None:
        if not self.last_deleted_batch:
            return

        restored = self.db_tool.insert_qso_records(self.last_deleted_batch)
        if restored <= 0:
            QMessageBox.warning(self, self.tr("恢复失败"), self.tr("未恢复任何记录"))
            return

        self.last_deleted_batch = []
        self.btn_undo_delete.setEnabled(False)
        self._reload_records(reset_page=False)

    def _copy_to_clipboard(self, text: str) -> None:
        if not text:
            return
        QGuiApplication.clipboard().setText(text)

    def _collect_all_filtered_records(self) -> List[Dict[str, Any]]:
        filters = self._current_filters()
        all_records: List[Dict[str, Any]] = []
        export_page_size = 500
        page = 1

        while True:
            page_records, total_count, _ignored = self.db_tool.query_qso_records(
                keyword=filters["keyword"],
                direction=filters["direction"],
                date_from=filters["date_from"],
                date_to=filters["date_to"],
                page=page,
                page_size=export_page_size,
                sort_desc=True,
            )
            all_records.extend(page_records)
            if len(all_records) >= total_count or not page_records:
                break
            page += 1

        return all_records

    def _export_csv(self) -> None:
        selected_records = self._selected_records()
        export_records = selected_records if selected_records else self._collect_all_filtered_records()
        if not export_records:
            QMessageBox.information(self, self.tr("提示"), self.tr("当前没有可导出的记录"))
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"qso_records_{timestamp}.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("导出 CSV"),
            default_name,
            self.tr("CSV 文件 (*.csv)"),
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".csv"):
            file_path += ".csv"

        try:
            with open(file_path, "w", encoding="utf-8-sig", newline="") as fp:
                writer = csv.DictWriter(fp, fieldnames=self.EXPORT_FIELDS)
                writer.writeheader()
                for record in export_records:
                    message_text = str(record.get("message_text") or "").strip()
                    if not message_text:
                        message_text = self._safe_translate(str(record.get("message_morse") or ""))

                    writer.writerow(
                        {
                            "id": int(record.get("id") or 0),
                            "time": str(record.get("created_at") or ""),
                            "direction": str(record.get("direction") or ""),
                            "sender": str(record.get("sender") or ""),
                            "duration_sec": float(record.get("duration_sec") or 0.0),
                            "message_text": message_text,
                            "message_morse": str(record.get("message_morse") or ""),
                            "has_timeline": int(record.get("has_timeline") or 0),
                        }
                    )
        except Exception as exc:
            QMessageBox.critical(
                self,
                self.tr("导出失败"),
                self.tr("写入文件失败：{0}").format(str(exc)),
            )
            return

        if selected_records:
            msg = self.tr("已导出选中的 {0} 条记录。").format(len(export_records))
        else:
            msg = self.tr("已导出当前筛选结果，共 {0} 条记录。").format(len(export_records))
        QMessageBox.information(self, self.tr("导出完成"), msg)


class WaterfallGraph(QDialog):
    """Timeline visualizer for one QSO record."""

    def __init__(self, lengths: Sequence[float], gaps: Sequence[float], parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("时序可视化"))
        self.resize(820, 320)

        main_layout = QVBoxLayout(self)
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene, self)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        main_layout.addWidget(self.view)

        self._draw_waveform(list(lengths), list(gaps))

    def _draw_waveform(self, lengths: List[float], gaps: List[float]) -> None:
        if not lengths:
            self.scene.addText(self.tr("该记录无可用时序数据"))
            return

        # Prevent huge durations from creating an unusable scene.
        tone_scale = 0.12
        gap_scale = 0.08
        x = 10.0
        y = 24.0
        h = 28.0

        if len(gaps) < len(lengths):
            gaps = gaps + [80.0] * (len(lengths) - len(gaps))

        for idx, length in enumerate(lengths):
            if idx > 0:
                gap = max(0.0, float(gaps[idx]))
                x += max(2.0, min(gap * gap_scale, 220.0))

            width = max(1.0, min(float(length) * tone_scale, 420.0))
            item = QGraphicsRectItem(x, y, width, h)
            item.setBrush(Qt.black)
            item.setPen(Qt.NoPen)
            self.scene.addItem(item)
            x += width

        self.scene.setSceneRect(0, 0, x + 20.0, 90.0)
