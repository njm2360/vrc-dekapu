import requests
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class HttpClient:

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:142.0) "
            "Gecko/20100101 Firefox/142.0"
        )
    }

    def __init__(self) -> None:
        self.session = self._create_session()

    def _create_session(self) -> Session:
        session = requests.session()
        session.headers.update(self.DEFAULT_HEADERS)

        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        resp = self.session.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp
