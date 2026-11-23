"""Part 3 of the hyperscaler/semiconductor trade study.

Run in Jupyter with: %run scenario_analysis.py
The inputs below are hypothetical opening positions, price shocks, and rates.
Basket shocks are price-only. Dividend cash flows are modeled separately.
Dollar P&L uses fixed opening exposures with no rebalancing within the scenario.
"""

import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.ticker import FuncFormatter, PercentFormatter
import numpy as np
import pandas as pd


LONG_NOTIONAL = 50_000
SHORT_NOTIONAL = 50_000
GROSS_EXPOSURE = LONG_NOTIONAL + SHORT_NOTIONAL
HOLD_DAYS = 90
LOSS_BUDGET = 10_000

# Illustrative annualized rates, expressed as decimals.
SHORT_ETFS = pd.DataFrame(
    {
        "Weight": [0.75, 0.25],
        "Borrow rate": [0.005, 0.02],
        "Distribution yield": [0.008, 0.004],
    },
    index=["SMH", "DRAM"],
)
LONG_DIVIDEND_YIELD = 0.004
SHORT_PROCEEDS_INTEREST_RATE = 0.0  # Effective credited rate on short notional.
ROUND_TRIP_COST_BPS = 10  # Entry and exit combined, estimated on opening gross.
MARGIN_DEBIT = 25_000  # Extra sensitivity case. The base case uses cash for longs.
MARGIN_RATE = 0.05

# Hyperscaler and semiconductor basket price moves, in that order.
PRICE_SHOCKS = {
    "Thesis plays out": (0.02, -0.15),
    "Semis fall alone": (0.00, -0.10),
    "Both sell off": (-0.05, -0.10),
    "Equal selloff": (-0.10, -0.10),
    "Hyperscalers fall alone": (-0.05, 0.00),
    "Semiconductor squeeze": (0.03, 0.20),
    "Larger squeeze, longs flat": (0.00, 0.25),
}

def stress_test(shocks):
    """Return the modeled scenario P&L and itemized costs in dollars."""
    if not np.isclose(SHORT_ETFS["Weight"].sum(), 1) or (SHORT_ETFS["Weight"] < 0).any():
        raise ValueError("Short ETF weights must be nonnegative and sum to 100%.")

    year_fraction = HOLD_DAYS / 365
    etf_notionals = SHORT_NOTIONAL * SHORT_ETFS["Weight"]
    carry = pd.Series({
        "Stock borrow fees": -(etf_notionals * SHORT_ETFS["Borrow rate"]).sum() * year_fraction,
        "ETF distributions owed": -(etf_notionals * SHORT_ETFS["Distribution yield"]).sum() * year_fraction,
        "Long dividends received": LONG_NOTIONAL * LONG_DIVIDEND_YIELD * year_fraction,
        "Short proceeds interest": SHORT_NOTIONAL * SHORT_PROCEEDS_INTEREST_RATE * year_fraction,
        "Round-trip trading costs": -GROSS_EXPOSURE * ROUND_TRIP_COST_BPS / 10_000,
    })
    margin_interest = MARGIN_DEBIT * MARGIN_RATE * year_fraction
    results = pd.DataFrame.from_dict(shocks, orient="index", columns=["Hyperscalers", "Semis"])
    results["Long P&L"] = LONG_NOTIONAL * results["Hyperscalers"]
    results["Short P&L"] = -SHORT_NOTIONAL * results["Semis"]
    results["Gross P&L"] = results["Long P&L"] + results["Short P&L"]
    results["Net cash-funded"] = results["Gross P&L"] + carry.sum()
    results["Net with margin"] = results["Net cash-funded"] - margin_interest
    return results, carry, margin_interest


def display_results(results, carry, margin_interest):
    print(f"Hypothetical {HOLD_DAYS}-day stress test | Opening gross exposure: " + format_dollars(GROSS_EXPOSURE))
    print()
    print("Cash funded · dollars added to gross P&L")
    print(carry.to_string(float_format=lambda value: f"{value:+,.2f}"))
    print(f"Net cash-funded cost: {format_dollars(-carry.sum())}")
    print(f"Additional cost with a {format_dollars(MARGIN_DEBIT)} margin debit: {format_dollars(margin_interest)}")
    print()
    report = results.copy()
    for column in ["Hyperscalers", "Semis"]:
        report[column] = report[column].map(lambda value: f"{value:+.0%}")
    for column in report.columns[2:]:
        report[column] = report[column].map(lambda value: format_dollars(value, 2))
    print(report.to_string())


def format_dollars(value, decimals=0):
    sign = "−" if value < 0 else ""
    return sign + "$" + f"{abs(value):,.{decimals}f}"


def build_chart(results, cash_cost):
    fig, (bars, heatmap) = plt.subplots(
        1, 2, figsize=(14, 6.2), gridspec_kw={"width_ratios": [1.08, 1]}
    )
    fig.suptitle("Hyperscalers vs. semiconductors | Stress test",
                 x=0.15, y=0.97, ha="left", fontsize=19, fontweight="bold")
    fig.text(0.15, 0.885,
             f"{format_dollars(GROSS_EXPOSURE)} gross exposure  •  {HOLD_DAYS} calendar days  •  Hypothetical price moves and costs",
             fontsize=10, color="#516176")

    y = np.arange(len(results))
    bars.barh(y - 0.17, results["Gross P&L"], height=0.30, color="#AAD0E0", label="Before costs")
    bars.barh(y + 0.17, results["Net cash-funded"], height=0.30, color="#134F75", label="After costs, cash-funded")
    bars.axvline(0, color="#516176", linewidth=0.9)
    bars.axvline(-LOSS_BUDGET, color="#A22E40", linewidth=1.1, linestyle="--", label="Loss budget")
    bars.set_yticks(y, results.index)
    bars.invert_yaxis()
    bars.xaxis.set_major_formatter(FuncFormatter(lambda value, _: format_dollars(value)))
    bars.set_xlabel("Trade P&L")
    bars.set_title("P&L by scenario", loc="left", fontsize=13, fontweight="bold", pad=10)
    bars.grid(axis="x", color="#DDE5EE")
    bars.set_axisbelow(True)
    bars.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.50, -0.15), ncol=2, fontsize=9)

    semi_shocks = np.linspace(-0.20, 0.30, 151)
    hyperscaler_shocks = np.linspace(-0.20, 0.20, 121)
    semi_grid, hyperscaler_grid = np.meshgrid(semi_shocks, hyperscaler_shocks)
    net_grid = LONG_NOTIONAL * hyperscaler_grid - SHORT_NOTIONAL * semi_grid - cash_cost
    bound = np.abs(net_grid).max()
    colors = heatmap.pcolormesh(
        semi_grid, hyperscaler_grid, net_grid, shading="auto", cmap="RdBu",
        norm=TwoSlopeNorm(vmin=-bound, vcenter=0, vmax=bound),
    )
    threshold_styles = {
        -LOSS_BUDGET: ("#A22E40", "--", format_dollars(-LOSS_BUDGET)),
        0: ("#203244", "-", "Break-even"),
    }
    thresholds = [level for level in threshold_styles if net_grid.min() < level < net_grid.max()]
    if thresholds:
        levels = heatmap.contour(
            semi_grid, hyperscaler_grid, net_grid, levels=thresholds,
            colors=[threshold_styles[level][0] for level in thresholds],
            linestyles=[threshold_styles[level][1] for level in thresholds],
            linewidths=1.4,
        )
        heatmap.clabel(levels, fmt={level: threshold_styles[level][2] for level in thresholds},
                      fontsize=9)
    heatmap.set_xlabel("Semiconductor basket price move")
    heatmap.set_ylabel("Hyperscaler basket price move")
    heatmap.set_title("Cash-funded P&L across price shocks", loc="left", fontsize=13, fontweight="bold", pad=10)
    heatmap.xaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    heatmap.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    colorbar = fig.colorbar(colors, ax=heatmap, shrink=0.90, pad=0.035, aspect=26)
    colorbar.formatter = FuncFormatter(lambda value, _: format_dollars(value))
    colorbar.update_ticks()

    bars.spines[["top", "right"]].set_visible(False)
    fig.subplots_adjust(left=0.15, right=0.95, top=0.80, bottom=0.24, wspace=0.30)
    fig.text(0.15, 0.045,
             "Source: Illustrative scenario assumptions  |  Analysis and charts: Luke Gillespie",
             color="#516176", fontsize=9)
    fig.savefig("scenario_analysis.png", dpi=250, bbox_inches="tight", facecolor="white")
    plt.show()


if __name__ == "__main__":
    scenario_results, cash_adjustments, financing_interest = stress_test(PRICE_SHOCKS)
    display_results(scenario_results, cash_adjustments, financing_interest)
    build_chart(scenario_results, -cash_adjustments.sum())
