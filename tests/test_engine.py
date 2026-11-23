from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import pytest

from portfolio_engine import (Settings, scenario_pnl, demo_prices, prices_to_returns,
                              prior_rolling_betas, simulate, summarize, historical_windows)


def test_stress_cases_50_50():
    s=Settings()
    a=scenario_pnl(s,-5,-10,90)
    assert a['Gross P&L']==2500
    assert a['Long price']==-2500
    assert a['Short price']==5000
    assert a['Net P&L']==pytest.approx(2255.14,abs=.01)
    equal=scenario_pnl(s,-10,-10,90)
    assert equal['Gross P&L']==0
    assert equal['Net P&L']<0
    assert scenario_pnl(s,0,25,90)['Net P&L'] < -10_000


def test_demo_is_deterministic():
    c,a=demo_prices();c2,a2=demo_prices()
    pd.testing.assert_frame_equal(c,c2)
    pd.testing.assert_frame_equal(a,a2)
    r=prices_to_returns(c,a)
    assert len(r)>100
    assert set(['Long','ShortBasket','Market','Long_price','Short_price']).issubset(r.columns)


def test_price_dividend_reconciliation():
    c,a=demo_prices();r=prices_to_returns(c,a)
    s=Settings()
    m=simulate(r,s,'2026-11-05')
    gross_price=(m['Price P&L'] + m['Long dividends approximated']
                   + m['Short distributions approximated']).to_numpy()
    assert np.allclose(gross_price,m['Gross P&L'].to_numpy())
    assert np.allclose(m['Long $ target'] + m['Short $ target'],s.gross)
    assert np.allclose(m['Net $ target'],0)
    z=summarize(m,s)
    assert np.isfinite(z['net_pnl'])
    assert m.index[0]>pd.Timestamp('2026-11-05')
    assert m['Cumulative Net P&L'].iloc[-1]==pytest.approx(m['Net P&L'].sum())


def test_future_perturbation_does_not_affect_prior_betas():
    c,a=demo_prices();r=prices_to_returns(c,a)
    base=prior_rolling_betas(r,30)
    ix=r.index[-1]
    altered=r.copy();altered.loc[ix,'Long']=50
    new=prior_rolling_betas(altered,30)
    assert base.loc[ix,'beta_long_prior']==pytest.approx(new.loc[ix,'beta_long_prior'])
    assert base.loc[ix,'long_weight_beta_target']==pytest.approx(new.loc[ix,'long_weight_beta_target'])


def test_beta_target_uses_prior_only():
    c,a=demo_prices();r=prices_to_returns(c,a)
    s=Settings()
    t=simulate(r,s,'2026-11-05',beta_target=True)
    assert len(t)>0
    assert (t['Long $ target']>0).all()
    assert np.allclose(t['Gross $ target'],s.gross)


def test_shock_windows():
    c,a=demo_prices();r=prices_to_returns(c,a)
    e=historical_windows(r,Settings(),5)
    assert len(e)==len(r)-4
    assert e['P&L'].notna().all()
