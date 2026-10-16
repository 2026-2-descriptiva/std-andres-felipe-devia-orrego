"""Dashboard de marketing sobre los resultados de `main.py`."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import main

FOLDER = Path(__file__).resolve().parents[1]
OUTPUT_DIR = FOLDER / "submission"

MONEY_KPIS = {"ad_spend", "revenue", "gross_profit", "avg_daily_revenue",
              "avg_daily_ad_spend"}
HEADLINE_KPIS = ["revenue", "ad_spend", "gross_profit", "roas", "ctr",
                 "profit_margin"]


@st.cache_data
def load_tables():
    """Lee las tablas de `submission`, generándolas si aún no existen."""
    if not (OUTPUT_DIR / "kpis.csv").is_file():
        main.main()

    daily = pd.read_csv(OUTPUT_DIR / "daily_summary.csv", parse_dates=["utc_date"])
    return {
        "kpis": pd.read_csv(OUTPUT_DIR / "kpis.csv"),
        "daily": daily,
        "campaigns": pd.read_csv(OUTPUT_DIR / "campaign_summary.csv"),
        "sources": pd.read_csv(OUTPUT_DIR / "source_summary.csv"),
    }


def format_kpi(name, value):
    try:
        value = float(value)
    except ValueError:
        return value
    if name in MONEY_KPIS:
        return f"${value:,.0f}"
    if value < 10:
        return f"{value:,.2f}"
    return f"{value:,.0f}"


def render_kpis(kpis):
    headline = kpis.set_index("kpi").loc[HEADLINE_KPIS, "value"]
    for column, (name, value) in zip(st.columns(len(headline)), headline.items()):
        column.metric(name.replace("_", " ").title(), format_kpi(name, value))


def render_trend(daily):
    st.subheader("Tendencia diaria")
    metric = st.selectbox(
        "Métrica", ["revenue", "ad_spend", "gross_profit", "roas", "ctr"]
    )
    columns = [metric]
    rolling = f"{metric}_rolling_7d"
    if rolling in daily.columns:
        columns.append(rolling)

    figure = px.line(daily, x="utc_date", y=columns, labels={"value": metric})
    st.plotly_chart(figure, use_container_width=True)

    monthly = daily.groupby("month", as_index=False)[
        ["revenue", "ad_spend", "gross_profit"]
    ].sum()
    st.plotly_chart(
        px.bar(monthly, x="month", y=["ad_spend", "gross_profit"], barmode="stack"),
        use_container_width=True,
    )


def render_sources(sources):
    st.subheader("Fuentes de tráfico")
    st.plotly_chart(
        px.bar(sources, x="traffic_source", y="revenue", color="action"),
        use_container_width=True,
    )
    st.dataframe(
        sources[["traffic_source", "revenue", "ad_spend", "roas", "cpa", "ctr",
                 "profit_margin", "action"]],
        hide_index=True,
        use_container_width=True,
    )


def render_campaigns(campaigns):
    st.subheader("Campañas por dispositivo")
    st.plotly_chart(
        px.bar(
            campaigns,
            x="template_name",
            y="revenue",
            color="device_viewed",
            barmode="group",
        ),
        use_container_width=True,
    )
    st.dataframe(
        campaigns[["template_name", "device_viewed", "revenue", "ad_spend",
                   "roas", "cpa", "ctr", "roas_level"]],
        hide_index=True,
        use_container_width=True,
    )


def main_app():
    st.set_page_config(page_title="Marketing Dashboard", layout="wide")
    st.title("Dashboard de campañas de marketing")

    tables = load_tables()
    daily = tables["daily"]

    start, end = st.sidebar.select_slider(
        "Rango de fechas",
        options=list(daily["utc_date"].dt.date),
        value=(daily["utc_date"].min().date(), daily["utc_date"].max().date()),
    )
    mask = daily["utc_date"].dt.date.between(start, end)

    render_kpis(tables["kpis"])
    render_trend(daily[mask])
    render_sources(tables["sources"])
    render_campaigns(tables["campaigns"])


if __name__ == "__main__":
    main_app()
