from enum import IntEnum
from typing import Optional

from app.http import HttpClient


class LightPattern(IntEnum):
    OFF = 0  # 消灯
    ON = 1  # 点灯
    BLINK1 = 2  # 点滅パターン1
    BLINK2 = 3  # 点滅パターン2
    BLINK3 = 4  # 点滅パターン3
    BLINK4 = 5  # 点滅パターン4
    KEEP = 9  # 変化なし


class BuzzerPattern(IntEnum):
    SILENT = 0  # 非吹鳴
    PATTERN1 = 1  # 吹鳴パターン1
    PATTERN2 = 2  # 吹鳴パターン2
    PATTERN3 = 3  # 吹鳴パターン3
    PATTERN4 = 4  # 吹鳴パターン4
    PATTERN5 = 5  # 吹鳴パターン5
    KEEP = 9  # 変化なし


class PatliteAPI:
    def __init__(self, http: HttpClient, ip_address: Optional[str] = None) -> None:
        self.http = http
        self.ip_address = ip_address

    def control(
        self,
        r: Optional[LightPattern] = None,
        y: Optional[LightPattern] = None,
        g: Optional[LightPattern] = None,
        b: Optional[LightPattern] = None,
        c: Optional[LightPattern] = None,
        bz: Optional[BuzzerPattern] = None,
    ) -> None:
        if self.ip_address is None:
            return

        pattern = self._build_pattern(r, y, g, b, c, bz)
        resp = self.http.request(
            "GET",
            f"http://{self.ip_address}/api/control",
            params={"alert": pattern},
            verify=False,
        )
        resp.raise_for_status()

    @staticmethod
    def _build_pattern(
        r: Optional[LightPattern],
        y: Optional[LightPattern],
        g: Optional[LightPattern],
        b: Optional[LightPattern],
        c: Optional[LightPattern],
        bz: Optional[BuzzerPattern],
    ) -> str:
        vals = [
            (r if r is not None else LightPattern.KEEP),
            (y if y is not None else LightPattern.KEEP),
            (g if g is not None else LightPattern.KEEP),
            (b if b is not None else LightPattern.KEEP),
            (c if c is not None else LightPattern.KEEP),
            (bz if bz is not None else BuzzerPattern.KEEP),
        ]
        return "".join(str(int(v)) for v in vals)
