from dataclasses import dataclass
from enum import IntEnum, StrEnum
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


class VoiceType(StrEnum):
    MALE = "male"
    FEMALE = "female"


@dataclass(frozen=True)
class LedOptions:
    red: Optional[LightPattern] = None
    yellow: Optional[LightPattern] = None
    green: Optional[LightPattern] = None
    blue: Optional[LightPattern] = None
    white: Optional[LightPattern] = None

    def to_pattern(self) -> str:
        vals = [
            (self.red if self.red is not None else LightPattern.KEEP),
            (self.yellow if self.yellow is not None else LightPattern.KEEP),
            (self.green if self.green is not None else LightPattern.KEEP),
            (self.blue if self.blue is not None else LightPattern.KEEP),
            (self.white if self.white is not None else LightPattern.KEEP),
        ]

        return "".join(str(int(v)) for v in vals)


@dataclass(frozen=True)
class ControlOptions:
    led: Optional[LedOptions] = None
    buzzer: Optional[BuzzerPattern] = None
    speech: Optional[str] = None
    sound: Optional[int] = None
    repeat: Optional[int] = None
    restore: Optional[int] = None
    stop: bool = False
    clear: bool = False
    voice: VoiceType = VoiceType.FEMALE
    speed: Optional[int] = None
    tone: Optional[int] = None
    notify: Optional[int] = None
    notify_tail: Optional[int] = None

    def __post_init__(self):
        if self.sound is not None and not (1 <= self.sound <= 71):
            raise ValueError(f"sound must be 1–71, got {self.sound}")
        if self.speech is not None and len(self.speech) > 400:
            raise ValueError(f"speech must be <=400 characters, got {len(self.speech)}")
        if self.repeat is not None:
            if not (0 <= self.repeat <= 254 or self.repeat == 255):
                raise ValueError(f"repeat must be 0–254 or 255, got {self.repeat}")
            if self.sound is None and self.speech is None:
                raise ValueError("repeat requires sound or speech to be set")
        if self.restore is not None and not (0 <= self.restore <= 99):
            raise ValueError(f"restore must be 0–99, got {self.restore}")
        if self.voice is not None and self.speech is None:
            raise ValueError("voice requires speech to be set")
        if self.speed is not None:
            if not (-5 <= self.speed <= 5):
                raise ValueError(f"speed must be -5..5, got {self.speed}")
            if self.speech is None:
                raise ValueError("speed requires speech to be set")
        if self.tone is not None:
            if not (-5 <= self.tone <= 5):
                raise ValueError(f"tone must be -5..5, got {self.tone}")
            if self.speech is None:
                raise ValueError("tone requires speech to be set")
        if self.notify is not None:
            if not (0 <= self.notify <= 10):
                raise ValueError(f"notify must be 0–10, got {self.notify}")
            if self.speech is None:
                raise ValueError("notify requires speech to be set")
        if self.notify_tail is not None:
            if not (0 <= self.notify_tail <= 10):
                raise ValueError(f"notify_tail must be 0–10, got {self.notify_tail}")
            if self.speech is None:
                raise ValueError("notify_tail requires speech to be set")

    def to_params(self) -> dict:
        params = {}

        if self.led:
            params["led"] = self.led.to_pattern()
        if self.buzzer:
            params["b-pat"] = str(self.buzzer)
        if self.speech:
            params["speech"] = self.speech
        if self.voice:
            params["voice"] = str(self.voice)
        if self.sound is not None:
            params["sound"] = self.sound
        if self.repeat is not None:
            params["repeat"] = self.repeat
        if self.restore is not None:
            params["restore"] = self.restore
        if self.stop:
            params["stop"] = 1
        if self.clear:
            params["clear"] = 1
        if self.speed is not None:
            params["speed"] = self.speed
        if self.tone is not None:
            params["tone"] = self.tone
        if self.notify is not None:
            params["notify"] = self.notify
        if self.notify_tail is not None:
            params["notifyTail"] = self.notify_tail

        return params


class PatliteAPI:
    def __init__(self, http: HttpClient, ip_address: Optional[str] = None) -> None:
        self.http = http
        self.ip_address = ip_address

    def control(self, options: ControlOptions) -> None:
        if self.ip_address is None:
            return

        params = options.to_params()

        resp = self.http.request(
            "GET",
            f"http://{self.ip_address}/api/control",
            params=params,
            verify=False,
        )
        resp.raise_for_status()
