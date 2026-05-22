import os
import csv
from datetime import datetime
import pandas as pd

class DataRecorder:
    def __init__(self):
        self.file_path = None
        self.file_format = None # "CSV" or "XLSX"
        self.is_recording = False

        self._csv_file = None
        self._csv_writer = None

        self._buffer = []
        self._batch_size = 100 # for XLSX

    def start_recording(self, file_path, format="CSV"):
        self.file_path = file_path
        self.file_format = format.upper()
        self.is_recording = True
        self._buffer = []

        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(self.file_path)), exist_ok=True)

        headers = [
            "AbsoluteTime", "RelativeTime_s", "SampleIndex",
            "AcquisitionMode",
            "CH1_V", "CH2_V", "CH3_V", "CH4_V",
            "Fx_N", "Fy_N", "Fz_N",
            "FxRaw_N", "FyRaw_N", "FzRaw_N",
            "FxFiltered_N", "FyFiltered_N", "FzFiltered_N",
            "D1_V", "D2_V", "D3_V", "D4_V",
            "Baseline1_V", "Baseline2_V", "Baseline3_V", "Baseline4_V",
            "DecoderStatus", "DecoderValid", "DecoderBackend", "DecoderValidated", "DecoderDllPath", "InputUnit", "InputScaleToV",
            "CalibrationName", "CalibrationVersion", "CalibrationDate",
            "Alarm1", "Alarm2", "Alarm3",
            "RawHex", "TrailerHex", "Status"
        ]

        if self.file_format == "CSV":
            self._csv_file = open(self.file_path, mode='w', newline='', encoding='utf-8')
            self._csv_writer = csv.writer(self._csv_file)
            self._csv_writer.writerow(headers)
        elif self.file_format == "XLSX":
            # Just create an empty dataframe to initialize file
            df = pd.DataFrame(columns=headers)
            df.to_excel(self.file_path, index=False)

    def stop_recording(self):
        self.is_recording = False

        if self.file_format == "CSV" and self._csv_file:
            self._csv_file.flush()
            self._csv_file.close()
            self._csv_file = None
            self._csv_writer = None
        elif self.file_format == "XLSX" and len(self._buffer) > 0:
            self._flush_xlsx_buffer()

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
            data_dict.get("decoder_backend", "未配置"),
            data_dict.get("decoder_validated", "未验证"),
            data_dict.get("c_dll_path", "未加载"),
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

        if self.file_format == "CSV":
            if self._csv_writer:
                self._csv_writer.writerow(row)
        elif self.file_format == "XLSX":
            self._buffer.append(row)
            if len(self._buffer) >= self._batch_size:
                self._flush_xlsx_buffer()

    def _flush_xlsx_buffer(self):
        if not self._buffer:
            return

        headers = [
            "AbsoluteTime", "RelativeTime_s", "SampleIndex",
            "AcquisitionMode",
            "CH1_V", "CH2_V", "CH3_V", "CH4_V",
            "Fx_N", "Fy_N", "Fz_N",
            "FxRaw_N", "FyRaw_N", "FzRaw_N",
            "FxFiltered_N", "FyFiltered_N", "FzFiltered_N",
            "D1_V", "D2_V", "D3_V", "D4_V",
            "Baseline1_V", "Baseline2_V", "Baseline3_V", "Baseline4_V",
            "DecoderStatus", "DecoderValid", "DecoderBackend", "DecoderValidated", "DecoderDllPath", "InputUnit", "InputScaleToV",
            "CalibrationName", "CalibrationVersion", "CalibrationDate",
            "Alarm1", "Alarm2", "Alarm3",
            "RawHex", "TrailerHex", "Status"
        ]
        new_df = pd.DataFrame(self._buffer, columns=headers)

        try:
            from openpyxl import load_workbook
            from openpyxl.utils.dataframe import dataframe_to_rows

            if os.path.exists(self.file_path):
                # Append without reading whole file
                wb = load_workbook(self.file_path)
                ws = wb.active
                for r in dataframe_to_rows(new_df, index=False, header=False):
                    ws.append(r)
                wb.save(self.file_path)
            else:
                new_df.to_excel(self.file_path, index=False)

        except Exception as e:
            print(f"Failed to flush XLSX buffer: {e}")

        self._buffer = []
