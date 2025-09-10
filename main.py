import sys
import time
import logging
from typing import Optional

from app.config import Config
from app.http import HttpClient
from app.auth import AuthManager
from app.model.vrchat import InstanceInfo, InstanceType, UserInfo, UserState
from app.api.vrchat_api import VRChatAPI
from app.api.patlite_api import PatliteAPI, LightPattern, BuzzerPattern
from app.util.launcher import VRCLauncher

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

cfg = Config()
http = HttpClient(cfg)
auth = AuthManager(http, cfg)
vrc_api = VRChatAPI(http, auth, cfg)
pl_api = PatliteAPI(http, ip_address=cfg.patlite_ip)
launcher = VRCLauncher(profile=cfg.profile)


def get_group_instance_info() -> list[InstanceInfo]:
    group_instances = vrc_api.get_group_instances(Config.DEKAPU_GROUP_ID)
    return [
        vrc_api.get_instance_info(Config.DEKAPU_WORLD_ID, gi.instance_id)
        for gi in group_instances
        if gi.world.id == Config.DEKAPU_WORLD_ID
    ]


def find_joinable_instance(
    world_id: str,
    group_id: Optional[str] = None,
    include_public: bool = True,
    capacity_margin: int = 1,
) -> Optional[InstanceInfo]:
    # Note: 探索条件はユーザー数がキャパシティからマージンを引いた分より少ないかつ、
    #       インスタンスがクローズしていないこと。グループ→パブリックの順に探索

    group_instance_info: list[InstanceInfo] = []

    if group_id:
        group_instances = vrc_api.get_group_instances(group_id)
        group_instance_info = [
            vrc_api.get_instance_info(world_id, gi.instance_id)
            for gi in group_instances
            if gi.world.id == world_id
        ]

    # グループ内から探索
    if group_instance_info:
        candidates = [
            i
            for i in group_instance_info
            if i.user_count < i.world.capacity - capacity_margin and i.closed_at is None
        ]
        joinable_instance = max(candidates, key=lambda x: x.user_count, default=None)
        if joinable_instance:
            return joinable_instance

    # パブリックから探索
    if include_public:
        worlds = vrc_api.get_worlds(world_id)
        sorted_world_entries = sorted(
            worlds.instances, key=lambda w: w.user_count, reverse=True
        )
        for entry in sorted_world_entries:
            info = vrc_api.get_instance_info(world_id, entry.instance_id)
            if info.type != InstanceType.PUBLIC or info.closed_at is not None:
                continue
            if info.user_count < info.world.capacity - capacity_margin:
                return info

    return None


def launch_with_joinable_instance():
    joinable_instance = find_joinable_instance(
        world_id=Config.DEKAPU_WORLD_ID,
        group_id=Config.DEKAPU_GROUP_ID,
    )

    if joinable_instance:
        logging.info(
            f"✅ Found joinable instance. Instance No: {joinable_instance.name}"
        )
    else:
        logging.info("ℹ️ No joinable instances available. Launch VRChat normally.")

    if launcher.is_running:
        logging.info("💾 VRChat is running. Closing the app to persistence save...")
        if not launcher.terminate():
            logging.error("Failed to terminate VRChat. Please exit VRChat manually.")
            return

    logging.info("🚀Launching VRChat...")
    launcher.launch(instance=joinable_instance)

    # ショップの自動購入は不可なので通知する
    pl_api.control(r=LightPattern.BLINK1, bz=BuzzerPattern.PATTERN1)


def check_traveling(user_info: UserInfo, traveling_count: int) -> int:
    if user_info.traveling_to_location is not None:
        traveling_count += 1
        logging.warning(f"⚠️ User is traveling... attempt {traveling_count}")

        if traveling_count >= 3:
            logging.error("❌ Traveling timeout exceeded. Restarting VRChat...")
            launch_with_joinable_instance()
    else:
        traveling_count = 0

    return traveling_count


def check_world(user_info: UserInfo):
    is_in_dekapu = user_info.world_id == Config.DEKAPU_WORLD_ID
    is_traveling_to_dekapu = user_info.traveling_to_world == Config.DEKAPU_WORLD_ID

    return bool(is_in_dekapu or is_traveling_to_dekapu)


def log_instance_list(group_instance_info: list[InstanceInfo]):
    for inst in sorted(group_instance_info, key=lambda x: x.user_count, reverse=True):
        msg = f"📌 Instance Name: {inst.name}, 👤Users: {inst.user_count:2d}/{inst.world.capacity}"
        msg += f", 👥Queue: {inst.queue_size if inst.queue_enabled else "disabled"}"

        if inst.closed_at:
            msg += f", 🚧Closed at: {inst.closed_at.isoformat()}"

        logging.info(msg)


def main():
    traveling_count = 0
    was_in_most_populated = True

    auth.load_session()

    try:
        while True:
            try:
                if not auth.ensure_logged_in():
                    logging.error("❌️ ログインに失敗しました")
                    sys.exit(-1)

                group_instance_info = get_group_instance_info()
                user_info = vrc_api.get_user_info(cfg.user_id)

                # ロスコネ, VRChat落ち対策
                if user_info.state != UserState.ONLINE:
                    logging.error("❌️ User is offline.")
                    launch_with_joinable_instance()
                else:
                    # 無限Joining対策
                    if user_info.traveling_to_location is not None:
                        traveling_count += 1
                        logging.warning(
                            f"⚠️ User is traveling... attempt {traveling_count}"
                        )

                        if traveling_count >= 3:
                            logging.error(
                                "❌ Traveling timeout exceeded. Restarting VRChat..."
                            )
                            launch_with_joinable_instance()
                    else:
                        traveling_count = 0

                    # でかプに滞在しているかチェック
                    if check_world(user_info):
                        logging.info("✅ Current world check: OK")
                    else:
                        logging.error("❌️ Current world check: NG")
                        pl_api.control(r=LightPattern.BLINK1, bz=BuzzerPattern.PATTERN1)

                    # グルパブ内で最多インスタンスに滞在しているかチェック
                    most_populated = max(
                        group_instance_info, key=lambda x: x.user_count, default=None
                    )

                    if most_populated is None:
                        logging.warning("⚠️ No populated instances found to compare.")
                        is_in_most_populated = True
                    else:
                        is_in_most_populated = (
                            user_info.location == most_populated.location
                        )

                        if is_in_most_populated:
                            logging.info("✅ This instance is the most populated one.")
                        else:
                            logging.warning(
                                "⚠️ This instance is not the most populated one."
                            )
                            vrc_api.invite_myself(most_populated)

                            # 最多インスタンスでなくなった際に1度だけパトライト通知
                            if was_in_most_populated and not is_in_most_populated:
                                pl_api.control(
                                    r=LightPattern.BLINK1, bz=BuzzerPattern.PATTERN1
                                )

                    was_in_most_populated = is_in_most_populated

                log_instance_list(group_instance_info)

            except Exception as e:
                logging.exception(e)

            time.sleep(60)

    except KeyboardInterrupt:
        pass
    finally:
        auth.save_session()


if __name__ == "__main__":
    main()
