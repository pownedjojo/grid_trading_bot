import logging, requests
from typing import Dict
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class LokiHandler(logging.Handler):
    def __init__(
        self, 
        url: str, 
        tags: Dict[str, str], 
        version: str = "1"
    ):
        super().__init__()
        self.url = url
        self.tags = tags
        self.version = version
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self.session.mount("http://", HTTPAdapter(max_retries=retries))

    def emit(self, record: logging.LogRecord) -> None:
        log_entry = {
            "streams": [
                {
                    "stream": self.tags,
                    "values": [
                        [str(int(record.created * 1e9)), self.format(record)]
                    ],
                }
            ]
        }

        try:
            response = self.session.post(self.url, json=log_entry, timeout=2)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Failed to send log to Loki: {e}")