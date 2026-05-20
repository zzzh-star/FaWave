import os
from datetime import datetime
import time
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QCheckBox,
                               QGroupBox, QGridLayout, QFormLayout, QFileDialog, QStatusBar, QMessageBox,
                               QSpacerItem, QSizePolicy, QSplitter, QScrollArea, QFrame, QListView, QButtonGroup)
from PySide6.QtCore import Qt, QTimer, QSize, Signal
from PySide6.QtGui import QFontMetrics, QIcon
from PySide6.QtSvgWidgets import QSvgWidget
import pyqtgraph as pg

from ..workers.acquisition_worker import AcquisitionWorker
from ..data.data_buffer import DataBuffer
from ..data.data_recorder import DataRecorder

class SegmentedControl(QWidget):
    currentChanged = Signal(str)

    def __init__(self, options, current=None):
        super().__init__()
        self.setObjectName("segmentedControl")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.group.buttonClicked.connect(self._on_button_clicked)

        self._buttons = {}
        for idx, option in enumerate(options):
            btn = QPushButton(option)
            btn.setCheckable(True)
            btn.setProperty("class", "segmentButton")
            self.group.addButton(btn, idx)
            layout.addWidget(btn)
            self._buttons[option] = btn

            if current and option == current:
                btn.setChecked(True)

        if not current and options:
            self._buttons[options[0]].setChecked(True)

    def currentText(self):
        btn = self.group.checkedButton()
        if btn:
            return btn.text()
        return ""

    def setCurrentText(self, text):
        if text in self._buttons:
            self._buttons[text].setChecked(True)

    def _on_button_clicked(self, button):
        self.currentChanged.emit(button.text())


class ValueCard(QWidget):
    def __init__(self, title, unit, color, compact=False):
        super().__init__()
        self.compact = compact
        self.setObjectName("valCard")
        layout = QVBoxLayout(self)
        margins = 6 if compact else 12
        layout.setContentsMargins(margins, margins, margins, margins)
        layout.setSpacing(2 if compact else 6)

        # Color indicator + Title
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)

        color_indicator = QLabel()
        ind_size = 8 if compact else 10
        color_indicator.setFixedSize(ind_size, ind_size)
        color_indicator.setStyleSheet(f"background-color: {color}; border-radius: {ind_size//2}px;")

        title_label = QLabel(title)
        title_label.setProperty("class", "channel-title-compact" if compact else "channel-title")

        title_layout.addWidget(color_indicator)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Value + Unit
        val_layout = QHBoxLayout()
        val_layout.setContentsMargins(0, 0, 0, 0)
        val_layout.setSpacing(4)

        self.val_label = QLabel("0.0000")
        self.val_label.setProperty("class", "channel-value-compact" if compact else "channel-value")
        self.val_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        unit_label = QLabel(unit)
        unit_label.setProperty("class", "channel-unit-compact" if compact else "channel-unit")
        unit_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)

        val_layout.addWidget(self.val_label)
        val_layout.addWidget(unit_label)
        val_layout.addStretch()
        layout.addLayout(val_layout)

    def set_value(self, val):
        self.val_label.setText(f"{val:.4f}")

class AlarmCard(QWidget):
    def __init__(self, title):
        super().__init__()
        self.setObjectName("alarmCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "alarm-title")

        self.status_label = QLabel("状态：未配置")
        self.status_label.setProperty("class", "alarm-status-unconfigured")

        self.desc_label = QLabel("说明：等待规则配置")
        self.desc_label.setProperty("class", "alarm-desc")
        self.desc_label.setWordWrap(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.desc_label)

    def set_status(self, status, desc):
        self.status_label.setText(f"状态：{status}")
        self.desc_label.setText(f"说明：{desc}")

        if status == "正常":
            self.status_label.setProperty("class", "alarm-status-normal")
        elif status == "预警":
            self.status_label.setProperty("class", "alarm-status-warning")
        elif status == "危险":
            self.status_label.setProperty("class", "alarm-status-danger")
        else:
            self.status_label.setProperty("class", "alarm-status-unconfigured")

        self.style().unpolish(self.status_label)
        self.style().polish(self.status_label)

class MainWindow(QMainWindow):
    def __init__(self, config, logger):
        super().__init__()
        self.config = config
        self.logger = logger
        self.current_theme = self.config.get("ui", {}).get("theme", "light")
        self.setWindowTitle("FaWave 多维力感知平台")
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "app_icon.svg")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setMinimumSize(1360, 780)
        self.resize(1500, 900)

        self.last_error = "无"

        self.data_buffer = DataBuffer(max_points=config.get("ui", {}).get("max_plot_points", 2000))
        self.data_recorder = DataRecorder()
        self.worker = AcquisitionWorker(config, self.data_buffer, self.data_recorder, self.logger)

        self.worker.connection_status_changed.connect(self.on_connection_status_changed)
        self.worker.error_occurred.connect(self.on_error_occurred)

        self.ui_timer = QTimer(self)
        self.refresh_rate_ms = config.get("ui", {}).get("refresh_rate_ms", 50)
        self.ui_timer.timeout.connect(self.update_ui)

        self.setup_ui()
        self.apply_theme()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(16, 16, 16, 8)
        main_layout.setSpacing(16)

        self.setup_header(main_layout)

        # Main Content Area - HBox
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        main_layout.addLayout(content_layout, stretch=1)

        self.setup_left_panel(content_layout)
        self.setup_center_panel(content_layout)
        self.setup_right_panel(content_layout)

        self.setup_status_bar()

    def setup_header(self, parent_layout):
        header_frame = QFrame()
        header_frame.setObjectName("headerCard")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 16, 20, 16)

        logo_layout = QHBoxLayout()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "logo.svg")
        if os.path.exists(logo_path):
            self.logo_widget = QSvgWidget(logo_path)
            self.logo_widget.setFixedSize(40, 40)
            logo_layout.addWidget(self.logo_widget)
            logo_layout.addSpacing(12)

        title_layout = QVBoxLayout()
        self.title_label = QLabel("FaWave 多维力感知采集与安全监测平台")
        self.title_label.setObjectName("headerTitle")

        self.subtitle_label = QLabel("面向多通道力传感、三维力解耦与安全报警的实时采集系统")
        self.subtitle_label.setObjectName("headerSubtitle")

        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)
        logo_layout.addLayout(title_layout)

        # Header Right side
        header_right_layout = QHBoxLayout()

        # Theme toggle Card-like
        theme_widget = QFrame()
        theme_widget.setObjectName("valCard")
        theme_layout = QHBoxLayout(theme_widget)
        theme_layout.setContentsMargins(12, 6, 12, 6)
        theme_label = QLabel("界面主题")
        theme_label.setProperty("class", "sys-stat-label")
        self.btn_theme = QPushButton("切换深色主题" if self.current_theme == 'light' else "切换浅色主题")
        self.btn_theme.setCursor(Qt.PointingHandCursor)
        self.btn_theme.clicked.connect(self.toggle_theme)
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.btn_theme)

        self.status_capsule = QLabel("● 未连接")
        self.status_capsule.setObjectName("statusCapsule_Disconnected")
        self.status_capsule.setAlignment(Qt.AlignCenter)

        header_right_layout.addWidget(theme_widget)
        header_right_layout.addSpacing(16)
        header_right_layout.addWidget(self.status_capsule)

        header_layout.addLayout(logo_layout)
        header_layout.addStretch()
        header_layout.addLayout(header_right_layout)
        parent_layout.addWidget(header_frame)

    def setup_left_panel(self, parent_layout):
        left_scroll = QScrollArea()
        left_scroll.setFixedWidth(360)
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(16)

        # 1. Communication
        conn_group = QGroupBox("通信设置")
        conn_layout = QFormLayout(conn_group)
        conn_layout.setSpacing(12)

        self.ip_input = QLineEdit(self.config.get("device_ip", "192.168.1.82"))
        self.port_input = QLineEdit(str(self.config.get("device_port", 16008)))

        # Arrange settings vertically per user request
        conn_layout.addRow(QLabel("设备 IP"))
        conn_layout.addRow(self.ip_input)

        conn_layout.addRow(QLabel("端口"))
        conn_layout.addRow(self.port_input)

        conn_layout.addRow(QLabel("采集模式"))

        default_acq_mode = "真实设备"
        if self.config.get("acquisition_mode") == "simulation":
            default_acq_mode = "仿真演示"

        self.mode_combo = SegmentedControl(["真实设备", "仿真演示"], default_acq_mode)
        conn_layout.addRow(self.mode_combo)

        conn_layout.addRow(QLabel("请求间隔 / ms"))
        self.interval_input = QLineEdit(str(self.config.get("request_interval_ms", 20)))
        conn_layout.addRow(self.interval_input)

        self.btn_connect = QPushButton("建立连接")
        self.btn_connect.setObjectName("btnConnect")
        self.btn_connect.setMinimumHeight(42)
        self.btn_connect.clicked.connect(self.toggle_connection)
        conn_layout.addRow(self.btn_connect)
        left_layout.addWidget(conn_group)

        # 2. Data Recording
        record_group = QGroupBox("数据记录")
        record_layout = QVBoxLayout(record_group)
        record_layout.setSpacing(12)

        self.record_checkbox = QCheckBox("启用本地存储")

        fmt_layout = QVBoxLayout()
        fmt_layout.setSpacing(6)
        fmt_layout.addWidget(QLabel("保存格式"))
        self.format_combo = SegmentedControl(["CSV", "XLSX"], "CSV")
        fmt_layout.addWidget(self.format_combo)

        self.path_btn = QPushButton("选择保存路径")
        self.path_btn.setMinimumHeight(40)
        self.path_btn.clicked.connect(self.select_save_path)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.save_path = os.path.join(os.getcwd(), "Data", f"FaWave_Data_{timestamp}.csv")
        self.path_label = QLabel(self.save_path)
        self.path_label.setProperty("class", "sys-stat-label")
        self.path_label.setToolTip(self.save_path)

        # Elide text if too long
        metrics = QFontMetrics(self.path_label.font())
        elided = metrics.elidedText(self.save_path, Qt.ElideMiddle, 300)
        self.path_label.setText(elided)

        record_layout.addWidget(self.record_checkbox)
        record_layout.addLayout(fmt_layout)
        record_layout.addWidget(self.path_btn)
        record_layout.addWidget(QLabel("当前路径:"))
        record_layout.addWidget(self.path_label)
        left_layout.addWidget(record_group)

        # 3. Controls
        ctrl_group = QGroupBox("操作控制")
        ctrl_layout = QVBoxLayout(ctrl_group)
        ctrl_layout.setSpacing(12)

        self.btn_autoscale = QPushButton("自动跟随：开启")
        self.btn_autoscale.setMinimumHeight(40)
        self.btn_autoscale.clicked.connect(self.toggle_auto_follow)

        self.auto_follow = True
        self.follow_window_s = 10.0
        self._programmatic_range_update = False

        self.btn_clear = QPushButton("清空波形")
        self.btn_clear.setMinimumHeight(40)
        self.btn_clear.clicked.connect(self.clear_plot)

        ctrl_layout.addWidget(self.btn_autoscale)
        ctrl_layout.addWidget(self.btn_clear)
        left_layout.addWidget(ctrl_group)

        left_layout.addStretch()
        left_scroll.setWidget(left_panel)
        parent_layout.addWidget(left_scroll)

    def setup_center_panel(self, parent_layout):
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(16)

        self.setup_value_cards(center_layout)

        # Splitter for the two plots
        plot_splitter = QSplitter(Qt.Vertical)

        self.setup_voltage_plot(plot_splitter)
        self.setup_force_plot(plot_splitter)

        # Set initial sizes (e.g. 55% / 45%)
        plot_splitter.setSizes([550, 450])

        center_layout.addWidget(plot_splitter, stretch=1)
        parent_layout.addWidget(center_panel, stretch=1)

    def setup_value_cards(self, parent_layout):
        overview_card = QWidget()
        overview_card.setProperty("class", "Card")
        overview_card.setMinimumHeight(135)
        overview_card.setMaximumHeight(165)
        layout = QVBoxLayout(overview_card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("实时数据总览")
        title.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(8)

        # Voltages
        self.card_ch1 = ValueCard("通道 1", "mV", "#2563EB", compact=True)
        self.card_ch2 = ValueCard("通道 2", "mV", "#F97316", compact=True)
        self.card_ch3 = ValueCard("通道 3", "mV", "#10B981", compact=True)
        self.card_ch4 = ValueCard("通道 4", "mV", "#8B5CF6", compact=True)

        grid.addWidget(self.card_ch1, 0, 0)
        grid.addWidget(self.card_ch2, 0, 1)
        grid.addWidget(self.card_ch3, 0, 2)
        grid.addWidget(self.card_ch4, 0, 3)

        # Forces
        # Add Decouple Status directly beneath the Row 1 layout but before Row 2 to simulate subheaders since we use a flat Grid
        f_title = QLabel("三维力")
        f_title.setProperty("class", "sys-stat-label")
        f_status = QLabel("解耦未启用")
        f_status.setStyleSheet("color: #94A3B8; font-size: 12px;")

        f_header = QHBoxLayout()
        f_header.addWidget(f_title)
        f_header.addWidget(f_status)
        f_header.addStretch()

        f_header_widget = QWidget()
        f_header_widget.setLayout(f_header)
        layout.addWidget(f_header_widget)

        self.card_fx = ValueCard("Fx", "N", "#0EA5E9", compact=True)
        self.card_fy = ValueCard("Fy", "N", "#F59E0B", compact=True)
        self.card_fz = ValueCard("Fz", "N", "#EF4444", compact=True)

        grid.addWidget(self.card_fx, 1, 0)
        grid.addWidget(self.card_fy, 1, 1)
        grid.addWidget(self.card_fz, 1, 2)

        # Blank placeholder for bottom right corner to maintain equal layout
        spacer_card = QWidget()
        spacer_card.setProperty("class", "valCard")
        grid.addWidget(spacer_card, 1, 3)

        layout.addLayout(grid)
        parent_layout.addWidget(overview_card, stretch=0)

    def create_legend_toggle_chip(self, text, color):
        btn = QPushButton(f"● {text}")
        btn.setProperty("class", "legend-chip")
        btn.setCheckable(True)
        btn.setChecked(True)
        # We handle dynamic color switching in style logic or directly
        btn.setStyleSheet(f"""
            QPushButton:checked {{
                color: {color};
            }}
        """)
        return btn

    def setup_voltage_plot(self, parent_splitter):
        container = QWidget()
        container.setProperty("class", "Card")
        layout = QVBoxLayout(container)

        # Header Row
        header_layout = QHBoxLayout()
        title = QLabel("原始电压曲线")
        title.setStyleSheet("font-size: 15px; font-weight: bold;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Custom Legend Toggle Chips
        self.chk_ch1 = self.create_legend_toggle_chip("通道 1", "#2563EB")
        self.chk_ch2 = self.create_legend_toggle_chip("通道 2", "#F97316")
        self.chk_ch3 = self.create_legend_toggle_chip("通道 3", "#10B981")
        self.chk_ch4 = self.create_legend_toggle_chip("通道 4", "#8B5CF6")

        for chk in [self.chk_ch1, self.chk_ch2, self.chk_ch3, self.chk_ch4]:
            chk.toggled.connect(self.update_plot_visibility)
            header_layout.addWidget(chk)

        layout.addLayout(header_layout)

        pg.setConfigOption('background', 'w') # Will be overridden in apply_theme
        pg.setConfigOption('foreground', 'k')

        self.plot_voltage = pg.PlotWidget()
        self.plot_voltage.showGrid(x=True, y=True, alpha=0.3)
        self.plot_voltage.setLabel('left', '电压', units='mV')
        self.plot_voltage.setLabel('bottom', '相对时间', units='s')
        self.plot_voltage.setYRange(-2.5, 2.5)

        self.curve_ch1 = self.plot_voltage.plot(pen=pg.mkPen('#2563EB', width=2))
        self.curve_ch2 = self.plot_voltage.plot(pen=pg.mkPen('#F97316', width=2))
        self.curve_ch3 = self.plot_voltage.plot(pen=pg.mkPen('#10B981', width=2))
        self.curve_ch4 = self.plot_voltage.plot(pen=pg.mkPen('#8B5CF6', width=2))

        self.plot_voltage.getViewBox().sigRangeChanged.connect(self.on_plot_interacted)

        layout.addWidget(self.plot_voltage)
        parent_splitter.addWidget(container)

    def setup_force_plot(self, parent_splitter):
        container = QWidget()
        container.setProperty("class", "Card")
        layout = QVBoxLayout(container)

        # Header Row
        header_layout = QHBoxLayout()
        title = QLabel("三维力解耦曲线")
        title.setStyleSheet("font-size: 15px; font-weight: bold;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Custom Legend Toggle Chips
        self.chk_fx = self.create_legend_toggle_chip("Fx", "#0EA5E9")
        self.chk_fy = self.create_legend_toggle_chip("Fy", "#F59E0B")
        self.chk_fz = self.create_legend_toggle_chip("Fz", "#EF4444")

        for chk in [self.chk_fx, self.chk_fy, self.chk_fz]:
            chk.toggled.connect(self.update_plot_visibility)
            header_layout.addWidget(chk)

        layout.addLayout(header_layout)

        self.plot_force = pg.PlotWidget()
        self.plot_force.showGrid(x=True, y=True, alpha=0.3)
        self.plot_force.setLabel('left', '力', units='N')
        self.plot_force.setLabel('bottom', '相对时间', units='s')
        self.plot_force.setYRange(-5, 5)

        self.curve_fx = self.plot_force.plot(pen=pg.mkPen('#0EA5E9', width=2))
        self.curve_fy = self.plot_force.plot(pen=pg.mkPen('#F59E0B', width=2))
        self.curve_fz = self.plot_force.plot(pen=pg.mkPen('#EF4444', width=2))

        self.plot_force.getViewBox().sigRangeChanged.connect(self.on_plot_interacted)

        layout.addWidget(self.plot_force)
        parent_splitter.addWidget(container)

    def setup_right_panel(self, parent_layout):
        right_panel = QWidget()
        right_panel.setFixedWidth(300)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)

        self.setup_alarm_panel(right_layout)
        self.setup_system_status_panel(right_layout)

        right_layout.addStretch()
        parent_layout.addWidget(right_panel)

    def setup_alarm_panel(self, parent_layout):
        alarm_card = QWidget()
        alarm_card.setProperty("class", "Card")
        layout = QVBoxLayout(alarm_card)
        layout.setSpacing(8)

        title = QLabel("安全报警")
        title.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(title)

        self.alarm_cards = []
        for i in range(3):
            card = AlarmCard(f"● 报警 {i+1}")
            self.alarm_cards.append(card)
            layout.addWidget(card)

        # Recent Alarms
        layout.addSpacing(8)
        recent_title = QLabel("最近报警")
        recent_title.setStyleSheet("font-weight: bold;")
        layout.addWidget(recent_title)

        self.recent_alarm_label = QLabel("暂无报警信息")
        self.recent_alarm_label.setProperty("class", "sys-stat-label")
        self.recent_alarm_label.setWordWrap(True)
        self.recent_alarm_label.setStyleSheet("background-color: transparent; border: 1px solid #DDE5F0; border-radius: 4px; padding: 6px;")
        layout.addWidget(self.recent_alarm_label)

        parent_layout.addWidget(alarm_card)

    def setup_system_status_panel(self, parent_layout):
        sys_card = QWidget()
        sys_card.setProperty("class", "Card")
        layout = QVBoxLayout(sys_card)
        layout.setSpacing(12)

        title = QLabel("系统状态")
        title.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setVerticalSpacing(12)
        grid.setHorizontalSpacing(16)

        labels = ["连接状态", "采集模式", "有效帧", "错误帧", "运行时间", "保存状态", "解耦状态"]
        self.sys_values = {}

        for i, lbl in enumerate(labels):
            l = QLabel(f"{lbl}")
            l.setProperty("class", "sys-stat-label")
            grid.addWidget(l, i, 0)

            v = QLabel("--")
            v.setProperty("class", "sys-stat-value")
            grid.addWidget(v, i, 1, alignment=Qt.AlignRight)
            self.sys_values[lbl] = v

        # Add Recent Error specifically
        layout.addLayout(grid)
        layout.addSpacing(8)

        err_title = QLabel("最近错误")
        err_title.setProperty("class", "sys-stat-label")
        layout.addWidget(err_title)

        self.sys_values["最近错误"] = QLabel("无")
        self.sys_values["最近错误"].setProperty("class", "sys-stat-value")
        self.sys_values["最近错误"].setWordWrap(True)
        layout.addWidget(self.sys_values["最近错误"])

        self.sys_values["连接状态"].setText("未连接")
        self.sys_values["保存状态"].setText("未保存")
        self.sys_values["解耦状态"].setText("未启用")
        self.sys_values["采集模式"].setText(self.get_display_mode())

        parent_layout.addWidget(sys_card)

    def setup_status_bar(self):
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.update_status()

    def apply_theme(self):
        try:
            theme_file = 'light.qss' if self.current_theme == 'light' else 'dark.qss'
            qss_path = os.path.join(os.path.dirname(__file__), 'themes', theme_file)
            with open(qss_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())

            # Update pg plots background
            bg_color = '#FFFFFF' if self.current_theme == 'light' else '#0B1120'
            fg_color = '#0F172A' if self.current_theme == 'light' else '#E5E7EB'
            grid_alpha = 50 if self.current_theme == 'light' else 80

            for plot in [self.plot_voltage, self.plot_force]:
                plot.setBackground(bg_color)
                plot.getAxis('left').setPen(fg_color)
                plot.getAxis('bottom').setPen(fg_color)
                plot.getAxis('left').setTextPen(fg_color)
                plot.getAxis('bottom').setTextPen(fg_color)
                plot.showGrid(x=True, y=True, alpha=grid_alpha/255.0)

        except Exception as e:
            print(f"Failed to load stylesheet: {e}")

    def toggle_theme(self):
        if self.current_theme == 'light':
            self.current_theme = 'dark'
            self.btn_theme.setText("切换浅色主题")
        else:
            self.current_theme = 'light'
            self.btn_theme.setText("切换深色主题")

        self.apply_theme()

    def select_save_path(self):
        fmt = self.format_combo.currentText().lower()
        default_dir = os.path.join(os.getcwd(), "Data")
        os.makedirs(default_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"FaWave_Data_{timestamp}.{fmt}"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择保存路径", os.path.join(default_dir, default_name),
            f"数据文件 (*.{fmt})"
        )
        if file_path:
            self.save_path = file_path
            self.path_label.setToolTip(self.save_path)

            metrics = QFontMetrics(self.path_label.font())
            elided = metrics.elidedText(self.save_path, Qt.ElideMiddle, 300)
            self.path_label.setText(elided)

    def update_plot_visibility(self):
        self.curve_ch1.setVisible(self.chk_ch1.isChecked())
        self.curve_ch2.setVisible(self.chk_ch2.isChecked())
        self.curve_ch3.setVisible(self.chk_ch3.isChecked())
        self.curve_ch4.setVisible(self.chk_ch4.isChecked())
        self.curve_fx.setVisible(self.chk_fx.isChecked())
        self.curve_fy.setVisible(self.chk_fy.isChecked())
        self.curve_fz.setVisible(self.chk_fz.isChecked())

    def clear_plot(self):
        self.data_buffer.clear()
        self.curve_ch1.setData([], [])
        self.curve_ch2.setData([], [])
        self.curve_ch3.setData([], [])
        self.curve_ch4.setData([], [])

        self.curve_fx.setData([], [])
        self.curve_fy.setData([], [])
        self.curve_fz.setData([], [])

    def on_plot_interacted(self):
        if not self._programmatic_range_update and self.auto_follow:
            self.auto_follow = False
            self.btn_autoscale.setText("自动跟随：关闭")

    def toggle_auto_follow(self):
        self.auto_follow = not self.auto_follow
        if self.auto_follow:
            self.btn_autoscale.setText("自动跟随：开启")
        else:
            self.btn_autoscale.setText("自动跟随：关闭")

    def get_worker_mode(self):
        if self.mode_combo.currentText() == "真实设备":
            return "TCP"
        elif self.mode_combo.currentText() == "仿真演示":
            return "Mock"
        return "TCP"

    def get_display_mode(self):
        return self.mode_combo.currentText()

    def toggle_connection(self):
        if not self.worker.is_running:
            # Connect
            ip = self.ip_input.text()
            try:
                port = int(self.port_input.text())
            except ValueError:
                QMessageBox.warning(self, "输入错误", "端口必须是整数。")
                return

            try:
                interval = int(self.interval_input.text())
                self.config["request_interval_ms"] = interval
            except ValueError:
                pass

            worker_mode = self.get_worker_mode()

            if self.record_checkbox.isChecked():
                fmt = self.format_combo.currentText()
                if not self.save_path.lower().endswith(f".{fmt.lower()}"):
                    self.save_path = f"{os.path.splitext(self.save_path)[0]}.{fmt.lower()}"

                    metrics = QFontMetrics(self.path_label.font())
                    elided = metrics.elidedText(self.save_path, Qt.ElideMiddle, 300)
                    self.path_label.setText(elided)
                    self.path_label.setToolTip(self.save_path)

                try:
                    self.data_recorder.start_recording(self.save_path, format=fmt)
                    self.logger.info(f"保存路径: {self.save_path}")
                except Exception as e:
                    self.logger.error(f"保存文件失败: {e}", exc_info=True)
                    QMessageBox.warning(self, "保存错误", f"无法开始记录:\n{e}")
                    return

            self.logger.info(f"连接参数: IP={ip}, Port={port}, Mode={worker_mode}")
            self.worker.set_connection_params(worker_mode, ip, port)
            self.worker.start()

            self.ui_timer.start(self.refresh_rate_ms)

            self.btn_connect.setText("断开连接")
            self.btn_connect.setObjectName("btnDisconnect")
            self.apply_theme() # Refresh styling

            self.ip_input.setEnabled(False)
            self.port_input.setEnabled(False)
            self.interval_input.setEnabled(False)
            self.mode_combo.setEnabled(False)
            # Need to disable buttons inside the segmented control manually if disabling widget isn't styled properly
            for btn in self.mode_combo._buttons.values(): btn.setEnabled(False)
            self.record_checkbox.setEnabled(False)

        else:
            # Disconnect
            self.logger.info("用户主动断开连接")
            self.worker.stop()
            self.data_recorder.stop_recording()
            self.ui_timer.stop()

            self.btn_connect.setText("建立连接")
            self.btn_connect.setObjectName("btnConnect")
            self.apply_theme()

            self.ip_input.setEnabled(True)
            self.port_input.setEnabled(True)
            self.interval_input.setEnabled(True)
            self.mode_combo.setEnabled(True)
            for btn in self.mode_combo._buttons.values(): btn.setEnabled(True)
            self.record_checkbox.setEnabled(True)

    def on_connection_status_changed(self, status):
        is_simulation = self.get_display_mode() == "仿真演示"

        if status == "Connected":
            disp_text = "● 仿真运行" if is_simulation else "● 已连接"
            self.status_capsule.setText(disp_text)
            self.status_capsule.setObjectName("statusCapsule_Connected")
            self.sys_values["连接状态"].setText(disp_text.replace("● ", ""))
        elif status == "Disconnected":
            self.status_capsule.setText("● 未连接")
            self.status_capsule.setObjectName("statusCapsule_Disconnected")
            self.sys_values["连接状态"].setText("未连接")
        else:
            self.status_capsule.setText("● 错误")
            self.status_capsule.setObjectName("statusCapsule_Error")
            self.sys_values["连接状态"].setText("错误")

            if self.worker.is_running:
                 self.toggle_connection()

        self.style().unpolish(self.status_capsule)
        self.style().polish(self.status_capsule)
        self.update_status()

    def on_error_occurred(self, err_msg):
        self.last_error = err_msg
        self.update_status()

    def update_status(self):
        conn_str = self.status_capsule.text().replace("● ", "")
        save_str = "正在保存" if self.data_recorder.is_recording else "未保存"
        acq_mode = self.get_display_mode()

        run_time_str = "00:00:00"
        if self.worker.is_running and self.worker.start_time > 0:
            import time
            elapsed = int(time.time() - self.worker.start_time)
            run_time_str = f"{elapsed//3600:02d}:{(elapsed%3600)//60:02d}:{elapsed%60:02d}"

        # Update System Status Card
        self.sys_values["采集模式"].setText(acq_mode)
        self.sys_values["有效帧"].setText(str(self.worker.recv_frames))
        self.sys_values["错误帧"].setText(str(self.worker.error_frames))
        self.sys_values["运行时间"].setText(run_time_str)
        self.sys_values["保存状态"].setText(save_str)

        err_display = self.last_error
        if err_display.startswith("最近错误："):
            err_display = err_display.replace("最近错误：", "")
        self.sys_values["最近错误"].setText(err_display)

        # Update bottom status bar
        status_text = (
            f"连接状态：{conn_str} | "
            f"采集模式：{acq_mode} | "
            f"有效帧：{self.worker.recv_frames} | "
            f"错误帧：{self.worker.error_frames} | "
            f"运行时间：{run_time_str} | "
            f"保存状态：{save_str} | "
            f"最近错误：{self.last_error}"
        )
        self.statusBar.showMessage(status_text)

    def auto_range_plot(self, plot_widget, datasets, default_range, padding=0.1):
        if not datasets:
            return

        min_y = float('inf')
        max_y = float('-inf')

        for data in datasets:
            if not data:
                continue
            curr_min = min(data)
            curr_max = max(data)
            if curr_min < min_y:
                min_y = curr_min
            if curr_max > max_y:
                max_y = curr_max

        if min_y == float('inf') or max_y == float('-inf'):
            plot_widget.setYRange(*default_range)
            return

        if max_y - min_y < 0.0001:
            if max_y == 0:
                plot_widget.setYRange(*default_range)
            else:
                margin = abs(max_y) * padding
                plot_widget.setYRange(min_y - margin, max_y + margin)
            return

        range_span = max_y - min_y
        margin = range_span * padding
        plot_widget.setYRange(min_y - margin, max_y + margin)

    def update_ui(self):
        self.update_status()

        t_data, idx_data, ch1, ch2, ch3, ch4, fx, fy, fz = self.data_buffer.get_data()

        if not t_data:
            return

        self.curve_ch1.setData(t_data, ch1)
        self.curve_ch2.setData(t_data, ch2)
        self.curve_ch3.setData(t_data, ch3)
        self.curve_ch4.setData(t_data, ch4)

        self.curve_fx.setData(t_data, fx)
        self.curve_fy.setData(t_data, fy)
        self.curve_fz.setData(t_data, fz)

        # Apply Auto Follow
        if hasattr(self, 'auto_follow') and self.auto_follow:
            self._programmatic_range_update = True

            t_end = t_data[-1]
            t_start = max(t_data[0], t_end - self.follow_window_s)

            self.plot_voltage.setXRange(t_start, t_end, padding=0)
            self.plot_force.setXRange(t_start, t_end, padding=0)

            # We filter data points to only those within [t_start, t_end]
            # To optimize, we can just use the whole array if it's within deque size
            # Since max_points=2000 at 20ms is 40s, we should slice it.
            try:
                start_idx = next(i for i, t in enumerate(t_data) if t >= t_start)
            except StopIteration:
                start_idx = 0

            # Voltage plot
            active_v_data = []
            if getattr(self, 'chk_ch1', None) and self.chk_ch1.isChecked(): active_v_data.append(ch1[start_idx:])
            if getattr(self, 'chk_ch2', None) and self.chk_ch2.isChecked(): active_v_data.append(ch2[start_idx:])
            if getattr(self, 'chk_ch3', None) and self.chk_ch3.isChecked(): active_v_data.append(ch3[start_idx:])
            if getattr(self, 'chk_ch4', None) and self.chk_ch4.isChecked(): active_v_data.append(ch4[start_idx:])
            self.auto_range_plot(self.plot_voltage, active_v_data, [-2.5, 2.5])

            # Force plot
            active_f_data = []
            if getattr(self, 'chk_fx', None) and self.chk_fx.isChecked(): active_f_data.append(fx[start_idx:])
            if getattr(self, 'chk_fy', None) and self.chk_fy.isChecked(): active_f_data.append(fy[start_idx:])
            if getattr(self, 'chk_fz', None) and self.chk_fz.isChecked(): active_f_data.append(fz[start_idx:])
            self.auto_range_plot(self.plot_force, active_f_data, [-5, 5])

            self._programmatic_range_update = False

        self.card_ch1.set_value(ch1[-1])
        self.card_ch2.set_value(ch2[-1])
        self.card_ch3.set_value(ch3[-1])
        self.card_ch4.set_value(ch4[-1])

        self.card_fx.set_value(fx[-1])
        self.card_fy.set_value(fy[-1])
        self.card_fz.set_value(fz[-1])

    def closeEvent(self, event):
        if self.worker.is_running:
            self.worker.stop()
        self.data_recorder.stop_recording()
        event.accept()
