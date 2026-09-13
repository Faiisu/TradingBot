import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


@dataclass(frozen=True)
class Mt5Config:
    login: int
    password: str
    server: str
    terminal_path: str


def load_mt5_config() -> Mt5Config:
    """Loads MT5_DEMO_* only. There is no code path anywhere that can read a live-account credential."""
    load_dotenv(_ENV_PATH)

    login = os.environ.get("MT5_DEMO_LOGIN")
    password = os.environ.get("MT5_DEMO_PASSWORD")
    server = os.environ.get("MT5_DEMO_SERVER")
    terminal_path = os.environ.get("MT5_TERMINAL_PATH")

    missing = [
        name
        for name, value in [
            ("MT5_DEMO_LOGIN", login),
            ("MT5_DEMO_PASSWORD", password),
            ("MT5_DEMO_SERVER", server),
            ("MT5_TERMINAL_PATH", terminal_path),
        ]
        if not value
    ]
    if missing:
        raise RuntimeError(
            f"Missing required demo-account config: {', '.join(missing)}. "
            f"Copy .env.example to .env and fill in your Exness DEMO account details."
        )

    return Mt5Config(login=int(login), password=password, server=server, terminal_path=terminal_path)
