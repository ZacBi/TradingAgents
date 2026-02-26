"""Streamlit dashboard for TradingAgents: decisions, NAV, and run stats."""

import os
import sys
from datetime import date, timedelta

try:
    import streamlit as st
except ImportError:
    sys.stderr.write(
        "Streamlit is required for the dashboard. Install with: uv sync --extra dashboard\n"
    )
    sys.exit(1)

st.set_page_config(page_title="TradingAgents Dashboard", layout="wide")

# Resolve database path from env or default
db_path = os.environ.get("TRADINGAGENTS_DB_PATH", "tradingagents.db")

# Default date range: last year to today
_today = date.today()
_default_end = _today
_default_start = _today - timedelta(days=365)


@st.cache_resource
def get_db():
    from tradingagents.database import DatabaseManager
    return DatabaseManager(db_path)


@st.cache_data(ttl=60)
def load_decisions(db_path_arg: str, ticker: str | None, limit: int) -> list[dict]:
    """Load decisions from DB; result cached to reduce repeated queries."""
    from tradingagents.database import DatabaseManager
    db = DatabaseManager(db_path_arg)
    return db.get_decisions(ticker=ticker, limit=limit)


@st.cache_data(ttl=60)
def load_daily_nav(db_path_arg: str, limit: int) -> list[dict]:
    """Load daily NAV from DB; result cached to reduce repeated queries."""
    from tradingagents.database import DatabaseManager
    db = DatabaseManager(db_path_arg)
    return db.get_daily_nav(limit=limit)


def main():
    st.title("TradingAgents Dashboard")
    st.caption("Decisions, NAV, and run statistics")

    db = get_db()

    tab_decisions, tab_nav, tab_about = st.tabs(["Decisions", "NAV / Returns", "About"])

    with tab_decisions:
        st.subheader("Agent decisions")
        ticker_filter = st.text_input("Filter by ticker (optional)", "").strip().upper()
        limit = st.slider("Max rows", 10, 500, 50)
        col_start, col_end = st.columns(2)
        with col_start:
            start_date = st.date_input("From date", value=_default_start, key="dec_start")
        with col_end:
            end_date = st.date_input("To date", value=_default_end, key="dec_end")

        decisions = load_decisions(db_path, ticker_filter or None, limit)
        if not decisions:
            st.info("No decisions in the database. Run analyses via CLI to persist decisions.")
        else:
            import pandas as pd
            df = pd.DataFrame(decisions)
            if "trade_date" in df.columns:
                df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
                df = df.dropna(subset=["trade_date"])
                mask = (df["trade_date"].dt.date >= start_date) & (df["trade_date"].dt.date <= end_date)
                df = df.loc[mask]
            if df.empty:
                st.info("No decisions in the selected date range.")
            else:
                if "final_decision" in df.columns:
                    st.subheader("Decision distribution")
                    counts = df["final_decision"].value_counts()
                    try:
                        import plotly.express as px
                        fig = px.pie(
                            values=counts.values,
                            names=counts.index,
                            title="Final decision distribution",
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    except ImportError:
                        st.bar_chart(counts)
                st.subheader("Table")
                cols = ["ticker", "trade_date", "final_decision", "confidence", "created_at"]
                cols = [c for c in cols if c in df.columns]
                st.dataframe(df[cols] if cols else df, use_container_width=True)
                if "langfuse_trace_url" in df.columns:
                    st.caption("View trace details in Langfuse using the trace URL stored with each decision.")

    with tab_nav:
        st.subheader("Net asset value")
        nav_start = st.date_input("From date", value=_default_start, key="nav_start")
        nav_end = st.date_input("To date", value=_default_end, key="nav_end")

        nav_rows = load_daily_nav(db_path, limit=730)
        if not nav_rows:
            st.info("No daily NAV data. Run backtests or record NAV via the system to see the curve.")
        else:
            import pandas as pd
            df = pd.DataFrame(nav_rows)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")
            mask = (df["date"].dt.date >= nav_start) & (df["date"].dt.date <= nav_end)
            df = df.loc[mask]
            if df.empty:
                st.info("No NAV data in the selected date range.")
            else:
                try:
                    import plotly.express as px
                    fig = px.line(df, x="date", y="total_value", title="Portfolio value")
                    fig.update_layout(yaxis_title="Total value")
                    st.plotly_chart(fig, use_container_width=True)
                    if "cumulative_return" in df.columns:
                        fig2 = px.line(df, x="date", y="cumulative_return", title="Cumulative return")
                        fig2.update_layout(yaxis_title="Cumulative return")
                        st.plotly_chart(fig2, use_container_width=True)
                except ImportError:
                    st.dataframe(df[["date", "total_value", "cumulative_return"]], use_container_width=True)
                    st.caption("Install plotly for chart: pip install plotly")

    with tab_about:
        st.subheader("About")
        st.markdown("""
        - **Decisions**: Persisted agent decisions from `TradingAgentsGraph.propagate()` (or CLI with DB enabled).
        - **NAV**: Daily net asset value from the database (e.g. backtest or live recording).
        - **Token / cost**: View per-run token and cost in the CLI output after each analysis, or in Langfuse by trace ID.
        """)
        st.markdown("This dashboard is built with **Streamlit** (open source).")
        st.code("uv run streamlit run dashboard/app.py", language="text")


if __name__ == "__main__":
    main()
