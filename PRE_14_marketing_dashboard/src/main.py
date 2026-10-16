"""Analítica descriptiva de las campañas de marketing digital."""

import os
from pathlib import Path

import pandas as pd

FOLDER = Path(__file__).resolve().parents[1]
INPUT_FILE = f"{FOLDER}/data/campaign_data.csv"
OUTPUT_DIR = f"{FOLDER}/submission"

ROLLING_WINDOW = 7


def load_data():
    df = pd.read_csv(INPUT_FILE)
    df["utc_date"] = pd.to_datetime(df["utc_date"])
    df["month"] = df["utc_date"].dt.to_period("M").astype(str)
    df["year"] = df["utc_date"].dt.year
    df["weekday"] = df["utc_date"].dt.day_name()

    # roas, rpc, cpc y cpa vienen calculados en la fuente; se recalculan sobre
    # los totales para agregarlos por campaña, fuente y día sin promediar
    # razones. La fuente mide cpc y rpc por clic en página y cpa por clic pago.
    return df


def summarize(df, by):
    """Indicadores estándar de campañas agrupados por `by`."""
    summary = df.groupby(by, dropna=False).agg(
        days=("utc_date", "nunique"),
        impressions=("impressions", "sum"),
        page_clicks=("page_clicks", "sum"),
        paid_clicks=("paid_clicks", "sum"),
        blocked_clicks=("blocked_clicks", "sum"),
        ad_spend=("ad_spend", "sum"),
        revenue=("revenue", "sum"),
        gross_profit=("gross_profit", "sum"),
        avg_ads_returned=("count_of_ads_returned", "mean"),
    )
    summary["ctr"] = summary["page_clicks"] / summary["impressions"]
    summary["paid_click_share"] = summary["paid_clicks"] / summary["page_clicks"]
    summary["blocked_click_rate"] = (
        summary["blocked_clicks"] / summary["page_clicks"]
    )
    summary["cpc"] = summary["ad_spend"] / summary["page_clicks"]
    summary["rpc"] = summary["revenue"] / summary["page_clicks"]
    summary["cpa"] = summary["ad_spend"] / summary["paid_clicks"]
    summary["roas"] = summary["revenue"] / summary["ad_spend"]
    summary["profit_margin"] = summary["gross_profit"] / summary["revenue"]
    summary["revenue_share"] = summary["revenue"] / df["revenue"].sum()
    summary["spend_share"] = summary["ad_spend"] / df["ad_spend"].sum()
    return summary.round(4).reset_index()


def kpis(df):
    totals = {
        "days": df["utc_date"].nunique(),
        "first_date": df["utc_date"].min().date().isoformat(),
        "last_date": df["utc_date"].max().date().isoformat(),
        "traffic_sources": df["traffic_source"].nunique(),
        "campaigns": df["template_name"].nunique(),
        "accounts": df["account_name"].nunique(),
        "countries": df["country"].nunique(),
        "impressions": df["impressions"].sum(),
        "page_clicks": df["page_clicks"].sum(),
        "paid_clicks": df["paid_clicks"].sum(),
        "blocked_clicks": df["blocked_clicks"].sum(),
        "ad_spend": df["ad_spend"].sum(),
        "revenue": df["revenue"].sum(),
        "gross_profit": df["gross_profit"].sum(),
        "ctr": df["page_clicks"].sum() / df["impressions"].sum(),
        "paid_click_share": df["paid_clicks"].sum() / df["page_clicks"].sum(),
        "blocked_click_rate": df["blocked_clicks"].sum() / df["page_clicks"].sum(),
        "cpc": df["ad_spend"].sum() / df["page_clicks"].sum(),
        "rpc": df["revenue"].sum() / df["page_clicks"].sum(),
        "cpa": df["ad_spend"].sum() / df["paid_clicks"].sum(),
        "roas": df["revenue"].sum() / df["ad_spend"].sum(),
        "profit_margin": df["gross_profit"].sum() / df["revenue"].sum(),
        "avg_daily_revenue": df.groupby("utc_date")["revenue"].sum().mean(),
        "avg_daily_ad_spend": df.groupby("utc_date")["ad_spend"].sum().mean(),
        "profitable_days_rate": (
            df.groupby("utc_date")["gross_profit"].sum() > 0
        ).mean(),
    }
    return pd.DataFrame({"kpi": totals.keys(), "value": totals.values()})


def daily_summary(df):
    """Serie diaria con medias móviles para el seguimiento del dashboard."""
    daily = summarize(df, "utc_date").sort_values("utc_date")
    for column in ["revenue", "ad_spend", "gross_profit", "roas"]:
        daily[f"{column}_rolling_{ROLLING_WINDOW}d"] = (
            daily[column].rolling(ROLLING_WINDOW, min_periods=1).mean().round(4)
        )
    daily["month"] = daily["utc_date"].dt.to_period("M").astype(str)
    daily["weekday"] = daily["utc_date"].dt.day_name()
    daily["utc_date"] = daily["utc_date"].dt.date
    return daily.drop(columns="days").reset_index(drop=True)


def campaign_summary(df):
    """Desempeño por plantilla de campaña y dispositivo."""
    campaigns = summarize(df, ["template_name", "device_viewed"])
    overall_roas = df["revenue"].sum() / df["ad_spend"].sum()
    campaigns["roas_level"] = campaigns["roas"].map(
        lambda value: "Above average" if value > overall_roas else "Below average"
    )
    return campaigns.sort_values("revenue", ascending=False).reset_index(drop=True)


def source_summary(df):
    """Desempeño por fuente de tráfico con recomendación de inversión."""
    sources = summarize(df, "traffic_source")
    overall_roas = df["revenue"].sum() / df["ad_spend"].sum()
    overall_cpa = df["ad_spend"].sum() / df["paid_clicks"].sum()

    efficient = sources["roas"] > overall_roas
    cheap = sources["cpa"] <= overall_cpa
    sources["action"] = "Review"
    sources.loc[efficient & cheap, "action"] = "Scale"
    sources.loc[efficient & ~cheap, "action"] = "Optimize cost"
    sources.loc[~efficient & cheap, "action"] = "Improve conversion"
    sources.loc[~efficient & ~cheap, "action"] = "Reduce spend"
    return sources.sort_values("revenue", ascending=False).reset_index(drop=True)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = load_data()

    outputs = {
        "kpis": kpis(df),
        "daily_summary": daily_summary(df),
        "campaign_summary": campaign_summary(df),
        "source_summary": source_summary(df),
    }
    for name, table in outputs.items():
        table.to_csv(f"{OUTPUT_DIR}/{name}.csv", index=False, encoding="utf-8")


if __name__ == "__main__":
    main()
