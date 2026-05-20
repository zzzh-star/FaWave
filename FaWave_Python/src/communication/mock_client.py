import struct
import math
import time
from .base_client import BaseClient

class MockClient(BaseClient):
    def __init__(self, config):
        self.config = config
        self._connected = False
        self.start_time = 0
        self.frame_length = config.get("frame_length", 35)

        protocol_config = config.get("protocol", {})
        self.header_hex = protocol_config.get("header_hex", "5AA5")
        self.float_endian = protocol_config.get("float_endian", "<")
        self.data_offset = protocol_config.get("data_offset", 5)
        self.trailer_offset = protocol_config.get("trailer_offset", 21)

        self.header_bytes = bytes.fromhex(self.header_hex)

    def connect(self):
        self._connected = True
        self.start_time = time.time()

    def disconnect(self):
        self._connected = False

    def send(self, data: bytes):
        if not self._connected:
            raise ConnectionError("Mock Client is not connected.")
        # Mock client just ignores the request data
        pass

    def receive(self, length: int) -> bytes:
        if not self._connected:
            raise ConnectionError("Mock Client is not connected.")

        t = time.time() - self.start_time

        # Generate 4 mock float values (sine wave with different phases)
        ch1 = math.sin(2 * math.pi * 1.0 * t) * 1000 + 500  # 1 Hz
        ch2 = math.cos(2 * math.pi * 2.0 * t) * 1000 + 1000 # 2 Hz
        ch3 = math.sin(2 * math.pi * 0.5 * t) * 500 + 200   # 0.5 Hz
        ch4 = math.cos(2 * math.pi * 0.2 * t) * 800 - 300   # 0.2 Hz

        values = [ch1, ch2, ch3, ch4]

        # Construct the raw frame
        # 1. Start with zeroes
        frame = bytearray(self.frame_length)

        # 2. Write header and metadata (e.g., 81 02 1D)
        for i, b in enumerate(self.header_bytes):
            if i < len(frame):
                frame[i] = b

        if len(frame) >= 5:
            frame[2] = 0x81
            frame[3] = 0x02
            frame[4] = 0x1D

        # 3. Write float values
        offset = self.data_offset
        fmt = self.float_endian + 'f'
        for val in values:
            b_val = struct.pack(fmt, val)
            for i, b in enumerate(b_val):
                if offset + i < len(frame):
                    frame[offset + i] = b
            offset += 4

        # 4. Write mock trailer
        trailer_mock = b'\xAA' * (self.frame_length - self.trailer_offset)
        for i, b in enumerate(trailer_mock):
            if self.trailer_offset + i < len(frame):
                frame[self.trailer_offset + i] = b

        return bytes(frame)

    def is_connected(self) -> bool:
        return self._connected
