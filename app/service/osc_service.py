import time
from pythonosc import udp_client


class OSCService:
    USELEFT_ADDR = "/input/UseLeft"

    def _client(self, ip: str, port: int):
        return udp_client.SimpleUDPClient(ip, port)

    def send(self, ip: str, port: int, address: str, value):
        client = self._client(ip, port)
        client.send_message(address, value)

    def send_use_left_lock(self, ip: str, port: int):
        client = self._client(ip, port)
        client.send_message(self.USELEFT_ADDR, 0)
        time.sleep(0.5)
        client.send_message(self.USELEFT_ADDR, 1)

    def send_use_left_release(self, ip: str, port: int):
        self.send(ip, port, self.USELEFT_ADDR, 0)
