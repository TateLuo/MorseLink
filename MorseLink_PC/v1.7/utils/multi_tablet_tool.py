from PyQt5.QtWidgets import  QTableWidgetItem, QVBoxLayout, QDialog, QDesktopWidget, QSizePolicy
from PyQt5.QtCore import Qt
from qfluentwidgets import TableWidget
from utils.config_manager import ConfigManager

class MultiTableTool(QDialog):
    def __init__(self,switch):
        super().__init__()
        switch =switch
        self.setWindowFlags(Qt.WindowCloseButtonHint)
        #self.resize(400,500)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setWindowTitle("HELP")  
        self.center()
        self.configer = ConfigManager()
        try:
            self.language = self.configer.get_language()
        except:
            self.language = "en"


        self.morse_code_dict = {
            '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E', '..-.': 'F',
            '--.': 'G', '....': 'H', '..': 'I', '.---': 'J', '-.-': 'K',
            '.-..': 'L', '--': 'M', '-.': 'N', '---': 'O', '.--.': 'P',
            '--.-': 'Q', '.-.': 'R', '...': 'S', '-': 'T', '..-': 'U',
            '...-': 'V', '.--': 'W', '-..-': 'X', '-.--': 'Y', '--..': 'Z',
            '-----': '0', '.----': '1', '..---': '2', '...--': '3', '....-': '4',
            '.....': '5', '-....': '6', '--...': '7', '---..': '8', '----.': '9',
            '.-.-.-': '.', '--..--': ',', '..--..': '?', '.----.': "'", '-.-.--': '!',
            '-..-.': '/', '-.--.': '(', '-.--.-': ')', '.-...': '&', '---...': ':',
            '-.-.-.': ';', '-...-': '=', '.-..-.': '"', '...-..-': '$', '.--.-.': '@'
        }

        self.communication_words_zh = [
            ["早上好", "GM"], ["下午好", "GA"], ["晚上好", "GE"],
            ["最好的", "BEST"], ["晚安", "GN"], ["幸运", "GL"],
            ["高兴", "GLD"], ["等待守听", "QRX"], ["很好", "FB"],
            ["谢谢你", "TU"], ["先生", "MR"], ["天电干扰", "QRN"],
            ["女士", "YL"], ["太太", "MRS"], ["老朋友", "OM"],
            ["信号衰落", "QSB"], ["改变频率", "QSY"], ["国家", "CNTY"],
            ["你的", "UR"], ["我的", "MY"], ["美好祝福", "73"],
            ["小功率", "QRP"], ["这里", "HR"], ["呼叫", "CL"],
            ["对不起", "SRI"], ["增加功率", "QRO"], ["请发慢些", "QRS"],
            ["电台", "STN"], ["天线", "ANT"], ["世界调节时间", "UTC"],
            ["电台关机", "QRT"], ["收到", "QSL"], ["上午", "AM"],
            ["中午", "NN"], ["下午", "PM"], ["工作频率", "QSS"],
            ["晚上", "NITE"], ["短波", "SW"], ["呼号", "CS"],
            ["何电台、人名", "QRA"], ["等幅电报", "CW"], ["紧急呼救", "SOS"],
            ["电台工作中", "QRL"], ["能否收到", "QRJ"], ["再次", "AGN"],
            ["地理位置", "QTH"], ["谁在呼叫", "QRZ"], ["再见", "CUL"],
            ["国家", "CNTY"], ["直接联络", "QS0"], ["姓名", "NAME"],
            ["报务员、操作员", "OP"], ["老手", "OT"], ["55 节快乐!", "HAPPY 55 DAY!"],
            ["世界调节时间", "UTC"]
        ]

        self.communication_words_en = [
            ["Good Morning", "GM"], ["Good Afternoon", "GA"], ["Good Evening", "GE"],
            ["Best", "BEST"], ["Good Night", "GN"], ["Lucky", "GL"],
            ["Happy", "GLD"], ["Waiting to Listen", "QRX"], ["Very Good", "FB"],
            ["Thank You", "TU"], ["Mister", "MR"], ["Atmospheric Interference", "QRN"],
            ["Miss", "YL"], ["Mrs.", "MRS"], ["Old Friend", "OM"],
            ["Signal Fading", "QSB"], ["Change Frequency", "QSY"], ["Country", "CNTY"],
            ["Your", "UR"], ["My", "MY"], ["Best Wishes", "73"],
            ["Low Power", "QRP"], ["Here", "HR"], ["Call", "CL"],
            ["Sorry", "SRI"], ["Increase Power", "QRO"], ["Please Send Slower", "QRS"],
            ["Station", "STN"], ["Antenna", "ANT"], ["Coordinated Universal Time", "UTC"],
            ["Station Shutdown", "QRT"], ["Received", "QSL"], ["Morning", "AM"],
            ["Noon", "NN"], ["Afternoon", "PM"], ["Working Frequency", "QSS"],
            ["Evening", "NITE"], ["Shortwave", "SW"], ["Call Sign", "CS"],
            ["Which Station/Name", "QRA"], ["Continuous Wave", "CW"], ["Emergency Call", "SOS"],
            ["Station in Operation", "QRL"], ["Can You Hear Me?", "QRJ"], ["Again", "AGN"],
            ["Geographical Location", "QTH"], ["Who is Calling?", "QRZ"], ["Goodbye", "CUL"],
            ["Country", "CNTY"], ["Direct Contact", "QS0"], ["Name", "NAME"],
            ["Operator", "OP"], ["Old Timer", "OT"], ["Happy 55 Day!", "HAPPY 55 DAY!"],
            ["Coordinated Universal Time", "UTC"]
        ]

        self.show_table(switch)


    def show_table(self, table_type):

        layout = QVBoxLayout()

        # 表格
        self.table = TableWidget()
        layout.addWidget(self.table)

        self.setLayout(layout)

        # 更新表格逻辑
        if table_type == "morse_code":
            self.table.setRowCount(len(self.morse_code_dict))
            self.table.setColumnCount(2)
            self.table.setHorizontalHeaderLabels(["MorseCode", "Letter"])
            for i, (code, letter) in enumerate(self.morse_code_dict.items()):
                self.table.setItem(i, 0, QTableWidgetItem(code))
                self.table.setItem(i, 1, QTableWidgetItem(letter))
        elif table_type == "communication_words":
            if self.language == "en":
                self.table.setRowCount(len(self.communication_words_en))
                self.table.setColumnCount(2)
                self.table.setHorizontalHeaderLabels(["EN", "Abbreviation"])
                for i, (word, abbreviation) in enumerate(self.communication_words_en):
                    self.table.setItem(i, 0, QTableWidgetItem(word))
                    self.table.setItem(i, 1, QTableWidgetItem(abbreviation))
            else:
                self.table.setRowCount(len(self.communication_words_zh))
                self.table.setColumnCount(2)
                self.table.setHorizontalHeaderLabels(["中文", "缩写"])
                for i, (word, abbreviation) in enumerate(self.communication_words_zh):
                    self.table.setItem(i, 0, QTableWidgetItem(word))
                    self.table.setItem(i, 1, QTableWidgetItem(abbreviation))

    
    def center(self):
        # 获取屏幕的尺寸信息
        screen = QDesktopWidget().screenGeometry()

        # 获取窗口的尺寸信息
        size = self.geometry()

        # 将窗口移动到指定位置
        self.center_point_x = int((screen.width() - size.width()) / 2)
        self.center_point_y = int((screen.height() - size.height()) / 2)
        self.move(self.center_point_x, self.center_point_y)

