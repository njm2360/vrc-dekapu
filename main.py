import os
import json
import sys
import time
import pyotp
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")
totp_secret = os.getenv("TOTP_SECRET")
user_id = os.getenv("USER_ID")


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


def has_cookie(domain: str, name: str) -> bool:
    now = time.time()
    for cookie in session.cookies:
        if cookie.domain == domain and cookie.name == name:
            # 有効期限が設定されていない場合は有効とみなす
            if cookie.expires is None:
                return True
            # 有効期限が現在時刻より後であれば有効
            if cookie.expires > now:
                return True
            else:
                print(
                    f"Cookie '{name}' for '{domain}' has expired at {time.ctime(cookie.expires)}"
                )
    return False


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
                print("TOTP is not required.")
                return False
        else:
            print("No requiresTwoFactorAuth field in response.")
            return False

        auth_cookie = response.cookies.get("auth")
        if not auth_cookie:
            print("Auth cookie not found.")
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
            print("TOTP verification failed.")
            return False

        return True

    except requests.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except ValueError as json_err:
        print(f"JSON decoding error: {json_err}")
    except Exception as err:
        print(f"Unexpected error: {err}")
    return False


def get_user_info(user_id: str):
    response = session.get(
        f"{BASE_URL}/users/{user_id}",
    )
    response.raise_for_status()

    # print(json.dumps(response.json(), indent=2, ensure_ascii=False))

    return response.json()


def get_group_instances(group_id: str):
    response = session.get(
        f"{BASE_URL}/groups/{group_id}/instances",
    )
    response.raise_for_status()

    # print(json.dumps(response.json(), indent=2, ensure_ascii=False))

    return response.json()


def get_instance_info(world_id: str, instance_id: str):
    response = session.get(
        f"{BASE_URL}/instances/{world_id}:{instance_id}",
    )
    response.raise_for_status()

    # print(json.dumps(response.json(), indent=2, ensure_ascii=False))

    return response.json()


def get_group_posts(group_id: str):
    response = session.get(
        f"{BASE_URL}/groups/{group_id}/posts",
    )
    response.raise_for_status()

    # print(json.dumps(response.json(), indent=2, ensure_ascii=False))

    return response.json()


def invite_myself(world_id: str, instance_id: str):
    response = session.post(
        f"{BASE_URL}/invite/myself/to/{world_id}:{instance_id}",
    )
    response.raise_for_status()

    # print(json.dumps(response.json(), indent=2, ensure_ascii=False))

    return response.json()


def main():
    traveling_count = 0

    load_cookies_from_json()

    try:
        while True:
            try:
                # 0. VRChatにログイン
                if not has_cookie("api.vrchat.cloud", "auth"):
                    if not login(username, password):
                        print("❌️ ログインに失敗しました")
                        sys.exit(-1)

                # 1. 現在のワールドがでかプかどうかチェック
                user_info = get_user_info(user_id)
                current_world_id = user_info["worldId"]
                current_instance_id = user_info["instanceId"]

                if current_instance_id == "traveling":
                    print("⚠️ 移動中です")
                    traveling_count += 1
                    if traveling_count >= 2:
                        print("❌️ 移動時間が長すぎます: NG")
                elif current_world_id == DEKAPU_WORLD_ID:
                    print("✅ 現在ワールドチェック: OK")
                    traveling_count = 0
                else:
                    print("❌️ 現在ワールドチェック: NG")
                    traveling_count = 0

                # 2. Groupインスタンス内で最多人数のインスタンスに居るかどうかチェック
                group_instances = get_group_instances(DEKAPU_GROUP_ID)

                most_populated_instance = None
                max_users = -1

                for group_instance in group_instances:
                    instance_id: str = group_instance["instanceId"]

                    instance_info: dict = get_instance_info(
                        DEKAPU_WORLD_ID, instance_id
                    )
                    user_count = instance_info.get("userCount", 0)
                    name = instance_info.get("name")

                    print(
                        f"Instance Name: {name} Users: {user_count}"
                    )

                    if user_count > max_users:
                        max_users = user_count
                        most_populated_instance = instance_id

                if current_instance_id == most_populated_instance:
                    print("✅ 現在のインスタンスは最多人数のインスタンスです")
                else:
                    print("⚠️ 現在のインスタンスは最多人数のインスタンスではありません")
                    invite_myself(DEKAPU_WORLD_ID, most_populated_instance)

            except Exception as e:
                print(e)

            time.sleep(60)

    finally:
        save_cookies_to_json()


if __name__ == "__main__":
    main()
