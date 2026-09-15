import itertools

from tradebot.strategies.adx_dmi import AdxDmiStrategy
from tradebot.strategies.asian_range_breakout import AsianRangeBreakoutStrategy
from tradebot.strategies.atr_channel_breakout import AtrChannelBreakoutStrategy
from tradebot.strategies.base import StrategyCandidate
from tradebot.strategies.bollinger_breakout import BollingerBreakoutStrategy
from tradebot.strategies.donchian_breakout import DonchianBreakoutStrategy
from tradebot.strategies.ma_crossover import MaCrossoverStrategy
from tradebot.strategies.macd import MacdStrategy
from tradebot.strategies.market_filter import MarketFilteredCandidate, ReferenceMarketConfig
from tradebot.strategies.mtf import MtfCandidate, ema_slope_filter
from tradebot.strategies.rsi_mean_reversion import RsiMeanReversionStrategy
from tradebot.strategies.stochastic_reversion import StochasticReversionStrategy
from tradebot.strategies.supertrend import SupertrendStrategy
from tradebot.strategies.volume_confirmed_breakout import VolumeConfirmedBreakoutStrategy
from tradebot.timeframe import Timeframe

RULE_SETS = [
    MaCrossoverStrategy,
    RsiMeanReversionStrategy,
    MacdStrategy,
    BollingerBreakoutStrategy,
    AtrChannelBreakoutStrategy,
    DonchianBreakoutStrategy,
    SupertrendStrategy,
    AdxDmiStrategy,
    StochasticReversionStrategy,
    AsianRangeBreakoutStrategy,
    VolumeConfirmedBreakoutStrategy,
]

TIMEFRAMES = [Timeframe.H1, Timeframe.M30, Timeframe.M15, Timeframe.M5]

# MTF Candidates: only the trend-following rule sets, where "only trade with the bigger trend" is
# conceptually sound. RSI Mean Reversion and Bollinger Breakout are excluded — RSI's whole point is
# catching short-term extremes that can legitimately happen against an HTF trend.
MTF_ENTRY_RULE_SETS = [MaCrossoverStrategy, MacdStrategy, AtrChannelBreakoutStrategy]
MTF_ENTRY_TIMEFRAME = Timeframe.M15
MTF_FILTER_TIMEFRAME = Timeframe.H1


def build_mtf_filters() -> dict[str, callable]:
    return {
        "ma_crossover": MaCrossoverStrategy(timeframe=MTF_FILTER_TIMEFRAME).generate_signals,
        "macd": MacdStrategy(timeframe=MTF_FILTER_TIMEFRAME).generate_signals,
        "ema_slope": ema_slope_filter,
    }


def build_mtf_candidates() -> list[MtfCandidate]:
    filters = build_mtf_filters()
    return [
        MtfCandidate(entry_cls(timeframe=MTF_ENTRY_TIMEFRAME), filter_fn, filter_name, MTF_FILTER_TIMEFRAME)
        for entry_cls, (filter_name, filter_fn) in itertools.product(MTF_ENTRY_RULE_SETS, filters.items())
    ]


# Market Filters: the six trend-following Rule Sets (unfiltered defaults), on the two Entry Timeframes
# rule-set-expansion ticket 07 specifies. Reused as-is for every Reference Market (tickets 07-09) —
# only the market's name, its relationship to gold, and its MT5 symbol (REFERENCE_MARKETS below)
# differ; the filter computation and candidate shape are identical.
MARKET_FILTER_ENTRY_RULE_SETS = [
    MaCrossoverStrategy,
    MacdStrategy,
    AtrChannelBreakoutStrategy,
    DonchianBreakoutStrategy,
    SupertrendStrategy,
    AdxDmiStrategy,
]
MARKET_FILTER_ENTRY_TIMEFRAMES = [Timeframe.M15, Timeframe.M5]
MARKET_FILTER_TIMEFRAME = Timeframe.H1

# name -> its fixed properties. "inverse": a rising Reference Market allows only short gold entries;
# "same": a rising Reference Market allows only long ones.
REFERENCE_MARKETS: dict[str, ReferenceMarketConfig] = {
    "DXY": ReferenceMarketConfig(symbol="DXYm", relationship="inverse"),
    "XAGUSD": ReferenceMarketConfig(symbol="XAGUSDm", relationship="same"),
}


def build_market_filtered_candidates() -> list[MarketFilteredCandidate]:
    return [
        MarketFilteredCandidate(entry_cls(timeframe=entry_timeframe), ema_slope_filter, market, MARKET_FILTER_TIMEFRAME, config.relationship)
        for entry_cls, entry_timeframe, (market, config) in itertools.product(
            MARKET_FILTER_ENTRY_RULE_SETS, MARKET_FILTER_ENTRY_TIMEFRAMES, REFERENCE_MARKETS.items()
        )
    ]


def build_candidates() -> list[StrategyCandidate]:
    single_timeframe = [rule_set(timeframe=tf) for rule_set, tf in itertools.product(RULE_SETS, TIMEFRAMES)]
    return single_timeframe + build_mtf_candidates() + build_market_filtered_candidates()
