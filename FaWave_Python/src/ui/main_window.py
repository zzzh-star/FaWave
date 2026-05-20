import os
from datetime import datetime
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QLineEdit, QComboBox, QPushButton, QCheckBox,
                               QGroupBox, QGridLayout, QFileDialog, QStatusBar, QMessageBox,
                               QSpacerItem, QSizePolicy, QTabWidget, QFrame)
from PySide6.QtCore import Qt, QTimer
import pyqtgraph as pg

from ..workers.acquisition_worker import AcquisitionWorker
from ..data.data_buffer import DataBuffer
from ..data.data_recorder import DataRecorder

class ValueCard(QWidget):
    def __init__(self, title, unit, color):
        super().__init__()
        self.setObjectName("valCard")
        layout = QVBoxLayout(self)

        # Color indicator + Title
        title_layout = QHBoxLayout()
        color_indicator = QLabel()
        color_indicator.setFixedSize(12, 12)
        color_indicator.setStyleSheet(f"background-color: {color}; border-radius: 6px;")

        title_label = QLabel(title)
        title_label.setProperty("class", "channel-title")

        title_layout.addWidget(color_indicator)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Value + Unit
        val_layout = QHBoxLayout()
        self.val_label = QLabel("0.0000")
        self.val_label.setProperty("class", "channel-value")
        self.val_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        unit_label = QLabel(unit)
        unit_label.setProperty("class", "channel-unit")
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

        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "alarm-title")

        self.status_label = QLabel("状态：正常")
        self.status_label.setProperty("class", "alarm-status-normal")

        self.desc_label = QLabel("说明：等待规则配置")
        self.desc_label.setProperty("class", "alarm-desc")

        layout.addWidget(self.title_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.desc_label)

    def set_status(self, status, desc):
        self.status_label.setText(f"状态：{status}")
        self.desc_label.setText(f"说明：{desc}")

        # Dynamic styling
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
        self.setWindowTitle("FaWave 四通道力传感采集系统")
        self.setMinimumSize(1280, 760)
        self.resize(1440, 860)

        self.start_time = None
        self.last_error = "无"

        # Initialize data components
        self.data_buffer = DataBuffer(max_points=config.get("ui", {}).get("max_plot_points", 2000))
        self.data_recorder = DataRecorder()
        self.worker = AcquisitionWorker(config, self.data_buffer, self.data_recorder, self.logger)

        # Connect worker signals
        self.worker.connection_status_changed.connect(self.on_connection_status_changed)
        self.worker.error_occurred.connect(self.on_error_occurred)
        self.worker.stats_updated.connect(self.on_stats_updated)

        # Setup UI Refresh Timer
        self.ui_timer = QTimer(self)
        self.refresh_rate_ms = config.get("ui", {}).get("refresh_rate_ms", 50)
        self.ui_timer.timeout.connect(self.update_ui)

        self.setup_ui()
        self.apply_theme()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # 1. Header Area
        header_layout = QHBoxLayout()
        title_layout = QVBoxLayout()
        title_label = QLabel("FaWave 四通道力传感采集系统")
        title_label.setStyleSheet("font-size: 26px; font-weight: bold; color: #0F172A;")
        subtitle_label = QLabel("基于以太网通信的四通道力传感数据采集与可视化平台")
        subtitle_label.setStyleSheet("font-size: 14px; color: #64748B;")
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)

        # Header Right side
        header_right_layout = QHBoxLayout()

        # Theme toggle
        self.btn_theme = QPushButton("切换深色主题")
        self.btn_theme.setObjectName("btnThemeToggle")
        self.btn_theme.clicked.connect(self.toggle_theme)

        # Status capsule
        self.status_capsule = QLabel("● 未连接")
        self.status_capsule.setStyleSheet("""
            background-color: #F1F5F9; color: #64748B;
            border-radius: 16px; padding: 6px 16px; font-weight: bold;
        """)

        header_right_layout.addWidget(self.btn_theme)
        header_right_layout.addSpacing(16)
        header_right_layout.addWidget(self.status_capsule)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        header_layout.addLayout(header_right_layout)
        main_layout.addLayout(header_layout)
        main_layout.addSpacing(16)

        # Main Content Layout (Left Panel + Right Tab Area)
        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout, stretch=1)

        # 2. Left Control Panel
        left_panel = QWidget()
        left_panel.setFixedWidth(320)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(left_panel)

        # Connection Settings Group
        conn_group = QGroupBox("通信设置")
        conn_layout = QGridLayout(conn_group)

        conn_layout.addWidget(QLabel("设备 IP:"), 0, 0)
        self.ip_input = QLineEdit(self.config.get("device_ip", "192.168.1.82"))
        conn_layout.addWidget(self.ip_input, 0, 1)

        conn_layout.addWidget(QLabel("端口:"), 1, 0)
        self.port_input = QLineEdit(str(self.config.get("device_port", 16008)))
        conn_layout.addWidget(self.port_input, 1, 1)

        conn_layout.addWidget(QLabel("通信方式:"), 2, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["TCP", "UDP", "Mock"])
        self.mode_combo.setCurrentText(self.config.get("communication_mode", "TCP"))
        conn_layout.addWidget(self.mode_combo, 2, 1)

        conn_layout.addWidget(QLabel("请求间隔 / ms:"), 3, 0)
        self.interval_input = QLineEdit(str(self.config.get("request_interval_ms", 20)))
        conn_layout.addWidget(self.interval_input, 3, 1)

        left_layout.addWidget(conn_group)

        # Data Recording Group
        record_group = QGroupBox("数据记录")
        record_layout = QGridLayout(record_group)

        self.record_checkbox = QCheckBox("启用本地存储")
        record_layout.addWidget(self.record_checkbox, 0, 0, 1, 2)

        record_layout.addWidget(QLabel("保存格式:"), 1, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["CSV", "XLSX"])
        record_layout.addWidget(self.format_combo, 1, 1)

        self.path_btn = QPushButton("选择保存路径")
        self.path_btn.clicked.connect(self.select_save_path)
        record_layout.addWidget(self.path_btn, 2, 0, 1, 2)

        # Default save path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.save_path = os.path.join(os.getcwd(), "Data", f"FaWave_Data_{timestamp}.csv")
        self.path_label = QLabel(self.save_path)
        self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet("font-size: 12px; color: #64748B;")
        record_layout.addWidget(self.path_label, 3, 0, 1, 2)

        left_layout.addWidget(record_group)

        # Controls Group
        control_group = QGroupBox("操作控制")
        control_layout = QVBoxLayout(control_group)

        self.btn_connect = QPushButton("建立连接")
        self.btn_connect.setObjectName("btnConnect")
        self.btn_connect.clicked.connect(self.toggle_connection)

        self.btn_clear = QPushButton("清空波形")
        self.btn_clear.clicked.connect(self.clear_plot)

        self.btn_autoscale = QPushButton("自动缩放")
        self.btn_autoscale.clicked.connect(self.auto_scale)

        control_layout.addWidget(self.btn_connect)
        control_layout.addWidget(self.btn_clear)
        control_layout.addWidget(self.btn_autoscale)

        left_layout.addWidget(control_group)

        # Channel Visibility
        vis_group = QGroupBox("通道显示")
        vis_layout = QVBoxLayout(vis_group)
        self.chk_ch1 = QCheckBox("■ 通道 1")
        self.chk_ch1.setStyleSheet("color: #2563EB;")
        self.chk_ch1.setChecked(True)
        self.chk_ch2 = QCheckBox("■ 通道 2")
        self.chk_ch2.setStyleSheet("color: #F97316;")
        self.chk_ch2.setChecked(True)
        self.chk_ch3 = QCheckBox("■ 通道 3")
        self.chk_ch3.setStyleSheet("color: #10B981;")
        self.chk_ch3.setChecked(True)
        self.chk_ch4 = QCheckBox("■ 通道 4")
        self.chk_ch4.setStyleSheet("color: #8B5CF6;")
        self.chk_ch4.setChecked(True)

        self.chk_ch1.stateChanged.connect(self.update_plot_visibility)
        self.chk_ch2.stateChanged.connect(self.update_plot_visibility)
        self.chk_ch3.stateChanged.connect(self.update_plot_visibility)
        self.chk_ch4.stateChanged.connect(self.update_plot_visibility)

        vis_layout.addWidget(self.chk_ch1)
        vis_layout.addWidget(self.chk_ch2)
        vis_layout.addWidget(self.chk_ch3)
        vis_layout.addWidget(self.chk_ch4)

        left_layout.addWidget(vis_group)
        left_layout.addStretch()

        # 3. Right Area (Tabbed)
        self.tab_widget = QTabWidget()
        content_layout.addWidget(self.tab_widget, stretch=1)

        # Overview Tab
        overview_tab = QWidget()
        self.setup_overview_tab(overview_tab)
        self.tab_widget.addTab(overview_tab, "系统总览")

        # Raw Voltage Tab
        raw_voltage_tab = QWidget()
        self.setup_raw_voltage_tab(raw_voltage_tab)
        self.tab_widget.addTab(raw_voltage_tab, "原始电压")

        # 3D Force Tab
        force_tab = QWidget()
        self.setup_force_tab(force_tab)
        self.tab_widget.addTab(force_tab, "三维力解耦")

        # Alarms Tab
        alarms_tab = QWidget()
        self.setup_alarms_tab(alarms_tab)
        self.tab_widget.addTab(alarms_tab, "安全报警")

        # 4. Status Bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.update_status_bar()

    def setup_overview_tab(self, parent):
        layout = QVBoxLayout(parent)

        # Top half: Value cards
        cards_layout = QGridLayout()

        self.card_ch1 = ValueCard("通道 1", "mV", "#2563EB")
        self.card_ch2 = ValueCard("通道 2", "mV", "#F97316")
        self.card_ch3 = ValueCard("通道 3", "mV", "#10B981")
        self.card_ch4 = ValueCard("通道 4", "mV", "#8B5CF6")

        self.card_fx = ValueCard("Fx", "N", "#0EA5E9")
        self.card_fy = ValueCard("Fy", "N", "#F59E0B")
        self.card_fz = ValueCard("Fz", "N", "#EF4444")

        cards_layout.addWidget(self.card_ch1, 0, 0)
        cards_layout.addWidget(self.card_ch2, 0, 1)
        cards_layout.addWidget(self.card_ch3, 0, 2)
        cards_layout.addWidget(self.card_ch4, 0, 3)

        cards_layout.addWidget(self.card_fx, 1, 0)
        cards_layout.addWidget(self.card_fy, 1, 1)
        cards_layout.addWidget(self.card_fz, 1, 2)

        layout.addLayout(cards_layout)
        layout.addStretch()

    def setup_raw_voltage_tab(self, parent):
        layout = QVBoxLayout(parent)

        # Plot Area
        pg.setConfigOption('background', 'w' if self.current_theme == 'light' else '#0B1120')
        pg.setConfigOption('foreground', 'k' if self.current_theme == 'light' else '#E5E7EB')

        self.plot_voltage = pg.PlotWidget(title="四通道实时电压波形")
        self.plot_voltage.showGrid(x=True, y=True, alpha=0.3)
        self.plot_voltage.setLabel('left', '电压', units='mV')
        self.plot_voltage.setLabel('bottom', '相对时间', units='s')
        self.plot_voltage.addLegend()
        self.plot_voltage.setYRange(-2.5, 2.5)

        self.curve_ch1 = self.plot_voltage.plot(pen=pg.mkPen('#2563EB', width=2), name='通道 1')
        self.curve_ch2 = self.plot_voltage.plot(pen=pg.mkPen('#F97316', width=2), name='通道 2')
        self.curve_ch3 = self.plot_voltage.plot(pen=pg.mkPen('#10B981', width=2), name='通道 3')
        self.curve_ch4 = self.plot_voltage.plot(pen=pg.mkPen('#8B5CF6', width=2), name='通道 4')

        layout.addWidget(self.plot_voltage)

    def setup_force_tab(self, parent):
        layout = QVBoxLayout(parent)

        # Plot Area
        self.plot_force = pg.PlotWidget(title="三维力解耦曲线")
        self.plot_force.showGrid(x=True, y=True, alpha=0.3)
        self.plot_force.setLabel('left', '力', units='N')
        self.plot_force.setLabel('bottom', '相对时间', units='s')
        self.plot_force.addLegend()
        self.plot_force.setYRange(-10, 10)

        self.curve_fx = self.plot_force.plot(pen=pg.mkPen('#0EA5E9', width=2), name='Fx')
        self.curve_fy = self.plot_force.plot(pen=pg.mkPen('#F59E0B', width=2), name='Fy')
        self.curve_fz = self.plot_force.plot(pen=pg.mkPen('#EF4444', width=2), name='Fz')

        # Visibility toggles for force
        toggle_layout = QHBoxLayout()
        self.chk_fx = QCheckBox("显示 Fx"); self.chk_fx.setChecked(True)
        self.chk_fy = QCheckBox("显示 Fy"); self.chk_fy.setChecked(True)
        self.chk_fz = QCheckBox("显示 Fz"); self.chk_fz.setChecked(True)

        self.chk_fx.stateChanged.connect(lambda: self.curve_fx.setVisible(self.chk_fx.isChecked()))
        self.chk_fy.stateChanged.connect(lambda: self.curve_fy.setVisible(self.chk_fy.isChecked()))
        self.chk_fz.stateChanged.connect(lambda: self.curve_fz.setVisible(self.chk_fz.isChecked()))

        toggle_layout.addWidget(self.chk_fx)
        toggle_layout.addWidget(self.chk_fy)
        toggle_layout.addWidget(self.chk_fz)
        toggle_layout.addStretch()

        layout.addWidget(self.plot_force)
        layout.addLayout(toggle_layout)

    def setup_alarms_tab(self, parent):
        layout = QVBoxLayout(parent)

        alarms_grid = QGridLayout()
        self.alarm_cards = []

        for i in range(3):
            card = AlarmCard(f"● 报警 {i+1}")
            self.alarm_cards.append(card)
            alarms_grid.addWidget(card, 0, i)

        layout.addLayout(alarms_grid)
        layout.addStretch()

    def apply_theme(self):
        try:
            theme_file = 'light.qss' if self.current_theme == 'light' else 'dark.qss'
            qss_path = os.path.join(os.path.dirname(__file__), 'themes', theme_file)
            with open(qss_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())

            # Update pg plots background
            bg_color = 'w' if self.current_theme == 'light' else '#0B1120'
            fg_color = 'k' if self.current_theme == 'light' else '#E5E7EB'
            pg.setConfigOption('background', bg_color)
            pg.setConfigOption('foreground', fg_color)

            # Note: Changing pg global options only affects new plots,
            # so we explicitly update existing widgets
            self.plot_voltage.setBackground(bg_color)
            self.plot_voltage.getAxis('left').setPen(fg_color)
            self.plot_voltage.getAxis('bottom').setPen(fg_color)

            self.plot_force.setBackground(bg_color)
            self.plot_force.getAxis('left').setPen(fg_color)
            self.plot_force.getAxis('bottom').setPen(fg_color)

        except Exception as e:
            print(f"Failed to load stylesheet: {e}")

    def toggle_theme(self):
        if self.current_theme == 'light':
            self.current_theme = 'dark'
            self.btn_theme.setText("切换浅色主题")

            # Update main title specific coloring if needed
            self.findChild(QLabel, "").setStyleSheet("font-size: 26px; font-weight: bold; color: #E5E7EB;") if self.findChild(QLabel, "") else None
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

            # Truncate path for display
            display_path = file_path
            if len(display_path) > 40:
                parts = display_path.split(os.sep)
                if len(parts) > 3:
                    display_path = f"{parts[0]}{os.sep}...{os.sep}{parts[-2]}{os.sep}{parts[-1]}"
            self.path_label.setText(display_path)

    def update_plot_visibility(self):
        self.curve_ch1.setVisible(self.chk_ch1.isChecked())
        self.curve_ch2.setVisible(self.chk_ch2.isChecked())
        self.curve_ch3.setVisible(self.chk_ch3.isChecked())
        self.curve_ch4.setVisible(self.chk_ch4.isChecked())

    def clear_plot(self):
        self.data_buffer.clear()
        self.curve_ch1.setData([], [])
        self.curve_ch2.setData([], [])
        self.curve_ch3.setData([], [])
        self.curve_ch4.setData([], [])

        self.curve_fx.setData([], [])
        self.curve_fy.setData([], [])
        self.curve_fz.setData([], [])

    def auto_scale(self):
        self.plot_voltage.autoRange()
        self.plot_force.autoRange()

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

            mode = self.mode_combo.currentText()

            # Setup recording
            if self.record_checkbox.isChecked():
                fmt = self.format_combo.currentText()
                if not self.save_path.lower().endswith(f".{fmt.lower()}"):
                    self.save_path = f"{os.path.splitext(self.save_path)[0]}.{fmt.lower()}"
                    self.path_label.setText(self.save_path) # we would truncate here too, but okay for now

                try:
                    self.data_recorder.start_recording(self.save_path, format=fmt)
                    self.logger.info(f"保存路径: {self.save_path}")
                except Exception as e:
                    self.logger.error(f"保存文件失败: {e}", exc_info=True)
                    QMessageBox.warning(self, "保存错误", f"无法开始记录:\n{e}")
                    return

            self.logger.info(f"连接参数: IP={ip}, Port={port}, Mode={mode}")
            self.worker.set_connection_params(mode, ip, port)
            self.worker.start()

            # Start UI timer
            self.ui_timer.start(self.refresh_rate_ms)

            self.btn_connect.setText("断开连接")
            self.btn_connect.setObjectName("btnDisconnect")
            self.apply_theme() # Reapply to update button color

            # Disable inputs
            self.ip_input.setEnabled(False)
            self.port_input.setEnabled(False)
            self.interval_input.setEnabled(False)
            self.mode_combo.setEnabled(False)
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

            # Enable inputs
            self.ip_input.setEnabled(True)
            self.port_input.setEnabled(True)
            self.interval_input.setEnabled(True)
            self.mode_combo.setEnabled(True)
            self.record_checkbox.setEnabled(True)

    def on_connection_status_changed(self, status):
        status_zh = {"Connected": "已连接", "Disconnected": "未连接", "Error": "错误"}.get(status, status)

        if status == "Connected":
            self.status_capsule.setText("● 已连接")
            self.status_capsule.setStyleSheet("background-color: #DCFCE7; color: #16A34A; border-radius: 16px; padding: 6px 16px; font-weight: bold;")
        elif status == "Disconnected":
            self.status_capsule.setText("● 未连接")
            self.status_capsule.setStyleSheet("background-color: #F1F5F9; color: #64748B; border-radius: 16px; padding: 6px 16px; font-weight: bold;")
        else:
            self.status_capsule.setText("● 错误")
            self.status_capsule.setStyleSheet("background-color: #FEE2E2; color: #DC2626; border-radius: 16px; padding: 6px 16px; font-weight: bold;")

            # If error occurred, auto disconnect UI state
            if self.worker.is_running:
                 self.toggle_connection()

        self.update_status_bar()

    def on_error_occurred(self, err_msg):
        self.last_error = err_msg
        self.update_status_bar()

    def on_stats_updated(self, recv, errors):
        # We handle this in update_ui so it's rate limited
        pass

    def update_status_bar(self):
        conn_str = self.status_capsule.text().replace("● ", "")

        save_str = "正在保存" if self.data_recorder.is_recording else "未保存"

        # Calculate uptime
        run_time_str = "00:00:00"
        if self.worker.is_running and self.worker.start_time > 0:
            import time
            elapsed = int(time.time() - self.worker.start_time)
            run_time_str = f"{elapsed//3600:02d}:{(elapsed%3600)//60:02d}:{elapsed%60:02d}"

        status_text = (
            f"连接状态：{conn_str} | "
            f"有效帧：{self.worker.recv_frames} | "
            f"错误帧：{self.worker.error_frames} | "
            f"运行时间：{run_time_str} | "
            f"保存状态：{save_str} | "
            f"最近错误：{self.last_error}"
        )
        self.statusBar.showMessage(status_text)

    def update_ui(self):
        """Called by QTimer to update plots and values from buffer."""
        self.update_status_bar()

        t_data, idx_data, ch1, ch2, ch3, ch4, fx, fy, fz = self.data_buffer.get_data()

        if not t_data:
            return

        # Update plots
        self.curve_ch1.setData(t_data, ch1)
        self.curve_ch2.setData(t_data, ch2)
        self.curve_ch3.setData(t_data, ch3)
        self.curve_ch4.setData(t_data, ch4)

        self.curve_fx.setData(t_data, fx)
        self.curve_fy.setData(t_data, fy)
        self.curve_fz.setData(t_data, fz)

        # Update latest values
        self.card_ch1.set_value(ch1[-1])
        self.card_ch2.set_value(ch2[-1])
        self.card_ch3.set_value(ch3[-1])
        self.card_ch4.set_value(ch4[-1])

        self.card_fx.set_value(fx[-1])
        self.card_fy.set_value(fy[-1])
        self.card_fz.set_value(fz[-1])

        # Update alarm cards if data is available
        # we can't get this from data_buffer directly unless we add it, but since alarms change rarely we can just
        # let it be handled by a signal if needed, or query worker for latest alarms.
        # For UI stub purposes, leaving as "unconfigured"

    def closeEvent(self, event):
        if self.worker.is_running:
            self.worker.stop()
        self.data_recorder.stop_recording()
        event.accept()
