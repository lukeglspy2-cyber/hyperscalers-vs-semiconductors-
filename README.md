# AI Infrastructure Bottlenecks: Hyperscalers vs. Semiconductors

**Independent Investment Research | Python | Long/Short Equity | Relative Value | Portfolio Risk**

## Investment Thesis

This project investigates whether electricity infrastructure constraints, grid interconnection delays, permitting restrictions, and data-center construction bottlenecks could cause semiconductor equities to underperform hyperscale cloud platforms.

The central hypothesis is that constraints on AI infrastructure deployment may disproportionately affect semiconductor suppliers relative to large technology platforms with more diversified businesses.

The research combines fundamental catalyst analysis with quantitative relative-value modeling and portfolio risk management.

## Trade Construction

| Position | Securities | Allocation |
|---|---|---|
| Long | AMZN, MSFT, GOOGL | Equally weighted |
| Short | SMH, DRAM | 75% SMH / 25% DRAM |

The reference portfolio uses $50,000 long and $50,000 short exposure, representing $100,000 gross exposure and zero initial net dollar exposure.

**Original hypothetical trade entry:** November 5, 2026, closing prices.

## Research Methodology

### Part 1 — Historical Relative-Value Analysis

- Historical adjusted-price and return analysis
- Cumulative performance of both equity baskets
- Rolling correlations and relative performance
- Comparison of recent and earlier market regimes

### Part 2 — Quantitative Risk and Factor Analysis

- Rolling volatility and correlations
- Portfolio beta to the S&P 500
- Sharpe ratio and maximum drawdown
- Dollar-neutral versus beta-targeted portfolio construction
- Dynamic portfolio weights

### Part 3 — Scenario Analysis

- Hypothetical semiconductor selloffs and short squeezes
- Long-side and short-side profit attribution
- Financing and stock-borrow assumptions
- ETF distributions and trading costs
- Portfolio stress-testing visualizations

### Part 4 — Fundamental Catalyst Research

- Dated infrastructure and capital-expenditure announcements
- Grid interconnection, permitting, and power-supply developments
- Event studies examining portfolio returns around announcements
- Market-beta-adjusted performance comparisons
- Fundamental catalyst timeline and event-study visualizations

The event studies are descriptive. They do not establish causation, and selected, overlapping announcements limit statistical inference.

### Part 5 — Interactive Streamlit Dashboard

An interactive Python dashboard allows users to explore portfolio performance, risk metrics, exposure, scenario assumptions, and fundamental catalysts.

**Technology:** Python, pandas, NumPy, matplotlib, Plotly, statsmodels, yfinance, and Streamlit.

## Selected Historical Findings

In the modeled common sample from May 19 to November 20, 2026:

| Metric | Dollar-neutral | SPY beta target |
|---|---:|---:|
| Cumulative modeled P&L | +$7,472 | +$2,928 |
| Realized SPY beta | -0.87 | -0.01 |
| Annualized volatility | 34.13% | 27.15% |
| Maximum drawdown | -21.32% | -17.91% |
| Annualized Sharpe ratio | 0.58 | 0.34 |

The dollar-neutral strategy displayed higher modeled returns but also greater market exposure and drawdown risk.

These historical results are distinct from the November 5 paper-trade entry and are not evidence of an independently validated trading strategy.

## Limitations

- Historical adjusted closing prices are not executable transaction prices.
- The models do not replicate actual Interactive Brokers share positions or transaction records.
- Some simulations assume daily rebalancing to target exposures.
- Carrying costs and execution expenses are estimates.
- Short borrowing conditions may change substantially.
- The DRAM ETF's limited trading history constrains the sample.
- Event-study relationships are associative, not causal.
- Historical backtests and hypothetical stress tests do not establish future profitability.

## Research Objective

The objective is not merely to identify a profitable trade, but to distinguish genuine relative-value opportunities from broader equity-market exposure, test adverse scenarios, and connect market performance to an economically grounded investment thesis.

**Research and analysis: Luke Gillespie**

**Market data:** Yahoo Finance / yfinance

**Status:** Independent historical research and hypothetical portfolio modeling. Not investment advice.
