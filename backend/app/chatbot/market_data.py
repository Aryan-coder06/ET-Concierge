from __future__ import annotations

import time
from datetime import datetime, timezone
from threading import Lock
from typing import Any

import yfinance as yf


MARKET_SNAPSHOT_TTL_SECONDS = 120

MARKET_SYMBOLS = [
    {
        "symbol": "^NSEI",
        "label": "Nifty 50",
        "et_route": "ET Markets",
        "href": "https://economictimes.indiatimes.com/markets",
    },
    {
        "symbol": "^BSESN",
        "label": "Sensex",
        "et_route": "Markets Tracker",
        "href": "https://economictimes.indiatimes.com/marketstracker.cms",
    },
    {
        "symbol": "GC=F",
        "label": "Gold",
        "et_route": "ET Wealth",
        "href": "https://economictimes.indiatimes.com/wealth/etwealth/",
    },
]

ET_MARKET_LINKS = [
    {
        "label": "Market Mood",
        "href": "https://economictimes.indiatimes.com/markets/stock-market-mood",
        "note": "ET sentiment surface",
    },
    {
        "label": "Markets Tracker",
        "href": "https://economictimes.indiatimes.com/marketstracker.cms",
        "note": "Broad market dashboard",
    },
    {
        "label": "ET Portfolio",
        "href": "https://etportfolio.economictimes.indiatimes.com/",
        "note": "Tracking and watchlists",
    },
]

_snapshot_cache: dict[str, Any] = {"expires_at": 0.0, "payload": None}
_snapshot_lock = Lock()


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_history_points(series) -> list[float]:
    points: list[float] = []
    for item in series.dropna().tail(8).tolist():
        value = _coerce_float(item)
        if value is not None:
            points.append(round(value, 2))
    return points


def _fetch_symbol_snapshot(symbol_spec: dict[str, str]) -> dict[str, Any] | None:
    ticker = yf.Ticker(symbol_spec["symbol"])

    intraday = ticker.history(period="1d", interval="5m", auto_adjust=False, timeout=8)
    recent = ticker.history(period="5d", interval="1d", auto_adjust=False, timeout=8)

    intraday_close = intraday.get("Close") if not intraday.empty else None
    recent_close = recent.get("Close") if not recent.empty else None

    intraday_points = _build_history_points(intraday_close) if intraday_close is not None else []
    recent_points = _build_history_points(recent_close) if recent_close is not None else []

    if intraday_points:
        price = intraday_points[-1]
        sparkline = intraday_points
    elif recent_points:
        price = recent_points[-1]
        sparkline = recent_points
    else:
        return None

    previous_close = recent_points[-2] if len(recent_points) >= 2 else recent_points[-1]
    change = round(price - previous_close, 2)
    change_pct = round((change / previous_close) * 100, 2) if previous_close else 0.0

    return {
        "symbol": symbol_spec["symbol"],
        "label": symbol_spec["label"],
        "price": price,
        "change": change,
        "change_pct": change_pct,
        "sparkline": sparkline,
        "et_route": symbol_spec["et_route"],
        "href": symbol_spec["href"],
    }


def get_market_snapshot(*, force_refresh: bool = False) -> dict[str, Any]:
    now = time.time()

    with _snapshot_lock:
        cached_payload = _snapshot_cache.get("payload")
        if not force_refresh and cached_payload and now < _snapshot_cache["expires_at"]:
            return cached_payload

    items = [item for item in (_fetch_symbol_snapshot(spec) for spec in MARKET_SYMBOLS) if item]

    payload = {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "source_label": "Structured market snapshot",
        "items": items,
        "et_links": ET_MARKET_LINKS,
    }

    with _snapshot_lock:
        _snapshot_cache["payload"] = payload
        _snapshot_cache["expires_at"] = now + MARKET_SNAPSHOT_TTL_SECONDS

    return payload
