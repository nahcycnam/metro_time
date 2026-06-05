import requests
import math
import sys
import os
import json
from PyQt6.QtCore import Qt, QSize, QEvent, QStringListModel
from PyQt6.QtGui import QFont, QIcon, QColor, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialog, QFrame, QSizePolicy, QWidget,
    QMainWindow, QHBoxLayout, QTextEdit, QMessageBox,
    QGridLayout, QCompleter
)
import concurrent.futures

# ==================== 资源路径处理 ====================
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ==================== 直接获取车站列表（不保存文件） ====================
_stations_cache = None          # 内存缓存，避免重复请求

def fetch_stations():
    """请求 API 获取所有车站名称列表，不保存到文件，直接返回列表"""
    global _stations_cache
    if _stations_cache is not None:
        return _stations_cache

    url = "https://apis.gzmtr.com/app-map/metroweb/linestation"
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(requests.post, url, timeout=(2, 2))
            response = future.result(timeout=2)
            lines = response.json()["businessObject"]

            stations = []
            for line in lines:
                for station in line['stations']:
                    station_name = station['stationName']
                    if station_name not in stations:
                        stations.append(station_name)
            print(f"成功获取 {len(stations)} 个车站")
            _stations_cache = stations
            return stations
    except (concurrent.futures.TimeoutError, requests.exceptions.Timeout):
        print("请求超时，无法获取车站列表，自动补全功能不可用")
    except Exception as e:
        print(f"获取车站列表失败: {e}")
    return []

# ==================== 加载站名转换映射（保留） ====================
def load_station_mapping():
    mapping_path = resource_path("station_mapping.json")
    if not os.path.exists(mapping_path):
        return {}
    try:
        with open(mapping_path, "r", encoding="utf-8") as f:
            mapping = json.load(f)
        return mapping if isinstance(mapping, dict) else {}
    except Exception:
        return {}

# ==================== 地铁应用主窗口 ====================
class MetroApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("广州地铁查询系统")
        self.setFixedSize(650, 550)
        self.set_app_icon()

        # 直接调用 fetch_stations 获取车站列表（内存中，不保存文件）
        self.all_stations = fetch_stations()
        self.station_mapping = load_station_mapping()

        self.setup_ui()
        self.setup_completer()
        self.setup_event_filters()

        self.start_input.setText("淘金")
        self.end_input.setText("聚龙")
        self.end_input.setFocus()

    def set_app_icon(self):
        icon_path = resource_path("metro_logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor("#3498db"))
            self.setWindowIcon(QIcon(pixmap))

    def setup_ui(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #f5f5f5; }
            QFrame#mainFrame {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
            QLabel { font-size: 14px; color: #333; }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #4a86e8;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton#swapButton {
                background-color: #5a96f8;
                border-radius: 50%;
                min-width: 42px;
                min-height: 42px;
            }
            QPushButton#swapButton:hover { background-color: #3a76d8; }
            QPushButton#swapButton:pressed { background-color: #2a66c8; }
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
            }
        """)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        title_label = QLabel("广州地铁线路查询")
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #1a5fb4;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        frame = QFrame()
        frame.setObjectName("mainFrame")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(20, 20, 20, 20)
        frame_layout.setSpacing(15)

        input_layout = QGridLayout()
        input_layout.setSpacing(15)
        input_layout.setColumnStretch(0, 1)
        input_layout.setColumnStretch(1, 9)
        input_layout.setColumnStretch(2, 2)
        input_layout.setColumnStretch(3, 1)
        input_layout.setColumnStretch(4, 9)

        start_label = QLabel("起点站:")
        self.start_input = QLineEdit()
        self.start_input.setPlaceholderText("例如: 淘金")
        self.start_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.swap_button = QPushButton()
        self.swap_button.setObjectName("swapButton")
        self.swap_button.setToolTip("交换起点和终点")
        self.swap_button.clicked.connect(self.swap_stations)

        swap_pixmap = QPixmap()
        if swap_pixmap.load("swap_icon.png"):
            self.swap_button.setIcon(QIcon(swap_pixmap))
            self.swap_button.setIconSize(QSize(28, 28))
        else:
            self.swap_button.setText("⇄")
            self.swap_button.setFont(QFont("Arial", 22, QFont.Weight.Bold))

        end_label = QLabel("终点站:")
        self.end_input = QLineEdit()
        self.end_input.setPlaceholderText("例如: 聚龙")
        self.end_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        input_layout.addWidget(start_label, 0, 0, 1, 1)
        input_layout.addWidget(self.start_input, 1, 0, 1, 2)
        input_layout.addWidget(self.swap_button, 1, 2, 1, 1, Qt.AlignmentFlag.AlignCenter)
        input_layout.addWidget(end_label, 0, 3, 1, 1)
        input_layout.addWidget(self.end_input, 1, 3, 1, 2)

        self.query_button = QPushButton("查询路线")
        self.query_button.setFixedHeight(40)
        self.query_button.clicked.connect(self.query_metro)
        input_layout.addWidget(self.query_button, 2, 0, 1, 5)

        frame_layout.addLayout(input_layout)

        result_label = QLabel("查询结果:")
        result_label.setFont(QFont("Arial", 12))
        frame_layout.addWidget(result_label)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(200)
        frame_layout.addWidget(self.result_text)

        main_layout.addWidget(frame)

        button_layout = QHBoxLayout()
        self.clear_button = QPushButton("清空")
        self.clear_button.clicked.connect(self.clear_fields)
        button_layout.addWidget(self.clear_button)
        self.exit_button = QPushButton("退出")
        self.exit_button.clicked.connect(self.close)
        button_layout.addWidget(self.exit_button)
        main_layout.addLayout(button_layout)

        self.start_input.returnPressed.connect(self.query_metro)
        self.end_input.returnPressed.connect(self.query_metro)

    def setup_completer(self):
        if not self.all_stations:
            print("自动补全功能未启用（无车站数据）")
            return

        model = QStringListModel()
        model.setStringList(self.all_stations)

        self.start_completer = QCompleter()
        self.start_completer.setModel(model)
        self.start_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.start_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.start_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.start_input.setCompleter(self.start_completer)

        self.end_completer = QCompleter()
        self.end_completer.setModel(model)
        self.end_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.end_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.end_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.end_input.setCompleter(self.end_completer)

        popup_style = """
            QListView {
                font-size: 14px;
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px;
            }
            QListView::item {
                padding: 6px;
            }
            QListView::item:selected {
                background-color: #4a86e8;
                color: white;
            }
        """
        self.start_completer.popup().setStyleSheet(popup_style)
        self.end_completer.popup().setStyleSheet(popup_style)

    def setup_event_filters(self):
        self.start_input.installEventFilter(self)
        self.end_input.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Right:
            if obj == self.start_input and hasattr(self, 'start_completer'):
                completer = self.start_completer
                line_edit = self.start_input
            elif obj == self.end_input and hasattr(self, 'end_completer'):
                completer = self.end_completer
                line_edit = self.end_input
            else:
                return super().eventFilter(obj, event)

            if completer and completer.popup().isVisible():
                idx = completer.popup().currentIndex()
                if idx.isValid():
                    text = idx.data()
                    line_edit.setText(text)
                    line_edit.setCursorPosition(len(text))
                    completer.popup().hide()
                    return True
        return super().eventFilter(obj, event)

    def convert_station_name(self, name):
        return self.station_mapping.get(name, name)

    def swap_stations(self):
        start = self.start_input.text()
        end = self.end_input.text()
        self.start_input.setText(end)
        self.end_input.setText(start)
        self.query_metro()

    def query_metro(self):
        start_raw = self.start_input.text().strip()
        end_raw = self.end_input.text().strip()

        if not start_raw or not end_raw:
            self.show_message("输入错误", "请输入起点和终点站名", QMessageBox.Icon.Warning)
            return

        start = self.convert_station_name(start_raw)
        end = self.convert_station_name(end_raw)

        if start == end:
            self.show_message("输入错误", "起点站和终点站不能相同", QMessageBox.Icon.Warning)
            return

        try:
            r = requests.post(f'https://apis.gzmtr.com/app-map/metroweb/route/{start}/{end}', timeout=10)
            data = r.json()

            stations = data['businessObject']['routes'][0]['metro'][0]['stations'][0]['station']
            route = ""
            for st in stations:
                if st['transfer_info']:
                    route += f"{st['station_name']}({st['transfer_info']}) → "
            route += stations[-1]['station_name']

            price = round(data['businessObject']['price'])
            num_stations = len(stations) - 1
            spend_time = math.ceil(int(data['businessObject']['routes'][0]['metro'][0]['spend_time']) / 60)

            result = f"路线: {route}\n\n票价: {price}元, 站点: {num_stations}个站, 耗时: {spend_time}分钟\n\n"

            if 'lastBus' in data['businessObject']:
                lb = data['businessObject']['lastBus']
                if lb['route'] != '——' or lb['lastTime'] != '——':
                    result += "------末班车信息------\n"
                    result += f"末班车时间: {lb['lastTime']}\n"
                    bus_stations = lb['stations']
                    bus_route = ""
                    for bs in bus_stations:
                        if bs['transferInfo'] != '到达终点':
                            bus_route += f"{bs['stationName']}({bs['transferInfo']}) → "
                    bus_route += bus_stations[-1]['stationName']
                    result += f"末班车推荐换乘路径: {bus_route}\n"

            self.result_text.setText(result)

        except Exception as e:
            self.show_message("查询错误", f"查询失败: {str(e)}\n请检查站名是否正确", QMessageBox.Icon.Critical)

    def show_message(self, title, msg, icon):
        mb = QMessageBox(self)
        mb.setWindowIcon(self.windowIcon())
        mb.setIcon(icon)
        mb.setWindowTitle(title)
        mb.setText(msg)
        mb.exec()

    def clear_fields(self):
        self.start_input.clear()
        self.end_input.clear()
        self.result_text.clear()

    def center(self):
        fg = self.frameGeometry()
        center = QApplication.primaryScreen().availableGeometry().center()
        fg.moveCenter(center)
        self.move(fg.topLeft())

    def show(self):
        super().show()
        self.center()
        self.end_input.setFocus()

# ==================== 程序入口 ====================
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 设置应用图标
    icon_path = resource_path("metro_logo.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    else:
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor("#3498db"))
        app.setWindowIcon(QIcon(pixmap))

    # 设置样式
    if app.platformName() in ("windows", "xcb"):
        app.setStyle("Fusion")
    elif app.platformName() == "cocoa":
        app.setStyle("macos")

    # 创建并显示主窗口
    window = MetroApp()
    window.show()
    sys.exit(app.exec())
