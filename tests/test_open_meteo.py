import ssl
from urllib.error import URLError

import certifi

from weather_update.open_meteo import JsonHttpClient


def test_json_http_client_uses_certifi_bundle() -> None:
    client = JsonHttpClient()

    assert isinstance(client.ssl_context, ssl.SSLContext)
    assert certifi.where()


def test_json_http_client_retries_retryable_url_errors(monkeypatch) -> None:
    attempts = {"count": 0}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return b'{"ok": true}'

    def fake_urlopen(request, timeout, context):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise URLError(TimeoutError("handshake timed out"))
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    client = JsonHttpClient(max_retries=3, retry_backoff_seconds=0)

    payload = client.get_json("https://example.com/test.json")

    assert payload == {"ok": True}
    assert attempts["count"] == 3
