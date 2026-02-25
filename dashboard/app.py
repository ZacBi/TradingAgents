"""Streamlit dashboard for TradingAgents: decisions, NAV, and run stats."""

import os
import streamlit as st

st.set_page_config(page_title="TradingAgents Dashboard", layout="wide")

# Resolve database path from env or default
db_path = os.environ.get("TRADINGAGENTS_DB_PATH", "tradingagents.db")


@st.cache_resource
def get_db():
    from tradingagents.database import DatabaseManager
    return DatabaseManager(db_path)


def main():
    st.title("TradingAgents Dashboard")
    st.caption("Decisions, NAV, and run statistics")

    db = get_db()

    tab_decisions, tab_nav, tab_about = st.tabs(["Decisions", "NAV / Returns", "About"])

    with tab_decisions:
        st.subheader("Agent decisions")
        ticker_filter = st.text_input("Filter by ticker (optional)", "").strip().upper()
        limit = st.slider("Max rows", 10, 200, 50)
        decisions = db.get_decisions(ticker=ticker_filter or None, limit=limit)
        if not decisions:
            st.info("No decisions in the database. Run analyses via CLI to persist decisions.")
        else:
            import pandas as pd
            df = pd.DataFrame(decisions)
            cols = ["ticker", "trade_date", "final_decision", "confidence", "created_at"]
            cols = [c for c in cols if c in df.columns]
            st.dataframe(df[cols] if cols else df, use_container_width=True)
            if "langfuse_trace_url" in df.columns:
                st.caption("View trace details in Langfuse using the trace URL stored with each decision.")

    with tab_nav:
        st.subheader("Net asset value")
        nav_rows = db.get_daily_nav(limit=365)
        if not nav_rows:
            st.info("No daily NAV data. Run backtests or record NAV via the system to see the curve.")
        else:
            import pandas as pd
            df = pd.DataFrame(nav_rows)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")
            try:
                import plotly.express as px
                fig = px.line(df, x="date", y="total_value", title="Portfolio value")
                fig.update_layout(yaxis_title="Total value")
                st.plotly_chart(fig, use_container_width=True)
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
        st.code("uv run streamlit run dashboard/app.py", language="text")


if __name__ == "__main__":
    main()
