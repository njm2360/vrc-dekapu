import sys
import time
import logging

from app.config import Config
from app.http import HttpClient
from app.auth import AuthManager
from app.model.vrchat import InstanceInfo
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

                # でかプのグループインスタンス情報を取得
                instance_info_list: list[InstanceInfo] = []
                group_instances = vrc_api.get_group_instances(Config.DEKAPU_GROUP_ID)

                for gi in group_instances:
                    # でかプ以外のワールドが建ってるかもしれない
                    if gi.world.id != Config.DEKAPU_WORLD_ID:
                        continue

                    inst_info = vrc_api.get_instance_info(
                        Config.DEKAPU_WORLD_ID, gi.instanceId
                    )
                    instance_info_list.append(inst_info)
                    logging.debug(
                        f"Instance Name: {inst_info.name} Users: {inst_info.userCount}"
                    )

                # 最多人数のインスタンスを決定
                most_populated = max(
                    instance_info_list, key=lambda x: x.userCount, default=None
                )

                # ユーザー情報を取得
                user_info = vrc_api.get_user_info(cfg.user_id)

                # オフラインの場合VRChatを起動
                if user_info.state == "offline":
                    logging.warning("⚠️ User is offline. Launching VRChat...")
                    launcher.launch(most_populated, no_vr=True, profile=cfg.profile)

                # 無限Joining対策
                if user_info.travelingToLocation:
                    logging.warning("⚠️ Travelling...")
                    traveling_count += 1
                    if traveling_count >= 2:
                        logging.error("❌️ Traveling time is too long: NG")
                        pl_api.control(r=LightPattern.BLINK1, bz=BuzzerPattern.PATTERN1)

                # ワールドチェック
                if user_info.worldId == Config.DEKAPU_WORLD_ID:
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
                        vrc_api.invite_myself(
                            Config.DEKAPU_WORLD_ID, most_populated.instanceId
                        )
                        pl_api.control(r=LightPattern.BLINK1, bz=BuzzerPattern.PATTERN1)

                # 人数が多い順に現在のインスタンス一覧を表示
                for inst in sorted(
                    instance_info_list, key=lambda x: x.userCount, reverse=True
                ):
                    logging.info(
                        f"📌 Instance Name: {inst.name}, Users: {inst.userCount}"
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
