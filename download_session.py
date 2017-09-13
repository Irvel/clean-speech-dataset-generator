from requests.packages.urllib3.util.retry import Retry
from requests.exceptions import ConnectionError
from urllib3.exceptions import ReadTimeoutError

import requests

MAX_RETRIES = 17
BACKOFF_FACTOR = 0.2  # Sleep for [0.0s, 0.4s, 0.6s, ...] between retries
POOL_CONNECTIONS = 20
POOL_MAX_SIZE = 50


def make_session():
    session = requests.Session()
    retry_policy = Retry(total=MAX_RETRIES,
                         backoff_factor=BACKOFF_FACTOR,
                         status_forcelist=[500, 502, 503, 504])  # Only retry on these status_codes

    http_adapter = requests.adapters.HTTPAdapter(pool_connections=POOL_CONNECTIONS,
                                                 pool_maxsize=POOL_MAX_SIZE,
                                                 max_retries=retry_policy)

    session.mount("http://", http_adapter)
    session.mount("https://", http_adapter)

    return session


def get_download_exceptions():
    return ConnectionError, ReadTimeoutError
