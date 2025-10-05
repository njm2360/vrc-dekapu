import logging
from typing import Optional
from datetime import datetime, timedelta

from app.model.vrchat import InstanceInfo, UserInfo
from app.api.patlite_api import (
    ControlOptions,
    LedOptions,
    LightPattern,
    NotifySound,
    PatliteAPI,
)


class PopulationMonitor:
    def __init__(
        self, pl_api: PatliteAPI, threshold: int = 8, notify_interval: int = 10
    ):
        self.pl_api = pl_api
        self.threshold = threshold
        self.notify_interval = timedelta(minutes=notify_interval)
        self._was_in_most_populated: Optional[bool] = True
        self._last_notify_time: Optional[datetime] = None

    def evaluate(self, instances: list[InstanceInfo], user: UserInfo) -> bool:
        # 現在のインスタンスが最も人数が多いインスタンスかどうか判定
        if not instances:
            logging.warning("⚠️ No populated instances found to compare")
            return True

        joinable_instances = [i for i in instances if i.closed_at is None]
        if not joinable_instances:
            logging.warning("⚠️ All instances are closed.")
            return True

        max_user_count = max(i.user_count for i in joinable_instances)
        current_instance = next(
            (i for i in instances if i.location == user.location),
            None,
        )

        # グルパブ外にいる場合
        if current_instance is None:
            logging.error("❌ User is not in any group instance")
            return self._handle_not_in_most_populated()

        diff = max_user_count - current_instance.user_count

        if diff <= 0:
            logging.info("✅ This instance is most populated one")
            return self._handle_in_most_populated()

        elif diff < self.threshold:
            logging.warning(f"⚠️ Nearly most populated (diff={diff})")
            return self._handle_in_most_populated()

        else:
            logging.error(
                f"❌ This instance is {diff} users behind the most populated one"
            )
            return self._handle_not_in_most_populated()

    def _handle_in_most_populated(self) -> bool:
        self._was_in_most_populated = True
        self._last_notify_time = None
        return True

    def _handle_not_in_most_populated(self) -> bool:
        now = datetime.now()
        should_notify = False

        if self._was_in_most_populated:
            # 初めて外れたタイミングで通知
            should_notify = True
        elif (
            self._last_notify_time is not None
            and now - self._last_notify_time >= self.notify_interval
        ):
            # 一定時間経過で再通知
            should_notify = True

        if should_notify:
            self._last_notify_time = now
            self._notify_user()

        self._was_in_most_populated = False
        return False

    def _notify_user(self):
        self.pl_api.control(
            ControlOptions(
                led=LedOptions(red=LightPattern.BLINK1),
                speech="最大インスタンスから外れています",
                repeat=255,
                notify=NotifySound.ALARM_1,
            )
        )
