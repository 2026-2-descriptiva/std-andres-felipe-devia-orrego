from pathlib import Path

import numpy as np
import pandas as pd

CHANNELS = ["letter", "web"]
DAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
LEGAL_BUSINESS_DAYS = 15


def _cargar_solicitudes():
    """Lee los dos canales, elimina filas repetidas y calcula los tiempos."""
    canales = []
    for canal in CHANNELS:
        solicitudes = pd.read_csv(
            f"data/historical_requests_{canal}.csv.gz"
        ).drop_duplicates()
        solicitudes["channel"] = canal
        canales.append(solicitudes)

    solicitudes = pd.concat(canales, ignore_index=True)
    solicitudes["in_date"] = pd.to_datetime(solicitudes["in_date"])
    solicitudes["out_date"] = pd.to_datetime(solicitudes["out_date"])

    respondidas = solicitudes["out_date"].notna()
    solicitudes["calendar_days"] = (
        solicitudes["out_date"] - solicitudes["in_date"]
    ).dt.days

    un_dia = np.timedelta64(1, "D")
    entrada = (
        solicitudes.loc[respondidas, "in_date"].to_numpy().astype("datetime64[D]")
    )
    salida = (
        solicitudes.loc[respondidas, "out_date"].to_numpy().astype("datetime64[D]")
    )

    dias_habiles = np.full(len(solicitudes), np.nan)
    dias_habiles[respondidas.to_numpy()] = np.busday_count(
        entrada + un_dia, salida + un_dia
    )
    solicitudes["business_days"] = dias_habiles
    solicitudes["on_time"] = solicitudes["business_days"].le(LEGAL_BUSINESS_DAYS)
    solicitudes["year"] = solicitudes["in_date"].dt.year

    return solicitudes


def _resumir(grupo, columnas):
    """Arma un resumen de un grupo de solicitudes con las columnas pedidas."""
    indicadores = {
        "requests": len(grupo),
        "answered": int(grupo["out_date"].notna().sum()),
        "pending": int(grupo["out_date"].isna().sum()),
        "median_calendar_days": grupo["calendar_days"].median(),
        "median_business_days": grupo["business_days"].median(),
        "on_time_rate": grupo["on_time"].mean(),
    }
    return pd.Series({columna: indicadores[columna] for columna in columnas})


def pregunta_01() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Una entidad pública recibe peticiones, quejas, reclamos y sugerencias
    (PQRS) por dos canales, la página web y las cartas, y la ley le da 15 días
    hábiles para responder cada una. Su tarea es medir si la entidad cumple
    ese plazo.

    Los archivos `data/historical_requests_web.csv.gz` y
    `data/historical_requests_letter.csv.gz` tienen una fila por solicitud
    recibida entre 2016 y 2021 por cada canal, con su identificador
    (`record_id`), la fecha de entrada (`in_date`), el día de la semana de
    entrada (`day_name`) y la fecha de respuesta (`out_date`). Si `out_date`
    está vacía, la solicitud todavía no ha sido respondida.

    Tenga en cuenta lo siguiente:

    - Algunas solicitudes aparecen repetidas: elimine las filas idénticas
      dentro de cada canal, para contar cada solicitud una sola vez. Las
      filas sin `record_id` son solicitudes válidas.
    - Llame `letter` al canal de las cartas y `web` al de la página web.
    - Los días hábiles de respuesta son los días de lunes a viernes
      posteriores a la fecha de entrada, hasta la fecha de respuesta
      incluida. Por ejemplo, una solicitud que entra un viernes y se responde
      el lunes siguiente tardó 1 día hábil. No considere los festivos.
    - Los días calendario de respuesta son la diferencia entre la fecha de
      respuesta y la de entrada.
    - Una solicitud cumple el plazo si fue respondida en 15 días hábiles o
      menos. Una solicitud pendiente no ha cumplido el plazo.
    - `on_time_rate` es la proporción de solicitudes que cumplen el plazo,
      sobre el total de solicitudes, incluidas las pendientes.
    - Las medianas de días se calculan solamente con las solicitudes
      respondidas.

    Genere tres archivos en `submission/`, sin el índice de Pandas y con las
    columnas en el orden indicado:

    1. `channel_summary.csv`, con una fila por canal, en orden alfabético:
       `channel`, `requests`, `answered`, `pending`,
       `median_business_days` y `on_time_rate`.

    2. `yearly_summary.csv`, con una fila por año de entrada y canal,
       ordenada por año y luego por canal: `year`, `channel`, `requests`,
       `pending` y `on_time_rate`.

    3. `entry_day_summary.csv`, con una fila por día de entrada, de lunes a
       domingo, con los dos canales juntos: `day_name`, `requests`,
       `median_calendar_days` y `median_business_days`.

    Observe en el tercer archivo cómo cambia la lectura del tiempo de
    respuesta según se cuenten días calendario o días hábiles.

    La función también debe retornar las tres tablas, en el mismo orden.

    Ejemplo del formato de `channel_summary.csv`:

        channel,requests,answered,pending,median_business_days,on_time_rate
        letter,28138,...
        ...
    """

    solicitudes = _cargar_solicitudes()

    columnas_canal = [
        "requests",
        "answered",
        "pending",
        "median_business_days",
        "on_time_rate",
    ]
    channels = (
        solicitudes.groupby("channel")[solicitudes.columns.tolist()]
        .apply(_resumir, columnas=columnas_canal)
        .reindex(CHANNELS)
        .reset_index()
    )

    columnas_anio = ["requests", "pending", "on_time_rate"]
    yearly = (
        solicitudes.groupby(["year", "channel"])[solicitudes.columns.tolist()]
        .apply(_resumir, columnas=columnas_anio)
        .sort_index()
        .reset_index()
    )

    columnas_dia = ["requests", "median_calendar_days", "median_business_days"]
    days = (
        solicitudes.groupby("day_name")[solicitudes.columns.tolist()]
        .apply(_resumir, columnas=columnas_dia)
        .reindex(DAY_NAMES)
        .reset_index()
    )

    for tabla, enteras in [
        (channels, ["requests", "answered", "pending"]),
        (yearly, ["requests", "pending"]),
        (days, ["requests"]),
    ]:
        for columna in enteras:
            tabla[columna] = tabla[columna].astype("int64")

    submission = Path("submission")
    submission.mkdir(exist_ok=True)
    channels.to_csv(submission / "channel_summary.csv", index=False)
    yearly.to_csv(submission / "yearly_summary.csv", index=False)
    days.to_csv(submission / "entry_day_summary.csv", index=False)

    return channels, yearly, days
