from datetime import datetime
from app.model.vrchat import InstanceInfo
from app.service.vrc_service import VRCService


class InstanceController:
    def __init__(self):
        self.service = VRCService()
        self.instances: list[InstanceInfo] = []
        self.cfg = self.service.cfg

    def get_profile(self) -> int:
        return self.cfg.profile

    def get_instance_name(self, index: int) -> str:
        inst = self.instances[index]
        return inst.display_name or inst.name

    def update_instances(self) -> list[InstanceInfo]:
        group_instances = self.service.get_group_instances()
        self.instances.clear()

        result = []
        for gi in group_instances:
            try:
                inst = self.service.get_instance_info(gi.world.id, gi.instance_id)
                result.append(inst)
                self.instances.append(inst)
            except Exception as e:
                print("取得失敗:", e)

        return result

    def close_instance(self, index: int):
        inst = self.instances[index]
        self.service.close_instance(inst)

    def launch_instance_by_index(self, index: int, profile: int, extra_args: list[str]):
        inst = self.instances[index]
        self.service.launch(inst, profile, extra_args)

    def launch_instance(self, inst: InstanceInfo, profile: int, extra_args: list[str]):
        self.service.launch(inst, profile, extra_args)

    def create_instance(self, name: str):
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"{name}支部_{date_str}"

        return self.service.create_instance(name)

    def get_launch_url(self, instance: InstanceInfo) -> str:
        return self.service.get_launch_url(instance)

    def save_session(self):
        self.service.save_session()
