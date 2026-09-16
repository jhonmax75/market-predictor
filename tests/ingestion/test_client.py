from __future__ import annotations

import pytest

from market_predictor.ingestion.client import (
    BybitAPIError,
    BybitClient,
    BybitClientConfig,
)


def test_client_builds_expected_url():
    client = BybitClient(BybitClientConfig(limit=84))

    url = client._build_url(start=1000, end=2000)

    assert "category=spot" in url
    assert "symbol=BTCUSDT" in url
    assert "interval=5" in url
    assert "limit=84" in url
    assert "start=1000" in url
    assert "end=2000" in url


def test_client_rejects_invalid_limit():
    with pytest.raises(ValueError):
        BybitClientConfig(limit=1001)


def test_client_rejects_invalid_attempts():
    with pytest.raises(ValueError):
        BybitClientConfig(max_attempts=0)


def test_api_error_is_not_retried(monkeypatch):
    client = BybitClient(
        BybitClientConfig(
            max_attempts=4,
            backoff_seconds=0,
        )
    )

    calls = 0

    def fake_request(_url):
        nonlocal calls
        calls += 1

        return {
            "retCode": 10001,
            "retMsg": "invalid request",
        }

    monkeypatch.setattr(client, "_request_once", fake_request)

    with pytest.raises(BybitAPIError):
        client.get_kline()

    assert calls == 1


def test_empty_page_stops_pagination(monkeypatch):
    client = BybitClient(
        BybitClientConfig(
            limit=10,
            backoff_seconds=0,
        )
    )

    monkeypatch.setattr(
        client,
        "get_kline",
        lambda **_kwargs: {
            "retCode": 0,
            "result": {"list": []},
        },
    )

    pages = list(
        client.iter_kline_pages(
            start=0,
            end=60_000,
        )
    )

    assert len(pages) == 1
