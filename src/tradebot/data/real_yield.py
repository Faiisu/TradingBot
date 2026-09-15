from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path

import httpx
import pandas as pd

FRED_SERIES_ID = "DFII10"  # 10-Year Treasury Inflation-Indexed Security, Constant Maturity

# FRED publishes a day's value after that day closes — using it before this offset would let the
# Backtest see the future (see CONTEXT.md's Market Filter entry and rule-set-expansion ticket 09).
PUBLICATION_LAG_DAYS = 2


class RealYieldDownloadError(RuntimeError):
    pass


def _fred_csv_url(series_id: str) -> str:
    return f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"


def _default_fetch_csv(series_id: str):
    def _fetch() -> str:
        response = httpx.get(_fred_csv_url(series_id), timeout=30.0)
        response.raise_for_status()
        return response.text

    return _fetch


def fetch_real_yield(series_id: str = FRED_SERIES_ID, fetch_csv=None) -> pd.DataFrame:
    """Downloads FRED's daily real-yield series and re-indexes it by the moment each value actually
    becomes usable (its own date + PUBLICATION_LAG_DAYS, at 00:00 UTC) rather than the date it
    describes — so every existing no-lookahead mechanism (align_htf_signal) treats this exactly like
    any other Reference Market's own OHLCV, with no special-casing. A download failure is raised
    clearly, not silently swallowed — callers decide whether that should fail loud (Backtest) or fall
    back to a stale cache (Paper Trading)."""
    fetch_csv = fetch_csv or _default_fetch_csv(series_id)
    try:
        csv_text = fetch_csv()
    except Exception as error:
        raise RealYieldDownloadError(f"Failed to download the real-yield series from FRED: {error}") from error

    raw = pd.read_csv(StringIO(csv_text))
    raw.columns = ["date", "close"]
    raw["close"] = pd.to_numeric(raw["close"], errors="coerce")
    raw = raw.dropna(subset=["close"])

    usable_from = pd.to_datetime(raw["date"]) + pd.Timedelta(days=PUBLICATION_LAG_DAYS)
    return pd.DataFrame({"close": raw["close"].to_numpy()}, index=pd.DatetimeIndex(usable_from, name="time"))


def load_real_yield(path: Path, series_id: str = FRED_SERIES_ID, fetch_csv=None) -> pd.DataFrame:
    """Backtest-side loading: cache-or-fetch, same shape as data/cache.py's load_ohlcv. A download
    failure with no existing cache is fatal (RealYieldDownloadError propagates) — a Backtest run
    should fail loud rather than silently proceed without this Reference Market's data."""
    if path.exists():
        return pd.read_parquet(path)

    df = fetch_real_yield(series_id=series_id, fetch_csv=fetch_csv)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df


def refresh_real_yield_cache(
    path: Path,
    series_id: str = FRED_SERIES_ID,
    fetch_csv=None,
    now: datetime | None = None,
    refresh_interval: timedelta = timedelta(days=1),
) -> tuple[pd.DataFrame, RealYieldDownloadError | None]:
    """Paper-Trading-side refresh: re-downloads at most once per `refresh_interval`, and falls back to
    the existing (now-stale) cache on a failed download rather than crashing the loop — "the rest of
    the Ensemble keeps running" (rule-set-expansion ticket 09). Returns (data, error); `error` is None
    on success, or the RealYieldDownloadError from a failed refresh whose stale cache was still usable.
    Raises RealYieldDownloadError only when there is no cache at all to fall back to."""
    now = now or datetime.now(timezone.utc)

    if path.exists():
        cached_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if now - cached_at < refresh_interval:
            return pd.read_parquet(path), None

    try:
        df = fetch_real_yield(series_id=series_id, fetch_csv=fetch_csv)
    except RealYieldDownloadError as error:
        if path.exists():
            return pd.read_parquet(path), error
        raise

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df, None
