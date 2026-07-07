from dataclasses import dataclass, asdict
from typing import Dict, List
import pandas as pd
import yfinance as yf

from .option_signal_engine import _trend_score, _fundamental_score, _signal_from_scores


START_CAPITAL_DEFAULT = 1000.0


@dataclass
class Trade:
    ticker: str
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    shares: float
    pnl: float
    pnl_pct: float


def _safe_history(ticker: str, period: str = "3y", interval: str = "1d") -> pd.DataFrame:
    try:
        df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
        if df is None or df.empty:
            return pd.DataFrame()
        return df.dropna(subset=["Close"]).copy()
    except Exception:
        return pd.DataFrame()


def _derive_signal_from_close_window(ticker: str, close_window: pd.Series, option_type: str = "call") -> str:
    # technical score from rolling window
    tech = _trend_score(close_window) if len(close_window) >= 60 else {
        "tech_score": 0.0, "rsi14": 50.0, "macd_hist": 0.0
    }

    # fundamental score (static-ish)
    fund = _fundamental_score(ticker)
    fund_score = float(fund.get("fund_score", 0.0) or 0.0)

    # no live greeks in historical loop -> neutral placeholders
    sig = _signal_from_scores(
        option_type=option_type,
        tech_score=float(tech.get("tech_score", 0.0)),
        fund_score=fund_score,
        delta=0.5,   # neutral bullish call proxy
        theta=0.0
    )
    return sig


def run_backtest_for_ticker(
    ticker: str,
    start_capital: float = START_CAPITAL_DEFAULT,
    option_type: str = "call",
) -> Dict:
    df = _safe_history(ticker, period="1y", interval="1d")
    if df.empty or len(df) < 80:
        return {
            "ticker": ticker,
            "error": "Insufficient historical data",
            "start_capital": start_capital,
            "end_value": start_capital,
            "return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "trades": [],
            "equity_curve": [],
        }

    cash = float(start_capital)
    shares = 0.0
    in_position = False
    entry_price = 0.0
    entry_date = None
    trades: List[Trade] = []
    equity_curve = []

    closes = df["Close"]

    warmup = 30
    for i in range(warmup, len(df)):
        date = str(df.index[i].date())
        px = float(closes.iloc[i])

        window = closes.iloc[max(0, i-120):i+1]
        signal = _derive_signal_from_close_window(ticker, window, option_type=option_type)

        # Rules:
        # BUY -> open long if flat
        # SELL -> close long if in position
        # HOLD -> do nothing
        if signal == "BUY" and not in_position and cash > 0:
            shares = cash / px
            cash = 0.0
            in_position = True
            entry_price = px
            entry_date = date

        elif signal == "SELL" and in_position:
            exit_value = shares * px
            pnl = exit_value - (shares * entry_price)
            pnl_pct = (px / entry_price - 1.0) * 100.0 if entry_price > 0 else 0.0

            trades.append(Trade(
                ticker=ticker,
                entry_date=entry_date,
                entry_price=entry_price,
                exit_date=date,
                exit_price=px,
                shares=shares,
                pnl=pnl,
                pnl_pct=pnl_pct
            ))

            cash = exit_value
            shares = 0.0
            in_position = False
            entry_price = 0.0
            entry_date = None

        equity = cash + (shares * px if in_position else 0.0)
        equity_curve.append({"date": date, "equity": equity, "signal": signal, "price": px})

    # liquidate at end
    final_px = float(closes.iloc[-1])
    if in_position:
        exit_value = shares * final_px
        pnl = exit_value - (shares * entry_price)
        pnl_pct = (final_px / entry_price - 1.0) * 100.0 if entry_price > 0 else 0.0

        trades.append(Trade(
            ticker=ticker,
            entry_date=entry_date,
            entry_price=entry_price,
            exit_date=str(df.index[-1].date()),
            exit_price=final_px,
            shares=shares,
            pnl=pnl,
            pnl_pct=pnl_pct
        ))
        cash = exit_value
        shares = 0.0

    end_value = cash
    ret_pct = (end_value / start_capital - 1.0) * 100.0 if start_capital > 0 else 0.0

    eq_df = pd.DataFrame(equity_curve)
    if eq_df.empty:
        max_dd = 0.0
    else:
        eq_df["roll_max"] = eq_df["equity"].cummax()
        eq_df["dd"] = eq_df["equity"] / eq_df["roll_max"] - 1.0
        max_dd = float(eq_df["dd"].min() * 100.0)

    win_rate = 0.0
    if trades:
        wins = sum(1 for t in trades if t.pnl > 0)
        win_rate = 100.0 * wins / len(trades)

    return {
        "ticker": ticker,
        "start_capital": start_capital,
        "end_value": round(end_value, 2),
        "return_pct": round(ret_pct, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "trade_count": len(trades),
        "win_rate_pct": round(win_rate, 2),
        "trades": [asdict(t) for t in trades][-20:],
        "equity_curve": equity_curve[-120:],
    }


def run_backtest_multi(
    tickers: List[str],
    start_capital: float = START_CAPITAL_DEFAULT,
    option_type: str = "call",
) -> Dict:
    results = []
    for tk in tickers:
        results.append(run_backtest_for_ticker(
            ticker=tk.strip().upper(),
            start_capital=start_capital,
            option_type=option_type
        ))

    summary = {
        "tickers": tickers,
        "start_capital_per_ticker": start_capital,
        "results": results
    }
    return summary
