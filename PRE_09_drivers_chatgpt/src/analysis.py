import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

FOLDER = Path(__file__).resolve().parents[1]
DRIVERS_FILE = f"{FOLDER}/data/drivers.csv"
TIMESHEET_FILE = f"{FOLDER}/data/timesheet.csv"
SUMMARY_FILE = f"{FOLDER}/submission/summary.csv"
PLOT_FILE = f"{FOLDER}/submission/top10_drivers.png"


def load_data():
    drivers = pd.read_csv(DRIVERS_FILE)
    timesheet = pd.read_csv(TIMESHEET_FILE)
    return drivers, timesheet


def compute_summary(drivers, timesheet):
    totals = timesheet.groupby("driverId", as_index=False)[
        ["hours-logged", "miles-logged"]
    ].sum()
    summary = pd.merge(drivers[["driverId", "name"]], totals, on="driverId")
    return summary.sort_values("driverId").reset_index(drop=True)


def plot_top10(summary):
    top10 = summary.nlargest(10, "miles-logged").set_index("name")
    plt.figure(figsize=(8, 5))
    top10["miles-logged"].sort_values().plot.barh(color="tab:blue")
    plt.title("Top 10 conductores por millas registradas")
    plt.xlabel("Millas registradas")
    plt.ylabel("")
    plt.gca().spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(PLOT_FILE)
    plt.close()


def main():
    os.makedirs(f"{FOLDER}/submission", exist_ok=True)
    drivers, timesheet = load_data()
    summary = compute_summary(drivers, timesheet)
    summary.to_csv(SUMMARY_FILE, index=False)
    plot_top10(summary)


if __name__ == "__main__":
    main()

# solucion