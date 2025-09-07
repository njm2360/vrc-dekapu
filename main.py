import sys
import time
import logging
from typing import Optional

from app.config import Config
from app.http import HttpClient
from app.auth import AuthManager
from app.model.vrchat import InstanceInfo, UserState
from app.api.vrchat_api import VRChatAPI
from app.api.patlite_api import PatliteAPI, LightPattern, BuzzerPattern
from app.util.launcher import VRCLauncher

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(filename)s:%(lineno)d] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

cfg = Config()
http = HttpClient(cfg)
auth = AuthManager(http, cfg)
pl_api = PatliteAPI(http, cfg)
vrc_api = VRChatAPI(http, auth, cfg)
launcher = VRCLauncher()


def main():
    traveling_count = 0

    auth.load_session()

    try:
        while True:
            try:
                # ログイン状態を確認
                if not auth.ensure_logged_in():
                    logging.error("❌️ ログインに失敗しました")
                    sys.exit(-1)

                # グループインスタンスの詳細を取得（でかプのみ）
                group_instances = vrc_api.get_group_instances(Config.DEKAPU_GROUP_ID)
                group_instance_info: list[InstanceInfo] = [
                    vrc_api.get_instance_info(Config.DEKAPU_WORLD_ID, gi.instance_id)
                    for gi in group_instances
                    if gi.world.id == Config.DEKAPU_WORLD_ID
                ]

                # Invite送信用：グループ内で最多人数のインスタンスを求める
                most_populated = max(
                    group_instance_info, key=lambda x: x.user_count, default=None
                )

                # ユーザー情報を取得
                user_info = vrc_api.get_user_info(cfg.user_id)

                # オフラインかつVRChat未起動なら自動起動
                if user_info.state != UserState.ONLINE and not launcher.is_running():
                    # グループ内でJoin可能なインスタンス
                    joinable_instance = max(
                        (
                            i
                            for i in group_instance_info
                            if i.user_count < i.world.capacity
                        ),
                        key=lambda x: x.user_count,
                        default=None,
                    )

                    # 無ければPublicワールドから探索
                    if joinable_instance is None:
                        group_instance_ids = {gi.instance_id for gi in group_instances}
                        sorted_world_entries = sorted(
                            (
                                w
                                for w in vrc_api.get_worlds(
                                    Config.DEKAPU_WORLD_ID
                                ).instances
                                if w.instance_id not in group_instance_ids
                            ),
                            key=lambda w: w.user_count,
                            reverse=True,
                        )

                        for entry in sorted_world_entries:
                            info = vrc_api.get_instance_info(
                                Config.DEKAPU_WORLD_ID, entry.instance_id
                            )
                            if info.user_count < info.world.capacity:
                                joinable_instance = info
                                break

                    logging.info("User is offline. Launching VRChat...")
                    launcher.launch(joinable_instance, profile=cfg.profile)

                # 無限Joining対策
                if user_info.traveling_to_location is not None:
                    logging.warning("⚠️ Travelling...")
                    traveling_count += 1
                    if traveling_count >= 2:
                        logging.error("❌️ Traveling time is too long: NG")
                        pl_api.control(r=LightPattern.BLINK1, bz=BuzzerPattern.PATTERN1)

                # ワールドチェック
                if user_info.world_id == Config.DEKAPU_WORLD_ID:
                    logging.info("✅ Current world check: OK")
                    traveling_count = 0
                else:
                    logging.error("❌️ Current world check: NG")
                    pl_api.control(r=LightPattern.BLINK1, bz=BuzzerPattern.PATTERN1)
                    traveling_count = 0

                # 最多インスタンスにいるかどうかチェック
                if most_populated:
                    if user_info.location == most_populated.location:
                        logging.info("✅ This instance is the most populated one.")
                    else:
                        logging.warning(
                            "⚠️ This instance is not the most populated one."
                        )
                        # 自分を最多インスタンスに招待
                        vrc_api.invite_myself(most_populated)
                        pl_api.control(r=LightPattern.BLINK1, bz=BuzzerPattern.PATTERN1)

                # 人数が多い順に現在のインスタンス一覧を表示
                for inst in sorted(
                    group_instance_info, key=lambda x: x.user_count, reverse=True
                ):
                    logging.info(
                        f"📌 Instance Name: {inst.name}, Users: {inst.user_count}"
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
