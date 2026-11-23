"""Part 4 | AI infrastructure fundamental catalyst research and event studies.

Run from JupyterLab in the same folder as this script:
    %run fundamental_catalyst_research.py

Outputs: catalyst_events.csv, catalyst_event_results.csv, five PNG charts,
         and catalyst_research_notes.md, all in a subfolder named part4_outputs.

Study freeze: Nov 20, 2026 close. Prices: Yahoo Finance via yfinance.
Uses actual market data when downloaded; NEVER silently substitutes simulated data.
Event timing convention: first US trading session STRICTLY AFTER published date,
conservatively chosen because exact release timestamps are unavailable for many
sources. This may miss same-day price discovery for intraday announcements.

Research-only, not evidence that an announcement caused a given price move.
"""

from pathlib import Path
import textwrap
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

try:
    import yfinance as yf
except ImportError as exc:
    raise ImportError(
        "yfinance is missing. Run '%pip install yfinance' in a notebook code cell, "
        "then rerun this script."
    ) from exc

# ===========================================================================
# 1. Editable research assumptions
# ===========================================================================
AS_OF = "2026-11-20"         # Last COMPLETE US cash session in the study.
DOWNLOAD_START = "2026-03-20"  # Buffer for DRAM's April 2026 inception.
LONG_WEIGHTS = {"AMZN": 1/3, "MSFT": 1/3, "GOOGL": 1/3}
SHORT_WEIGHTS = {"SMH": 0.75, "DRAM": 0.25}
BENCHMARK = "SPY"
PRE_EVENT_BETA_SESSIONS = 40
MIN_BETA_OBSERVATIONS = 30
EVENT_PRE_DAYS = 5
EVENT_POST_DAYS = 5

OUT = Path("part4_outputs")
OUT.mkdir(exist_ok=True)
EVENT_CSV = OUT / "catalyst_events.csv"
METRIC_CSV = OUT / "fundamental_metrics.csv"
TICKERS = list(LONG_WEIGHTS) + list(SHORT_WEIGHTS) + [BENCHMARK]

# The date is the PUBLICATION / announcement date, not an assumed trading date.
# An independent source URL is included so that every row is auditable.
# 'Research interpretation' is a hypothesis to test, NOT a measured outcome.
EVENTS = [
    ("E01", "2026-06-10", "Grid/interconnection", "Texas directs PUC/ERCOT to protect customers from data-center grid costs", "Texas Governor",
     "State asked regulators to address who pays for grid infrastructure associated with data-center expansion.",
     "Electricity-infrastructure cost hurdle", "https://gov.texas.gov/news/post/governor-abbott-directs-puc-and-ercot-to-shield-texans-from-data-center-infrastructure-costs"),
    ("E02", "2026-06-18", "Grid/interconnection", "FERC launches large-load tariff reform action", "FERC",
     "FERC directed regional transmission organizations to justify or revise large-load interconnection rules.",
     "Grid access constraints and possible regulatory relief", "https://ferc.gov/news-events/news/ferc-launches-aggressive-targeted-action-speed-large-load-integration"),
    ("E03", "2026-06-22", "Construction/power", "Microsoft announces Pecos data-center campus", "Microsoft",
     "Microsoft announced a new AI data-center campus in Pecos, Texas.",
     "Expansion and local power supply", "https://blogs.microsoft.com/blog/2026/06/22/powering-the-next-wave-of-ai-expanding-capacity-with-our-new-datacenter-in-pecos/"),
    ("E04", "2026-07-14", "Construction/power", "Google announces Arkansas energy partnership", "Google",
     "Google announced a partnership with the Steel River Energy Center in Arkansas.",
     "Power sourcing solution", "https://blog.google/innovation-and-ai/infrastructure-and-cloud/global-network/steel-river-arkansas/"),
    ("E05", "2026-07-22", "CapEx/earnings", "Alphabet increases 2026 CapEx guidance", "Alphabet",
     "Alphabet raised 2026 CapEx guidance to $195-$205B from $180-$190B on its Q2 call.",
     "Accelerating capital deployment versus supply constraints", "https://abc.xyz/investor/events/event-details/2026/2026-Q2-Earnings-Call-2026-GgTAq7Is0z/"),
    ("E06", "2026-07-29", "CapEx/earnings", "Microsoft fiscal Q4 earnings and AI infrastructure commentary", "Microsoft",
     "Microsoft published FY2026 Q4 results and discussed ongoing AI infrastructure spending.",
     "Cloud and AI earnings / CapEx implications", "https://www.microsoft.com/en-us/investor/earnings/fy-2026-q4/press-release-webcast"),
    ("E07", "2026-07-30", "CapEx/earnings", "Amazon Q2: AI investments pressure free cash flow", "Amazon",
     "Amazon reported Q2 results and a decline in trailing free cash flow driven largely by increased AI property/equipment purchases.",
     "CapEx pace versus financial returns", "https://www.sec.gov/Archives/edgar/data/1018724/000101872426000024/amzn-20260630xex991.htm"),
    ("E08", "2026-08-03", "Grid/interconnection", "Texas orders audit of ERCOT data-center connection applications", "Texas Governor",
     "State ordered verification and auditing of data centers in ERCOT's interconnection process.",
     "Potential scheduling delays / project scrutiny", "https://gov.texas.gov/news/post/governor-abbott-directs-comprehensive-data-center-audit"),
    ("E09", "2026-08-10", "Construction/power", "Amazon outlines planned Pecos County data-center campus", "Amazon",
     "Amazon published its statement regarding a planned data-center campus in Pecos County, Texas.",
     "Construction pipeline despite grid constraints", "https://www.aboutamazon.com/news/company-news/amazon-pecos-county-texas-data-center-clean-energy-jobs"),
    ("E10", "2026-08-18", "Construction/power", "Amazon raises Louisiana data-center investment commitment", "Amazon",
     "Amazon updated an earlier statement, increasing its planned Louisiana data-center investment from $12B to $18B.",
     "Additional campus and infrastructure investment", "https://www.aboutamazon.com/news/company-news/amazon-data-center-louisiana-new-jobs"),
    ("E11", "2026-09-09", "Construction/power", "Amazon and Wiwynn expand Texas server-rack manufacturing", "Amazon",
     "Amazon described expansion of a Texas server-rack manufacturing facility with Wiwynn.",
     "Hardware supply-chain capacity", "https://www.aboutamazon.com/news/company-news/amazon-wiwynn-data-center-manufacturing-jobs-texas"),
    ("E12", "2026-09-21", "Permitting", "Texas orders TCEQ halt on data-center permits", "Texas Governor",
     "Governor directed TCEQ to halt data-center permits pending completion of ERCOT audit.",
     "Direct permit bottleneck", "https://gov.texas.gov/news/post/governor-abbott-directs-tceq-to-halt-data-center-permits"),
    ("E13", "2026-09-29", "Grid/interconnection", "PJM begins enhanced large-load demand review", "PJM",
     "PJM launched annual vetting of large load requests amid data-center-related power demand growth.",
     "Data center power-demand verification", "https://insidelines.pjm.com/pjm-kicks-off-annual-process-of-vetting-large-load-requests/"),
    ("E14", "2026-10-28", "CapEx/earnings", "Microsoft FY2027 Q1 earnings release", "Microsoft",
     "Microsoft announced September 2026-quarter results with discussion of Azure and AI investment.",
     "AI/cloud investment returns", "https://news.microsoft.com/source/2026/10/28/microsoft-announces-first-quarter-results-2/"),
    ("E15", "2026-10-28", "CapEx/earnings", "Alphabet Q3 maintains $195-$205B 2026 CapEx guidance", "Alphabet",
     "Alphabet reported September 2026-quarter results and maintained its 2026 CapEx range.",
     "AI investment intensity", "https://abc.xyz/investor/events/event-details/2026/2026-Q3-Earnings-Call-2026-Ujou16CTw9/"),
    ("E16", "2026-10-29", "CapEx/earnings", "Amazon Q3 reiterates roughly $220B 2026 cash CapEx", "Amazon",
     "Amazon reported Q3 and continued to expect approximately $220B cash capital expenditures in 2026.",
     "Rising infrastructure expenditure", "https://ir.aboutamazon.com/news-release/news-release-details/2026/Amazon-com-Announces-Third-Quarter-Results/"),
    ("E17", "2026-11-05", "Construction/power", "Google announces $17B Wyoming data-center project", "Google",
     "Google announced a Wyoming data center with associated on-site/dedicated energy infrastructure.",
     "Hyperscaler responds to electricity bottlenecks", "https://blog.google/innovation-and-ai/infrastructure-and-cloud/global-network/wyoming-data-center/"),
    ("E18", "2026-11-16", "Grid/interconnection", "PJM files Fast Energization interconnection proposal", "PJM",
     "PJM filed a proposal designed to shorten power-generation / large-load study timelines.",
     "Potential acceleration of grid buildout", "https://insidelines.pjm.com/pjm-proposal-would-cut-interconnection-process-time-in-half/"),
]

# Numerical evidence. These are DIFFERENT TYPES OF QUANTITIES and must never
# be aggregated into one "infrastructure investment" time series.
# "Planned" and "proposed" amounts are NOT completed realized capacity.
METRICS = [
    ("E02", "Regional grid operators in FERC large-load review", 6, "operators", "Directive / review", "2026-06-18"),
    ("E05", "Alphabet 2026 CapEx guidance midpoint", 200, "USD billions", "Company forecast", "2026-07-22"),
    ("E05", "Change in Alphabet 2026 CapEx guidance midpoint", 15, "USD billions", "Guidance revision", "2026-07-22"),
    ("E10", "Amazon planned Louisiana data-center investment", 18, "USD billions", "Planned investment", "2026-08-18"),
    ("E10", "Incremental planned Louisiana data-center investment", 6, "USD billions", "Revised plan", "2026-08-18"),
    ("E16", "Amazon 2026 cash CapEx expectation", 220, "USD billions", "Company forecast", "2026-10-29"),
    ("E17", "Google planned Wyoming data-center investment", 17, "USD billions", "Planned investment", "2026-11-05"),
    ("E17", "Google Wyoming contracted fuel-cell development", 702, "megawatts", "Planned power capacity", "2026-11-05"),
    ("E18", "PJM existing projected interconnection study timeline", 2, "years", "PJM comparison baseline", "2026-11-16"),
    ("E18", "PJM proposed Fast Energization study timeline", 1, "years", "Proposal (not implementation)", "2026-11-16"),
]

PALETTE = {
    "Grid/interconnection": "#356DB6",
    "Construction/power": "#14967D",
    "CapEx/earnings": "#C17A26",
    "Permitting": "#A14B91",
}
LABEL_SHORT = {"Grid/interconnection": "Grid", "Construction/power": "Build / power", "CapEx/earnings": "CapEx", "Permitting": "Permits"}
FOOTER = "Market prices: Yahoo Finance / yfinance  |  Catalyst announcements: linked primary sources  |  Research and charts: Luke Gillespie"


def research_events():
    columns = ["event_id", "published_date", "category", "title", "entity", "factual_summary", "research_angle", "source_url"]
    if not EVENT_CSV.exists():
        pd.DataFrame(EVENTS, columns=columns).to_csv(EVENT_CSV, index=False, encoding="utf-8-sig")
    if not METRIC_CSV.exists():
        pd.DataFrame(METRICS, columns=["event_id", "metric", "value", "units", "status", "reported_date"]).to_csv(
            METRIC_CSV, index=False, encoding="utf-8-sig")
    catalog = pd.read_csv(EVENT_CSV, dtype=str, keep_default_na=False)
    required = set(columns)
    if not required.issubset(catalog.columns):
        raise ValueError(f"Event CSV is missing columns: {sorted(required - set(catalog.columns))}")
    catalog["published_date"] = pd.to_datetime(catalog["published_date"], errors="raise").dt.normalize()
    catalog = catalog.sort_values(["published_date", "event_id"]).reset_index(drop=True)
    if catalog["event_id"].duplicated().any():
        raise ValueError("Each event_id must be unique in catalyst_events.csv")
    return catalog


def get_market_prices():
    # Yahoo end is exclusive. The study is deliberately frozen to 2026-11-20.
    end_exclusive = (pd.Timestamp(AS_OF) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    raw = yf.download(
        TICKERS, start=DOWNLOAD_START, end=end_exclusive,
        auto_adjust=True, progress=False, threads=False, group_by="column",
    )
    if raw is None or raw.empty:
        raise RuntimeError("No Yahoo Finance prices downloaded. Check internet / yfinance and rerun.")
    if isinstance(raw.columns, pd.MultiIndex):
        if "Close" in raw.columns.get_level_values(0):
            close = raw["Close"].copy()
        elif "Close" in raw.columns.get_level_values(1):
            close = raw.xs("Close", axis=1, level=1).copy()
        else:
            raise ValueError("Could not locate 'Close' in yfinance download.")
    else:
        raise ValueError("Expected a multi-ticker Yahoo Finance download, but got unexpected columns.")
    close.columns = [str(c).upper() for c in close.columns]
    missing = sorted(set(TICKERS).difference(close.columns))
    if missing:
        raise ValueError(f"Yahoo Finance returned no columns for: {missing}")
    close.index = pd.DatetimeIndex(pd.to_datetime(close.index)).tz_localize(None).normalize()
    close = close.reindex(columns=TICKERS).sort_index().dropna(how="any")
    if len(close) < 70:
        raise RuntimeError(f"Only {len(close)} common price dates downloaded. Need >= 70.")
    if close.index.max() < pd.Timestamp("2026-11-17"):
        warnings.warn("Yahoo Finance's latest usable close is older than expected; check data availability.")
    return close


def portfolio_daily_returns(close):
    px_ret = close.pct_change(fill_method=None).dropna(how="any")
    long_ret = sum(weight * px_ret[ticker] for ticker, weight in LONG_WEIGHTS.items())
    semi_ret = sum(weight * px_ret[ticker] for ticker, weight in SHORT_WEIGHTS.items())
    result = pd.DataFrame(index=px_ret.index)
    result["Hyper"] = long_ret
    result["Semi"] = semi_ret
    result["SPY"] = px_ret[BENCHMARK]
    result["Long_leg_on_gross"] = 0.5 * long_ret
    result["Short_leg_on_gross"] = -0.5 * semi_ret
    result["Gross_spread"] = result["Long_leg_on_gross"] + result["Short_leg_on_gross"]
    return result


def event_statistics(event_df, returns):
    rows = []
    sessions = returns.index
    for _, event in event_df.iterrows():
        published = pd.Timestamp(event["published_date"])
        # Strictly following session avoids incorrectly assigning a close-to-close
        # reaction to a late release with an unknown intraday timestamp.
        event_loc = sessions.searchsorted(published, side="right")
        if event_loc >= len(sessions):
            continue
        event_session = sessions[event_loc]
        if event_session > pd.Timestamp(AS_OF):
            continue
        history = returns.iloc[max(0, event_loc-PRE_EVENT_BETA_SESSIONS):event_loc]
        beta = np.nan
        if len(history) >= MIN_BETA_OBSERVATIONS and history["SPY"].var() > 0:
            beta = history["Gross_spread"].cov(history["SPY"]) / history["SPY"].var()
        entry = dict(event.to_dict())
        entry.update({
            "event_session": event_session, "beta_pre_event": beta,
            "baseline_pre3_pct": np.nan,
            "day0_pct": np.nan, "day0_to_day1_pct": np.nan,
            "day0_to_day3_pct": np.nan, "day0_to_day5_pct": np.nan,
            "long_contrib_3_pct": np.nan, "short_contrib_3_pct": np.nan,
            "spy_move_3_pct": np.nan, "spy_adjusted_3_pct": np.nan,
            "coverage_days_after": len(sessions)-event_loc-1,
        })
        if event_loc >= 3:
            entry["baseline_pre3_pct"] = 100 * returns.iloc[event_loc-3:event_loc]["Gross_spread"].sum()
        for horizon, key in [(0, "day0_pct"), (1, "day0_to_day1_pct"),
                             (3, "day0_to_day3_pct"), (5, "day0_to_day5_pct")]:
            if event_loc + horizon < len(sessions):
                entry[key] = 100 * returns.iloc[event_loc:event_loc+horizon+1]["Gross_spread"].sum()
        if event_loc + 3 < len(sessions):
            window = returns.iloc[event_loc:event_loc+4]
            entry["long_contrib_3_pct"] = 100 * window["Long_leg_on_gross"].sum()
            entry["short_contrib_3_pct"] = 100 * window["Short_leg_on_gross"].sum()
            entry["spy_move_3_pct"] = 100 * window["SPY"].sum()
            if pd.notna(beta):
                entry["spy_adjusted_3_pct"] = entry["day0_to_day3_pct"] - beta*entry["spy_move_3_pct"]
        rows.append(entry)
    if not rows:
        raise ValueError("None of the event dates are covered by the downloaded returns.")
    table = pd.DataFrame(rows)
    table["event_session"] = pd.to_datetime(table["event_session"])
    return table


def style_plot(fig, ax, title, subtitle=None):
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=.20)
    ax.set_axisbelow(True)
    fig.suptitle(title, x=.07, y=.98, ha="left", fontsize=18, fontweight="bold", color="#17324D")
    if subtitle:
        fig.text(.07, .935, subtitle, ha="left", va="top", fontsize=10, color="#516578")
    fig.text(.07, .027, FOOTER, fontsize=8.5, color="#677888")


def figure_timeline(returns, events):
    fig, ax = plt.subplots(figsize=(16, 8), dpi=135)
    # Fixed opening GROSS reference; additive daily P&L, not compounded NAV.
    cumulative = returns["Gross_spread"].cumsum()*100
    long_cum = returns["Long_leg_on_gross"].cumsum()*100
    short_cum = returns["Short_leg_on_gross"].cumsum()*100
    ax.plot(returns.index, cumulative, color="#153F78", lw=2.5, label="50/50 long-short (gross)")
    ax.plot(returns.index, long_cum, color="#168D83", lw=1.4, alpha=.75, label="Long-side contribution")
    ax.plot(returns.index, short_cum, color="#D48742", lw=1.4, alpha=.75, label="Short-side contribution")
    ax.axhline(0, color="#536472", lw=.9)
    for _, e in events.iterrows():
        color = PALETTE.get(e["category"], "#777777")
        d = e["event_session"]
        if d in cumulative.index:
            ax.scatter([d], [cumulative.loc[d]], s=32, color=color, zorder=4, edgecolors="white", linewidths=.5)
    selected = {"E08": "TX grid audit", "E12": "TX permit halt", "E17": "Google Wyoming"}
    for _, e in events.iterrows():
        if e["event_id"] in selected and e["event_session"] in cumulative.index:
            d = e["event_session"]
            ax.annotate(selected[e["event_id"]], (d, cumulative.loc[d]), xytext=(0, 22),
                        textcoords="offset points", ha="center", fontsize=9,
                        arrowprops=dict(arrowstyle="-", lw=.5, alpha=.5))
    from matplotlib.lines import Line2D
    category_keys = [Line2D([0], [0], marker="o", markersize=7, lw=0,
                            color=color, label=LABEL_SHORT.get(cat, cat)) for cat, color in PALETTE.items()]
    h, labels = ax.get_legend_handles_labels()
    ax.legend(handles=h+category_keys, loc="upper left", ncol=3, fontsize=9, frameon=False)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, pos: f"{v:+.0f}%"))
    ax.set_ylabel("Cumulative modeled gross P&L / gross exposure", fontsize=10)
    style_plot(fig, ax, "AI infrastructure | Trade performance and catalyst dates",
               "Colored dots mark the first session AFTER announcement; selected announcements annotated")
    fig.tight_layout(rect=[.04, .075, .985, .9])
    fig.savefig(OUT/"01_catalyst_timeline.png", dpi=180, bbox_inches="tight")
    plt.show()
    plt.close(fig)


def figure_heatmap(events):
    columns = ["day0_pct", "day0_to_day1_pct", "day0_to_day3_pct", "day0_to_day5_pct"]
    labels = ["Event day", "E0–E+1", "E0–E+3", "E0–E+5"]
    entries = events[columns].to_numpy(float)
    max_abs = max(1.0, float(np.nanmax(np.abs(entries))))
    fig, ax = plt.subplots(figsize=(13.2, max(7.3, .44*len(events)+2)), dpi=140)
    masked = np.ma.masked_invalid(entries)
    cmap = plt.get_cmap("RdYlGn").copy()
    cmap.set_bad("#F1F3F6")
    im = ax.imshow(masked, cmap=cmap, vmin=-max_abs, vmax=max_abs, aspect="auto")
    for i in range(len(events)):
        for j in range(4):
            value = entries[i,j]
            label = "n/a" if not np.isfinite(value) else f"{value:+.2f}%"
            ax.text(j, i, label, ha="center", va="center", fontsize=9,
                    color="white" if np.isfinite(value) and abs(value) > .65*max_abs else "#253A4D")
    ax.set_xticks(np.arange(4), labels)
    ax.set_yticks(np.arange(len(events)), [f"{r.event_id}  {r.published_date:%b %d}  {r.title[:43]}" for r in events.itertuples()], fontsize=9)
    ax.tick_params(length=0)
    ax.set_xticks(np.arange(-.5, 4, 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(events), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.tick_params(which="minor", length=0)
    cbar = fig.colorbar(im, ax=ax, fraction=.035, pad=.025)
    cbar.set_label("Modeled gross P&L / gross exposure (%)")
    style_plot(fig, ax, "Event study | Trade P&L around catalyst announcements",
               "Returns sum daily fixed-gross P&L; 'n/a' means insufficient post-event market data; overlapping events are NOT independent")
    fig.tight_layout(rect=[.02, .06, .97, .90])
    fig.savefig(OUT/"02_event_return_heatmap.png", dpi=180, bbox_inches="tight")
    plt.show()
    plt.close(fig)


def figure_beta_comparison(events):
    valid = events.dropna(subset=["day0_to_day3_pct", "spy_adjusted_3_pct"]).copy()
    if valid.empty:
        print("Skipping SPY comparison: insufficient pre-event history or subsequent data")
        return
    fig, ax = plt.subplots(figsize=(13.4, max(6.8, .38*len(valid)+2)), dpi=140)
    y = np.arange(len(valid))
    raw = valid["day0_to_day3_pct"].to_numpy(float)
    adj = valid["spy_adjusted_3_pct"].to_numpy(float)
    for i, (a,b) in enumerate(zip(raw, adj)):
        ax.plot([a,b], [y[i], y[i]], color="#AFC1CE", lw=2, zorder=1)
    ax.scatter(raw, y, color="#204F90", marker="o", s=50, label="Gross P&L", zorder=3)
    ax.scatter(adj, y, color="#C57A2A", marker="D", s=34, label="After subtracting pre-event SPY beta × SPY move", zorder=3)
    ax.axvline(0, color="#424E5B", lw=1)
    ax.set_yticks(y, [f"{r.event_id} · {r.title[:46]}" for r in valid.itertuples()], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("E0–E+3 gross P&L / gross exposure (%)", fontsize=10)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v,pos: f"{v:+.1f}%"))
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    style_plot(fig, ax, "Event study | Gross spread versus SPY-adjusted spread",
               "Pre-event SPY beta estimated from preceding 40 sessions (>=30 required); NOT a causal or statistically significant alpha estimate")
    fig.tight_layout(rect=[.03,.065,.98,.9])
    fig.savefig(OUT/"03_spy_adjusted_reactions.png", dpi=180, bbox_inches="tight")
    plt.show()
    plt.close(fig)


def figure_attribution(events):
    valid = events.dropna(subset=["long_contrib_3_pct", "short_contrib_3_pct"]).copy()
    if valid.empty:
        return
    fig, ax = plt.subplots(figsize=(13.8, max(7, .39*len(valid)+2)), dpi=140)
    yy = np.arange(len(valid))
    long_side = valid["long_contrib_3_pct"].to_numpy(float)
    short_side = valid["short_contrib_3_pct"].to_numpy(float)
    # Diverging stacks: positives to the right, negatives to the left.
    pos = np.zeros(len(valid)); neg = np.zeros(len(valid))
    for data,color,label in [(long_side,"#178C81","Long hyperscalers"),(short_side,"#DA873C","Short semiconductors")]:
        left = np.where(data>=0,pos,neg)
        ax.barh(yy, data, left=left, height=.63, color=color, label=label)
        pos += np.where(data>0,data,0)
        neg += np.where(data<0,data,0)
    ax.axvline(0, color="#485968", lw=.9)
    ax.set_yticks(yy, [f"{r.event_id}  {r.title[:45]}" for r in valid.itertuples()], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("P&L contribution / opening gross exposure (percentage points)")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v,pos: f"{v:+.1f}%"))
    ax.legend(loc="lower right", frameon=False)
    style_plot(fig, ax, "Event study | Which side drove the result?",
               "Daily-reset $50k long + $50k short; cumulative contribution from E0 through E+3 (inclusive), before borrow and financing costs")
    fig.tight_layout(rect=[.02,.055,.99,.9])
    fig.savefig(OUT/"04_long_short_attribution.png", dpi=180, bbox_inches="tight")
    plt.show()
    plt.close(fig)


def figure_event_paths(returns, events):
    fig, ax = plt.subplots(figsize=(12.5, 7.4), dpi=140)
    possible = np.arange(-EVENT_PRE_DAYS, EVENT_POST_DAYS+1)
    sessions = returns.index
    complete_counts = {}
    for category, subset in events.groupby("category", sort=True):
        paths = []
        for _, e in subset.iterrows():
            loc = sessions.get_indexer([e["event_session"]])[0]
            if loc >= EVENT_PRE_DAYS and loc + EVENT_POST_DAYS < len(sessions):
                # Starts at cumulative 0 on E-6; values by E-5..E+5.
                path = 100*returns.iloc[loc-EVENT_PRE_DAYS:loc+EVENT_POST_DAYS+1]["Gross_spread"].cumsum().to_numpy()
                paths.append(path)
        complete_counts[category] = len(paths)
        if paths:
            avg = np.mean(paths, axis=0)
            ax.plot(possible, avg, lw=2.5, color=PALETTE.get(category),
                    marker="o", ms=4, label=f"{LABEL_SHORT.get(category,category)}  (n={len(paths)})")
    ax.axvline(0, color="#364857", linestyle="--", lw=1.3, label="First session after release")
    ax.axhline(0, color="#758595", lw=.8)
    ax.set_xticks(possible)
    ax.set_xlabel("Trading sessions relative to the first session after publication")
    ax.set_ylabel("Average cumulative fixed-gross P&L (%)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v,pos:f"{v:+.1f}%"))
    ax.legend(frameon=False, loc="upper left")
    style_plot(fig, ax, "Event study | Average return path by announcement type",
               "Descriptive only: small, selected samples; clustered announcements; pre-event drift is included; complete E-5..E+5 windows only")
    fig.tight_layout(rect=[.04,.075,.99,.9])
    fig.savefig(OUT/"05_category_event_paths.png", dpi=180, bbox_inches="tight")
    plt.show()
    plt.close(fig)
    print("Complete 11-session windows by category:", complete_counts)


def write_notes(events, returns):
    completed = events.dropna(subset=["day0_to_day3_pct"])
    ranked = completed.sort_values("day0_to_day3_pct", ascending=False)
    top = ranked.head(3)
    bottom = ranked.tail(3).iloc[::-1]
    lines = [
        "# Part 4 | Fundamental Catalyst Research and Event Studies", "",
        "**Research author:** Luke Gillespie  ",
        "**Sample cutoff:** 2026-11-20 closing prices  ",
        f"**Data coverage:** {returns.index.min():%Y-%m-%d} to {returns.index.max():%Y-%m-%d}  ",
        "**Market prices:** Yahoo Finance via yfinance, dividend/split adjusted closes", "",
        "## Economic question", "",
        "Do data-center grid constraints, permitting, construction and CapEx announcements coincide with relative-value moves between cloud hyperscalers and semiconductor exposure?", "",
        "## Portfolio convention", "",
        "- 50% opening gross in equal-weight AMZN/MSFT/GOOGL long.",
        "- 50% opening gross short: 75% SMH, 25% DRAM.",
        "- Daily arithmetic returns; daily-rebalanced, fixed-gross P&L is 0.5 × hyperscaler basket return minus 0.5 × semiconductor basket return.",
        "- P&L is expressed as a percent of $100,000 starting gross, before borrow fees, financing, dividends not already captured in adjusted returns, and execution costs.",
        "- The adjusted-price series reflects dividend/split adjustments. Cash-flow modeling belongs in Part 3 and must not be added again to total-return data.", "",
        "## Timing / event definitions", "",
        "- Source publication dates appear in catalyst_events.csv, with directly linked evidence.",
        "- Conservatively use the **first trading session strictly AFTER** the publication date as E0. Some news was released during the trading day, so E0 may **miss** the initial reaction. This is not a close-to-close release-time accurate event study.",
        "- E0..E+3 means 4 trading sessions, summed as fixed-gross daily P&L, not a compounded ETF return.",
        "- SPY beta is estimated using at most 40 PRE-event sessions, at least 30 observed sessions. The SPY-adjusted spread subtracts beta × the contemporary SPY move; it does not demonstrate causal alpha.",
        "- Events may overlap (especially multiple company earnings on October 28–29); do not assume independent observations or sum event profits as an actual portfolio history.",
        "- The selection is purposive and retrospective; event categories, publication timestamps, revised articles, and potential prior market knowledge should be independently audited before sharing as rigorous evidence.",
        "- Announcements are sometimes proposals, intentions or plans—not completed permits, energized grid connections or completed buildings.",
        "- This cannot establish whether infrastructure bottlenecks caused the relative performance; market, semiconductor, earnings, rate, and AI factors overlap.",
        "- DRAM only has a short ETF history; the basket is not a multi-year validated strategy.", "",
        "## Descriptive E0–E+3 results (gross, before costs)", "",
        "These are correlations in a selected catalog, not tests of an identified causal effect.", "",
        "### Highest modeled gross outcomes", "",
    ]
    for row in top.itertuples():
        lines.append(f"- **{row.event_id} {row.published_date:%Y-%m-%d}** {row.title}: {row.day0_to_day3_pct:+.2f}%")
    lines.extend(["", "### Lowest modeled gross outcomes", ""])
    for row in bottom.itertuples():
        lines.append(f"- **{row.event_id} {row.published_date:%Y-%m-%d}** {row.title}: {row.day0_to_day3_pct:+.2f}%")
    lines.extend([
        "", "## Follow-up research", "",
        "1. Validate intraday release timing from official IR calls/press-release timestamps, and redo E0 alignment.",
        "2. Record surprise vs. consensus CapEx expectations, not just CapEx levels.",
        "3. Add permit approvals vs. rejections, MW of interconnection approvals, queue withdrawals and construction delays with measured magnitude.",
        "4. Test sensitivity to SOXX/SMH and DRAM, event-window length, factor controls, sector benchmarks, and excluding earnings days.",
        "5. Separate ex-ante dated hypotheses from retrospectively selected catalysts to avoid confirmation bias.",
        "", "## Files", "",
        "- catalyst_events.csv: editable dated source-linked database.",
        "- fundamental_metrics.csv: measured and planned numerical quantities tied to event IDs; check their status and distinct units.",
        "- catalyst_event_results.csv: event study statistics and dates.",
        "- 01_catalyst_timeline.png ... 05_category_event_paths.png: sourced charts for articles and GitHub.",
        "- fundamental_catalyst_research.py: reproducible analysis source.", "",
        "**Sources and factual descriptions:** see URL in each row of catalyst_events.csv.", "",
    ])
    (OUT/"catalyst_research_notes.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    events = research_events()
    prices = get_market_prices()
    daily = portfolio_daily_returns(prices)
    analysis = event_statistics(events, daily)
    analysis.to_csv(OUT/"catalyst_event_results.csv", index=False, encoding="utf-8-sig", float_format="%.8f")
    print("PART 4 — FUNDAMENTAL CATALYST EVENT STUDIES")
    print(f"Source-linked announcements: {len(events)} | analyzed: {len(analysis)}")
    print(f"Common adjusted close sample: {prices.index.min():%Y-%m-%d} → {prices.index.max():%Y-%m-%d}  ({len(prices)} sessions)")
    print(f"Analysis dates / portfolio: {daily.index.min():%Y-%m-%d} → {daily.index.max():%Y-%m-%d} | 50% long/50% short on gross")
    print("EVENT TIMING: next US trading session after the publication date (conservative; NOT necessarily immediate price reaction)")
    printable = analysis[["event_id", "published_date", "event_session", "category", "day0_pct", "day0_to_day3_pct", "spy_adjusted_3_pct"]].copy()
    print("\nEvent table: 0 and 3 additional sessions | gross P&L (% of $100k gross), before costs")
    with pd.option_context("display.max_rows", 30, "display.width", 160):
        print(printable.to_string(index=False, formatters={
            "published_date": lambda x: x.strftime("%b %d"),
            "event_session": lambda x: x.strftime("%b %d"),
            "day0_pct": lambda x: "n/a" if pd.isna(x) else f"{x:+.2f}%",
            "day0_to_day3_pct": lambda x: "n/a" if pd.isna(x) else f"{x:+.2f}%",
            "spy_adjusted_3_pct": lambda x: "n/a" if pd.isna(x) else f"{x:+.2f}%",
        }))
    figure_timeline(daily, analysis)
    figure_heatmap(analysis)
    figure_beta_comparison(analysis)
    figure_attribution(analysis)
    figure_event_paths(daily, analysis)
    write_notes(analysis, daily)
    print("\nSAVED to:", OUT.resolve())
    for p in sorted(OUT.iterdir()):
        print("  ", p.name)
    print("\nNext: open catalyst_research_notes.md, check sources, and add the verified findings to your GitHub README.")


if __name__ == "__main__":
    main()
