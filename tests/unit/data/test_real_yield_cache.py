from datetime import datetime, timedelta, timezone

import pandas as pd

from tradebot.data.real_yield import RealYieldDownloadError, load_real_yield, refresh_real_yield_cache


def _fake_df(values: list[float], start: str = "2024-01-01") -> pd.DataFrame:
    index = pd.date_range(start, periods=len(values), freq="D")
    return pd.DataFrame({"close": values}, index=index)


def test_load_real_yield_fetches_and_caches_on_first_call(tmp_path):
    path = tmp_path / "real_yield.parquet"
    df = load_real_yield(path, fetch_csv=lambda: "observation_date,DFII10\n2024-01-02,1.50\n")

    assert not df.empty
    assert path.exists()


def test_load_real_yield_reads_from_cache_without_fetching(tmp_path):
    path = tmp_path / "real_yield.parquet"
    _fake_df([1.0, 2.0]).to_parquet(path)

    def _boom():
        raise AssertionError("should not fetch when a cache already exists")

    df = load_real_yield(path, fetch_csv=_boom)
    assert len(df) == 2


def test_load_real_yield_raises_when_no_cache_and_download_fails(tmp_path):
    path = tmp_path / "real_yield.parquet"

    def _boom():
        raise ConnectionError("network unreachable")

    try:
        load_real_yield(path, fetch_csv=_boom)
        assert False, "expected RealYieldDownloadError"
    except RealYieldDownloadError:
        pass
    assert not path.exists()


def test_refresh_real_yield_cache_skips_refetching_within_a_day(tmp_path):
    path = tmp_path / "real_yield.parquet"
    _fake_df([1.0]).to_parquet(path)

    def _boom():
        raise AssertionError("should not fetch again within the refresh interval")

    df, error = refresh_real_yield_cache(path, fetch_csv=_boom, now=datetime.now(timezone.utc))
    assert error is None
    assert len(df) == 1


def test_refresh_real_yield_cache_refetches_after_the_interval_elapses(tmp_path):
    path = tmp_path / "real_yield.parquet"
    _fake_df([1.0]).to_parquet(path)
    old_time = (datetime.now(timezone.utc) - timedelta(days=2)).timestamp()
    import os

    os.utime(path, (old_time, old_time))

    df, error = refresh_real_yield_cache(
        path, fetch_csv=lambda: "observation_date,DFII10\n2024-06-01,3.00\n2024-06-02,3.10\n", now=datetime.now(timezone.utc)
    )
    assert error is None
    assert list(df["close"]) == [3.00, 3.10]  # the cache was overwritten with the fresh download


def test_refresh_real_yield_cache_falls_back_to_the_stale_cache_on_a_failed_download(tmp_path):
    path = tmp_path / "real_yield.parquet"
    _fake_df([1.0, 2.0]).to_parquet(path)
    old_time = (datetime.now(timezone.utc) - timedelta(days=2)).timestamp()
    import os

    os.utime(path, (old_time, old_time))

    def _boom():
        raise ConnectionError("network unreachable")

    df, error = refresh_real_yield_cache(path, fetch_csv=_boom, now=datetime.now(timezone.utc))
    assert error is not None
    assert "network unreachable" in str(error)
    assert len(df) == 2  # the old cache is still usable — a failed refresh doesn't lose it


def test_refresh_real_yield_cache_raises_when_there_is_no_cache_and_the_download_fails(tmp_path):
    path = tmp_path / "real_yield.parquet"

    def _boom():
        raise ConnectionError("network unreachable")

    try:
        refresh_real_yield_cache(path, fetch_csv=_boom, now=datetime.now(timezone.utc))
        assert False, "expected RealYieldDownloadError"
    except RealYieldDownloadError:
        pass
