from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QTableWidgetItem,
    QVBoxLayout,
    QHeaderView,
)
from ui_widgets import TableWidget

from utils.config_manager import ConfigManager


class MultiTableTool(QDialog):
    """Help table dialog for morse mapping and common abbreviations."""

    def __init__(self, switch):
        super().__init__()
        self.table_type = switch
        self.setWindowFlags(Qt.WindowCloseButtonHint)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.resize(760, 520)
        self.center()

        self.configer = ConfigManager()
        try:
            self.language = str(self.configer.get_language() or "zh").lower()
        except Exception:
            self.language = "zh"

        self.morse_code_dict = {
            ".-": "A", "-...": "B", "-.-.": "C", "-..": "D", ".": "E", "..-.": "F",
            "--.": "G", "....": "H", "..": "I", ".---": "J", "-.-": "K",
            ".-..": "L", "--": "M", "-.": "N", "---": "O", ".--.": "P",
            "--.-": "Q", ".-.": "R", "...": "S", "-": "T", "..-": "U",
            "...-": "V", ".--": "W", "-..-": "X", "-.--": "Y", "--..": "Z",
            "-----": "0", ".----": "1", "..---": "2", "...--": "3", "....-": "4",
            ".....": "5", "-....": "6", "--...": "7", "---..": "8", "----.": "9",
            ".-.-.-": ".", "--..--": ",", "..--..": "?", ".----.": "'", "-.-.--": "!",
            "-..-.": "/", "-.--.": "(", "-.--.-": ")", ".-...": "&", "---...": ":",
            "-.-.-.": ";", "-...-": "=", ".-..-.": '"', "...-..-": "$", ".--.-.": "@",
        }

        self.communication_words_zh = [
            ["早上好", "GM"], ["下午好", "GA"], ["晚上好", "GE"], ["晚安", "GN"],
            ["谢谢", "TU"], ["很高兴", "GLD"], ["幸运", "GL"], ["很好", "FB"],
            ["请稍等", "QRX"], ["先生", "MR"], ["女士", "YL"], ["太太", "MRS"],
            ["老朋友", "OM"], ["信号衰落", "QSB"], ["改变频率", "QSY"], ["国家", "CNTY"],
            ["你的", "UR"], ["我的", "MY"], ["祝好", "73"], ["小功率", "QRP"],
            ["这里", "HR"], ["呼叫", "CL"], ["对不起", "SRI"], ["增大功率", "QRO"],
            ["请慢发", "QRS"], ["电台", "STN"], ["天线", "ANT"], ["世界时", "UTC"],
            ["停机", "QRT"], ["收到", "QSL"], ["上午", "AM"], ["中午", "NN"],
            ["下午", "PM"], ["工作频率", "QSS"], ["短波", "SW"], ["呼号", "CS"],
            ["你是谁", "QRA"], ["等幅电报", "CW"], ["紧急呼救", "SOS"],
            ["电台忙", "QRL"], ["能否抄收", "QRJ"], ["再发一次", "AGN"],
            ["地理位置", "QTH"], ["谁在呼叫", "QRZ"], ["再见", "CUL"],
            ["直接通联", "QSO"], ["姓名", "NAME"], ["操作员", "OP"], ["老火腿", "OT"],
        ]

        self.communication_words_en = [
            ["Good Morning", "GM"], ["Good Afternoon", "GA"], ["Good Evening", "GE"],
            ["Good Night", "GN"], ["Thank You", "TU"], ["Very Good", "FB"],
            ["Please Wait", "QRX"], ["Mister", "MR"], ["Miss", "YL"], ["Mrs.", "MRS"],
            ["Old Friend", "OM"], ["Signal Fading", "QSB"], ["Change Frequency", "QSY"],
            ["Country", "CNTY"], ["Your", "UR"], ["My", "MY"], ["Best Wishes", "73"],
            ["Low Power", "QRP"], ["Here", "HR"], ["Call", "CL"], ["Sorry", "SRI"],
            ["Increase Power", "QRO"], ["Send Slower", "QRS"], ["Station", "STN"],
            ["Antenna", "ANT"], ["UTC", "UTC"], ["Station Shut Down", "QRT"],
            ["Received", "QSL"], ["Morning", "AM"], ["Noon", "NN"], ["Afternoon", "PM"],
            ["Working Frequency", "QSS"], ["Shortwave", "SW"], ["Call Sign", "CS"],
            ["Who Are You", "QRA"], ["Continuous Wave", "CW"], ["Emergency", "SOS"],
            ["Station Busy", "QRL"], ["Can You Copy?", "QRJ"], ["Again", "AGN"],
            ["Location", "QTH"], ["Who Is Calling?", "QRZ"], ["See You Later", "CUL"],
            ["Direct Contact", "QSO"], ["Name", "NAME"], ["Operator", "OP"],
            ["Old Timer", "OT"],
        ]

        self._init_ui()
        self._load_table()

    def _init_ui(self):
        self.setWindowTitle(self._window_title_for_type())

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(8)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self.tr("输入关键字过滤…"))
        self.search_edit.textChanged.connect(self._apply_filter)

        self.count_label = QLabel("")
        self.count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        top.addWidget(self.search_edit, 1)
        top.addWidget(self.count_label)

        self.table = TableWidget()
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(TableWidget.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self._copy_cell)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setStretchLastSection(True)

        root.addLayout(top)
        root.addWidget(self.table, 1)

    def _window_title_for_type(self):
        if self.table_type == "morse_code":
            return self.tr("摩尔斯电码参考表")
        if self.table_type == "communication_words":
            return self.tr("常用短语对照表")
        return self.tr("帮助")

    def _load_table(self):
        if self.table_type == "morse_code":
            data = [[code, letter] for code, letter in self.morse_code_dict.items()]
            headers = [self.tr("摩尔斯码"), self.tr("字符")]
        elif self.table_type == "communication_words":
            if self.language == "en":
                data = self.communication_words_en
                headers = [self.tr("英文"), self.tr("缩写")]
            else:
                data = self.communication_words_zh
                headers = [self.tr("中文"), self.tr("缩写")]
        else:
            data = []
            headers = [self.tr("键"), self.tr("值")]

        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(data))

        for row, values in enumerate(data):
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                self.table.setItem(row, col, item)

        self._update_count_label()

    def _apply_filter(self):
        keyword = self.search_edit.text().strip().lower()
        for row in range(self.table.rowCount()):
            row_text = []
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                row_text.append(item.text().lower() if item else "")
            joined = " ".join(row_text)
            self.table.setRowHidden(row, bool(keyword) and keyword not in joined)
        self._update_count_label()

    def _visible_row_count(self):
        return sum(1 for row in range(self.table.rowCount()) if not self.table.isRowHidden(row))

    def _update_count_label(self):
        visible = self._visible_row_count()
        total = self.table.rowCount()
        self.count_label.setText(self.tr("显示 {0}/{1}").format(visible, total))

    def _copy_cell(self, item):
        if not item:
            return
        QGuiApplication.clipboard().setText(item.text())

    def center(self):
        screen = QApplication.primaryScreen().availableGeometry()
        size = self.geometry()
        center_point_x = int((screen.width() - size.width()) / 2)
        center_point_y = int((screen.height() - size.height()) / 2)
        self.move(center_point_x, center_point_y)


