import os
import csv
import threading
import queue
import time
import pandas as pd

class AsyncDataRecorder:
    def __init__(self):
        self.file_path = None
        self.file_format = None
        self.is_recording = False

        self.queue = queue.Queue()
        self._writer_thread = None

        self._csv_file = None
        self._csv_writer = None
        self.csv_headers = [
            "AbsoluteTime", "RelativeTime_s", "SampleIndex",
            "AcquisitionMode",
            "CH1_V", "CH2_V", "CH3_V", "CH4_V",
            "Fx_N", "Fy_N", "Fz_N",
            "FxRaw_N", "FyRaw_N", "FzRaw_N",
            "FxFiltered_N", "FyFiltered_N", "FzFiltered_N",
            "D1_V", "D2_V", "D3_V", "D4_V",
            "Baseline1_V", "Baseline2_V", "Baseline3_V", "Baseline4_V",
            "DecoderStatus", "DecoderValid", "Algorithm", "InputUnit", "InputScaleToV",
            "CalibrationName", "CalibrationVersion", "CalibrationDate",
            "Alarm1", "Alarm2", "Alarm3",
            "RawHex", "TrailerHex", "Status"
        ]

        self.queued_count = 0
        self.saved_count = 0

    def start_recording(self, file_path, format="CSV"):
        if self.is_recording:
            return

        self.file_path = file_path
        self.file_format = format.upper()
        self.is_recording = True

        self.queued_count = 0
        self.saved_count = 0
        self.queue = queue.Queue()

        os.makedirs(os.path.dirname(os.path.abspath(self.file_path)), exist_ok=True)

        if self.file_format == "CSV":
            self._csv_file = open(self.file_path, mode='w', newline='', encoding='utf-8')
            self._csv_writer = csv.writer(self._csv_file)
            self._csv_writer.writerow(self.csv_headers)
        elif self.file_format == "XLSX":
            # For XLSX we write to a temporary CSV during acquisition to prevent blocking
            self._tmp_path = self.file_path + ".tmp.csv"
            self._csv_file = open(self._tmp_path, mode='w', newline='', encoding='utf-8')
            self._csv_writer = csv.writer(self._csv_file)
            self._csv_writer.writerow(self.csv_headers)

        self._writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self._writer_thread.start()

    def stop_recording(self):
        if not self.is_recording:
            return

        self.is_recording = False

        if self._writer_thread and self._writer_thread.is_alive():
            self._writer_thread.join(timeout=3.0)

        if self._csv_file:
            self._csv_file.flush()
            self._csv_file.close()
            self._csv_file = None
            self._csv_writer = None

        if self.file_format == "XLSX":
            self._convert_temp_csv_to_xlsx()

    def record_point(self, abs_time, rel_time, sample_idx, data_dict, raw_hex="", status="OK", trailer_hex=""):
        if not self.is_recording:
            return

        alarms = data_dict.get("alarms", [
            {"level": "未配置"}, {"level": "未配置"}, {"level": "未配置"}
        ])
        alarm1 = alarms[0]["level"] if len(alarms) > 0 else "未配置"
        alarm2 = alarms[1]["level"] if len(alarms) > 1 else "未配置"
        alarm3 = alarms[2]["level"] if len(alarms) > 2 else "未配置"

        d = data_dict.get("d", [0.0]*4)
        baseline = data_dict.get("baseline", [0.0]*4)

        row = [
            abs_time,
            f"{rel_time:.3f}",
            sample_idx,
            data_dict.get("acquisition_mode", "未知"),
            data_dict.get("ch1", 0.0),
            data_dict.get("ch2", 0.0),
            data_dict.get("ch3", 0.0),
            data_dict.get("ch4", 0.0),
            data_dict.get("fx", 0.0),
            data_dict.get("fy", 0.0),
            data_dict.get("fz", 0.0),
            data_dict.get("fx_raw", 0.0),
            data_dict.get("fy_raw", 0.0),
            data_dict.get("fz_raw", 0.0),
            data_dict.get("fx_filtered", 0.0),
            data_dict.get("fy_filtered", 0.0),
            data_dict.get("fz_filtered", 0.0),
            d[0], d[1], d[2], d[3],
            baseline[0], baseline[1], baseline[2], baseline[3],
            data_dict.get("decoder_status", "未启用"),
            data_dict.get("decoder_valid", False),
            data_dict.get("Algorithm", "未配置"),
            data_dict.get("input_unit", "V"),
            data_dict.get("input_scale_to_v", 1.0),
            data_dict.get("calibration_name", "未配置"),
            data_dict.get("calibration_version", "未知"),
            data_dict.get("calibration_date", "未配置"),
            alarm1,
            alarm2,
            alarm3,
            raw_hex,
            trailer_hex,
            status
        ]

        self.queue.put(row)
        self.queued_count += 1

    def _writer_loop(self):
        batch = []
        batch_size = 100
        last_flush_time = time.time()
        flush_interval = 0.5

        while self.is_recording or not self.queue.empty():
            try:
                row = self.queue.get(timeout=0.1)
                batch.append(row)
                self.queued_count -= 1
            except queue.Empty:
                pass

            current_time = time.time()
            # If batch gets too big, or it's been long enough AND we have items, flush.
            # On shutdown (not is_recording), also flush remaining items.
            if len(batch) >= batch_size or (batch and (current_time - last_flush_time) >= flush_interval) or (not self.is_recording and batch):
                if self._csv_writer:
                    self._csv_writer.writerows(batch)
                    self._csv_file.flush()
                    self.saved_count += len(batch)
                    batch.clear()
                last_flush_time = current_time

    def _convert_temp_csv_to_xlsx(self):
        if not hasattr(self, '_tmp_path') or not os.path.exists(self._tmp_path):
            return

        try:
            df = pd.read_csv(self._tmp_path)
            df.to_excel(self.file_path, index=False)
            os.remove(self._tmp_path)
        except Exception as e:
            print(f"Failed to convert temp CSV to XLSX: {e}")

    def get_status(self):
        return {
            "queued": self.queued_count,
            "saved": self.saved_count
        }
