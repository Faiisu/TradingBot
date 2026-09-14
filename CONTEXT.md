# TradeBot

An automated trading system for Gold (XAUUSD), starting with strategy research (backtesting) and paper trading before any real-money execution.

## Language

**Instrument**:
The single tradable symbol this system targets: XAUUSD (Gold vs. US Dollar), traded as a CFD/forex-style instrument via MetaTrader 5.
_Avoid_: Gold, ticker, symbol (when ambiguous)

**Trading Platform**:
MetaTrader 5 (MT5) — the terminal application and Python API (`MetaTrader5` package) used for both historical price data and order execution. Requires a running, logged-in MT5 terminal.
_Avoid_: broker (the platform is distinct from the broker account connected to it)

**Rule Set**:
One specific trading logic (e.g. MACD 12/26/9, Donchian breakout) with a single fixed set of default parameters, deciding at each bar close whether to be long, short or flat. Every Rule Set trades both directions and exits only by changing that state or by the shared Risk Controls. A Rule Set is not tested on its own — it becomes one Strategy Candidate per Timeframe.
_Avoid_: strategy, indicator (an indicator is an input to a Rule Set, not the Rule Set itself), setup

**Strategy Candidate**:
One specific, fully-defined signal-generating unit evaluated against all others before any one is trusted. Three shapes exist: a **Single-Timeframe Candidate** is a `(rule set, Timeframe)` pair (e.g. "50/200 MA crossover on H1"); an **MTF Candidate** (see below) is a `(rule set, Entry Timeframe, Trend Filter)` triple; a **Market-Filtered Candidate** is a `(rule set, Entry Timeframe, Market Filter)` triple. A candidate carries at most one filter — Trend and Market Filters are never stacked. Changing any part of a shape produces a distinct Strategy Candidate.
_Avoid_: strategy (when referring to the general concept vs. a specific candidate), algorithm, bot logic

**MTF Candidate**:
A Strategy Candidate that only takes a rule set's entry signal on its Entry Timeframe when a Trend Filter computed on a higher Timeframe agrees with that signal's direction (e.g. only take an M15 MACD long entry when the H1 Trend Filter also says "up"). Distinct from a Single-Timeframe Candidate, which ignores every timeframe but its own.
_Avoid_: multi-timeframe strategy (too vague — doesn't say which timeframe does what)

**Trend Filter**:
An indicator computed on a higher Timeframe than an MTF Candidate's Entry Timeframe, reduced to a single up/down direction. Three Trend Filter variants are evaluated as separate MTF Candidates: MA Crossover state, EMA(50) slope, and MACD state — the Performance Metric decides which filter is best, rather than that being fixed in advance.
_Avoid_: confirmation, signal (a Trend Filter gates a candidate's entries, it never produces a trade by itself)

**Reference Market**:
A market this system watches but never trades, used only as input to a Market Filter: the US Dollar Index (DXY), silver (XAGUSD), and the US 10-year real yield. The Instrument remains the only thing traded.
_Avoid_: instrument (reserved for XAUUSD), external symbol, correlated asset

**Market Filter**:
A direction computed from a Reference Market that gates a Rule Set's entries the same way a Trend Filter does — an entry is only taken when the Market Filter agrees with it. Each Reference Market has a fixed relationship to gold: a falling dollar or falling real yields favors long gold (inverse), rising silver favors long gold (same direction). Differs from a Trend Filter only in its source: a Trend Filter reads gold on a higher Timeframe, a Market Filter reads a different market. A Reference Market value is only usable from the moment it would actually have been published, never from the date it describes. A Market Filter whose latest usable value is more than 3 business days old has **no opinion**: its candidate opens no new trades until fresh data arrives, while trades already open exit normally.
_Avoid_: macro filter, correlation filter, signal

**Entry Timeframe**:
The Timeframe an MTF Candidate actually trades on — where entries, stops, and exits are all evaluated (H1 filters, M15 enters, in the current Trend Filter design).
_Avoid_: lower timeframe, execution timeframe

**Ensemble**:
The set of Strategy Candidates that Paper Trading runs: every candidate that clears a minimum Performance Metric bar (not a fixed count) over the full history. At most one member is admitted per `(Rule Set, Entry Timeframe)` — among an unfiltered candidate and its filtered variants, only the one with the best Performance Metric enters, so near-identical candidates can't silently stack the same position. That selection rule, including the one-per-pair limit, is exactly what Walk-Forward Validation checks — the Ensemble used for Paper Trading is the same rule applied to all available history, not an extra filter on top. Each member runs independently and simultaneously, trading an equal slice of account capital. Candidates are not blended into a single signal — they can hold conflicting positions at the same time.
_Avoid_: portfolio (ambiguous with account/position portfolio), combined strategy, voting

**Walk-Forward Validation**:
Checking whether the way the Ensemble is chosen actually works on data it has never seen. History is cut into consecutive Test Windows; before each one, the Ensemble is chosen using only everything earlier (the Selection Window, which grows each step), then scored on that Test Window alone. The Test Window results, joined end to end, are the out-of-sample record. It validates the selection rule, not any single Strategy Candidate. It **passes** when that joined record has a Performance Metric above zero; Paper Trading can still be started when it fails, but only as a deliberate, acknowledged choice.
_Avoid_: backtest (a Backtest scores on the same data used to choose), cross-validation, out-of-sample test (one fixed holdout)

**Selection Window**:
The history, from the start of the data up to a Test Window, used to choose that step's Ensemble. Never overlaps the Test Window it chooses for.
_Avoid_: training window, in-sample period

**Test Window**:
A stretch of history after its Selection Window, used only to score the Ensemble chosen before it. No decision is ever made using a Test Window's data. Each Test Window's Ensemble starts with no open positions, and anything still open when the window ends is closed at its last bar — so every window's score comes only from its own decisions.
_Avoid_: validation set, holdout, out-of-sample period

**Performance Metric**:
The measure used to rank Strategy Candidates: return % adjusted/penalized by max drawdown, not raw return % alone. A candidate with a smaller drawdown beats one with a larger raw return but a larger drawdown.
_Avoid_: score, results, % output

**Risk Controls**:
Position sizing and stop-loss rules applied uniformly to every Strategy Candidate during Backtest and Paper Trading, so Performance Metric comparisons reflect risk-adjusted trading rather than raw signal accuracy.
_Avoid_: money management, risk management (used too loosely elsewhere)

**Broker**:
The financial institution providing the MT5 account/server that the Trading Platform connects to. This project uses Exness.
_Avoid_: platform (see Trading Platform, which is distinct)

**Timeframe**:
The candle interval a Strategy Candidate trades on: H1, 30m, 15m, or 5m. Phase 1 evaluates candidates across multiple Timeframes rather than committing to one upfront.
_Avoid_: period, interval, resolution

**Backtest**:
Running a Strategy Candidate against historical XAUUSD price data to simulate trades and measure performance. No live connection, no account, no real-time data.
_Avoid_: simulation (too broad), test (too broad)

**Paper Trading**:
Running a Strategy Candidate against live/streaming XAUUSD prices with simulated (non-real-money) order execution. Distinct from Backtest in that it uses real-time data and tests real-time behavior (latency, slippage assumptions, live data gaps).
_Avoid_: demo trading, simulated trading, sandbox trading

**Live Trading**:
Real-money execution against a real account. Explicitly out of scope for Phase 1 of this project.
_Avoid_: production trading, real trading

**Phase 1**:
The current scope of the project: Backtest and Paper Trading only, no Live Trading. Connects exclusively to a dedicated Exness demo account — the user's existing live account is never referenced in code or config until a future, not-yet-defined phase covers the transition to Live Trading.
_Avoid_: MVP, v1 (too generic — this project uses "Phase 1" specifically to mean "no real money")
