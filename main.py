import os
import json
import sys
import time
import pyotp
import logging
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(filename)s:%(lineno)d] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

load_dotenv()

username = os.getenv("ID")
password = os.getenv("PASSWORD")
totp_secret = os.getenv("TOTP_SECRET")
user_id = os.getenv("USER_ID")
patlite_ip = os.getenv("PATLITE_IP")

BASE_URL = "https://api.vrchat.cloud/api/1"
COOKIE_FILE = "cookie.json"

DEKAPU_GROUP_ID = "grp_5900a25d-0bb9-48d4-bab1-f3bd5c9a5e73"
DEKAPU_WORLD_ID = "wrld_1af53798-92a3-4c3f-99ae-a7c42ec6084d"

session = requests.session()
session.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:142.0) Gecko/20100101 Firefox/142.0"
    }
)


# Cookieが存在し、有効期限内かどうかを確認する
def has_cookie(domain: str, name: str) -> bool:
    now = time.time()
    for cookie in session.cookies:
        if cookie.domain.lstrip(".") == domain and cookie.name == name:
            if cookie.expires is None:
                return True
            if cookie.expires > now:
                return True
            else:
                logging.warning(
                    f"Cookie '{name}' for '{domain}' has expired at {time.ctime(cookie.expires)}"
                )
    return False


# CookieをJSONファイルに保存する
def save_cookies_to_json():
    cookies = []
    for cookie in session.cookies:
        cookies.append(
            {
                "name": cookie.name,
                "value": cookie.value,
                "domain": cookie.domain,
                "path": cookie.path,
                "secure": cookie.secure,
                "expires": cookie.expires,
            }
        )
    with open(COOKIE_FILE, "w") as f:
        json.dump(cookies, f)


# CookieをJSONファイルから読み込む
def load_cookies_from_json():
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "r") as f:
            cookies = json.load(f)
            for c in cookies:
                session.cookies.set(
                    name=c["name"],
                    value=c["value"],
                    domain=c["domain"],
                    path=c["path"],
                    secure=c.get("secure", False),
                    expires=c.get("expires"),
                )


# ログイン処理
def login(username: str, password: str) -> bool:
    try:
        response = session.get(
            f"{BASE_URL}/auth/user",
            auth=HTTPBasicAuth(username, password),
        )
        response.raise_for_status()
        data = response.json()

        if "requiresTwoFactorAuth" in data:
            if "totp" not in data["requiresTwoFactorAuth"]:
                logging.error("TOTP is not required.")
                return False
        else:
            logging.error("No requiresTwoFactorAuth field in response.")
            return False

        auth_cookie = response.cookies.get("auth")
        if not auth_cookie:
            logging.error("Auth cookie not found.")
            return False

        totp = pyotp.TOTP(totp_secret.replace(" ", ""))
        current_otp = totp.now()

        response = session.post(
            f"{BASE_URL}/auth/twofactorauth/totp/verify",
            data={"code": current_otp},
        )
        response.raise_for_status()
        verify_data = response.json()

        if not verify_data.get("verified"):
            logging.error("TOTP verification failed.")
            return False

        return True

    except requests.HTTPError as http_err:
        logging.error(f"HTTP error occurred: {http_err}")
    except ValueError as json_err:
        logging.error(f"JSON decoding error: {json_err}")
    except Exception as err:
        logging.error(f"Unexpected error: {err}")
    return False


# ユーザー情報を取得
def get_user_info(user_id: str):
    response = session.get(
        f"{BASE_URL}/users/{user_id}",
    )
    response.raise_for_status()

    logging.debug(json.dumps(response.json(), indent=2, ensure_ascii=False))

    return response.json()


# グループのインスタンス一覧を取得
def get_group_instances(group_id: str):
    response = session.get(
        f"{BASE_URL}/groups/{group_id}/instances",
    )
    response.raise_for_status()

    logging.debug(json.dumps(response.json(), indent=2, ensure_ascii=False))

    return response.json()


# インスタンスの詳細情報を取得
def get_instance_info(world_id: str, instance_id: str):
    response = session.get(
        f"{BASE_URL}/instances/{world_id}:{instance_id}",
    )
    response.raise_for_status()

    logging.debug(json.dumps(response.json(), indent=2, ensure_ascii=False))

    return response.json()


# グループの投稿一覧を取得
def get_group_posts(group_id: str):
    response = session.get(
        f"{BASE_URL}/groups/{group_id}/posts",
    )
    response.raise_for_status()

    logging.debug(json.dumps(response.json(), indent=2, ensure_ascii=False))

    return response.json()


# 自分を指定したインスタンスに招待
def invite_myself(world_id: str, instance_id: str):
    response = session.post(
        f"{BASE_URL}/invite/myself/to/{world_id}:{instance_id}",
    )
    response.raise_for_status()

    logging.debug(json.dumps(response.json(), indent=2, ensure_ascii=False))

    return response.json()


def alert_patlite():
    # NHV4/6 HTTPコマンド受信機能互換
    if patlite_ip is None:
        return

    response = session.get(
        f"http://{patlite_ip}/api/control",
        params={"alert": "200001"},  # 赤色:パターン1 ブザー:パターン1
        verify=False,
    )
    response.raise_for_status()


def main():
    traveling_count = 0

    load_cookies_from_json()

    try:
        while True:
            try:
                # Cookieが無い、または期限切れの場合はログインを試みる
                if not has_cookie("api.vrchat.cloud", "auth"):
                    if not login(username, password):
                        logging.error("❌️ ログインに失敗しました")
                        sys.exit(-1)

                user_info = get_user_info(user_id)
                current_world_id = user_info["worldId"]
                current_instance_id = user_info["instanceId"]

                if current_instance_id == "traveling":
                    logging.warning("⚠️ 移動中です")
                    traveling_count += 1
                    # 無限Joining検知
                    if traveling_count >= 2:
                        logging.error("❌️ 移動時間が長すぎます: NG")
                        alert_patlite()
                elif current_world_id == DEKAPU_WORLD_ID:
                    logging.info("✅ 現在ワールドチェック: OK")
                    traveling_count = 0
                else:
                    logging.error("❌️ 現在ワールドチェック: NG")
                    alert_patlite()
                    traveling_count = 0

                group_instances = get_group_instances(DEKAPU_GROUP_ID)

                instance_info_list = []

                for group_instance in group_instances:
                    # でかプ以外のワールドが建ってるかもしれない
                    if group_instance["world"]["id"] != DEKAPU_WORLD_ID:
                        continue

                    instance_id: str = group_instance["instanceId"]
                    instance_info: dict = get_instance_info(
                        DEKAPU_WORLD_ID, instance_id
                    )
                    user_count = instance_info.get("userCount", 0)
                    name = instance_info.get("name")
                    instance_info_list.append(
                        {
                            "instanceId": instance_id,
                            "userCount": user_count,
                            "name": name,
                        }
                    )

                    logging.debug(f"Instance Name: {name} Users: {user_count}")

                # 最多人数のインスタンスを特定
                most_populated = max(
                    instance_info_list, key=lambda x: x["userCount"], default=None
                )
                most_populated_instance = (
                    most_populated["instanceId"] if most_populated else None
                )

                if current_instance_id == most_populated_instance:
                    logging.info("✅ 現在のインスタンスは最多人数のインスタンスです")
                else:
                    logging.warning(
                        "⚠️ 現在のインスタンスは最多人数のインスタンスではありません"
                    )
                    invite_myself(DEKAPU_WORLD_ID, most_populated_instance)
                    alert_patlite()

                # 人数が多い順に現在のインスタンス一覧を表示
                sorted_instances = sorted(
                    instance_info_list, key=lambda x: x["userCount"], reverse=True
                )
                for inst in sorted_instances:
                    logging.info(
                        f"📌 Instance Name: {inst['name']}, Users: {inst['userCount']}"
                    )

            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 401:
                    logging.warning("⚠️ 認証エラーが発生しました。再ログインします。")
                    if not login(username, password):
                        logging.error("❌ ログインに失敗しました")
                        sys.exit(-1)
                    continue  # 再試行

            except Exception as e:
                logging.exception(e)

            time.sleep(60)

    except KeyboardInterrupt:
        pass

    finally:
        save_cookies_to_json()


if __name__ == "__main__":
    main()
