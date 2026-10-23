from pathlib import Path

import pandas as pd

DISCOUNT_BANDS = ["0%", "1%-5%", "6%-10%", "más de 10%"]


def _banda_de_descuento(descuento):
    """Clasifica un descuento en uno de los cuatro rangos definidos."""
    if descuento <= 0:
        return "0%"
    if descuento <= 0.05:
        return "1%-5%"
    if descuento <= 0.10:
        return "6%-10%"
    return "más de 10%"


def _indicadores(grupo):
    """Calcula ventas, utilidad, margen y pérdidas de un conjunto de líneas."""
    perdidas = grupo.loc[grupo["Profit"] < 0, "Profit"]
    ventas = grupo["Sales"].sum()
    utilidad = grupo["Profit"].sum()
    return pd.Series(
        {
            "lines": len(grupo),
            "sales": ventas,
            "profit": utilidad,
            "profit_margin": utilidad / ventas,
            "loss_line_rate": len(perdidas) / len(grupo),
            "lost_profit": -perdidas.sum(),
        }
    )


def pregunta_01() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Una cadena de suministros de oficina vende mucho, pero la gerencia
    sospecha que parte de esas ventas no deja utilidad. El archivo
    `data/superstore_orders.csv.gz` tiene una fila por línea de pedido, con
    el número de pedido (`Order ID`), las ventas (`Sales`), la utilidad
    (`Profit`), el descuento aplicado (`Discount`, como proporción), el
    segmento del cliente (`Customer Segment`) y la categoría del producto
    (`Product Category`). Una utilidad negativa significa que la línea se
    vendió con pérdida.

    Use estas definiciones:

    - Margen (`profit_margin`): utilidad sobre ventas.
    - Línea con pérdida: una línea cuya utilidad es negativa.
    - `loss_line_rate`: la proporción de líneas con pérdida.
    - `lost_profit`: la suma de las pérdidas de las líneas con pérdida,
      escrita como número positivo.
    - Rango de descuento (`discount_band`): `0%` si no hubo descuento,
      `1%-5%` si fue mayor que 0 y hasta 5 %, `6%-10%` si fue mayor que 5 % y
      hasta 10 %, y `más de 10%` en otro caso.

    Genere tres archivos en `submission/`, sin el índice de Pandas y con las
    columnas en el orden indicado:

    1. `profitability_summary.csv`, con una sola fila: `lines` (cantidad de
       líneas), `orders` (pedidos distintos), `sales`, `profit`,
       `profit_margin`, `loss_lines` (cantidad de líneas con pérdida),
       `loss_line_rate` y `lost_profit`.

    2. `discount_summary.csv`, con una fila por rango de descuento, en el
       orden en que se definieron arriba: `discount_band`, `lines`, `sales`,
       `profit`, `profit_margin`, `loss_line_rate` y `lost_profit`.

    3. `priority_segments.csv`, con los cinco segmentos segmento–categoría
       que más utilidad pierden: `Customer Segment`, `Product Category`,
       `lines`, `sales`, `profit`, `profit_margin` y `lost_profit`. Considere
       solamente segmentos con al menos 100 líneas y ordénelos por
       `lost_profit` de mayor a menor.

    La función también debe retornar las tres tablas, en el mismo orden.

    Ejemplo del formato de `discount_summary.csv`:

        discount_band,lines,sales,profit,profit_margin,loss_line_rate,...
        0%,166,170539.05,29472.3789,0.1728,0.488,...
        ...
    """

    pedidos = pd.read_csv(
        "data/superstore_orders.csv.gz", sep=";", decimal=","
    )
    pedidos["discount_band"] = pedidos["Discount"].apply(_banda_de_descuento)

    perdidas = pedidos.loc[pedidos["Profit"] < 0, "Profit"]
    ventas = pedidos["Sales"].sum()
    utilidad = pedidos["Profit"].sum()
    summary = pd.DataFrame(
        [
            {
                "lines": len(pedidos),
                "orders": pedidos["Order ID"].nunique(),
                "sales": ventas,
                "profit": utilidad,
                "profit_margin": utilidad / ventas,
                "loss_lines": len(perdidas),
                "loss_line_rate": len(perdidas) / len(pedidos),
                "lost_profit": -perdidas.sum(),
            }
        ]
    )

    discounts = (
        pedidos.groupby("discount_band")[pedidos.columns.tolist()]
        .apply(_indicadores)
        .reindex(DISCOUNT_BANDS)
        .reset_index()
    )
    discounts["lines"] = discounts["lines"].astype("int64")

    segments = (
        pedidos.groupby(["Customer Segment", "Product Category"])[
            pedidos.columns.tolist()
        ]
        .apply(_indicadores)
        .reset_index()
        .drop(columns="loss_line_rate")
    )
    segments["lines"] = segments["lines"].astype("int64")
    segments = (
        segments[segments["lines"] >= 100]
        .sort_values("lost_profit", ascending=False)
        .head(5)
        .reset_index(drop=True)
    )
    segments = segments[
        [
            "Customer Segment",
            "Product Category",
            "lines",
            "sales",
            "profit",
            "profit_margin",
            "lost_profit",
        ]
    ]

    submission = Path("submission")
    submission.mkdir(exist_ok=True)
    summary.to_csv(submission / "profitability_summary.csv", index=False)
    discounts.to_csv(submission / "discount_summary.csv", index=False)
    segments.to_csv(submission / "priority_segments.csv", index=False)

    return summary, discounts, segments
