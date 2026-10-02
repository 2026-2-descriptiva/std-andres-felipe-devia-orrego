import os
from pathlib import Path

import pandas as pd

FOLDER = Path(__file__).resolve().parents[1]
INPUT_FILE = f"{FOLDER}/data/sales.csv"
OUTPUT_DIR = f"{FOLDER}/submission"

TOP_N = 10


def load_data():
    df = pd.read_csv(INPUT_FILE, parse_dates=["OrderDate"])
    df["NetAmount"] = df["TotalAmount"].where(df["IsReturned"] == 0, 0.0)
    df["Month"] = df["OrderDate"].dt.to_period("M").astype(str)
    df["DayType"] = df["OrderDate"].dt.dayofweek.map(
        lambda day: "Weekend" if day >= 5 else "Weekday"
    )
    return df


def summarize(df, by):
    """Indicadores estándar de ventas agrupados por `by`."""
    summary = df.groupby(by).agg(
        orders=("OrderID", "count"),
        units=("Quantity", "sum"),
        gross_sales=("TotalAmount", "sum"),
        net_sales=("NetAmount", "sum"),
        avg_order_value=("TotalAmount", "mean"),
        return_rate=("IsReturned", "mean"),
    )
    summary["sales_share"] = summary["gross_sales"] / df["TotalAmount"].sum()
    return summary.round(4).reset_index()


def kpi_summary(df):
    kpis = {
        "orders": len(df),
        "customers": df["CustomerID"].nunique(),
        "products": df["ProductID"].nunique(),
        "units": df["Quantity"].sum(),
        "gross_sales": df["TotalAmount"].sum(),
        "net_sales": df["NetAmount"].sum(),
        "returned_sales": df["TotalAmount"].sum() - df["NetAmount"].sum(),
        "avg_order_value": df["TotalAmount"].mean(),
        "avg_units_per_order": df["Quantity"].mean(),
        "return_rate": df["IsReturned"].mean(),
    }
    return pd.DataFrame({"kpi": kpis.keys(), "value": kpis.values()}).round(4)


def top_entities(df, by, n=TOP_N):
    return summarize(df, by).nlargest(n, "net_sales").reset_index(drop=True)


def return_risk(df):
    """Tasa de devolución por categoría y canal, de mayor a menor riesgo."""
    risk = summarize(df, ["Category", "SalesChannel"])
    risk["returned_sales"] = risk["gross_sales"] - risk["net_sales"]
    overall_rate = df["IsReturned"].mean()
    risk["risk_level"] = risk["return_rate"].map(
        lambda rate: "High" if rate > overall_rate else "Low"
    )
    return risk.sort_values("return_rate", ascending=False).reset_index(drop=True)


def priority_segments(df):
    """Clasifica segmentos categoría-canal-pago según ventas netas y devoluciones."""
    segments = summarize(df, ["Category", "SalesChannel", "PaymentMethod"])
    high_sales = segments["net_sales"] >= segments["net_sales"].median()
    high_returns = segments["return_rate"] > df["IsReturned"].mean()
    segments["priority"] = "Monitor"
    segments.loc[high_sales & ~high_returns, "priority"] = "Protect"
    segments.loc[high_sales & high_returns, "priority"] = "Fix returns"
    segments.loc[~high_sales & ~high_returns, "priority"] = "Grow"
    return segments.sort_values("net_sales", ascending=False).reset_index(drop=True)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = load_data()

    outputs = {
        "kpi_summary": kpi_summary(df),
        "monthly_sales": summarize(df, "Month"),
        "category_summary": summarize(df, "Category"),
        "payment_summary": summarize(df, "PaymentMethod"),
        "day_type_summary": summarize(df, "DayType"),
        "top_customers": top_entities(df, "CustomerID"),
        "top_products": top_entities(df, ["ProductID", "ProductName", "Category"]),
        "return_risk": return_risk(df),
        "priority_segments": priority_segments(df),
    }
    for name, table in outputs.items():
        table.to_csv(f"{OUTPUT_DIR}/{name}.csv", index=False)


if __name__ == "__main__":
    main()
