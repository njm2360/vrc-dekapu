import logging
import json
import requests

from app.config import Config
from app.http import HttpClient
from app.auth import AuthManager
from app.model.vrchat import UserInfo, GroupInstance, InstanceInfo


class VRChatAPI:
    def __init__(self, http: HttpClient, auth: AuthManager, config: Config) -> None:
        self.http = http
        self.auth = auth
        self.config = config

    def _request_with_relogin(self, method: str, url: str, **kwargs):
        try:
            return self.http.request(method, url, **kwargs)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                logging.warning("認証エラー: 再ログインしてリトライ")
                if not self.auth.login():
                    raise
                return self.http.request(method, url, **kwargs)
            raise

    def get_user_info(self, user_id: str) -> UserInfo:
        resp = self._request_with_relogin(
            "GET", f"{self.config.BASE_URL}/users/{user_id}"
        )
        data = resp.json()
        logging.debug(json.dumps(data, indent=2, ensure_ascii=False))
        return UserInfo(**data)

    def get_group_instances(self, group_id: str) -> list[GroupInstance]:
        resp = self._request_with_relogin(
            "GET", f"{self.config.BASE_URL}/groups/{group_id}/instances"
        )
        data = resp.json()
        logging.debug(json.dumps(data, indent=2, ensure_ascii=False))
        return [GroupInstance(**gi) for gi in data]

    def get_instance_info(self, world_id: str, instance_id: str) -> InstanceInfo:
        resp = self._request_with_relogin(
            "GET", f"{self.config.BASE_URL}/instances/{world_id}:{instance_id}"
        )
        data = resp.json()
        logging.debug(json.dumps(data, indent=2, ensure_ascii=False))
        return InstanceInfo(**data)

    def get_group_posts(self, group_id: str) -> dict:
        resp = self._request_with_relogin(
            "GET", f"{self.config.BASE_URL}/groups/{group_id}/posts"
        )
        return resp.json()

    def invite_myself(self, world_id: str, instance_id: str) -> dict:
        resp = self._request_with_relogin(
            "POST", f"{self.config.BASE_URL}/invite/myself/to/{world_id}:{instance_id}"
        )
        return resp.json()
