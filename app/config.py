import os
from typing import Final, Optional
from dotenv import load_dotenv


class ConfigError(Exception):
    pass


class Config:
    BASE_URL: Final[str] = "https://api.vrchat.cloud/api/1"
    COOKIE_FILE: Final[str] = "cookie.json"

    DEKAPU_GROUP_ID: Final[str] = "grp_5900a25d-0bb9-48d4-bab1-f3bd5c9a5e73"
    DEKAPU_WORLD_ID: Final[str] = "wrld_1af53798-92a3-4c3f-99ae-a7c42ec6084d"

    def __init__(self) -> None:
        load_dotenv(override=True)

        self.username: str = self._require_env("ID")
        self.password: str = self._require_env("PASSWORD")
        self.totp_secret: str = self._require_env("TOTP_SECRET")
        self.user_id: str = self._require_env("USER_ID")
        self.profile: int = int(os.getenv("PROFILE", 0))
        self.patlite_ip: Optional[str] = os.getenv("PATLITE_IP")

    @staticmethod
    def _require_env(key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise ConfigError(f"Environment variable {key} is not set")
        return value
