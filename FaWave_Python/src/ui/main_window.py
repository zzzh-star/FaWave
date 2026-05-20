import os
from datetime import datetime
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QLineEdit, QComboBox, QPushButton, QCheckBox,
                               QGroupBox, QGridLayout, QFileDialog, QStatusBar, QMessageBox,
                               QSpacerItem, QSizePolicy)
from PySide6.QtCore import Qt, QTimer
import pyqtgraph as pg

from ..workers.acquisition_worker import AcquisitionWorker
from ..data.data_buffer import DataBuffer
from ..data.data_recorder import DataRecorder

class MainWindow(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setWindowTitle("FaWave Force Acquisition System")
        self.resize(1200, 800)

        # Initialize data components
        self.data_buffer = DataBuffer(max_points=config.get("ui", {}).get("max_plot_points", 2000))
        self.data_recorder = DataRecorder()
        self.worker = AcquisitionWorker(config, self.data_buffer, self.data_recorder)

        # Connect worker signals
        self.worker.connection_status_changed.connect(self.on_connection_status_changed)
        self.worker.error_occurred.connect(self.on_error_occurred)
        self.worker.stats_updated.connect(self.on_stats_updated)

        # Setup UI Refresh Timer
        self.ui_timer = QTimer(self)
        self.refresh_rate_ms = config.get("ui", {}).get("refresh_rate_ms", 50)
        self.ui_timer.timeout.connect(self.update_ui)

        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # 1. Header Area
        header_layout = QHBoxLayout()
        title_layout = QVBoxLayout()
        title_label = QLabel("FaWave Force Acquisition System")
        title_label.setProperty("class", "header-title")
        subtitle_label = QLabel("Four-channel Ethernet-based force sensing platform")
        subtitle_label.setProperty("class", "header-subtitle")
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)

        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #6B7280;")

        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)
        main_layout.addLayout(header_layout)

        # Main Content Layout (Left Panel + Right Plot Area)
        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout, stretch=1)

        # 2. Left Control Panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        content_layout.addWidget(left_panel, stretch=1)

        # Connection Settings Group
        conn_group = QGroupBox("Connection Settings")
        conn_layout = QGridLayout(conn_group)

        conn_layout.addWidget(QLabel("IP Address:"), 0, 0)
        self.ip_input = QLineEdit(self.config.get("device_ip", "192.168.1.82"))
        conn_layout.addWidget(self.ip_input, 0, 1)

        conn_layout.addWidget(QLabel("Port:"), 1, 0)
        self.port_input = QLineEdit(str(self.config.get("device_port", 16006)))
        conn_layout.addWidget(self.port_input, 1, 1)

        conn_layout.addWidget(QLabel("Mode:"), 2, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["TCP", "UDP", "Mock"])
        self.mode_combo.setCurrentText(self.config.get("communication_mode", "TCP"))
        conn_layout.addWidget(self.mode_combo, 2, 1)

        left_layout.addWidget(conn_group)

        # Data Recording Group
        record_group = QGroupBox("Data Recording")
        record_layout = QGridLayout(record_group)

        self.record_checkbox = QCheckBox("Enable Local Storage")
        record_layout.addWidget(self.record_checkbox, 0, 0, 1, 2)

        record_layout.addWidget(QLabel("Format:"), 1, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["CSV", "XLSX"])
        record_layout.addWidget(self.format_combo, 1, 1)

        self.path_btn = QPushButton("Select Save Path")
        self.path_btn.clicked.connect(self.select_save_path)
        record_layout.addWidget(self.path_btn, 2, 0, 1, 2)

        # Default save path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.save_path = os.path.join(os.getcwd(), "Data", f"FaWave_Data_{timestamp}.csv")
        self.path_label = QLabel(self.save_path)
        self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet("font-size: 11px; color: #6B7280;")
        record_layout.addWidget(self.path_label, 3, 0, 1, 2)

        left_layout.addWidget(record_group)

        # Controls Group
        control_group = QGroupBox("Controls")
        control_layout = QVBoxLayout(control_group)

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setObjectName("btnConnect")
        self.btn_connect.clicked.connect(self.toggle_connection)

        self.btn_clear = QPushButton("Clear Plot")
        self.btn_clear.clicked.connect(self.clear_plot)

        self.btn_autoscale = QPushButton("Auto Scale")
        self.btn_autoscale.clicked.connect(self.auto_scale)

        control_layout.addWidget(self.btn_connect)
        control_layout.addWidget(self.btn_clear)
        control_layout.addWidget(self.btn_autoscale)

        left_layout.addWidget(control_group)

        # Channel Visibility
        vis_group = QGroupBox("Channel Visibility")
        vis_layout = QVBoxLayout(vis_group)
        self.chk_ch1 = QCheckBox("CH1 (Blue)"); self.chk_ch1.setChecked(True)
        self.chk_ch2 = QCheckBox("CH2 (Orange)"); self.chk_ch2.setChecked(True)
        self.chk_ch3 = QCheckBox("CH3 (Green)"); self.chk_ch3.setChecked(True)
        self.chk_ch4 = QCheckBox("CH4 (Purple)"); self.chk_ch4.setChecked(True)

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

        # 3. Right Area (Plot + Value Cards)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        content_layout.addWidget(right_panel, stretch=3)

        # Value Cards Layout
        cards_layout = QHBoxLayout()

        self.val_ch1 = QLabel("0.00 mV")
        self.val_ch1.setProperty("class", "channel-value")
        self.val_ch1.setObjectName("valCh1")
        self.val_ch1.setAlignment(Qt.AlignCenter)

        self.val_ch2 = QLabel("0.00 mV")
        self.val_ch2.setProperty("class", "channel-value")
        self.val_ch2.setObjectName("valCh2")
        self.val_ch2.setAlignment(Qt.AlignCenter)

        self.val_ch3 = QLabel("0.00 mV")
        self.val_ch3.setProperty("class", "channel-value")
        self.val_ch3.setObjectName("valCh3")
        self.val_ch3.setAlignment(Qt.AlignCenter)

        self.val_ch4 = QLabel("0.00 mV")
        self.val_ch4.setProperty("class", "channel-value")
        self.val_ch4.setObjectName("valCh4")
        self.val_ch4.setAlignment(Qt.AlignCenter)

        cards_layout.addWidget(self.val_ch1)
        cards_layout.addWidget(self.val_ch2)
        cards_layout.addWidget(self.val_ch3)
        cards_layout.addWidget(self.val_ch4)

        right_layout.addLayout(cards_layout)

        # Plot Area
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', 'Voltage', units='mV')
        self.plot_widget.setLabel('bottom', 'Relative Time', units='s')
        self.plot_widget.addLegend()

        # Colors: Blue, Orange, Green, Purple
        self.curve_ch1 = self.plot_widget.plot(pen=pg.mkPen('#2563EB', width=2), name='CH1')
        self.curve_ch2 = self.plot_widget.plot(pen=pg.mkPen('#F97316', width=2), name='CH2')
        self.curve_ch3 = self.plot_widget.plot(pen=pg.mkPen('#10B981', width=2), name='CH3')
        self.curve_ch4 = self.plot_widget.plot(pen=pg.mkPen('#8B5CF6', width=2), name='CH4')

        right_layout.addWidget(self.plot_widget)

        # 4. Status Bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.stats_label = QLabel("Frames: 0 | Errors: 0")
        self.statusBar.addPermanentWidget(self.stats_label)

    def apply_styles(self):
        try:
            qss_path = os.path.join(os.path.dirname(__file__), 'style.qss')
            with open(qss_path, 'r') as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Failed to load stylesheet: {e}")

    def select_save_path(self):
        fmt = self.format_combo.currentText().lower()
        default_dir = os.path.join(os.getcwd(), "Data")
        os.makedirs(default_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"FaWave_Data_{timestamp}.{fmt}"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Select Save Path", os.path.join(default_dir, default_name),
            f"Data Files (*.{fmt})"
        )
        if file_path:
            self.save_path = file_path
            self.path_label.setText(file_path)

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

    def auto_scale(self):
        self.plot_widget.autoRange()

    def toggle_connection(self):
        if not self.worker.is_running:
            # Connect
            ip = self.ip_input.text()
            try:
                port = int(self.port_input.text())
            except ValueError:
                QMessageBox.warning(self, "Input Error", "Port must be an integer.")
                return

            mode = self.mode_combo.currentText()

            # Setup recording
            if self.record_checkbox.isChecked():
                # Ensure the extension matches the selected format
                fmt = self.format_combo.currentText()
                if not self.save_path.lower().endswith(f".{fmt.lower()}"):
                    self.save_path = f"{os.path.splitext(self.save_path)[0]}.{fmt.lower()}"
                    self.path_label.setText(self.save_path)

                try:
                    self.data_recorder.start_recording(self.save_path, format=fmt)
                except Exception as e:
                    QMessageBox.warning(self, "Recording Error", f"Failed to start recording:\n{e}")
                    return

            self.worker.set_connection_params(mode, ip, port)
            self.worker.start()

            # Start UI timer
            self.ui_timer.start(self.refresh_rate_ms)

            self.btn_connect.setText("Disconnect")
            self.btn_connect.setObjectName("btnDisconnect")
            self.btn_connect.setStyleSheet("/* Trigger pseudo state update */")
            self.apply_styles() # Reapply to update button color

            # Disable inputs
            self.ip_input.setEnabled(False)
            self.port_input.setEnabled(False)
            self.mode_combo.setEnabled(False)
            self.record_checkbox.setEnabled(False)

        else:
            # Disconnect
            self.worker.stop()
            self.data_recorder.stop_recording()
            self.ui_timer.stop()

            self.btn_connect.setText("Connect")
            self.btn_connect.setObjectName("btnConnect")
            self.apply_styles()

            # Enable inputs
            self.ip_input.setEnabled(True)
            self.port_input.setEnabled(True)
            self.mode_combo.setEnabled(True)
            self.record_checkbox.setEnabled(True)

    def on_connection_status_changed(self, status):
        self.statusBar.showMessage(f"Connection Status: {status}", 5000)
        self.status_label.setText(f"Status: {status}")
        if status == "Connected":
            self.status_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #16A34A;")
        elif status == "Disconnected":
            self.status_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #6B7280;")
        else:
            self.status_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #DC2626;")

            # If error occurred, auto disconnect UI state
            if self.worker.is_running:
                 self.toggle_connection()

    def on_error_occurred(self, err_msg):
        self.statusBar.showMessage(f"Error: {err_msg}", 5000)

    def on_stats_updated(self, recv, errors):
        self.stats_label.setText(f"Frames: {recv} | Errors: {errors}")

    def update_ui(self):
        """Called by QTimer to update plots and values from buffer."""
        t_data, idx_data, ch1, ch2, ch3, ch4 = self.data_buffer.get_data()

        if not t_data:
            return

        # Update plots
        self.curve_ch1.setData(t_data, ch1)
        self.curve_ch2.setData(t_data, ch2)
        self.curve_ch3.setData(t_data, ch3)
        self.curve_ch4.setData(t_data, ch4)

        # Update latest values
        self.val_ch1.setText(f"{ch1[-1]:.2f} mV")
        self.val_ch2.setText(f"{ch2[-1]:.2f} mV")
        self.val_ch3.setText(f"{ch3[-1]:.2f} mV")
        self.val_ch4.setText(f"{ch4[-1]:.2f} mV")

    def closeEvent(self, event):
        if self.worker.is_running:
            self.worker.stop()
        self.data_recorder.stop_recording()
        event.accept()
