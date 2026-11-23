"""Run after the price and return cells in the hyperscaler/semiconductor notebook.

In a Jupyter code cell, run: %run -i risk_and_factor_analysis.py
The original notebook supplies the returns DataFrame and source_label.
"""

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter, StrMethodFormatter
import numpy as np
import pandas as pd


AS_OF = "2026-11-20"
ENTRY_CLOSE = "2026-11-05"
WINDOW = 30
ANNUAL_SESSIONS = 252
GROSS_EXPOSURE = 100_000
STARTING_EQUITY = 100_000
RISK_FREE_RATE = 0.0

DOLLAR_NEUTRAL = "Dollar-neutral 50/50"
BETA_TARGET = "SPY beta target"
COLORS = {DOLLAR_NEUTRAL: "#124977", BETA_TARGET: "#BC5A1D"}
GRID_COLOR = "#DCE3EB"
LONG_COLOR = "#238073"
SHORT_COLOR = "#8B4F91"


def compare_portfolios(basket_returns):
    """Build comparable daily P&L and risk series from matched basket returns."""
    market = basket_returns["Market"]
    market_variance = market.rolling(WINDOW).var().replace(0, np.nan)
    basket_betas = basket_returns[["Hyperscalers", "Semiconductors"]].apply(
        lambda basket: basket.rolling(WINDOW).cov(market) / market_variance
    )

    # The trade earns the close-to-close return ending on this row's date.
    # Estimate through two closes back, then set weights at the prior close.
    known_betas = basket_betas.shift(2)
    beta_sum = known_betas.sum(axis=1, min_count=2).replace(0, np.nan)
    long_weight = known_betas["Semiconductors"] / beta_sum

    # The solution must keep a positive long sleeve and a positive short sleeve.
    weights = long_weight.loc[long_weight.between(0, 1, inclusive="neither")]
    if len(weights) < 2:
        raise ValueError("The analysis needs at least two sessions with feasible beta-target weights.")

    sample = basket_returns.loc[weights.index]
    long_basket = sample["Hyperscalers"]
    short_basket = sample["Semiconductors"]
    sp500 = sample["Market"]
    gross_returns = pd.DataFrame({
        DOLLAR_NEUTRAL: 0.5 * long_basket - 0.5 * short_basket,
        BETA_TARGET: weights * long_basket - (1 - weights) * short_basket,
    })
    daily_pnl = GROSS_EXPOSURE * gross_returns
    equity = STARTING_EQUITY + daily_pnl.cumsum()
    if (equity <= 0).any().any():
        raise ValueError("Equity reached zero or below. Check the modeled capital and gross exposure.")

    equity_returns = daily_pnl / equity.shift(1, fill_value=STARTING_EQUITY)
    drawdown = equity / equity.cummax().clip(lower=STARTING_EQUITY) - 1
    realized_beta = gross_returns.apply(
        lambda strategy: strategy.rolling(WINDOW).cov(sp500)
        / sp500.rolling(WINDOW).var().replace(0, np.nan)
    )
    annualized_volatility = equity_returns.std() * np.sqrt(ANNUAL_SESSIONS)
    excess_returns = equity_returns - RISK_FREE_RATE / ANNUAL_SESSIONS
    summary = pd.DataFrame({
        "Cumulative P&L ($)": daily_pnl.sum(),
        "P&L after Nov. 5 close ($)": daily_pnl.loc[daily_pnl.index > ENTRY_CLOSE].sum(min_count=1),
        "Realized beta to SPY": gross_returns.apply(
            lambda strategy: strategy.cov(sp500) / sp500.var() if sp500.var() > 0 else np.nan
        ),
        "Annualized volatility (%)": 100 * annualized_volatility,
        "Maximum drawdown (%)": 100 * drawdown.min(),
        "Annualized Sharpe": (
            excess_returns.mean() / equity_returns.std().replace(0, np.nan)
            * np.sqrt(ANNUAL_SESSIONS)
        ),
    }).T
    return summary, daily_pnl, equity_returns, drawdown, realized_beta, weights, sample


def style_panel(ax, title, ylabel, formatter=None):
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", pad=9)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#AAB6C4")
    ax.set_xlabel("")
    if formatter is not None:
        ax.yaxis.set_major_formatter(formatter)


def save_chart(fig, axes, title, filename, attribution, sample):
    fig.suptitle(title, x=0.08, y=0.98, ha="left", fontsize=17, fontweight="bold")
    first, last = sample.index[0], sample.index[-1]
    fig.text(
        0.08, 0.90, f"Common sample  |  {first:%b %d} to {last:%b %d, %Y}",
        color="#536477", fontsize=10,
    )
    fig.text(0.08, 0.035, attribution, fontsize=9, color="#536477")
    for ax in axes:
        locator = mdates.AutoDateLocator(minticks=4, maxticks=7)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        ax.tick_params(labelbottom=True)

    fig.subplots_adjust(left=0.08, right=0.98, bottom=0.12, top=0.82, hspace=0.40, wspace=0.26)
    fig.savefig(filename, dpi=250, bbox_inches="tight", facecolor="white")


def run_risk_analysis(returns, source):
    columns = ["Hyperscalers", "Semiconductors", "Market"]
    basket_returns = returns[columns].sort_index().loc[:AS_OF].dropna()
    if basket_returns.index.has_duplicates:
        raise ValueError("The notebook data contain duplicate dates. Keep one row per trading session.")

    summary, pnl, equity_returns, drawdown, realized_beta, weights, sample = compare_portfolios(basket_returns)
    sample_start = sample.index[0]
    excluded = len(basket_returns.loc[sample_start:]) - len(sample)
    print(f"{source}")
    print(f"Shared dates: {sample_start:%Y-%m-%d} to {sample.index[-1]:%Y-%m-%d} ({len(sample)} sessions)")
    print(f"Sessions skipped after the comparison started: {excluded}")
    print(f"Starting model equity: ${STARTING_EQUITY:,.0f} | Daily gross exposure: ${GROSS_EXPOSURE:,.0f}")
    print(f"Latest target weights: {weights.iloc[-1]:.1%} long / {1 - weights.iloc[-1]:.1%} short")
    print(summary.to_string(float_format=lambda value: f"{value:,.2f}"))

    footer = f"Source: {source} | Analysis and charts: Luke Gillespie"
    fig, axes = plt.subplots(2, 2, figsize=(13, 8.4))
    pnl.cumsum().plot(x_compat=True, ax=axes[0, 0], color=COLORS, linewidth=1.8)
    style_panel(axes[0, 0], "Cumulative trade P&L", "Gross P&L", StrMethodFormatter("${x:,.0f}"))
    axes[0, 0].axhline(0, color="#8B98A7", linewidth=0.8)
    axes[0, 0].legend(frameon=False, fontsize=9)

    realized_beta.plot(x_compat=True, ax=axes[0, 1], color=COLORS, linewidth=1.8, legend=False)
    style_panel(axes[0, 1], f"Realized SPY beta ({WINDOW} sessions)", "Beta")
    axes[0, 1].axhline(0, color="#8B98A7", linewidth=0.8)

    drawdown.plot(x_compat=True, ax=axes[1, 0], color=COLORS, linewidth=1.8, legend=False)
    style_panel(axes[1, 0], "Drawdown from equity peak", "Drawdown", PercentFormatter(1))

    rolling_vol = equity_returns.rolling(WINDOW).std() * np.sqrt(ANNUAL_SESSIONS)
    rolling_vol.plot(x_compat=True, ax=axes[1, 1], color=COLORS, linewidth=1.8, legend=False)
    style_panel(
        axes[1, 1], f"Rolling volatility ({WINDOW} sessions)", "Annualized volatility", PercentFormatter(1)
    )
    save_chart(fig, axes.flat, "Hyperscalers vs. semiconductors | Strategy risk",
               "risk_dashboard.png", footer, sample)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.8))
    market = sample["Market"]
    correlations = (pnl / GROSS_EXPOSURE).apply(
        lambda strategy: strategy.rolling(WINDOW).corr(market)
    )
    basket_label = "Hyperscalers vs. semis"
    correlations[basket_label] = sample["Hyperscalers"].rolling(WINDOW).corr(sample["Semiconductors"])
    correlations.plot(x_compat=True, ax=axes[0], color={**COLORS, basket_label: "#6D7888"}, linewidth=1.7)
    style_panel(axes[0], f"Rolling correlations ({WINDOW} sessions)", "Correlation")
    axes[0].set_ylim(-1.05, 1.05)
    axes[0].axhline(0, color="#8B98A7", linewidth=0.8)
    axes[0].legend(title="Strategies vs. SPY / baskets vs. each other", frameon=False, fontsize=8, title_fontsize=8)

    weights.plot(x_compat=True, ax=axes[1], color=LONG_COLOR, label="Long hyperscalers", linewidth=1.8)
    (1 - weights).plot(x_compat=True, ax=axes[1], color=SHORT_COLOR, label="Short semis", linewidth=1.8)
    axes[1].axhline(0.5, color="#8B98A7", linestyle="--", label="50/50 reference")
    style_panel(axes[1], "Beta-target basket weights", "Share of gross exposure", PercentFormatter(1))
    axes[1].set_ylim(0, 1)
    axes[1].legend(frameon=False, fontsize=9)
    save_chart(fig, axes, "Hyperscalers vs. semiconductors | Correlation and sizing",
               "factor_exposures.png", footer, sample)
    plt.show()


if __name__ == "__main__":
    if "returns" not in globals():
        raise RuntimeError("Run the earlier cells that create returns, then use %run -i from Jupyter.")
    run_risk_analysis(returns, globals().get("source_label", "Notebook price data"))
