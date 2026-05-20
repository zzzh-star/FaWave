import socket
from .base_client import BaseClient

class TCPClient(BaseClient):
    def __init__(self, ip, port, timeout=2.0):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.socket = None
        self._connected = False

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout)
        self.socket.connect((self.ip, self.port))
        self._connected = True

    def disconnect(self):
        if self.socket:
            self.socket.close()
            self.socket = None
        self._connected = False

    def send(self, data: bytes):
        if not self._connected or not self.socket:
            raise ConnectionError("TCP Client is not connected.")
        self.socket.sendall(data)

    def receive(self, length: int) -> bytes:
        if not self._connected or not self.socket:
            raise ConnectionError("TCP Client is not connected.")

        # Read exactly `length` bytes if possible
        chunks = []
        bytes_recd = 0
        while bytes_recd < length:
            chunk = self.socket.recv(length - bytes_recd)
            if chunk == b'':
                raise ConnectionError("Socket connection broken")
            chunks.append(chunk)
            bytes_recd += len(chunk)
        return b''.join(chunks)

    def is_connected(self) -> bool:
        return self._connected
