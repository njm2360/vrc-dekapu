import logging
import requests
import pyotp
import json
import os
import time
from typing import Final
from requests.auth import HTTPBasicAuth

from app.config import Config
from app.util.http import HttpClient
from app.model.vrchat import AuthVerifyResponse


class AuthError(Exception):
    pass


class AuthManager:
    AUTH_DOMAIN: Final[str] = "api.vrchat.cloud"
    AUTH_COOKIE: Final[str] = "auth"

    def __init__(self, http: HttpClient, config: Config) -> None:
        self.http = http
        self.config = config
        self.cookie_file = config.cookie_file
        self.session = http.session

    @staticmethod
    def generate_totp(secret: str) -> str:
        totp = pyotp.TOTP(secret.replace(" ", ""))
        return totp.now()

    def save_session(self) -> None:
        cookies = []
        for cookie in self.session.cookies:
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
        with open(self.cookie_file, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False)

    def load_session(self) -> None:
        if not os.path.exists(self.cookie_file):
            return

        with open(self.cookie_file, "r", encoding="utf-8") as f:
            cookies = json.load(f)
            for c in cookies:
                self.session.cookies.set(
                    name=c["name"],
                    value=c["value"],
                    domain=c["domain"],
                    path=c.get("path", "/"),
                    secure=c.get("secure", False),
                    expires=c.get("expires"),
                )

    def has_valid_cookie(self) -> bool:
        now = time.time()
        for cookie in self.session.cookies:
            if cookie.domain.lstrip(".") == self.AUTH_DOMAIN.lstrip(".") and cookie.name == self.AUTH_COOKIE:
                if cookie.expires is None or cookie.expires > now:
                    return True
                else:
                    logging.info(
                        f"Cookie '{self.AUTH_COOKIE}' expired at {time.ctime(cookie.expires)}"
                    )
        return False


    def ensure_logged_in(self) -> bool:
        if not self.has_valid_cookie():
            return self.login()

        try:
            resp = self.http.request("GET", f"{self.config.BASE_URL}/auth/user")
            resp.raise_for_status()
            return True
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                return self.login()
            raise
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            return False

    def login(self) -> bool:
        try:
            response = self.http.request(
                "GET",
                f"{self.config.BASE_URL}/auth/user",
                auth=HTTPBasicAuth(self.config.username, self.config.password),
            )
            response.raise_for_status()
            data = response.json()

            if "requiresTwoFactorAuth" not in data or "totp" not in data["requiresTwoFactorAuth"]:
                logging.error("TOTP is not required in the response")
                return False

            if not self.has_valid_cookie():
                logging.error("Auth Cookie not found after login")
                return False

            current_otp = self.generate_totp(self.config.totp_secret)
            verify_resp = self.http.request(
                "POST",
                f"{self.config.BASE_URL}/auth/twofactorauth/totp/verify",
                data={"code": current_otp},
            )
            verify_resp.raise_for_status()

            verify_data = AuthVerifyResponse(**verify_resp.json())
            if not verify_data.verified:
                logging.error("TOTP verification failed")
                return False

            return True

        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            return False
