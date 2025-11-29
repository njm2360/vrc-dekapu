from app.service.osc_service import OSCService

class OSCController:
    def __init__(self):
        self.osc = OSCService()

    def lock(self, ip: str, port: int):
        self.osc.send_use_left_lock(ip, port)

    def release(self, ip: str, port: int):
        self.osc.send_use_left_release(ip, port)
