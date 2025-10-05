import logging
from typing import Optional

from app.api.vrchat_api import VRChatAPI
from app.model.vrchat import GroupPostInfo


class PostManager:
    def __init__(self, vrc_api: VRChatAPI, group_id: str):
        self.vrc_api = vrc_api
        self.group_id = group_id
        self.last_post_id: Optional[str] = None

    def check_new_post(self) -> Optional[GroupPostInfo]:
        posts = self.vrc_api.get_group_posts(self.group_id, n_count=1)
        if not posts:
            return None

        newest_post = posts[0]
        if newest_post.id != self.last_post_id:
            if self.last_post_id is not None:
                logging.info(
                    f"Found new post:\nTitle: {newest_post.title}\nText: {newest_post.text}"
                )
                self.last_post_id = newest_post.id
                return newest_post

            self.last_post_id = newest_post.id

        return None
