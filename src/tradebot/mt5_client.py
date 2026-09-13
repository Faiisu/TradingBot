from contextlib import contextmanager

from tradebot.config import Mt5Config, load_mt5_config


class Mt5ConnectionError(RuntimeError):
    pass


class Mt5NotDemoAccountError(RuntimeError):
    pass


@contextmanager
def mt5_session(config: Mt5Config | None = None):
    """Connects to the MT5 terminal for the confirmed demo account, and refuses to proceed if the
    connected account is not a demo account (defense-in-depth; the primary safety control is that
    load_mt5_config() only ever reads MT5_DEMO_* env vars, so a live account can't be passed in here
    at all — see ADR 0001)."""
    import MetaTrader5 as mt5

    config = config or load_mt5_config()

    if not mt5.initialize(path=config.terminal_path, login=config.login, password=config.password, server=config.server):
        raise Mt5ConnectionError(f"MT5 initialize() failed: {mt5.last_error()}")

    try:
        account = mt5.account_info()
        if account is None:
            raise Mt5ConnectionError(f"MT5 account_info() failed: {mt5.last_error()}")
        if account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
            raise Mt5NotDemoAccountError(
                "Connected MT5 account is not a demo account. Phase 1 refuses to run against a live account."
            )
        yield mt5
    finally:
        mt5.shutdown()
