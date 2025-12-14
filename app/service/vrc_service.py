from datetime import datetime
from app.api.vrchat_api import VRChatAPI
from app.const.group import DEKAPU_WORLD_ID
from app.model.instance.create import CreateInstanceConfig
from app.model.instance_type import InstanceType
from app.model.region import Region
from app.model.group_access_type import GroupAccessType
from app.model.vrchat import GroupRole, InstanceInfo
from app.ui.dialog.create_instance_dialog import CreateInstanceInput
from app.util.http import HttpClient
from app.util.auth import AuthManager
from app.config import Config
from app.util.launcher import VRCLauncher, LaunchOptions


class VRCService:
    def __init__(self):
        self.cfg = Config()
        self.http = HttpClient()
        self.auth = AuthManager(self.http, self.cfg)
        self.api = VRChatAPI(self.http, self.auth, self.cfg)
        self.launcher = VRCLauncher(manage_process=False)

        self.auth.load_session()
        if not self.auth.ensure_logged_in():
            raise Exception("VRChat login failed")

    def get_group_instances(self, group_id: str):
        return self.api.get_group_instances(group_id)

    def get_instance_info(self, world_id: str, instance_id: str):
        return self.api.get_instance_info(world_id, instance_id)

    def close_instance(self, inst: InstanceInfo):
        self.api.close_instance(inst)

    def create_instance(self, input: CreateInstanceInput) -> InstanceInfo:
        display_name = None

        if input.display_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            display_name = f"{input.display_name}_{timestamp}"

        config = CreateInstanceConfig(
            world_id=DEKAPU_WORLD_ID,
            type=InstanceType.GROUP,
            region=Region.JP,
            owner_id=input.group_id,
            group_access_type=GroupAccessType.MEMBER,
            queue_enabled=input.queue_enabled,
            display_name=display_name,
        )

        return self.api.create_instance(config)

    def launch(self, instance, profile: int, extra_args: list[str]):
        self.launcher.launch(
            LaunchOptions(
                instance=instance,
                profile=profile,
                extra_args=extra_args,
            )
        )

    def get_launch_url(self, instance: InstanceInfo) -> str:
        return self.launcher.get_launch_url(instance)

    def get_group_roles(self, group_id: str) -> list[GroupRole]:
        return self.api.get_group_roles(group_id)

    def save_session(self):
        self.auth.save_session()
