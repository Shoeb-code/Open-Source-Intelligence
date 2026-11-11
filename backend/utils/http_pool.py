from contextlib import contextmanager
import threading
from typing import Dict, Iterator
from urllib.parse import urlparse
import httpx

_ORIGINAL_HTTPX_CLIENT = httpx.Client
_client_lock = threading.Lock()
_shared_clients: Dict[float, httpx.Client] = {}


@contextmanager
def borrow_http_client(
    timeout_seconds: float = 10.0,
    connect_timeout: float = 4.0,
    follow_redirects: bool = True,
) -> Iterator[httpx.Client]:
    """
    Yields a reusable connection-pooled httpx.Client without closing the pool across threads.
    When tests monkeypatch httpx.Client, yields a fresh context-managed mock client cleanly.
    """
    if httpx.Client is not _ORIGINAL_HTTPX_CLIENT:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=follow_redirects) as mock_client:
            yield mock_client
        return

    with _client_lock:
        client = _shared_clients.get(timeout_seconds)
        if client is None or client.is_closed:
            client = httpx.Client(
                timeout=httpx.Timeout(timeout_seconds, connect=connect_timeout),
                limits=httpx.Limits(max_connections=40, max_keepalive_connections=20),
                follow_redirects=True,
            )
            _shared_clients[timeout_seconds] = client
    yield client


class DomainConcurrencyLimiter:
    """Caps concurrent outbound HTTP requests per hostname to avoid rate-limiting and 429 blocks."""

    def __init__(self, max_per_domain: int = 2):
        self._max = max(1, max_per_domain)
        self._lock = threading.Lock()
        self._semaphores: Dict[str, threading.Semaphore] = {}

    @contextmanager
    def acquire(self, url: str):
        host = (urlparse(url).netloc or "default").lower()
        with self._lock:
            sem = self._semaphores.get(host)
            if sem is None:
                sem = threading.Semaphore(self._max)
                self._semaphores[host] = sem
        sem.acquire()
        try:
            yield
        finally:
            sem.release()
