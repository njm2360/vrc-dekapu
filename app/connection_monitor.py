import logging

from app.api.patlite_api import (
    ControlOptions,
    LedOptions,
    LightPattern,
    NotifySound,
    PatliteAPI,
)
from app.model.vrchat import UserInfo, UserState


class ConnectionMonitor:
    def __init__(self, pl_api: PatliteAPI, max_attempts: int = 3):
        self.pl_api = pl_api
        self.max_attempts = max_attempts
        self._lost_count = 0

    def check(self, user_info: UserInfo) -> bool:
        if user_info.state != UserState.ONLINE:
            self._lost_count += 1
            logging.warning(f"⚠️ User is offline... attempt {self._lost_count}")

            if self._lost_count == 1:
                self._notify()

            if self._lost_count == self.max_attempts:
                logging.error("❌ Lost connection persists.")
                return True
            return False

        else:
            if self._lost_count > 0:
                logging.info("✅ Connection restored.")
            self._lost_count = 0
            return False

    def _notify(self):
        self.pl_api.control(
            ControlOptions(
                led=LedOptions(red=LightPattern.BLINK1),
                speech="ロスコネクションを検知しました、注意してください",
                repeat=255,
                notify=NotifySound.ALARM_1,
            )
        )
