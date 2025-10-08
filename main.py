import sys
import time
import logging
from typing import Optional

from app.populate_monitor import PopulationMonitor
from app.post_manager import PostManager
from app.instance_manager import InstanceManager
from app.travelling_monitor import TravelingMonitor
from app.connection_monitor import ConnectionMonitor
from app.config import Config
from app.util.http import HttpClient
from app.util.auth import AuthManager
from app.util.logger import setup_logger
from app.util.launcher import LaunchOptions, VRCLauncher
from app.model.vrchat import InstanceInfo, UserState
from app.api.vrchat_api import VRChatAPI
from app.api.patlite_api import (
    ControlOptions,
    LedOptions,
    NotifySound,
    PatliteAPI,
    LightPattern,
)

setup_logger()

cfg = Config()
http = HttpClient()
auth = AuthManager(http, cfg)
vrc_api = VRChatAPI(http, auth, cfg)
pl_api = PatliteAPI(http, ip_address=cfg.patlite_ip)
launcher = VRCLauncher(profile=cfg.profile)


def launch_with_instance(instance: Optional[InstanceInfo]):
    if instance:
        logging.info(f"Instance specified. Instance No: {instance.name}")
    else:
        logging.info("No instance specified. Launch VRChat normally.")

    if launcher.is_running:
        logging.info("VRChat is running. Closing application...")
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
            instance=instance,
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


def main():
    instance_manager = InstanceManager(
        vrc_api=vrc_api,
        group_id=Config.DEKAPU_GROUP_ID,
        world_id=Config.DEKAPU_WORLD_ID,
    )
    traveling_checker = TravelingMonitor(pl_api)
    population_monitor = PopulationMonitor(pl_api)
    connection_monitor = ConnectionMonitor(pl_api)
    post_manager = PostManager(vrc_api=vrc_api, group_id=Config.DEKAPU_GROUP_ID)

    auth.load_session()

    try:
        while True:
            try:
                if not auth.ensure_logged_in():
                    logging.error("❌️ ログインに失敗しました")
                    sys.exit(-1)

                instance_manager.update()
                user_info = vrc_api.get_user_info(cfg.user_id)

                # VRChat落ち対策
                if not launcher.is_running:
                    logging.error("❌️ VRChat is not running. Restarting...")
                    instance = instance_manager.find()
                    launch_with_instance(instance)

                # ロスコネ対策
                if connection_monitor.check(user_info):
                    # Note: パラレルワールドが発生してオンライン状態が壊れる場合があるので一旦コメントアウト

                    # オフライン状態が継続する場合は再起動
                    # instance = instance_manager.find_joinable()
                    # launch_with_instance(instance)
                    pass

                # オンライン時: メイン処理
                if user_info.state == UserState.ONLINE:
                    # 無限Joining対策
                    if traveling_checker.check(user_info):
                        instance = instance_manager.find()
                        launch_with_instance(instance)

                    # でかプに滞在しているかチェック
                    if instance_manager.is_in_world(user_info):
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
                    if not population_monitor.evaluate(
                        instance_manager.instances, user_info
                    ):
                        # Inviteなので最大人数インスタンスを検索
                        if target := instance_manager.find(most_populate=True):
                            vrc_api.invite_myself(target)

                # 直近のグループ投稿を確認
                if post := post_manager.check_new_post():
                    pl_api.control(
                        ControlOptions(
                            led=LedOptions(blue=LightPattern.BLINK1),
                            speech=f"新しい投稿があります。{post.title} {post.text}",
                            repeat=255,
                            notify=NotifySound.CHIME_2,
                        )
                    )

                # インスタンス一覧情報を表示
                instance_manager.print(user_info.location)

            except Exception as e:
                logging.exception(e)

            time.sleep(60)

    except KeyboardInterrupt:
        pass
    finally:
        auth.save_session()


if __name__ == "__main__":
    main()
