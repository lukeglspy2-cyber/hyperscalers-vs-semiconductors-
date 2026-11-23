# Part 4 | Fundamental Catalyst Research and Event Studies

**Research author:** Luke Gillespie  
**Sample cutoff:** 2026-11-20 closing prices  
**Data coverage:** 2026-04-06 to 2026-11-20  
**Market prices:** Yahoo Finance via yfinance, dividend/split adjusted closes

## Economic question

Do data-center grid constraints, permitting, construction and CapEx announcements coincide with relative-value moves between cloud hyperscalers and semiconductor exposure?

## Portfolio convention

- 50% opening gross in equal-weight AMZN/MSFT/GOOGL long.
- 50% opening gross short: 75% SMH, 25% DRAM.
- Daily arithmetic returns; daily-rebalanced, fixed-gross P&L is 0.5 × hyperscaler basket return minus 0.5 × semiconductor basket return.
- P&L is expressed as a percent of $100,000 starting gross, before borrow fees, financing, dividends not already captured in adjusted returns, and execution costs.
- The adjusted-price series reflects dividend/split adjustments. Cash-flow modeling belongs in Part 3 and must not be added again to total-return data.

## Timing / event definitions

- Source publication dates appear in catalyst_events.csv, with directly linked evidence.
- Conservatively use the **first trading session strictly AFTER** the publication date as E0. Some news was released during the trading day, so E0 may **miss** the initial reaction. This is not a close-to-close release-time accurate event study.
- E0..E+3 means 4 trading sessions, summed as fixed-gross daily P&L, not a compounded ETF return.
- SPY beta is estimated using at most 40 PRE-event sessions, at least 30 observed sessions. The SPY-adjusted spread subtracts beta × the contemporary SPY move; it does not demonstrate causal alpha.
- Events may overlap (especially multiple company earnings on October 28–29); do not assume independent observations or sum event profits as an actual portfolio history.
- The selection is purposive and retrospective; event categories, publication timestamps, revised articles, and potential prior market knowledge should be independently audited before sharing as rigorous evidence.
- Announcements are sometimes proposals, intentions or plans—not completed permits, energized grid connections or completed buildings.
- This cannot establish whether infrastructure bottlenecks caused the relative performance; market, semiconductor, earnings, rate, and AI factors overlap.
- DRAM only has a short ETF history; the basket is not a multi-year validated strategy.

## Descriptive E0–E+3 results (gross, before costs)

These are correlations in a selected catalog, not tests of an identified causal effect.

### Highest modeled gross outcomes

- **E16 2026-10-29** Amazon Q3 reiterates roughly $220B 2026 cash CapEx: +8.20%
- **E04 2026-07-14** Google announces Arkansas energy partnership: +4.97%
- **E05 2026-07-22** Alphabet increases 2026 CapEx guidance: +4.88%

### Lowest modeled gross outcomes

- **E17 2026-11-05** Google announces $17B Wyoming data-center project: -6.72%
- **E09 2026-08-10** Amazon outlines planned Pecos County data-center campus: -4.89%
- **E01 2026-06-10** Texas directs PUC/ERCOT to protect customers from data-center grid costs: -4.13%

## Follow-up research

1. Validate intraday release timing from official IR calls/press-release timestamps, and redo E0 alignment.
2. Record surprise vs. consensus CapEx expectations, not just CapEx levels.
3. Add permit approvals vs. rejections, MW of interconnection approvals, queue withdrawals and construction delays with measured magnitude.
4. Test sensitivity to SOXX/SMH and DRAM, event-window length, factor controls, sector benchmarks, and excluding earnings days.
5. Separate ex-ante dated hypotheses from retrospectively selected catalysts to avoid confirmation bias.

## Files

- catalyst_events.csv: editable dated source-linked database.
- fundamental_metrics.csv: measured and planned numerical quantities tied to event IDs; check their status and distinct units.
- catalyst_event_results.csv: event study statistics and dates.
- 01_catalyst_timeline.png ... 05_category_event_paths.png: sourced charts for articles and GitHub.
- fundamental_catalyst_research.py: reproducible analysis source.

**Sources and factual descriptions:** see URL in each row of catalyst_events.csv.
