"""Part 5: interactive hyperscaler vs semiconductor relative-value dashboard.

Launch (from folder containing this file): python -m streamlit run dashboard.py
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
import io
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from portfolio_engine import (TICKERS, Settings, demo_prices, prices_to_returns,
                              prior_rolling_betas, simulate, summarize,
                              scenario_pnl, historical_windows)

st.set_page_config(page_title="AI Infrastructure | Relative Value", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

NAVY = "#153553"; BLUE = "#28629c"; TEAL = "#159a91"; AMBER = "#da8738"
RED = "#cd4959"; GREY = "#77889a"; LIGHT = "#d9e1ec"; PURPLE = "#7657b1"
CHART = dict(template="plotly_white", font=dict(family="Arial",size=12,color=NAVY),
             paper_bgcolor="white",plot_bgcolor="white",margin=dict(l=28,r=18,t=48,b=36),
             hovermode="x unified",legend=dict(orientation="h",y=1.08,x=0))

st.markdown("""<style>
.block-container {padding-top:1.5rem; padding-bottom:2rem}
h1, h2, h3 {color:#153553; letter-spacing:-.02em}
[data-testid="stMetric"] {background:#f6f8fb; padding:14px 16px; border-radius:10px; border:1px solid #e6ebf2}
.smallnote {color:#6b7d90;font-size:.85rem}
</style>""",unsafe_allow_html=True)


def line_fig(title, ytitle="USD"):
    fig=go.Figure();fig.update_layout(**CHART,title=dict(text=title,x=0,xanchor="left"),
                                      yaxis_title=ytitle,xaxis_title=None)
    fig.update_xaxes(showgrid=False);fig.update_yaxes(gridcolor="#edf1f5",zerolinecolor="#d3dae4")
    return fig


def render(fig, key=None):
    st.plotly_chart(fig, width="stretch", key=key)


def pct(x): return f"{x:+.2f}%"

def money(x): return f"${x:,.0f}" if x>=0 else f"−${abs(x):,.0f}"


@st.cache_data(ttl=3600,show_spinner="Fetching historical Yahoo prices...")
def download_yahoo(start_date, end_exclusive):
    import yfinance as yf
    data = yf.download(TICKERS,start=start_date,end=end_exclusive,
                       auto_adjust=False,actions=False,progress=False,threads=False,group_by="column")
    if data.empty or not isinstance(data.columns,pd.MultiIndex):
        raise ValueError("Yahoo returned no multi-ticker daily prices. Check internet access, date range and yfinance.")
    fields=set(data.columns.get_level_values(0))
    if "Close" not in fields or "Adj Close" not in fields:
        raise ValueError("Yahoo response has no Close / Adj Close. This app explicitly requests auto_adjust=False.")
    close=data["Close"].copy();adj=data["Adj Close"].copy()
    missing=[t for t in TICKERS if t not in close.columns or t not in adj.columns or adj[t].notna().sum()<3]
    if missing: raise ValueError(f"Missing usable historical ticker(s): {', '.join(missing)}. DRAM has a short listing history.")
    return close,adj


def load_uploaded_csv(file):
    df=pd.read_csv(file)
    cols={c.lower().replace("_"," ").strip(): c for c in df.columns}
    need=["date","ticker","close","adj close"]
    if not all(t in cols for t in need):
        raise ValueError("CSV must have columns Date, Ticker, Close, Adj Close (one row per ticker/date).")
    df=df.rename(columns={cols[k]:k for k in need})
    df["date"]=pd.to_datetime(df["date"],errors="raise")
    df["ticker"]=df["ticker"].astype(str).str.upper().str.strip()
    if df.duplicated(["date","ticker"]).any():
        raise ValueError("CSV has duplicate (date,ticker) observations.")
    close=df.pivot(index="date",columns="ticker",values="close")
    adj=df.pivot(index="date",columns="ticker",values="adj close")
    missing=set(TICKERS)-set(close.columns)
    if missing: raise ValueError(f"CSV is missing tickers: {', '.join(sorted(missing))}")
    return close.sort_index(), adj.sort_index()


def plot_series(fig, dates, values, name, color, dash=None, fill=None):
    fig.add_trace(go.Scatter(x=dates,y=values,name=name,mode="lines",line=dict(color=color,width=2.4,dash=dash),fill=fill))


st.title("AI Infrastructure | Relative-Value Trading Dashboard")
st.caption("Part 5 · Interactive Python/Streamlit research · Long AMZN / MSFT / GOOGL · Short 75% SMH / 25% DRAM")

with st.sidebar:
    st.header("Research inputs")
    source=st.radio("Price source",["Yahoo historical prices","Simulated demo","Upload daily-prices CSV"],index=0,
                    help="The simulated demo is synthetic and must never be reported as historical market performance.")
    uploaded_prices = st.file_uploader("Upload Date, Ticker, Close, Adj Close", type=["csv"]) if source=="Upload daily-prices CSV" else None
    st.divider()
    st.subheader("Portfolio")
    nav=st.number_input("Reference portfolio NAV ($)", min_value=10000, max_value=100_000_000,
                        value=1_000_000,step=100_000)
    gross=st.number_input("Daily gross notional ($)",min_value=1_000,max_value=10_000_000,value=100_000,step=10_000)
    long_pct=st.slider("Gross allocated to long hyperscalers (%)",10,90,50,5)
    risk_pct=st.number_input("Risk budget (% of NAV)",min_value=0.1,max_value=20.0,value=1.0,step=.1)
    with st.expander("Modeled execution & carrying costs",expanded=False):
        smh_rate=st.number_input("SMH borrow APR (%)",min_value=0.,max_value=50.,value=.60,step=.10)
        dram_rate=st.number_input("DRAM borrow APR (%)",min_value=0.,max_value=50.,value=1.70,step=.10)
        margin_debit=st.number_input("Margin debit ($)",min_value=0,max_value=10_000_000,value=0,step=5000)
        margin_rate=st.number_input("Margin borrowing APR (%)",min_value=0.,max_value=30.,value=5.,step=.25)
        execution_cost=st.number_input("Estimated FULL round-trip commissions & slippage ($)",min_value=0.,max_value=10000.,value=100.,step=25.)
    st.caption("Cost rates are illustrative—not live IBKR rates. Adjust to your broker's actual quotes.")

settings=Settings(gross=float(gross),long_weight=long_pct/100,borrow_smh_pct=smh_rate,
                  borrow_dram_pct=dram_rate,margin_debit=float(margin_debit),
                  margin_apr_pct=margin_rate,execution_cost=execution_cost,
                  nav=float(nav),risk_budget_pct=risk_pct)

try:
    if source=="Simulated demo":
        close,adj=demo_prices(); label="SIMULATED DEMO · NOT MARKET DATA"
    elif source=="Upload daily-prices CSV":
        if uploaded_prices is None:
            st.info("Upload a CSV with the columns Date, Ticker, Close, Adj Close. You need all six tickers for shared dates.")
            st.stop()
        close,adj=load_uploaded_csv(uploaded_prices);label="USER-SUPPLIED CSV · VERIFY PROVENANCE"
    else:
        # Excludes the current calendar day to avoid partial daily bars.
        close,adj=download_yahoo("2026-04-02",date.today().isoformat())
        label="YAHOO FINANCE · ADJUSTED DAILY CLOSES · HISTORICAL"
    rets=prices_to_returns(close,adj)
except Exception as exc:
    st.error(f"Price download/validation failed: {exc}")
    st.info("Try 'Simulated demo' to explore the interface, then switch back to Yahoo. There is no silent substitution of simulated data.")
    st.stop()

with st.sidebar:
    max_entry=rets.index[-2].date() if len(rets)>1 else rets.index[-1].date()
    default_entry=min(max(date(2026,11,5),rets.index[0].date()),max_entry)
    entry=st.date_input("Trade reference CLOSE",value=default_entry,min_value=rets.index[0].date(),max_value=max_entry,
                        help="Modeled trading starts with the NEXT day's close-to-close return.")
    beta_window=st.slider("Factor estimation lookback (sessions)",20,60,30,5)
    compare_beta=st.checkbox("Compare rolling SPY-beta-target construction",value=True)

st.caption(f"**{label}**  |  Shared returns {rets.index[0]:%b %d, %Y} – {rets.index[-1]:%b %d, %Y}  |  Modeled entry: after {entry:%b %d, %Y} close")
if source=="Simulated demo":
    st.error("SYNTHETIC DATA ACTIVE: charts and statistics below are fabricated examples for software testing—not backtest evidence.")

try:
    trade=simulate(rets,settings,str(entry),beta_target=False,beta_window=beta_window)
    beta_trade=simulate(rets,settings,str(entry),beta_target=True,beta_window=beta_window)
except Exception as exc:
    st.error(f"Unable to model selected entry: {exc}");st.stop()
metric=summarize(trade,settings)
beta_metric=summarize(beta_trade,settings)

st.info("**Model convention:** both sides rebalance to the selected gross dollars every trading session. This is NOT your actual IBKR share inventory or fills. Historical adjusted closes include dividend/distribution effects, so they are **not** added again. Carrying costs and one estimated round-trip execution cost are applied separately. No tax, market impact, daily borrow recalls or margin liquidation simulation.")

m1,m2,m3,m4,m5=st.columns(5)
with m1: st.metric("Net modeled trade P&L",money(metric["net_pnl"]),pct(metric["gross_return_pct"])+" of gross")
with m2: st.metric("Return on portfolio NAV",pct(metric["nav_return_pct"]))
with m3: st.metric("Trade Sharpe (annualized)",f"{metric['sharpe']:.2f}")
with m4: st.metric("Realized SPY beta",f"{metric['realized_beta']:+.2f}")
with m5: st.metric("Worst loss / risk budget",f"{metric['risk_used_pct']:.0f}%",help="Max below-entry cumulative modeled P&L divided by your chosen risk budget; not an ex-ante max loss.")

main_tab,risk_tab,scenario_tab,events_tab,method_tab=st.tabs([
    "📈 Performance & exposure","📐 Beta, volatility & correlations",
    "⚡ Scenario laboratory","🗓️ Catalysts","📁 Data & methodology"])

with main_tab:
    a,b=st.columns(2)
    with a:
        fig=line_fig("Net P&L since the selected entry close")
        plot_series(fig,trade.index,trade["Cumulative Gross P&L"],"Original gross",GREY,dash="dot")
        plot_series(fig,trade.index,trade["Cumulative Net P&L"],"Original net",BLUE)
        if compare_beta:plot_series(fig,beta_trade.index,beta_trade["Cumulative Net P&L"],"Beta-target net",TEAL)
        fig.add_hline(y=-settings.budget_dollars,line=dict(color=RED,dash="dash"),annotation_text="-risk budget")
        render(fig,"pnl")
    with b:
        fig=line_fig("Cumulative leg attribution (fixed daily notional)")
        plot_series(fig,trade.index,trade["Cumulative Long P&L"],"Long hyperscalers",TEAL)
        plot_series(fig,trade.index,trade["Cumulative Short P&L"],"Short semiconductors",AMBER)
        plot_series(fig,trade.index,trade["Cumulative Costs"],"Modeled costs",RED)
        fig.add_hline(y=0,line_color=GREY,line_width=1)
        render(fig,"legs")
    a,b=st.columns(2)
    with a:
        fig=line_fig("Basket growth since entry (total-return index)","Index (100 = entry)")
        for series,color,label_ in [("Long",TEAL,"Long basket"),("ShortBasket",AMBER,"Short basket"),("Market",GREY,"SPY")]:
            vals=100*(1+trade[series]).cumprod()
            plot_series(fig,trade.index,vals,label_,color)
        render(fig,"basketgrowth")
    with b:
        fig=line_fig("Drawdown from model equity high-water mark","Drawdown (%)")
        plot_series(fig,trade.index,trade["Trade drawdown %"],"Original 50/50",BLUE)
        if compare_beta:plot_series(fig,beta_trade.index,beta_trade["Trade drawdown %"],"Beta-target",TEAL)
        render(fig,"drawdown")
    a,b=st.columns(2)
    with a:
        fig=line_fig("Target long, short, gross and net dollars")
        plot_series(fig,trade.index,trade["Long $ target"],"Long $",TEAL)
        plot_series(fig,trade.index,-trade["Short $ target"],"Short $ (negative)",RED)
        plot_series(fig,trade.index,trade["Gross $ target"],"Gross $",BLUE,dash="dot")
        plot_series(fig,trade.index,trade["Net $ target"],"Net $",GREY,dash="dash")
        render(fig,"exposure")
    with b:
        st.subheader("Attribution & exposure snapshot")
        attribution=pd.DataFrame({"Measure":["Long total-return P&L","Short total-return P&L","Approx. long dividend component",
               "Approx. short distribution component","Borrow fees","Margin interest","Est. round-trip costs","Net model P&L"],
            "USD":[trade["Long P&L"].sum(),trade["Short P&L"].sum(),trade["Long dividends approximated"].sum(),
                   trade["Short distributions approximated"].sum(),trade["Borrow fees"].sum(),
                   trade["Financing"].sum(),trade["Round-trip execution costs"].sum(),metric["net_pnl"]]})
        st.dataframe(attribution.style.format({"USD":"${:,.2f}"}),hide_index=True,width="stretch")
        st.caption("Dividend components are already embedded in adjusted-close P&L; these rows are a breakdown, not extra cashflows. Gross and net target exposure are reset daily, not actual share holdings.")

with risk_tab:
    window=st.slider("Rolling risk lookback (trading sessions)",10,60,30,5,key="risk_window")
    baseline=rets.copy()
    spread=settings.long_weight*baseline["Long"]-(1-settings.long_weight)*baseline["ShortBasket"]
    rolling_beta=(spread.rolling(window).cov(baseline["Market"])/baseline["Market"].rolling(window).var())
    corr_l_s=baseline["Long"].rolling(window).corr(baseline["ShortBasket"])
    corr_trade_spy=spread.rolling(window).corr(baseline["Market"])
    vol_trade=100*np.sqrt(252)*spread.rolling(window).std()
    vol_spy=100*np.sqrt(252)*baseline["Market"].rolling(window).std()
    a,b=st.columns(2)
    with a:
        fig=line_fig(f"Realized SPY beta ({window} sessions)","Beta")
        plot_series(fig,baseline.index,rolling_beta,"Original trade",BLUE)
        fig.add_hline(y=0,line_color=GREY);render(fig,"rollbeta")
    with b:
        fig=line_fig(f"Rolling daily correlations ({window} sessions)","Correlation")
        plot_series(fig,baseline.index,corr_l_s,"Hyperscalers ↔ semis",TEAL)
        plot_series(fig,baseline.index,corr_trade_spy,"Long-short ↔ SPY",AMBER)
        fig.add_hline(y=0,line_color=GREY);fig.update_yaxes(range=[-1.02,1.02]);render(fig,"rollcorr")
    a,b=st.columns(2)
    with a:
        fig=line_fig(f"Annualized realized volatility ({window} sessions)","Annualized volatility (%)")
        plot_series(fig,baseline.index,vol_trade,"Long-short",BLUE)
        plot_series(fig,baseline.index,vol_spy,"SPY",GREY)
        render(fig,"rollvol")
    with b:
        prior=prior_rolling_betas(rets,beta_window)
        fig=line_fig(f"Beta-target long weight ({beta_window}-session prior data)","% of gross")
        plot_series(fig,prior.index,100*prior["long_weight_beta_target"],"Long exposure",TEAL)
        fig.add_hline(y=50,line=dict(color=GREY,dash="dash"),annotation_text="Original 50/50")
        fig.update_yaxes(range=[0,100]);render(fig,"betasizing")
    st.caption("Beta-target weights come from the preceding data and are lagged one session to reduce look-ahead bias. When both estimated basket betas are not positive, the code falls back to 50/50; weights are bounded 5–95%. Neither specification is a fully hedged multivariate factor model.")
    if compare_beta:
        cmp=pd.DataFrame({"Metric":["Modeled net P&L", "Gross return", "SPY beta", "Annualized Sharpe", "Max drawdown (% of model equity)"],
                          "Original 50/50":[money(metric["net_pnl"]),pct(metric["gross_return_pct"]),f"{metric['realized_beta']:+.2f}",f"{metric['sharpe']:.2f}",pct(metric["max_drawdown_pct"])],
                          "Beta-target":[money(beta_metric["net_pnl"]),pct(beta_metric["gross_return_pct"]),f"{beta_metric['realized_beta']:+.2f}",f"{beta_metric['sharpe']:.2f}",pct(beta_metric["max_drawdown_pct"])]})
        st.dataframe(cmp,hide_index=True,width="stretch")

with scenario_tab:
    st.markdown("### Change the price shocks and see the result immediately")
    st.caption("Forward shocks below are **hypothetical price changes**, unlike the adjusted-close historical backtest. Cash dividends and short ETF distributions are modeled separately here to avoid double-counting.")
    c1,c2,c3=st.columns(3)
    with c1: long_move=st.slider("Hyperscaler basket price move (%)",-40,50,-5,1)
    with c2: semis_move=st.slider("Semiconductor basket price move (%)",-40,70,-10,1)
    with c3: horizon=st.slider("Scenario horizon (calendar days)",1,365,90,1)
    with st.expander("Scenario cash distribution assumptions"):
        long_yield=st.number_input("Long dividends (% annualized)",min_value=0.0,max_value=15.0,value=.40,step=.1)
        short_yield=st.number_input("Short ETF distributions owed (% annualized)",min_value=0.0,max_value=15.0,value=.70,step=.1)
    result=scenario_pnl(settings,long_move,semis_move,horizon,long_yield,short_yield)
    a,b,c,d=st.columns(4)
    with a: st.metric("Long price P&L",money(result["Long price"]))
    with b: st.metric("Short price P&L",money(result["Short price"]))
    with c: st.metric("Net after model costs",money(result["Net P&L"]))
    with d: st.metric("Return on gross",pct(100*result["Net P&L"]/settings.gross))
    if result["Net P&L"] < -settings.budget_dollars:
        st.warning("This scenario exceeds your selected risk budget. That budget is an internal limit, not a maximum possible loss or an enforced stop. Short losses can exceed the original notional.")
    a,b=st.columns([.75,1.25])
    with a:
        fig=go.Figure()
        parts=[k for k in result if k not in ["Gross P&L","Net P&L"]]
        fig.add_trace(go.Bar(x=[result[k] for k in parts],y=parts,orientation="h",
                             marker_color=[TEAL if result[k]>=0 else RED for k in parts],name="Contribution"))
        # Apply the shared layout first, then override its margin separately.
        # Passing margin= together with **CHART (which also includes margin)
        # raises: TypeError: got multiple values for keyword argument 'margin'.
        fig.update_layout(**CHART,title="Scenario P&L bridge (components)",
                          xaxis_title="USD",showlegend=False,height=450)
        fig.update_layout(margin=dict(l=8,r=8,t=54,b=40))
        fig.add_vline(x=0,line_color=GREY);render(fig,"shockparts")
    with b:
        xs=np.linspace(-40,70,112);ys=np.linspace(-40,50,92)
        base=scenario_pnl(settings,0,0,horizon,long_yield,short_yield)["Net P&L"]
        z=settings.long_dollars*ys[:,None]/100 - settings.short_dollars*xs[None,:]/100 +base
        lim=max(abs(np.nanmin(z)),abs(np.nanmax(z)))
        fig=go.Figure(go.Heatmap(z=z,x=xs,y=ys,colorscale=[[0,RED],[.5,"#f8f9fc"],[1,BLUE]],
                                 zmid=0,zmin=-lim,zmax=lim,colorbar=dict(title="Net $"),hovertemplate="Semis: %{x:+.1f}%<br>Hyperscalers: %{y:+.1f}%<br>Net: $%{z:,.0f}<extra></extra>"))
        zero_y=(settings.short_dollars*xs/100-base)/settings.long_dollars*100
        budget_y=(settings.short_dollars*xs/100-base-settings.budget_dollars)/settings.long_dollars*100
        fig.add_trace(go.Scatter(x=xs,y=zero_y,mode="lines",name="Net break-even",line=dict(color=NAVY,width=2)))
        fig.add_trace(go.Scatter(x=xs,y=budget_y,mode="lines",name="−Risk budget",line=dict(color=RED,width=2,dash="dash")))
        fig.add_trace(go.Scatter(x=[semis_move],y=[long_move],mode="markers",name="Your scenario",
                                 marker=dict(color="black",size=12,symbol="x")))
        fig.update_layout(**CHART,title="Stress map · move either basket",xaxis_title="Semiconductor price move (%)",
                          yaxis_title="Hyperscaler price move (%)",height=450)
        fig.update_yaxes(range=[-40,50]);render(fig,"shockmap")
    presets=[("Thesis plays out",2,-15),("Semis down alone",0,-10),("Both sell off",-5,-10),
             ("Equal selloff",-10,-10),("Hyperscalers down alone",-5,0),
             ("Semiconductor squeeze",3,20),("Larger squeeze",0,25)]
    preset_rows=[]
    for name,lv,sv in presets:
        p=scenario_pnl(settings,lv,sv,horizon,long_yield,short_yield)
        preset_rows.append({"Scenario":name,"Hyperscalers (%)":lv,"Semis (%)":sv,
                            "Gross P&L ($)":p["Gross P&L"],"Net P&L ($)":p["Net P&L"],
                            "Net / gross (%)":100*p["Net P&L"]/settings.gross})
    st.subheader("Seven fixed scenario cases")
    preset_df=pd.DataFrame(preset_rows)
    st.dataframe(preset_df.style.format({"Gross P&L ($)":"${:,.0f}","Net P&L ($)":"${:,.0f}",
                                         "Net / gross (%)":"{:+.2f}%"}),hide_index=True,width="stretch")
    st.download_button("Export scenario table (CSV)",preset_df.to_csv(index=False),file_name="part5_scenarios.csv",mime="text/csv")
    st.divider()
    window=st.select_slider("Historical rolling shock window (trading sessions)",options=[3,5,10,20],value=5)
    episodes=historical_windows(rets,settings,window)
    st.caption("These historical episodes are overlapping windows with fixed opening allocations. They are not independent backtests, not implied future forecasts and exclude financing costs.")
    a,b=st.columns(2)
    with a:
        fig=line_fig(f"Past {window}-session shock P&L, fixed opening exposures")
        plot_series(fig,episodes.index,episodes["P&L"],f"{window}-session gross P&L",BLUE)
        fig.add_hline(y=-settings.budget_dollars,line=dict(color=RED,dash="dash"))
        render(fig,"episodes")
    with b:
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=100*episodes["ShortBasket"],y=100*episodes["Long"],mode="markers",
                                 marker=dict(color=episodes["P&L"],colorscale="RdBu",cmid=0,
                                             size=7,colorbar=dict(title="Gross P&L $")),
                                 text=[x.strftime("%Y-%m-%d") for x in episodes.index],
                                 hovertemplate="Window end %{text}<br>Semis %{x:+.1f}%<br>Hyperscalers %{y:+.1f}%<extra></extra>"))
        fig.update_layout(**CHART,title=f"Observed basket shocks ({window}-session windows)",
                          xaxis_title="Semiconductor return (%)",yaxis_title="Hyperscaler return (%)")
        render(fig,"shockscatter")
    worst=episodes.nsmallest(8,"P&L").copy()
    worst["End date"]=worst.index.strftime("%Y-%m-%d")
    st.markdown("**Eight worst historical rolling windows (gross, no modeled costs)**")
    st.dataframe(worst[["End date","Long","ShortBasket","Market","P&L"]].style.format({
        "Long":"{:+.2%}","ShortBasket":"{:+.2%}","Market":"{:+.2%}","P&L":"${:,.0f}"}),
        hide_index=True,width="stretch")

with events_tab:
    st.markdown("### Overlay the Part 4 announcement database")
    st.caption("This overlays historical event DATES, not claimed causation. The first session AFTER the date is used for the marker; same-day earnings reactions may be missed.")
    found=None
    for p in [Path.cwd()/"part4_outputs"/"catalyst_events.csv",
              Path.cwd().parent/"part4_outputs"/"catalyst_events.csv"]:
        if p.exists():found=p;break
    uploaded=st.file_uploader("Optional: upload your Part 4 catalyst_events.csv",type="csv",key="events")
    try:
        events=pd.read_csv(uploaded if uploaded is not None else found) if uploaded is not None or found is not None else None
    except Exception as exc:
        events=None;st.error(f"Could not read catalyst CSV: {exc}")
    fig=line_fig("Your long/short net P&L and dated catalysts")
    plot_series(fig,trade.index,trade["Cumulative Net P&L"],"Net modeled P&L",BLUE)
    if events is not None:
        date_col=next((x for x in ["published_date","event_date","date"] if x in events.columns),None)
        label_col=next((x for x in ["headline","event","title","description","event_name"] if x in events.columns),None)
        category_col=next((x for x in ["category","event_type"] if x in events.columns),None)
        if date_col is None:
            st.warning("Catalyst CSV found, but no 'published_date' / 'event_date' / 'date' column exists.")
        else:
            ev=events.copy();ev[date_col]=pd.to_datetime(ev[date_col],errors="coerce")
            ev=ev.dropna(subset=[date_col]);xs=[];ys=[];labels=[]
            for _,e in ev.iterrows():
                match=trade.index[trade.index>e[date_col].normalize()]
                if not len(match):continue
                d=match[0];xs.append(d);ys.append(float(trade.loc[d,"Cumulative Net P&L"]))
                title=str(e[label_col]) if label_col else "Catalyst"
                category=str(e[category_col]) if category_col else ""
                labels.append(f"{title} | {category} | released {e[date_col]:%Y-%m-%d}")
            if xs:
                fig.add_trace(go.Scatter(x=xs,y=ys,mode="markers",name="Post-announcement session",
                                         marker=dict(color=AMBER,size=10,symbol="diamond"),
                                         text=labels,hovertemplate="%{text}<br>Net P&L: $%{y:,.0f}<extra></extra>"))
                st.success(f"Overlaid {len(xs)} catalysts occurring within the selected trade window.")
            st.dataframe(ev,hide_index=True,width="stretch")
    else: st.info("No local Part 4 event file detected. Upload `catalyst_events.csv` from `Downloads\\part4_outputs` to see the overlay.")
    render(fig,"events_overlay")

with method_tab:
    st.subheader("How to interpret this app")
    st.markdown("""
    - **It is a Python program, served locally in your browser by Streamlit.** Sliders trigger new calculations and chart renders; you don't rerun notebook cells.
    - **Positions:** equal-weight AMZN, MSFT and GOOGL on the long side; SMH (75%) and DRAM (25%) on the short side.
    - **Backtest:** close-to-close dividend-adjusted returns and daily reset to the selected dollar exposures. First trading return is after the selected entry close. Uses common dates across all six tickers. This is not an IBKR activity report.
    - **P&L:** daily long dollar exposure × long basket return minus daily short dollar exposure × semis return. Historical dividend/ETF distribution effects are already in adjusted closes. Borrow/financing and estimated round-trip trading costs are added separately; costs are assumptions, not broker statements.
    - **Exposure:** Gross = abs(long) + abs(short). Net = long − short. Dollar neutral (net zero) does not mean beta neutral.
    - **Risk budget:** Selected percent of the $1M portfolio, not an enforceable cap. Short positions can lose more than the initial short proceeds. Drawdown chart uses model equity equal to opening gross exposure plus cumulative net P&L, **not** the full account NAV.
    - **Sharpe:** annualized mean daily modeled return on gross divided by its standard deviation × √252; zero risk-free reference. Historical fit is not out-of-sample evidence.
    - **Beta target:** rolling betas only from prior daily observations; invalid beta conditions revert to 50/50, clipped to 5–95% gross long, so realized beta need not be precisely zero.
    - **Future scenarios:** terminal *price* changes, with distributions modeled separately at assumed yields; no adjusting close used here. Carrying costs approximate a fixed number of calendar days.
    - **Historical windows:** overlapping, compounded historical basket moves, a diagnostic—not independent event tests or a forecast.
    - **Data limits:** DRAM launched in 2026. Yahoo data can be delayed, revised, unavailable, or include ticker-specific issues. Real orders, borrow availability, taxes, dynamic margin, cash interest, trading impact, rebalances and true inventory P&L need IBKR data.
    """)
    st.markdown("**Portfolio construction and provenance**")
    st.table(pd.DataFrame({"Side":["Long","Long","Long","Short","Short","Benchmark"],
                          "Ticker":["AMZN","MSFT","GOOGL","SMH","DRAM","SPY"],
                          "Weights within sleeve":["33.3%","33.3%","33.3%","75%","25%","n/a"]}))
    t=trade.copy();t.index.name="Date"
    st.download_button("Download modeled daily P&L data",t.to_csv(),file_name="part5_daily_pnl.csv",mime="text/csv")
    st.download_button("Download source basket return data",rets.to_csv(),file_name="part5_basket_returns.csv",mime="text/csv")
    st.caption("Sources: Yahoo Finance historical market data when selected, via yfinance; manually supplied local user CSV, or explicitly synthetic demo. Research and implementation: portfolio owner. This code intentionally sends no trading orders and has no brokerage authentication.")

st.divider()
st.caption("Research dashboard · illustrative model, not trading advice · Uses price history through the last downloaded completed session · No automatic broker execution")
