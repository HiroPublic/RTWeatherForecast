from pathlib import Path

from weather_update.open_meteo import OpenMeteoClient


class StubHttpClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.urls = []

    def get_json(self, url: str) -> dict:
        self.urls.append(url)
        return self.responses.pop(0)


def test_geocode_retries_with_city_alias(tmp_path: Path) -> None:
    http_client = StubHttpClient(
        [
            {},
            {
                "results": [
                    {
                        "latitude": 45.4372,
                        "longitude": 12.3346,
                        "timezone": "Europe/Rome",
                        "country": "Italy",
                        "country_code": "IT",
                    }
                ]
            },
        ]
    )
    client = OpenMeteoClient(cache_dir=tmp_path, http_client=http_client)

    location = client.geocode("ベネチア", "イタリア")

    assert location.latitude == 45.4372
    assert "name=Venice" in http_client.urls[1]
