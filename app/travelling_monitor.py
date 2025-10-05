import logging

from app.api.patlite_api import (
    PatliteAPI,
    ControlOptions,
    LedOptions,
    LightPattern,
    NotifySound,
)
from app.model.vrchat import UserInfo


class TravelingMonitor:
    def __init__(self, pl_api: PatliteAPI, max_attempts: int = 3):
        self.pl_api = pl_api
        self.traveling_count = 0
        self.max_attempts = max_attempts

    def check(self, user_info: UserInfo) -> bool:
        if user_info.traveling_to_location is not None:
            self.traveling_count += 1
            logging.warning(f"⚠️ User is traveling... attempt {self.traveling_count}")

            if self.traveling_count >= self.max_attempts:
                logging.error("❌ Traveling timeout exceeded.")
                self._notify()
                return True
        else:
            self.traveling_count = 0

        return False

    def _notify(self):
        self.pl_api.control(
            ControlOptions(
                led=LedOptions(red=LightPattern.BLINK1),
                speech="無限ジョインを検知しました、注意してください",
                notify=NotifySound.ALARM_1,
            )
        )
