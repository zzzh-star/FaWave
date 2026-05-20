import time
from datetime import datetime
from PySide6.QtCore import QThread, Signal
from ..communication.tcp_client import TCPClient
from ..communication.udp_client import UDPClient
from ..communication.mock_client import MockClient
from ..protocol.fawave_protocol import FaWaveProtocol, ProtocolError

class AcquisitionWorker(QThread):
    # Signals for UI updates
    data_received = Signal(float, int, dict) # rel_time, sample_index, data_dict
    error_occurred = Signal(str)
    connection_status_changed = Signal(str) # "Connected", "Disconnected", "Error"
    stats_updated = Signal(int, int) # recv_frames, error_frames

    def __init__(self, config, data_buffer, data_recorder):
        super().__init__()
        self.config = config
        self.data_buffer = data_buffer
        self.data_recorder = data_recorder
        self.protocol = FaWaveProtocol(self.config)

        self.client = None
        self.is_running = False

        self.request_interval = self.config.get("request_interval_ms", 20) / 1000.0
        self.frame_length = self.config.get("frame_length", 29)

        self.recv_frames = 0
        self.error_frames = 0
        self.consecutive_errors = 0
        self.max_consecutive_errors = 20
        self.sample_index = 0
        self.start_time = 0

    def set_connection_params(self, mode, ip, port, local_ip=""):
        self.mode = mode
        if mode == "TCP":
            self.client = TCPClient(ip, port)
        elif mode == "UDP":
            self.client = UDPClient(ip, port, local_ip)
        elif mode == "Mock":
            self.client = MockClient(self.config)
        else:
            raise ValueError(f"Unknown communication mode: {mode}")

    def run(self):
        self.is_running = True
        self.recv_frames = 0
        self.error_frames = 0
        self.consecutive_errors = 0
        self.sample_index = 0

        try:
            self.client.connect()
            self.connection_status_changed.emit("Connected")
            self.start_time = time.time()
        except Exception as e:
            self.error_occurred.emit(f"Connection failed: {str(e)}")
            self.connection_status_changed.emit("Error")
            self.is_running = False
            return

        request_frame = self.protocol.build_request_frame()

        while self.is_running:
            loop_start = time.time()

            try:
                # 1. Send request
                self.client.send(request_frame)

                # 2. Receive response
                response_frame = self.client.receive(self.frame_length)

                # 3. Parse response
                data_dict = self.protocol.parse_response_frame(response_frame)

                # Reset error counter on success
                self.consecutive_errors = 0
                self.recv_frames += 1
                self.sample_index += 1

                abs_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                rel_time = time.time() - self.start_time

                # 4. Add to buffer
                self.data_buffer.add_point(
                    rel_time,
                    self.sample_index,
                    data_dict.get("ch1", 0.0),
                    data_dict.get("ch2", 0.0),
                    data_dict.get("ch3", 0.0),
                    data_dict.get("ch4", 0.0)
                )

                # 5. Record if enabled
                self.data_recorder.record_point(
                    abs_time, rel_time, self.sample_index, data_dict, data_dict.get("raw_hex", ""), "OK"
                )

                # Emit data for the UI (UI can choose to use this directly or read from buffer via QTimer)
                self.data_received.emit(rel_time, self.sample_index, data_dict)
                self.stats_updated.emit(self.recv_frames, self.error_frames)

            except ProtocolError as e:
                self.error_frames += 1
                self.consecutive_errors += 1
                self.error_occurred.emit(f"Protocol Error: {str(e)}")

                # Still record the error frame if recording
                if hasattr(self, 'data_recorder') and self.data_recorder.is_recording:
                    abs_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    rel_time = time.time() - self.start_time
                    self.data_recorder.record_point(abs_time, rel_time, self.sample_index, {}, "", "ProtocolError")

                if self.consecutive_errors >= self.max_consecutive_errors:
                    self.error_occurred.emit("Too many consecutive protocol errors! Disconnecting.")
                    self.connection_status_changed.emit("Error")
                    break

            except Exception as e:
                self.error_occurred.emit(f"Communication Error: {str(e)}")
                self.connection_status_changed.emit("Error")
                break

            # 6. Wait for next interval
            elapsed = time.time() - loop_start
            sleep_time = self.request_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        # Cleanup
        if self.client:
            try:
                self.client.disconnect()
            except:
                pass

        self.connection_status_changed.emit("Disconnected")

    def stop(self):
        self.is_running = False
        self.wait() # wait for thread to finish safely
