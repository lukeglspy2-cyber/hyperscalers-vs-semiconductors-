# Uploading Part 5 to your existing GitHub repository

Streamlit is a *separate app* from JupyterLab. Its Python files can live in the same GitHub repository as your notebooks.

## Suggested structure

```
hyperscalers-vs-semiconductors/
  README.md                          # your main research narrative
  hyperscalers_vs_semiconductors.ipynb
  risk_and_factor_analysis.py
  scenario_analysis.py
  fundamental_catalyst_research.py
  dashboard/                         # optional subfolder for Part 5
    dashboard.py
    portfolio_engine.py
    requirements.txt
    tests/test_engine.py
    README.md
```

If you want the app in a subfolder, note that the start command becomes:

```
cd /d "%USERPROFILE%\Downloads\ai_relative_value_dashboard"
conda activate finance
python -m streamlit run dashboard.py
```

To upload through the GitHub website:

1. Open the specific existing repository, not just your GitHub profile.
2. Select **Add file** > **Upload files**.
3. Upload the app's `dashboard.py`, `portfolio_engine.py`, `requirements.txt`, `.gitignore`, and `README.md`. Upload `tests/test_engine.py` into a `tests` folder (GitHub's web UI supports dragging in a directory on many desktop browsers, or create it first).
4. If you upload at repository root rather than a dedicated `dashboard/` subfolder, preserve your existing root README and either merge the dashboard instructions or rename the app readme to `DASHBOARD_README.md`.
5. Enter a commit message like `Add interactive Streamlit portfolio dashboard` and click **Commit changes**.
6. Refresh the repository and verify each uploaded file is visible. **Local files are not automatically synced to GitHub.**
7. If the repo is private, only you and people you invite can see it. To use it as public evidence for your resume, make it public only when you have removed confidential information and are ready.

## For the one-line Plotly error fix

In `dashboard.py`, replace the `fig.update_layout` call for `Scenario P&L bridge (components)` with:

```python
fig.update_layout(**CHART, title="Scenario P&L bridge (components)",
                  xaxis_title="USD", showlegend=False, height=450)
fig.update_layout(margin=dict(l=8, r=8, t=54, b=40))
```

Save the file; Streamlit should reload it. If the live app asks to rerun, press Rerun; else stop and relaunch it from Anaconda Prompt.

**Note:** GitHub stores the **source code**. Uploading it does not itself host the running app. A hosted deployment is optional; `localhost:8501` is local to your computer.
