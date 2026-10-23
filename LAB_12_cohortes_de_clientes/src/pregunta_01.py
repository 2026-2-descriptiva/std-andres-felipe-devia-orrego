from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


def _graficar(retencion, archivo):
    """Dibuja el mapa de calor de retención por cohorte y período."""
    matriz = retencion.pivot(
        index="cohort_month", columns="period_index", values="retention_rate"
    )

    figura, ejes = plt.subplots(figsize=(10, 6))
    imagen = ejes.imshow(matriz.values, cmap="Blues", vmin=0, vmax=1)

    ejes.set_xticks(range(len(matriz.columns)))
    ejes.set_xticklabels(matriz.columns)
    ejes.set_yticks(range(len(matriz.index)))
    ejes.set_yticklabels(matriz.index)
    ejes.set_xlabel("Períodos desde la primera compra")
    ejes.set_ylabel("Cohorte")
    ejes.set_title("Retención de clientes por cohorte")

    for fila in range(matriz.shape[0]):
        for columna in range(matriz.shape[1]):
            valor = matriz.values[fila, columna]
            if pd.isna(valor):
                continue
            ejes.text(
                columna,
                fila,
                f"{valor:.1%}",
                ha="center",
                va="center",
                color="white" if valor > 0.5 else "black",
                fontsize=8,
            )

    figura.colorbar(imagen, ax=ejes, label="Retención")
    figura.tight_layout()
    figura.savefig(archivo, dpi=150)
    plt.close(figura)


def build_cohort_analysis() -> pd.DataFrame:
    """
    Una tienda quiere saber si sus clientes vuelven a comprar después de su
    primera compra. Para responder, agrupe a los clientes en cohortes según
    el mes de su primera compra y mida, mes a mes, qué proporción de cada
    cohorte vuelve a comprar. Use `data/sales.csv.gz`, que tiene una fila por
    orden con su cliente (`CustomerID`) y su fecha (`OrderDate`).

    Use estas definiciones:

    - `cohort_month`: el mes de la primera compra del cliente, escrito como
      `AAAA-MM`.
    - `period_index`: los meses transcurridos desde `cohort_month`; es 0 en el
      mes de la primera compra, 1 en el mes siguiente, y así sucesivamente.
    - `active_customers`: la cantidad de clientes distintos de la cohorte que
      compraron en ese período.
    - `cohort_size`: la cantidad de clientes de la cohorte, es decir, sus
      clientes activos en el período 0.
    - `retention_rate`: `active_customers` sobre `cohort_size`.

    Genere dos archivos en `submission/`:

    1. `cohort_retention.csv`, sin el índice de Pandas, con las columnas
       `cohort_month`, `period_index`, `active_customers`, `cohort_size` y
       `retention_rate`, y una fila por cada combinación cohorte–período
       observada, ordenadas por cohorte y período.

    2. `cohort_retention_heatmap.png`, un mapa de calor de `retention_rate`
       con una fila por cohorte (eje vertical) y una columna por período
       (eje horizontal). Muestre los valores como porcentajes. Los períodos
       que todavía no se pueden observar para una cohorte no significan
       retención cero: déjelos vacíos en el mapa.

    La función también debe retornar la tabla de retención.

    Ejemplo del formato de `cohort_retention.csv`:

        cohort_month,period_index,active_customers,cohort_size,retention_rate
        2022-01,0,100,100,1.0
        2022-01,1,26,100,0.26
        ...
    """

    ventas = pd.read_csv("data/sales.csv.gz", parse_dates=["OrderDate"])
    ventas["order_month"] = ventas["OrderDate"].dt.to_period("M")
    ventas["cohort"] = ventas.groupby("CustomerID")["order_month"].transform("min")
    ventas["period_index"] = (
        ventas["order_month"] - ventas["cohort"]
    ).apply(lambda periodos: periodos.n)

    retencion = (
        ventas.groupby(["cohort", "period_index"])["CustomerID"]
        .nunique()
        .reset_index(name="active_customers")
    )
    retencion["cohort_month"] = retencion["cohort"].astype(str)
    tamanos = retencion[retencion["period_index"] == 0].set_index("cohort_month")[
        "active_customers"
    ]
    retencion["cohort_size"] = retencion["cohort_month"].map(tamanos)
    retencion["retention_rate"] = (
        retencion["active_customers"] / retencion["cohort_size"]
    )
    retencion = (
        retencion.sort_values(["cohort_month", "period_index"])
        .reset_index(drop=True)[
            [
                "cohort_month",
                "period_index",
                "active_customers",
                "cohort_size",
                "retention_rate",
            ]
        ]
    )

    submission = Path("submission")
    submission.mkdir(exist_ok=True)
    retencion.to_csv(submission / "cohort_retention.csv", index=False)
    _graficar(retencion, submission / "cohort_retention_heatmap.png")

    return retencion
