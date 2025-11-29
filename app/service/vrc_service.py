from typing import Optional
from app.api.vrchat_api import VRChatAPI
from app.model.instance.create import CreateInstanceConfig
from app.model.instance_type import InstanceType
from app.model.region import Region
from app.model.group_access_type import GroupAccessType
from app.model.vrchat import InstanceInfo
from app.util.http import HttpClient
from app.util.auth import AuthManager
from app.config import Config
from app.util.launcher import VRCLauncher, LaunchOptions


DEKAPU_WORLD_ID = "wrld_1af53798-92a3-4c3f-99ae-a7c42ec6084d"
DKPSKL_GROUP_ID = "grp_f664b62c-df1a-4ad4-a1df-2b9df679bc04"
BUPPA_RENGO_ROLE_ID = "grol_c8676ba2-83e7-4780-9cb9-fbe9f60c25ba"


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

    def get_group_instances(self):
        return self.api.get_group_instances(DKPSKL_GROUP_ID)

    def get_instance_info(self, world_id: str, instance_id: str):
        return self.api.get_instance_info(world_id, instance_id)

    def close_instance(self, inst: InstanceInfo):
        self.api.close_instance(inst)

    def create_instance(self, display_name: Optional[str]) -> InstanceInfo:
        return self.api.create_instance(
            CreateInstanceConfig(
                world_id=DEKAPU_WORLD_ID,
                type=InstanceType.GROUP,
                region=Region.JP,
                owner_id=DKPSKL_GROUP_ID,
                role_ids=[BUPPA_RENGO_ROLE_ID],
                group_access_type=GroupAccessType.MEMBER,
                queue_enabled=True,
                display_name=display_name,
            )
        )

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

    def save_session(self):
        self.auth.save_session()
