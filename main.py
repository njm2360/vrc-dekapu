import sys
import time
import logging
from pathlib import Path
from typing import Final, Optional
from datetime import datetime, timedelta

from app.config import Config
from app.http import HttpClient
from app.auth import AuthManager
from app.model.vrchat import InstanceInfo, InstanceType, UserInfo, UserState
from app.api.vrchat_api import VRChatAPI
from app.api.patlite_api import (
    ControlOptions,
    LedOptions,
    NotifySound,
    PatliteAPI,
    LightPattern,
)
from app.util.launcher import LaunchOptions, VRCLauncher

cfg = Config()
http = HttpClient()
auth = AuthManager(http, cfg)
vrc_api = VRChatAPI(http, auth, cfg)
pl_api = PatliteAPI(http, ip_address=cfg.patlite_ip)
launcher = VRCLauncher(profile=cfg.profile)

POPULATION_DIFF_THRESHOLD: Final[int] = 8


def logger_init():
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    start_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{start_time}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
        force=True,
    )


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
            pl_api.control(
                ControlOptions(
                    led=LedOptions(red=LightPattern.BLINK1),
                    speech="正常終了できませんでした。手動で起動して下さい。",
                    repeat=255,
                    notify=NotifySound.ALARM_1,
                )
            )
            return

    logging.info("🚀Launching VRChat...")
    launcher.launch(
        LaunchOptions(
            instance=joinable_instance,
            extra_args=["--process-priority=2", "--main-thread-priority=2"],
        )
    )

    # ショップの自動購入は不可なので通知する
    pl_api.control(
        ControlOptions(
            led=LedOptions(red=LightPattern.BLINK1),
            speech="再起動しました。初期操作をしてください",
            repeat=255,
            notify=NotifySound.ALARM_1,
        )
    )


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


def log_instance_list(group_instance_info: list[InstanceInfo], current_location: str):
    for inst in sorted(group_instance_info, key=lambda x: x.user_count, reverse=True):
        msg = f"📌 Instance Name: {inst.name}, 👤Users: {inst.user_count:2d}/{inst.world.capacity}"
        msg += f", 👥Queue: {inst.queue_size if inst.queue_enabled else 'disabled'}"

        if inst.closed_at:
            msg += f", 🚧Closed at: {inst.closed_at.isoformat()}"

        if inst.location == current_location:
            msg += " (*)"

        logging.info(msg)


def main():
    traveling_count: int = 0
    losconn_count: int = 0
    was_in_most_populated: Optional[bool] = True
    last_notify_time: Optional[datetime] = None
    last_post_id: Optional[str] = None

    logger_init()
    auth.load_session()

    try:
        while True:
            try:
                if not auth.ensure_logged_in():
                    logging.error("❌️ ログインに失敗しました")
                    sys.exit(-1)

                group_instance_info = get_group_instance_info()
                user_info = vrc_api.get_user_info(cfg.user_id)

                if not launcher.is_running:
                    # VRChat落ち対策
                    logging.error("❌️ VRChat is not running. Restarting...")
                    launch_with_joinable_instance()
                elif user_info.state != UserState.ONLINE:
                    # ロスコネ対策
                    losconn_count += 1
                    logging.warning(f"⚠️ User is offline... attempt {losconn_count}")

                    if losconn_count == 1:
                        # 初回のみ通知
                        pl_api.control(
                            ControlOptions(
                                led=LedOptions(red=LightPattern.BLINK1),
                                speech="ロスコネクションを検知しました、注意してください",
                                repeat=255,
                                notify=NotifySound.ALARM_1,
                            )
                        )

                    # if losconn_count >= 3:
                    #     # 3回継続してオフラインの場合は強制再起動
                    #     logging.error(
                    #         "❌️ Lost connection persists. Restarting VRChat..."
                    #     )
                    #     losconn_count = 0
                    #     launch_with_joinable_instance()
                else:
                    losconn_count = 0

                    # 無限Joining対策
                    if user_info.traveling_to_location is not None:
                        traveling_count += 1
                        logging.warning(
                            f"⚠️ User is traveling... attempt {traveling_count}"
                        )

                        if traveling_count >= 3:
                            # 3回継続して移動中の場合は強制再起動
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
                        pl_api.control(
                            ControlOptions(
                                led=LedOptions(red=LightPattern.BLINK1),
                                speech="ワールドをチェックしてください",
                                repeat=255,
                                notify=NotifySound.ALARM_1,
                            )
                        )

                    # グルパブ内で最多インスタンスに滞在しているかチェック
                    if not group_instance_info:
                        logging.warning("⚠️ No populated instances found to compare")
                        is_in_most_populated = True
                    else:
                        joinable_instances = [
                            i for i in group_instance_info if i.closed_at is None
                        ]
                        max_user_count = max(i.user_count for i in joinable_instances)
                        current_instance = next(
                            (
                                i
                                for i in group_instance_info
                                if i.location == user_info.location
                            ),
                            None,
                        )

                        if current_instance is None:
                            # グルパブ外にいる場合はNG
                            logging.error("❌️ User is not in any group instance")
                            is_in_most_populated = False
                        else:
                            # 最多インスタンスとの差分チェック
                            diff = max_user_count - current_instance.user_count

                            if diff <= 0:
                                is_in_most_populated = True
                                logging.info("✅ This instance is most populated one")
                            elif diff < POPULATION_DIFF_THRESHOLD:
                                is_in_most_populated = True
                                logging.warning(
                                    f"⚠️ This instance is nearly most populated (diff={diff})"
                                )
                            else:
                                is_in_most_populated = False
                                logging.error(
                                    f"❌️ This instance is {diff} users behind the most populated one"
                                )

                        if is_in_most_populated:
                            last_notify_time = None
                        else:
                            most_populated_instances = [
                                i
                                for i in joinable_instances
                                if i.user_count == max_user_count
                            ]
                            # JoinQueueが有効 => QueueSizeが小さいものの順番で選定
                            queue_enabled_instances = [
                                i for i in most_populated_instances if i.queue_enabled
                            ]

                            if queue_enabled_instances:
                                invite_target = min(
                                    queue_enabled_instances, key=lambda x: x.queue_size
                                )
                            else:
                                invite_target = most_populated_instances[0]

                            vrc_api.invite_myself(invite_target)

                            now = datetime.now()

                            # 最大から外れたとき or 10分経過毎にパトライト通知
                            if (was_in_most_populated and not is_in_most_populated) or (
                                last_notify_time is not None
                                and now - last_notify_time >= timedelta(minutes=10)
                            ):
                                last_notify_time = now
                                pl_api.control(
                                    ControlOptions(
                                        led=LedOptions(red=LightPattern.BLINK1),
                                        speech="最大インスタンスから外れています",
                                        repeat=255,
                                        notify=NotifySound.ALARM_1,
                                    )
                                )

                    was_in_most_populated = is_in_most_populated

                log_instance_list(group_instance_info, user_info.location)

                # 直近のグループ投稿を確認
                posts = vrc_api.get_group_posts(Config.DEKAPU_GROUP_ID, n_count=1)
                if posts:
                    newest_post = posts[0]
                    if last_post_id is None:
                        last_post_id = newest_post.id
                    elif newest_post.id != last_post_id:
                        last_post_id = newest_post.id
                        logging.info(
                            f"Found new post:\nTitle: {newest_post.title}\nText: {newest_post.text}"
                        )
                        pl_api.control(
                            ControlOptions(
                                led=LedOptions(blue=LightPattern.BLINK1),
                                speech=f"新しい投稿があります。{newest_post.title} {newest_post.text}",
                                repeat=255,
                                notify=NotifySound.CHIME_2,
                            )
                        )

            except Exception as e:
                logging.exception(e)

            time.sleep(60)

    except KeyboardInterrupt:
        pass
    finally:
        auth.save_session()


if __name__ == "__main__":
    main()
