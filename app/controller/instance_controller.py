from dataclasses import dataclass
from datetime import datetime, timezone
from app.model.vrchat import GroupRole, InstanceInfo
from app.service.vrc_service import VRCService
from app.ui.dialog.create_instance_dialog import CreateInstanceInput


@dataclass(frozen=True)
class InstanceCache:
    instances: list[InstanceInfo]
    updated_at: datetime


class InstanceController:
    def __init__(self):
        self.service = VRCService()
        self.instances_by_group: dict[str, InstanceCache] = {}
        self.cfg = self.service.cfg

    def get_profile(self) -> int:
        return self.cfg.profile

    def get_group_instances(
        self, group_id: str, refresh: bool = False
    ) -> InstanceCache:
        if not refresh and group_id in self.instances_by_group:
            return self.instances_by_group[group_id]

        instances: list[InstanceInfo] = []

        group_instances = self.service.get_group_instances(group_id)
        for gi in group_instances:
            try:
                inst = self.service.get_instance_info(gi.world.id, gi.instance_id)
                instances.append(inst)
            except Exception as e:
                print("取得失敗:", e)

        result = InstanceCache(
            instances=instances,
            updated_at=datetime.now(timezone.utc),
        )
        self.instances_by_group[group_id] = result
        return result

    def launch(
        self,
        inst: InstanceInfo,
        profile: int,
        extra_args: list[str],
    ):
        self.service.launch(inst, profile, extra_args)

    def launch(self, inst: InstanceInfo, profile: int, extra_args: list[str]):
        self.service.launch(inst, profile, extra_args)

    def close_instance(self, inst: InstanceInfo):
        self.service.close_instance(inst)

    def get_launch_url(self, instance: InstanceInfo) -> str:
        return self.service.get_launch_url(instance)

    def get_group_roles(self, group_id: str) -> list[GroupRole]:
        return self.service.get_group_roles(group_id)

    def create_instance(self, group_id: str, input: CreateInstanceInput):
        return self.service.create_instance(
            group_id=group_id,
            display_name=input.display_name,
            role_ids=input.role_ids,
            queue_enabled=input.queue_enabled,
        )

    def save_session(self):
        self.service.save_session()

    def get_instance_by_id(self, group_id: str, id: str) -> InstanceInfo:
        cache = self.instances_by_group.get(group_id)
        if not cache:
            raise ValueError("インスタンスキャッシュが存在しません")

        for inst in cache.instances:
            if inst.id == id:
                return inst

        raise ValueError("指定されたインスタンスが見つかりません")
