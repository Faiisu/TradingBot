import pandas as pd
import pytest

from tradebot.data.real_yield import FRED_SERIES_ID, RealYieldDownloadError, fetch_real_yield


def _csv(rows: str) -> str:
    return "observation_date,DFII10\n" + rows


def test_fetch_real_yield_shifts_each_value_to_become_usable_two_days_later():
    csv_text = _csv("2024-01-02,1.50\n2024-01-03,1.55\n")
    df = fetch_real_yield(fetch_csv=lambda: csv_text)

    assert list(df.index) == [pd.Timestamp("2024-01-04"), pd.Timestamp("2024-01-05")]
    assert list(df["close"]) == [1.50, 1.55]


def test_fetch_real_yield_drops_blank_observations():
    csv_text = _csv("2024-01-02,1.50\n2024-01-03,.\n2024-01-04,1.60\n")
    df = fetch_real_yield(fetch_csv=lambda: csv_text)

    assert list(df["close"]) == [1.50, 1.60]


def test_fetch_real_yield_reports_a_download_failure_clearly():
    def _boom():
        raise ConnectionError("network unreachable")

    with pytest.raises(RealYieldDownloadError, match="network unreachable"):
        fetch_real_yield(fetch_csv=_boom)


def test_fetch_real_yield_defaults_to_the_real_fred_series():
    assert FRED_SERIES_ID == "DFII10"
