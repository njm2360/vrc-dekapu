import logging
from typing import Optional
from datetime import datetime, timedelta, timezone

from app.api.vrchat_api import VRChatAPI
from app.model.vrchat import GroupAccessType, InstanceInfo, InstanceType, UserInfo


class InstanceManager:
    def __init__(self, vrc_api: VRChatAPI, world_id: str, group_id: str):
        self.vrc_api = vrc_api
        self.world_id = world_id
        self.group_id = group_id
        self._instances: list[InstanceInfo] = []

    @property
    def instances(self) -> list[InstanceInfo]:
        return self._instances

    def update(self) -> None:
        group_instances = self.vrc_api.get_group_instances(self.group_id)
        self._instances = [
            self.vrc_api.get_instance_info(self.world_id, gi.instance_id)
            for gi in group_instances
            if gi.world.id == self.world_id
        ]

    def find(
        self,
        include_public: bool = True,
        most_populate: bool = False,
        capacity_margin: int = 1,
        close_margin: Optional[timedelta] = None,
    ) -> Optional[InstanceInfo]:
        now = datetime.now()

        def is_effectively_open(inst: InstanceInfo) -> bool:
            if inst.closed_at is None:
                return True
            if close_margin and inst.closed_at > now + close_margin:
                return True
            return False

        # グループ内から探索
        candidates = [
            i
            for i in self._instances
            if i.group_access_type == GroupAccessType.PUBLIC
            and is_effectively_open(i)
            and (most_populate or (i.user_count < i.world.capacity - capacity_margin))
        ]

        # グループで該当がない場合パブリックからも探索
        if include_public and len(candidates) == 0:
            worlds = self.vrc_api.get_worlds(self.world_id)
            for entry in worlds.instances:
                info = self.vrc_api.get_instance_info(self.world_id, entry.instance_id)
                if (
                    info.type == InstanceType.PUBLIC
                    and is_effectively_open(info)
                    and (
                        most_populate
                        or (info.user_count < info.world.capacity - capacity_margin)
                    )
                ):
                    candidates.append(info)

        return max(candidates, key=lambda x: x.user_count, default=None)

    def print(self, current_location: str) -> None:
        if not self._instances:
            logging.info("ℹ️ No instance data available (call update() first).")
            return

        for inst in sorted(
            self._instances, key=lambda x: (x.closed_at is not None, -x.user_count)
        ):
            msg = f"📌 Instance Name: {inst.name}, 👤Users: {inst.user_count}/{inst.world.capacity}"
            msg += f", 👥Queue: {inst.queue_size if inst.queue_enabled else 'disabled'}"

            if inst.closed_at:
                closed_jst = inst.closed_at.astimezone(timezone(timedelta(hours=9)))
                msg += f", 🚧Closed: {closed_jst.strftime('%Y-%m-%d %H:%M:%S')}"

            if inst.location == current_location:
                msg += " (*)"

            logging.info(msg)

    def is_in_world(self, user: UserInfo) -> bool:
        return (
            user.world_id == self.world_id or user.traveling_to_world == self.world_id
        )
