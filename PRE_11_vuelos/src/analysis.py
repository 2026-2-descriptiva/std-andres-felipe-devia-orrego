"""Analítica descriptiva de demoras de vuelos por aerolínea, mes y horario."""

import os
from pathlib import Path

import pandas as pd

FOLDER = Path(__file__).resolve().parents[1]
MONTH_FILE = f"{FOLDER}/data/flights_by_carrier_month.csv.gz"
DAY_HOUR_FILE = f"{FOLDER}/data/flights_by_carrier_day_hour.csv.gz"
OUTPUT_DIR = f"{FOLDER}/submission"

MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}

DAY_NAMES = {
    1: "Monday",
    2: "Tuesday",
    3: "Wednesday",
    4: "Thursday",
    5: "Friday",
    6: "Saturday",
    7: "Sunday",
}

METRIC_COLUMNS = [
    "scheduled_flights",
    "cancelled_flights",
    "operated_flights",
    "delayed_departure_15_flights",
    "positive_departure_delay_minutes",
]


def load_monthly():
    df = pd.read_csv(MONTH_FILE)
    df["month_name"] = df["month"].map(MONTH_NAMES)
    df["period"] = (
        df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2)
    )
    return df


def load_day_hour():
    df = pd.read_csv(DAY_HOUR_FILE)
    df["day_name"] = df["day_of_week"].map(DAY_NAMES)
    df["time_block"] = pd.cut(
        df["scheduled_departure_hour"],
        bins=[-1, 5, 11, 17, 23],
        labels=["Night", "Morning", "Afternoon", "Evening"],
    ).astype(str)
    return df


def add_rates(summary, total_scheduled=None):
    """Agrega las tasas de servicio derivadas de los conteos de vuelos."""
    summary["cancellation_rate"] = (
        summary["cancelled_flights"] / summary["scheduled_flights"]
    )
    summary["completion_rate"] = (
        summary["operated_flights"] / summary["scheduled_flights"]
    )
    summary["delay_rate"] = (
        summary["delayed_departure_15_flights"] / summary["operated_flights"]
    )
    summary["on_time_rate"] = 1 - summary["delay_rate"]
    summary["avg_delay_minutes_per_operated"] = (
        summary["positive_departure_delay_minutes"] / summary["operated_flights"]
    )
    summary["avg_delay_minutes_per_delayed"] = (
        summary["positive_departure_delay_minutes"]
        / summary["delayed_departure_15_flights"]
    )
    if total_scheduled:
        summary["scheduled_share"] = summary["scheduled_flights"] / total_scheduled
    return summary


def summarize(df, by):
    """Indicadores estándar de puntualidad agrupados por `by`."""
    summary = df.groupby(by, observed=True)[METRIC_COLUMNS].sum()
    summary = add_rates(summary, df["scheduled_flights"].sum())
    return summary.round(4).reset_index()


def overall_kpis(monthly):
    totals = monthly[METRIC_COLUMNS].sum()
    kpis = {
        "years_covered": monthly["year"].nunique(),
        "months_covered": monthly["period"].nunique(),
        "carriers": monthly["reporting_airline"].nunique(),
        "scheduled_flights": totals["scheduled_flights"],
        "cancelled_flights": totals["cancelled_flights"],
        "operated_flights": totals["operated_flights"],
        "delayed_departure_15_flights": totals["delayed_departure_15_flights"],
        "positive_departure_delay_minutes": totals[
            "positive_departure_delay_minutes"
        ],
        "cancellation_rate": totals["cancelled_flights"] / totals["scheduled_flights"],
        "completion_rate": totals["operated_flights"] / totals["scheduled_flights"],
        "delay_rate": (
            totals["delayed_departure_15_flights"] / totals["operated_flights"]
        ),
        "avg_delay_minutes_per_operated": (
            totals["positive_departure_delay_minutes"] / totals["operated_flights"]
        ),
        "avg_delay_minutes_per_delayed": (
            totals["positive_departure_delay_minutes"]
            / totals["delayed_departure_15_flights"]
        ),
    }
    return pd.DataFrame({"kpi": kpis.keys(), "value": kpis.values()}).round(4)


def monthly_national_kpis(monthly):
    """Serie mensual consolidada de todas las aerolíneas."""
    summary = summarize(monthly, ["year", "month", "month_name", "period"])
    return summary.sort_values(["year", "month"]).reset_index(drop=True)


def seasonality(monthly):
    """Perfil promedio por mes calendario, comparado contra el nivel nacional."""
    summary = summarize(monthly, ["month", "month_name"])
    national_delay_rate = (
        monthly["delayed_departure_15_flights"].sum()
        / monthly["operated_flights"].sum()
    )
    summary["delay_rate_vs_national"] = (
        summary["delay_rate"] - national_delay_rate
    ).round(4)
    summary["season_level"] = summary["delay_rate_vs_national"].map(
        lambda gap: "High season" if gap > 0 else "Low season"
    )
    return summary.sort_values("month").reset_index(drop=True)


def carrier_summary(monthly):
    summary = summarize(monthly, "reporting_airline")
    summary["delay_rank"] = summary["delay_rate"].rank(ascending=False).astype(int)
    summary["volume_rank"] = (
        summary["scheduled_flights"].rank(ascending=False).astype(int)
    )
    return summary.sort_values("scheduled_flights", ascending=False).reset_index(
        drop=True
    )


def day_hour_delay(day_hour):
    """Mapa de calor día de la semana x hora programada de salida."""
    summary = summarize(
        day_hour,
        ["day_of_week", "day_name", "scheduled_departure_hour", "time_block"],
    )
    return summary.sort_values(
        ["day_of_week", "scheduled_departure_hour"]
    ).reset_index(drop=True)


def priority_segments(day_hour):
    """Clasifica segmentos aerolínea-día-franja según volumen y demora."""
    segments = summarize(
        day_hour, ["reporting_airline", "day_name", "time_block"]
    )
    high_volume = segments["scheduled_flights"] >= segments["scheduled_flights"].median()
    high_delay = segments["delay_rate"] > (
        day_hour["delayed_departure_15_flights"].sum()
        / day_hour["operated_flights"].sum()
    )
    segments["priority"] = "Monitor"
    segments.loc[high_volume & high_delay, "priority"] = "Fix first"
    segments.loc[high_volume & ~high_delay, "priority"] = "Protect"
    segments.loc[~high_volume & high_delay, "priority"] = "Investigate"
    return segments.sort_values(
        ["priority", "scheduled_flights"], ascending=[True, False]
    ).reset_index(drop=True)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    monthly = load_monthly()
    day_hour = load_day_hour()

    outputs = {
        "overall_kpis": overall_kpis(monthly),
        "monthly_national_kpis": monthly_national_kpis(monthly),
        "seasonality": seasonality(monthly),
        "carrier_summary": carrier_summary(monthly),
        "day_hour_delay": day_hour_delay(day_hour),
        "priority_segments": priority_segments(day_hour),
    }
    for name, table in outputs.items():
        table.to_csv(f"{OUTPUT_DIR}/{name}.csv", index=False)


if __name__ == "__main__":
    main()
