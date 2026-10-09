"""Analítica descriptiva de la cadena de suministro de medicamentos e insumos."""

import os
from pathlib import Path

import pandas as pd

FOLDER = Path(__file__).resolve().parents[1]
INPUT_FILE = f"{FOLDER}/data/supply_chain.csv"
OUTPUT_DIR = f"{FOLDER}/submission"

TOP_N = 15

NUMERIC_TEXT_COLUMNS = ["Weight (Kilograms)", "Freight Cost (USD)"]


def load_data():
    df = pd.read_csv(INPUT_FILE, encoding="latin-1")

    # Weight y Freight Cost traen textos como "Freight Included in Commodity
    # Cost", "Invoiced Separately" o referencias a otro embarque ("See ASN-...").
    for column in NUMERIC_TEXT_COLUMNS:
        df[column] = pd.to_numeric(
            df[column].astype(str).str.replace(",", "", regex=False), errors="coerce"
        )
    df = df.rename(
        columns={
            "Weight (Kilograms)": "weight_kg",
            "Freight Cost (USD)": "freight_cost_usd",
            "Line Item Value": "line_item_value",
            "Line Item Quantity": "line_item_quantity",
            "Line Item Insurance (USD)": "insurance_usd",
            "Shipment Mode": "shipment_mode",
            "Country": "country",
            "Product Group": "product_group",
            "Sub Classification": "sub_classification",
            "Vendor INCO Term": "inco_term",
            "Fulfill Via": "fulfill_via",
            "Managed By": "managed_by",
        }
    )
    df["shipment_mode"] = df["shipment_mode"].fillna("Unknown")

    # Las fechas de entrega vienen como "2-Jun-06" con centinelas no fecha.
    for column, target in [
        ("Scheduled Delivery Date", "scheduled_delivery_date"),
        ("Delivered to Client Date", "delivered_date"),
    ]:
        df[target] = pd.to_datetime(
            df[column], format="%d-%b-%y", errors="coerce"
        )

    # La fecha de orden de compra usa formato m/d/yy y centinelas como
    # "N/A - From RDC" o "Date Not Captured".
    df["po_sent_date"] = pd.to_datetime(
        df["PO Sent to Vendor Date"], format="mixed", errors="coerce"
    )

    df["delay_days"] = (
        df["delivered_date"] - df["scheduled_delivery_date"]
    ).dt.days
    df["is_late"] = (df["delay_days"] > 0).where(df["delay_days"].notna())
    df["lead_time_days"] = (
        df["delivered_date"] - df["po_sent_date"]
    ).dt.days
    df["month"] = df["delivered_date"].dt.to_period("M").astype(str)
    df["year"] = df["delivered_date"].dt.year
    df["weight_kg"] = df["weight_kg"].replace(0, pd.NA).astype("Float64")
    df["freight_per_kg"] = df["freight_cost_usd"] / df["weight_kg"]
    df["freight_share_of_value"] = df["freight_cost_usd"] / df["line_item_value"]
    df["freight_reported"] = df["freight_cost_usd"].notna()
    return df


def summarize(df, by):
    """Indicadores estándar de embarques agrupados por `by`."""
    summary = df.groupby(by, dropna=False).agg(
        shipments=("ID", "count"),
        units=("line_item_quantity", "sum"),
        total_value=("line_item_value", "sum"),
        avg_line_value=("line_item_value", "mean"),
        total_weight_kg=("weight_kg", "sum"),
        total_freight_usd=("freight_cost_usd", "sum"),
        avg_freight_usd=("freight_cost_usd", "mean"),
        avg_freight_per_kg=("freight_per_kg", "mean"),
        avg_unit_price=("Unit Price", "mean"),
        avg_delay_days=("delay_days", "mean"),
        late_rate=("is_late", "mean"),
        avg_lead_time_days=("lead_time_days", "mean"),
        freight_reported_rate=("freight_reported", "mean"),
    )
    summary["value_share"] = summary["total_value"] / df["line_item_value"].sum()
    summary["freight_share_of_value"] = (
        summary["total_freight_usd"] / summary["total_value"]
    )
    return summary.round(4).reset_index()


def overall_kpis(df):
    kpis = {
        "shipments": len(df),
        "countries": df["country"].nunique(),
        "vendors": df["Vendor"].nunique(),
        "shipment_modes": df["shipment_mode"].nunique(),
        "product_groups": df["product_group"].nunique(),
        "units": df["line_item_quantity"].sum(),
        "total_value": df["line_item_value"].sum(),
        "total_freight_usd": df["freight_cost_usd"].sum(),
        "total_insurance_usd": df["insurance_usd"].sum(),
        "total_weight_kg": df["weight_kg"].sum(),
        "avg_line_value": df["line_item_value"].mean(),
        "avg_freight_usd": df["freight_cost_usd"].mean(),
        "avg_freight_per_kg": df["freight_per_kg"].mean(),
        "freight_share_of_value": (
            df["freight_cost_usd"].sum() / df["line_item_value"].sum()
        ),
        "freight_reported_rate": df["freight_reported"].mean(),
        "avg_delay_days": df["delay_days"].mean(),
        "late_rate": df["is_late"].mean(),
        "avg_lead_time_days": df["lead_time_days"].mean(),
    }
    return pd.DataFrame({"kpi": kpis.keys(), "value": kpis.values()}).round(4)


def monthly_summary(df):
    summary = summarize(df.dropna(subset=["delivered_date"]), "month")
    return summary.sort_values("month").reset_index(drop=True)


def mode_summary(df):
    return summarize(df, "shipment_mode").sort_values(
        "total_value", ascending=False
    ).reset_index(drop=True)


def country_summary(df):
    return summarize(df, "country").sort_values(
        "total_value", ascending=False
    ).reset_index(drop=True)


def country_mode_summary(df):
    return summarize(df, ["country", "shipment_mode"]).sort_values(
        ["country", "total_value"], ascending=[True, False]
    ).reset_index(drop=True)


def freight_by_mode(df):
    """Costo logístico por modo de embarque y grupo de producto."""
    freight = summarize(df, ["shipment_mode", "product_group"])
    overall_per_kg = (
        df["freight_cost_usd"].sum() / df["weight_kg"].sum()
    )
    freight["freight_usd_per_kg"] = (
        freight["total_freight_usd"] / freight["total_weight_kg"]
    ).round(4)
    freight["cost_level"] = freight["freight_usd_per_kg"].map(
        lambda rate: "Above average"
        if pd.notna(rate) and rate > overall_per_kg
        else "Below average"
    )
    return freight.sort_values("total_freight_usd", ascending=False).reset_index(
        drop=True
    )


def priority_countries(df, n=TOP_N):
    """Países con mayor valor movilizado y su desempeño de entrega."""
    countries = summarize(df, "country")
    overall_late_rate = df["is_late"].mean()
    countries["late_level"] = countries["late_rate"].map(
        lambda rate: "High"
        if pd.notna(rate) and rate > overall_late_rate
        else "Low"
    )
    return countries.nlargest(n, "total_value").reset_index(drop=True)


def priority_segments(df):
    """Clasifica segmentos país-modo-grupo según valor y cumplimiento."""
    segments = summarize(df, ["country", "shipment_mode", "product_group"])
    high_value = segments["total_value"] >= segments["total_value"].median()
    high_late = segments["late_rate"] > df["is_late"].mean()
    segments["priority"] = "Monitor"
    segments.loc[high_value & ~high_late, "priority"] = "Protect"
    segments.loc[high_value & high_late, "priority"] = "Fix delivery"
    segments.loc[~high_value & ~high_late, "priority"] = "Grow"
    return segments.sort_values("total_value", ascending=False).reset_index(drop=True)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = load_data()

    outputs = {
        "overall_kpis": overall_kpis(df),
        "monthly_summary": monthly_summary(df),
        "mode_summary": mode_summary(df),
        "country_summary": country_summary(df),
        "country_mode_summary": country_mode_summary(df),
        "freight_by_mode": freight_by_mode(df),
        "priority_countries": priority_countries(df),
        "priority_segments": priority_segments(df),
    }
    for name, table in outputs.items():
        table.to_csv(f"{OUTPUT_DIR}/{name}.csv", index=False, encoding="utf-8")


if __name__ == "__main__":
    main()
