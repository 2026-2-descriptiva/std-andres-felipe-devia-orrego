from pathlib import Path

import pandas as pd

TEXT_COLUMNS = [
    "sexo",
    "tipo_de_emprendimiento",
    "idea_negocio",
    "barrio",
    "línea_credito",
]


def pregunta_01():
    """
    El archivo `data/solicitudes_de_credito.csv.gz` contiene las solicitudes de
    un programa de crédito, pero llegó sucio: tiene una columna de índice que
    no pertenece a los datos, registros duplicados, registros incompletos y
    valores que representan lo mismo escritos de formas distintas en los
    campos de texto, las fechas, el estrato y el monto.

    Su tarea es limpiarlo y guardar el resultado en
    `submission/solicitudes_de_credito.csv`, usando punto y coma (`;`) como
    separador y sin el índice de Pandas.

    El archivo limpio debe cumplir lo siguiente:

    - Contiene solamente las nueve columnas `sexo`, `tipo_de_emprendimiento`,
      `idea_negocio`, `barrio`, `estrato`, `comuna_ciudadano`,
      `fecha_de_beneficio`, `monto_del_credito` y `línea_credito`, en ese
      orden.
    - Los campos de texto están en minúsculas y sus palabras separadas por
      espacios.
    - `estrato` y `monto_del_credito` son números enteros, sin símbolos ni
      separadores de miles.
    - Todas las fechas de `fecha_de_beneficio` usan un mismo formato, por
      ejemplo `AAAA-MM-DD`.
    - No hay registros incompletos. La única excepción es
      `comuna_ciudadano`: sus valores faltantes son parte de los datos
      originales y deben conservarse.
    - No hay registros duplicados.

    Ejemplo del formato del archivo:

        sexo;tipo_de_emprendimiento;idea_negocio;barrio;estrato;...
        femenino;comercio;almacen de ropa en;los cerros el vergel;2;...
        ...
    """

    solicitudes = pd.read_csv(
        "data/solicitudes_de_credito.csv.gz",
        sep=";",
        index_col=0,
        encoding="utf-8",
    )

    for columna in TEXT_COLUMNS:
        solicitudes[columna] = (
            solicitudes[columna]
            .str.lower()
            .str.replace("-", " ", regex=False)
            .str.replace("_", " ", regex=False)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
        )

    solicitudes["monto_del_credito"] = (
        solicitudes["monto_del_credito"]
        .astype(str)
        .str.replace(r"[$,\s]", "", regex=True)
        .str.replace(r"\.00$", "", regex=True)
        .astype(float)
        .astype("int64")
    )

    fechas = pd.to_datetime(
        solicitudes["fecha_de_beneficio"], format="%d/%m/%Y", errors="coerce"
    )
    fechas = fechas.fillna(
        pd.to_datetime(
            solicitudes["fecha_de_beneficio"], format="%Y/%m/%d", errors="coerce"
        )
    )
    solicitudes["fecha_de_beneficio"] = fechas.dt.strftime("%Y-%m-%d")

    obligatorias = [
        columna for columna in solicitudes.columns if columna != "comuna_ciudadano"
    ]
    solicitudes = solicitudes.dropna(subset=obligatorias)

    solicitudes["estrato"] = solicitudes["estrato"].astype("int64")
    solicitudes["comuna_ciudadano"] = solicitudes["comuna_ciudadano"].astype("Int64")

    solicitudes = solicitudes.drop_duplicates()

    submission = Path("submission")
    submission.mkdir(exist_ok=True)
    solicitudes.to_csv(
        submission / "solicitudes_de_credito.csv",
        sep=";",
        index=False,
        encoding="utf-8",
    )

    return solicitudes
