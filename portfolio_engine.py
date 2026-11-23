"""Auditable calculations for the Hyperscalers / Semiconductors model dashboard.

Research-only: daily-rebalanced TARGET exposures, not actual Interactive Brokers fills.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd

TICKERS = ["AMZN", "MSFT", "GOOGL", "SMH", "DRAM", "SPY"]
LONGS = ["AMZN", "MSFT", "GOOGL"]
SHORTS = {"SMH": .75, "DRAM": .25}

@dataclass(frozen=True)
class Settings:
    gross: float = 100_000.0
    long_weight: float = 0.50       # shares of gross; short is remainder
    borrow_smh_pct: float = 0.60    # percent per annum, illustrative
    borrow_dram_pct: float = 1.70   # percent per annum, illustrative
    margin_debit: float = 0.0
    margin_apr_pct: float = 5.0
    execution_cost: float = 100.0  # estimate for FULL round trip, charged at start
    nav: float = 1_000_000.0
    risk_budget_pct: float = 1.0

    @property
    def long_dollars(self):
        return self.gross * self.long_weight

    @property
    def short_dollars(self):
        return self.gross * (1 - self.long_weight)

    @property
    def budget_dollars(self):
        return self.nav * self.risk_budget_pct / 100

    @property
    def borrow_rate(self):
        return (SHORTS["SMH"] * self.borrow_smh_pct + SHORTS["DRAM"] * self.borrow_dram_pct) / 100


def prices_to_returns(close: pd.DataFrame, adjusted: pd.DataFrame) -> pd.DataFrame:
    """Align raw Close and dividend-adjusted Close; daily returns with exact basket weights.

    Adj Close includes distributions; comparing with Close exposes approximate distribution P&L.
    """
    close = close[TICKERS].apply(pd.to_numeric, errors="coerce")
    adjusted = adjusted[TICKERS].apply(pd.to_numeric, errors="coerce")
    close.index = pd.to_datetime(close.index).tz_localize(None).normalize() if close.index.tz is not None else pd.to_datetime(close.index).normalize()
    adjusted.index = pd.to_datetime(adjusted.index).tz_localize(None).normalize() if adjusted.index.tz is not None else pd.to_datetime(adjusted.index).normalize()
    common = close.join(adjusted, how="inner", lsuffix="_close", rsuffix="_adj").dropna()
    if len(common) < 3:
        raise ValueError("Insufficient shared daily prices for AMZN, MSFT, GOOGL, SMH, DRAM and SPY.")
    c = common[[f"{t}_close" for t in TICKERS]].rename(columns={f"{t}_close": t for t in TICKERS})
    a = common[[f"{t}_adj" for t in TICKERS]].rename(columns={f"{t}_adj": t for t in TICKERS})
    if (c <= 0).any().any() or (a <= 0).any().any():
        raise ValueError("Close and Adj Close must contain positive prices.")
    r = a.pct_change().dropna()
    rp = c.pct_change().loc[r.index]
    out = pd.DataFrame(index=r.index)
    out["Long"] = r[LONGS].mean(axis=1)
    out["ShortBasket"] = .75 * r["SMH"] + .25 * r["DRAM"]
    out["Market"] = r["SPY"]
    out["Long_price"] = rp[LONGS].mean(axis=1)
    out["Short_price"] = .75 * rp["SMH"] + .25 * rp["DRAM"]
    out["Long_distribution"] = out["Long"] - out["Long_price"]
    out["Short_distribution"] = out["ShortBasket"] - out["Short_price"]
    return out


def prior_rolling_betas(returns: pd.DataFrame, window: int = 30):
    """Lag all factors by 1 trading day so weights use only previously observed prices."""
    market_var = returns["Market"].rolling(window, min_periods=window).var()
    beta_l = (returns["Long"].rolling(window, min_periods=window).cov(returns["Market"]) / market_var).shift(1)
    beta_s = (returns["ShortBasket"].rolling(window, min_periods=window).cov(returns["Market"]) / market_var).shift(1)
    denominator = beta_l + beta_s
    valid = (beta_l > 0) & (beta_s > 0) & (denominator > 0)
    long_w = (beta_s / denominator).where(valid, 0.50)
    long_w = long_w.clip(lower=0.05, upper=0.95)
    return pd.DataFrame({"beta_long_prior":beta_l,"beta_short_prior":beta_s,
                         "long_weight_beta_target":long_w,"beta_target_valid":valid},index=returns.index)


def simulate(returns: pd.DataFrame, settings: Settings, entry_close: str, beta_target=False, beta_window=30):
    """P&L from close-to-close adjusted returns, daily reset to chosen gross notionals.

    Entry close is the reference; first traded return is the FOLLOWING trading session.
    Daily financing/borrow accrued on calendar days between observations.
    """
    returns = returns.sort_index()
    entry_close = pd.Timestamp(entry_close).normalize()
    eligible = returns.index[returns.index <= entry_close]
    if len(eligible)==0:
        raise ValueError("The chosen entry date is before the price-history sample.")
    reference = eligible[-1]
    t = returns.loc[returns.index > reference].copy()
    if t.empty:
        raise ValueError("No trading sessions after the chosen entry close.")
    beta = prior_rolling_betas(returns, window=beta_window)
    t = t.join(beta, how="left")
    long_w = t["long_weight_beta_target"] if beta_target else pd.Series(settings.long_weight,index=t.index)
    short_w = 1.0 - long_w
    t["Long $ target"] = settings.gross * long_w
    t["Short $ target"] = settings.gross * short_w
    t["Gross $ target"] = t["Long $ target"] + t["Short $ target"]
    t["Net $ target"] = t["Long $ target"] - t["Short $ target"]
    t["Long P&L"] = t["Long $ target"] * t["Long"]
    t["Short P&L"] = -t["Short $ target"] * t["ShortBasket"]
    t["Price P&L"] = t["Long $ target"] * t["Long_price"] - t["Short $ target"] * t["Short_price"]
    t["Long dividends approximated"] = t["Long $ target"] * t["Long_distribution"]
    t["Short distributions approximated"] = -t["Short $ target"] * t["Short_distribution"]
    t["Gross P&L"] = t["Long P&L"] + t["Short P&L"]
    reference_dates = pd.DatetimeIndex([reference]).append(t.index[:-1])
    days = (t.index - reference_dates).days
    t["Borrow fees"] = -t["Short $ target"] * settings.borrow_rate * days / 365.0
    t["Financing"] = -settings.margin_debit * settings.margin_apr_pct/100 * days / 365.0
    t["Round-trip execution costs"] = 0.0
    t.iloc[0, t.columns.get_loc("Round-trip execution costs")] = -settings.execution_cost
    t["Costs"] = t["Borrow fees"] + t["Financing"] + t["Round-trip execution costs"]
    t["Net P&L"] = t["Gross P&L"] + t["Costs"]
    for col in ["Long P&L", "Short P&L", "Gross P&L", "Net P&L", "Costs", "Price P&L"]:
        t[f"Cumulative {col}"] = t[col].cumsum()
    # Start at gross notional for model-only drawdown (NOT the full paper NAV).
    t["Trade model equity"] = settings.gross + t["Cumulative Net P&L"]
    peak = np.maximum.accumulate(np.r_[settings.gross, t["Trade model equity"].to_numpy()])[1:]
    t["Trade drawdown %"] = 100.0 * (t["Trade model equity"].to_numpy()/peak - 1)
    t["Return on gross"] = t["Net P&L"] / settings.gross
    t.attrs["reference_date"] = reference.strftime("%Y-%m-%d")
    t.attrs["beta_target"] = beta_target
    return t


def realized_beta(series, market):
    s = pd.concat([series, market],axis=1).dropna()
    return float(s.iloc[:,0].cov(s.iloc[:,1])/s.iloc[:,1].var()) if len(s)>=5 and s.iloc[:,1].var()>0 else float("nan")


def summarize(t: pd.DataFrame, settings:Settings):
    cumulative = float(t["Cumulative Net P&L"].iloc[-1]); low = float(t["Cumulative Net P&L"].min())
    daily = t["Return on gross"]
    sharpe = float(np.sqrt(252) * daily.mean() / daily.std(ddof=1)) if len(daily)>2 and daily.std(ddof=1)>0 else float("nan")
    return {"net_pnl": cumulative,"gross_pnl":float(t["Cumulative Gross P&L"].iloc[-1]),
            "long_pnl":float(t["Cumulative Long P&L"].iloc[-1]),"short_pnl":float(t["Cumulative Short P&L"].iloc[-1]),
            "cost":float(t["Cumulative Costs"].iloc[-1]),"sharpe":sharpe,
            "realized_beta":realized_beta(t["Return on gross"],t["Market"]),
            "max_drawdown_pct":float(t["Trade drawdown %"].min()),
            "worst_loss_vs_entry":min(0.0,low),
            "risk_used_pct":max(0,-low)/settings.budget_dollars*100,
            "nav_return_pct":100*cumulative/settings.nav,
            "gross_return_pct":100*cumulative/settings.gross}


def scenario_pnl(settings: Settings, long_move_pct:float, short_move_pct:float,
                 days:int=90, dividend_yield_long_pct=.4, distribution_yield_short_pct=.7):
    """Illustrative TERMINAL PRICE SHOCK. Dividends modeled separately (no adjusted return used)."""
    l = settings.long_dollars * long_move_pct / 100
    s = -settings.short_dollars * short_move_pct / 100
    b = -settings.short_dollars * settings.borrow_rate * days/365
    f = -settings.margin_debit * settings.margin_apr_pct/100 * days/365
    dl = settings.long_dollars * dividend_yield_long_pct/100 * days/365
    ds = -settings.short_dollars * distribution_yield_short_pct/100 * days/365
    fee = -settings.execution_cost
    return {"Long price":l,"Short price":s,"Borrow fees":b,"Financing":f,
            "Long dividends":dl,"Short distributions owed":ds,"Trading costs":fee,
            "Gross P&L":l+s,"Net P&L":l+s+b+f+dl+ds+fee}


def historical_windows(returns:pd.DataFrame, settings:Settings, window:int=5):
    """Overlapping, historical shock windows; hold opening exposures for window, exclude costs."""
    if window < 1:
        raise ValueError("window must be positive")
    out = pd.DataFrame(index=returns.index)
    for col in ["Long","ShortBasket","Market"]:
        out[col] = (1 + returns[col]).rolling(window).apply(np.prod,raw=True) - 1
    out["P&L"] = settings.long_dollars*out["Long"] - settings.short_dollars*out["ShortBasket"]
    return out.dropna()


def demo_prices():
    """Deterministic SYNTHETIC prices. Never confuse with sourced market data."""
    rng=np.random.default_rng(8126)
    dates=pd.bdate_range("2026-04-02", "2026-11-20")
    n=len(dates); market=rng.normal(.0004,.012,n)
    tech=rng.normal(0,.010,n)
    data={}
    for i,ticker in enumerate(TICKERS):
        if ticker=="SPY": ret=market
        elif ticker in LONGS: ret=0.8*market+0.6*tech+rng.normal(0,.008,n)
        else: ret=1.6*market+1.2*tech+rng.normal(0,.018,n)
        if ticker in ["SMH","DRAM"]:
            ret += np.where(dates>=pd.Timestamp("2026-10-12"), -0.006, 0.001)
        if ticker in LONGS:
            ret += np.where(dates>=pd.Timestamp("2026-10-12"), -0.002, 0.0006)
        p=100*np.cumprod(1+ret)
        # Tiny TOTAL RETURN difference to mimic quarterly dividends; artificial.
        adjusted=p*np.cumprod(1+np.where(np.arange(n)%63==0, .001,0))
        data[ticker]=(p,adjusted)
    close=pd.DataFrame({k:v[0] for k,v in data.items()},index=dates)
    adj=pd.DataFrame({k:v[1] for k,v in data.items()},index=dates)
    return close,adj
