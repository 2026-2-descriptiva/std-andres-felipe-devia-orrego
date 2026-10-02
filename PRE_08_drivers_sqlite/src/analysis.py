import os
import sqlite3
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

SUMMARY_QUERY = """
SELECT
    d.driverId,
    d.name,
    SUM(t."hours-logged") AS "hours-logged",
    SUM(t."miles-logged") AS "miles-logged"
FROM drivers d
JOIN timesheet t ON d.driverId = t.driverId
GROUP BY d.driverId, d.name
ORDER BY d.driverId
"""

TOP10_QUERY = """
SELECT name, "miles-logged"
FROM summary
ORDER BY "miles-logged" DESC
LIMIT 10
"""


def load_tables(conn):
    pd.read_csv(DRIVERS_FILE).to_sql("drivers", conn, index=False)
    pd.read_csv(TIMESHEET_FILE).to_sql("timesheet", conn, index=False)


def plot_top10(top10):
    top10 = top10.set_index("name").sort_values("miles-logged")
    plt.figure(figsize=(8, 5))
    top10["miles-logged"].plot.barh(color="tab:blue")
    plt.title("Top 10 conductores por millas registradas")
    plt.xlabel("Millas registradas")
    plt.ylabel("")
    plt.gca().spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(PLOT_FILE)
    plt.close()


def main():
    os.makedirs(f"{FOLDER}/submission", exist_ok=True)
    with sqlite3.connect(":memory:") as conn:
        load_tables(conn)
        summary = pd.read_sql_query(SUMMARY_QUERY, conn)
        summary.to_sql("summary", conn, index=False)
        top10 = pd.read_sql_query(TOP10_QUERY, conn)
    summary.to_csv(SUMMARY_FILE, index=False)
    plot_top10(top10)


if __name__ == "__main__":
    main()
