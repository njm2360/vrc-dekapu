import sys
import time
import logging

from app.config import Config
from app.auth import AuthManager
from app.http import HttpClient
from app.model.vrchat import InstanceInfo
from app.api.vrchat_api import VRChatAPI
from app.api.patlite_api import BuzzerPattern, LightPattern, PatliteAPI

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

                # ユーザー情報を取得
                user_info = vrc_api.get_user_info(cfg.user_id)
                current_instance_id = user_info.instanceId

                # 無限Joining対策
                if current_instance_id == "traveling":
                    logging.warning("⚠️ 移動中です")
                    traveling_count += 1
                    if traveling_count >= 2:
                        logging.error("❌️ 移動時間が長すぎます: NG")
                        pl_api.control(r=LightPattern.BLINK1, bz=BuzzerPattern.PATTERN1)

                # ワールドチェック
                if user_info.worldId == Config.DEKAPU_WORLD_ID:
                    logging.info("✅ 現在ワールドチェック: OK")
                    traveling_count = 0
                else:
                    logging.error("❌️ 現在ワールドチェック: NG")
                    pl_api.control(r=LightPattern.BLINK1, bz=BuzzerPattern.PATTERN1)
                    traveling_count = 0

                # グループインスタンス一覧を取得
                group_instances = vrc_api.get_group_instances(Config.DEKAPU_GROUP_ID)

                instance_info_list: list[InstanceInfo] = []

                for group_instance in group_instances:
                    # でかプ以外のワールドが建ってるかもしれない
                    if group_instance.world.id != Config.DEKAPU_WORLD_ID:
                        continue

                    instance_id: str = group_instance.instanceId
                    instance_info = vrc_api.get_instance_info(
                        Config.DEKAPU_WORLD_ID, instance_id
                    )
                    instance_info_list.append(instance_info)

                    logging.debug(
                        f"Instance Name: {instance_info.name} Users: {instance_info.userCount}"
                    )

                # 最多人数のインスタンスを特定
                most_populated = max(
                    instance_info_list, key=lambda x: x.userCount, default=None
                )
                most_populated_instance = (
                    most_populated.instanceId if most_populated else None
                )

                if current_instance_id == most_populated_instance:
                    logging.info("✅ 現在のインスタンスは最多人数のインスタンスです")
                else:
                    logging.warning(
                        "⚠️ 現在のインスタンスは最多人数のインスタンスではありません"
                    )
                    vrc_api.invite_myself(
                        Config.DEKAPU_WORLD_ID, most_populated_instance
                    )
                    pl_api.control(r=LightPattern.BLINK1, bz=BuzzerPattern.PATTERN1)

                # 人数が多い順に現在のインスタンス一覧を表示
                sorted_instances = sorted(
                    instance_info_list, key=lambda x: x.userCount, reverse=True
                )
                for inst in sorted_instances:
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
