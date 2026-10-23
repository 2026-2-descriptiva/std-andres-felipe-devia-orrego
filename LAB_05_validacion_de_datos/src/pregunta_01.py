import json
import re
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = [
    "supplier_id",
    "supplier",
    "country",
    "city",
    "purchase_date",
    "amount",
    "discount",
    "weight",
    "units",
    "unit_price",
    "contact_email",
]

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalizar(nombre):
    """Pasa un encabezado a minúsculas sin BOM ni espacios externos."""
    return nombre.replace("﻿", "").strip().lower().replace(" ", "_")


def _es_faltante(serie):
    """Marca como faltantes las celdas vacías y las que contienen `N/A`."""
    valores = serie.str.strip()
    return (valores == "") | (valores == "N/A")


def main():
    """
    Antes de limpiar o analizar un conjunto de datos, un analista debe
    documentar qué problemas tiene. En este laboratorio usted no va a limpiar
    `data/ventas.csv.gz`: va a construir un reporte de calidad que deje evidencia
    de sus problemas, tal como están en el archivo.

    Lea `data/ventas.csv.gz` sin modificar sus valores. Para trabajar con los
    encabezados, normalícelos: páselos a minúsculas, elimine los espacios al
    inicio y al final (y cualquier marca BOM) y reemplace los espacios
    internos por `_`. Las columnas requeridas son `supplier_id`, `supplier`,
    `country`, `city`, `purchase_date`, `amount`, `discount`, `weight`,
    `units`, `unit_price` y `contact_email`.

    Escriba el reporte en `submission/data_quality_report.json` con estas
    claves:

    - `row_count`: cantidad de filas de datos.
    - `column_count`: cantidad de columnas.
    - `missing_required_columns`: lista ordenada de columnas requeridas que no
      están en el archivo.
    - `unexpected_columns`: lista ordenada de columnas del archivo que no son
      requeridas.
    - `duplicate_row_count`: cantidad de filas idénticas a una fila anterior.
    - `duplicate_supplier_id_row_count`: cantidad de filas cuyo `supplier_id`
      aparece más de una vez (cuente todas esas filas, no solo las
      repetidas).
    - `missing_value_count_by_column`: diccionario con la cantidad de valores
      faltantes de cada columna. Considere faltantes las celdas vacías y las
      que contienen `N/A`.
    - `invalid_email_count`: cantidad de valores de `contact_email` que no
      tienen la forma `usuario@dominio.extension`.
    - `invalid_unit_count`: cantidad de valores numéricos de `units` que no son
      enteros positivos. Los valores faltantes no se cuentan aquí.
    - `country_values`: lista ordenada de los valores distintos de `country`,
      escritos exactamente como aparecen en el archivo.

    La función también debe retornar el reporte como un diccionario.

    Ejemplo del formato del reporte:

        {
          "row_count": 103,
          "column_count": 11,
          "missing_required_columns": [],
          ...
          "country_values": [" Colombia ", "CO", ...]
        }
    """

    ventas = pd.read_csv(
        "data/ventas.csv.gz",
        dtype=str,
        keep_default_na=False,
        encoding="utf-8",
        encoding_errors="replace",
    )
    ventas.columns = [_normalizar(nombre) for nombre in ventas.columns]

    units = pd.to_numeric(ventas["units"].str.strip(), errors="coerce")

    report = {
        "row_count": len(ventas),
        "column_count": len(ventas.columns),
        "missing_required_columns": sorted(
            columna for columna in REQUIRED_COLUMNS if columna not in ventas.columns
        ),
        "unexpected_columns": sorted(
            columna for columna in ventas.columns if columna not in REQUIRED_COLUMNS
        ),
        "duplicate_row_count": int(ventas.duplicated().sum()),
        "duplicate_supplier_id_row_count": int(
            ventas["supplier_id"].duplicated(keep=False).sum()
        ),
        "missing_value_count_by_column": {
            columna: int(_es_faltante(ventas[columna]).sum())
            for columna in ventas.columns
        },
        "invalid_email_count": int(
            sum(
                EMAIL_PATTERN.match(valor.strip()) is None
                for valor in ventas["contact_email"]
            )
        ),
        "invalid_unit_count": int(
            ((units.notna()) & ((units <= 0) | (units != units.round()))).sum()
        ),
        "country_values": sorted(ventas["country"].unique()),
    }

    submission = Path("submission")
    submission.mkdir(exist_ok=True)
    (submission / "data_quality_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return report
