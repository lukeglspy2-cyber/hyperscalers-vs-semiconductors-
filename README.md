# AI Infrastructure: Hyperscalers vs. Semiconductors — Interactive Portfolio Dashboard

**Part 5 | Long/short relative-value research | Python + Streamlit**

This local interactive research dashboard extends the prior Jupyter notebook and Parts 2–4 scripts. It is **not** a brokerage account display and does **not** submit orders.

## The trade

- **Long sleeve**: AMZN, MSFT, GOOGL (equal weights within the sleeve).
- **Short sleeve**: SMH (75% of sleeve), DRAM (25% of sleeve).
- **Original reference model**: $50,000 long + $50,000 short = **$100,000 daily gross exposure**, **$0 net dollar exposure**.
- **Reference paper portfolio NAV**: $1,000,000; 1% of NAV = **$10,000 research risk budget**.
- **Trade reference date**: close of November 5, 2026; first modeled return is the following session.

The hypothesis is that electricity and physical infrastructure constraints may lead AI-linked semiconductor exposures to underperform hyperscalers. The user may also intentionally hold negative broad-equity beta. The dashboard does not claim to prove this thesis.

## What is Streamlit?

Streamlit is a Python framework that runs a small local web server and turns Python data analysis into an interactive browser page. You choose dates, change allocations, move stress-test sliders, inspect tooltips, and download CSVs; Streamlit recalculates the display automatically. It is **not** another Jupyter notebook and it does **not** require hosting a public website or paying for web hosting.

## Exact Windows installation instructions (Anaconda Prompt)

1. Download the `ai_relative_value_dashboard.zip` archive and save it to **Downloads**.
2. In Windows File Explorer → Downloads, **right-click the ZIP → Extract All → Extract**. You should see the folder `Downloads\ai_relative_value_dashboard`, with `dashboard.py`, `portfolio_engine.py`, and `requirements.txt` inside. If Windows nests it one level deeper, open the deeper folder.
3. Open **Anaconda Prompt** (the same program used to start JupyterLab).
4. Paste these commands **one line at a time**, pressing Enter after each:

   ```bat
   conda activate finance
   cd /d "%USERPROFILE%\Downloads\ai_relative_value_dashboard"
   python -m pip install -r requirements.txt
   python -m streamlit run dashboard.py
   ```

5. Chrome should open a new tab, usually **http://localhost:8501**. If not, copy the **Local URL** displayed in Anaconda Prompt into Chrome.
6. **Leave Anaconda Prompt open** while using the dashboard. Closing it shuts down the local dashboard server. Press **Ctrl+C** in Anaconda Prompt when finished.
7. On the left, choose **Yahoo historical prices**, **Simulated demo**, or **Upload daily-prices CSV**. The demo is always conspicuously marked simulated.

**Do not run this with `%run dashboard.py` inside a Jupyter notebook.** Streamlit applications must be launched from the terminal as above. JupyterLab (normally localhost:8888) and Streamlit (normally localhost:8501) are separate servers and can run at the same time.

If `cd` reports a missing folder, open the extracted folder in File Explorer, click its address bar, copy the full path, and run `cd /d "PASTE_FULL_FOLDER_PATH_HERE"`.

If Yahoo Finance is temporarily unavailable, choose the **Simulated demo** mode to explore the interface and try Yahoo again later. The app will **never quietly swap in synthetic data**.

## Dashboard sections

| Tab | Features |
|---|---|
| Performance & exposure | Cumulative gross/net modeled P&L; long/short attribution; indexed basket returns; drawdown; exposure chart; dividend/borrow cost breakdown |
| Beta, volatility & correlations | 30-session rolling SPY beta, rolling basket correlation, volatility, prior-data beta-target long weights; 50/50 vs beta-target comparison |
| Scenario laboratory | Interactive long and semiconductor price shocks; cash-cost assumptions; heatmap, P&L components; seven premade scenarios; historical rolling-shock analysis |
| Catalysts | Optional overlay of Part 4's `catalyst_events.csv`, with pop-up event labels |
| Data & methodology | Definitions, limitations, source provenance, daily model P&L and basket returns CSV exports |

## Optional Part 4 integration

In JupyterLab, Part 4 saved a folder such as `C:\Users\lukeg\Downloads\part4_outputs` containing `catalyst_events.csv`.

The new dashboard automatically checks for the CSV beside the app or in a sibling folder called `part4_outputs`. You can also **upload that CSV** in the dashboard's **Catalysts** tab. No need to move or alter the original notebook.

## Historical price source

Default mode downloads historical prices from Yahoo Finance using `yfinance.download` with `auto_adjust=False`. The script uses both `Close` and `Adj Close` fields. It aligns the six tickers on shared trading sessions and starts no earlier than DRAM's April 2026 availability.

* The historical P&L uses **adjusted-close total returns**, which incorporate ordinary dividends/distributions. Do not add ETF distributions a second time.
* The `Price P&L`, `Long dividends approximated`, and `Short distributions approximated` components are a *reconciliation* using adjusted-versus-unadjusted daily returns, not exact broker cashflows.
* The hypothetical **forward-shock scenario lab** instead uses **terminal price moves** and separately estimates dividends/ETF payments with configurable annualized yields. These two methods are consistent: **different bases, no double counting**.
* Borrow APRs (SMH 0.6% and DRAM 1.7%), financing APR (5%), and round-trip trading costs ($100) are **illustrative assumptions**. Actual borrow availability/fees, commission schedules, payouts, and financing costs must be verified from IBKR.
* Actual positions drift between rebalances; this model resets dollar notionals each session. A live holdings P&L system needs actual share counts, fills, corporate actions, financing and borrow charges.

### CSV upload format

If you already have historic daily bars, upload a CSV with one row per ticker per date:

```csv
Date,Ticker,Close,Adj Close
2026-11-05,AMZN,250.00,249.50
2026-11-05,MSFT,500.00,498.00
2026-11-05,GOOGL,200.00,199.00
```

You also need **SMH, DRAM and SPY**, all tickers, and multiple **shared dates**. The example prices above are just schema illustrations, not actual historical quotations.

## Risk disclosures and honest claims

- A $10,000 **risk budget is not a loss ceiling**, because a short can lose more than its opening proceeds. No stop-loss is enforced by the software.
- Gross exposure is the absolute sum of the long and short notional; net dollar exposure is long minus short notional. Dollar neutrality does **not** imply beta neutrality.
- Annualized Sharpe uses √252 and zero risk-free reference. Model drawdowns are calculated on opening *gross notional + cumulative model P&L*, not the entire $1 million reference NAV.
- The beta-target model estimates constituent basket betas from prior observations and shifts the inputs a day to avoid same-session look-ahead. Its weights are bounded to 5–95%; weak/unusual beta estimates cause fallback to 50/50. It doesn't guarantee exactly zero realized beta.
- Historical shock windows overlap and do not establish independently tested events, performance persistence or causality.
- Figures are **modeled**, not independently verified trades. Data are historical, and Yahoo download access may be delayed, incomplete or blocked. DRAM's short history limits inference. ETF tracking and sector exposures evolve over time.
- This model ignores taxes, overnight gaps, enforced margin maintenance, stock-loan recalls, short dividend timing, varying borrow rates, FX, bid-ask dynamics, position drift, liquidity constraints, and detailed execution costs.

## Project structure

```
Dashboard/
├── dashboard.py           # Browser-based interactive UI
├── portfolio_engine.py    # Price, factor, P&L, risk and scenario calculations
├── requirements.txt       # Python dependencies
├── README.md              # Setup, assumptions, methodology and limitations
└── tests/
    └── test_engine.py     # Test math and guard against forward-looking beta inputs
```

## Developer checks

```bat
python -m pip install pytest
python -m pytest tests -q
```

For a public GitHub portfolio, publish the Python files, README and tests, but keep account-level exports or private brokerage statements out of the repository. The offline demo is illustrative and must never be presented as real backtested returns.

Sources: [Streamlit documentation](https://docs.streamlit.io/), [yfinance documentation](https://ranaroussi.github.io/yfinance/), and Yahoo Finance historical prices obtained **only if run in Yahoo mode**.
