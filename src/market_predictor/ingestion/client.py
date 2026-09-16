from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class BybitClientError(RuntimeError):
    """Base error for Bybit ingestion failures."""


class BybitAPIError(BybitClientError):
    """Raised when Bybit returns a non-zero retCode."""


class BybitHTTPError(BybitClientError):
    """Raised when an HTTP error cannot be retried successfully."""


@dataclass(frozen=True)
class BybitClientConfig:
    base_url: str = "https://api.bybit.com"
    category: str = "spot"
    symbol: str = "BTCUSDT"
    interval: str = "5"
    limit: int = 1000
    timeout_seconds: float = 15.0
    max_attempts: int = 4
    backoff_seconds: float = 1.0
    jitter: bool = True

    def __post_init__(self) -> None:
        if self.limit < 1 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")

        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        if self.backoff_seconds < 0:
            raise ValueError("backoff_seconds cannot be negative")


class BybitClient:
    """Minimal Bybit Spot REST client for historical kline ingestion."""

    ENDPOINT = "/v5/market/kline"

    def __init__(
        self,
        config: BybitClientConfig | None = None,
    ) -> None:
        self.config = config or BybitClientConfig()

    def _build_url(
        self,
        *,
        start: int | None = None,
        end: int | None = None,
    ) -> str:
        params: dict[str, Any] = {
            "category": self.config.category,
            "symbol": self.config.symbol,
            "interval": self.config.interval,
            "limit": self.config.limit,
        }

        if start is not None:
            params["start"] = start

        if end is not None:
            params["end"] = end

        return f"{self.config.base_url}{self.ENDPOINT}?{urlencode(params)}"

    def _sleep_before_retry(self, attempt: int) -> None:
        if self.config.backoff_seconds <= 0:
            return

        delay = self.config.backoff_seconds * (2 ** (attempt - 1))

        if self.config.jitter:
            delay += random.uniform(0, self.config.backoff_seconds)

        time.sleep(delay)

    def _request_once(self, url: str) -> dict[str, Any]:
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "market-predictor/0.3",
            },
            method="GET",
        )

        try:
            with urlopen(
                request,
                timeout=self.config.timeout_seconds,
            ) as response:
                payload = response.read().decode("utf-8")

        except HTTPError as exc:
            if exc.code in {429, 500, 502, 503, 504}:
                raise

            raise BybitHTTPError(
                f"Non-retryable HTTP error: {exc.code}"
            ) from exc

        except URLError as exc:
            raise ConnectionError(str(exc)) from exc

        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise BybitClientError(
                "Bybit returned invalid JSON"
            ) from exc

        if not isinstance(data, dict):
            raise BybitClientError(
                "Bybit response must be a JSON object"
            )

        return data

    def get_kline(
        self,
        *,
        start: int | None = None,
        end: int | None = None,
    ) -> dict[str, Any]:
        """Fetch one raw Bybit kline response."""

        url = self._build_url(start=start, end=end)

        last_error: Exception | None = None

        for attempt in range(1, self.config.max_attempts + 1):
            try:
                response = self._request_once(url)

                ret_code = response.get("retCode")

                if ret_code != 0:
                    raise BybitAPIError(
                        f"Bybit retCode={ret_code}: {response.get('retMsg', 'unknown error')}"
                    )

                return response

            except BybitAPIError:
                raise

            except HTTPError as exc:
                last_error = exc

                if attempt == self.config.max_attempts:
                    raise BybitHTTPError(
                        f"HTTP retry limit exceeded: {exc.code}"
                    ) from exc

                self._sleep_before_retry(attempt)

            except (ConnectionError, URLError) as exc:
                last_error = exc

                if attempt == self.config.max_attempts:
                    raise BybitClientError(
                        "Network retry limit exceeded"
                    ) from exc

                self._sleep_before_retry(attempt)

        raise BybitClientError(
            "Request failed"
        ) from last_error

    def iter_kline_pages(
        self,
        *,
        start: int,
        end: int,
    ):
        """
        Yield raw Bybit responses for a temporal interval.

        The API may return candles in reverse chronological order.
        Pagination is controlled independently from response ordering.
        """

        if start >= end:
            raise ValueError("start must be smaller than end")

        current_start = start
        interval_ms = int(self.config.interval) * 60_000
        page_span_ms = interval_ms * self.config.limit

        while current_start < end:
            current_end = min(
                end,
                current_start + page_span_ms - interval_ms,
            )

            response = self.get_kline(
                start=current_start,
                end=current_end,
            )

            yield response

            result = response.get("result", {})
            rows = result.get("list", [])

            if not rows:
                break

            timestamps: list[int] = []

            for row in rows:
                if not row:
                    continue

                try:
                    timestamps.append(int(row[0]))
                except (TypeError, ValueError):
                    continue

            if not timestamps:
                break

            latest_timestamp = max(timestamps)
            next_start = latest_timestamp + interval_ms

            if next_start <= current_start:
                raise BybitClientError(
                    "Pagination did not advance"
                )

            current_start = next_start
