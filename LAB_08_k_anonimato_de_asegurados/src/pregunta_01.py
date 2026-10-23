import json
from pathlib import Path

import pandas as pd

ORIGINAL_QUASI_IDENTIFIERS = ["age", "sex", "bmi", "children", "region"]
SCHEMES = {
    "with_children": ["age_group", "sex", "bmi_group", "children_group", "region"],
    "without_children": ["age_group", "sex", "bmi_group", "region"],
}
K = 5


def _generalizar(asegurados):
    """Agrega las columnas generalizadas de edad, masa corporal e hijos."""
    asegurados = asegurados.copy()
    asegurados["age_group"] = pd.cut(
        asegurados["age"],
        bins=[18, 30, 40, 50, 65],
        right=False,
        labels=["18-29", "30-39", "40-49", "50-64"],
    ).astype(str)
    asegurados["bmi_group"] = pd.cut(
        asegurados["bmi"],
        bins=[0, 18.5, 25, 30, float("inf")],
        right=False,
        labels=["bajo peso", "normal", "sobrepeso", "obesidad"],
    ).astype(str)
    asegurados["children_group"] = pd.cut(
        asegurados["children"],
        bins=[0, 1, 3, float("inf")],
        right=False,
        labels=["0", "1-2", "3+"],
    ).astype(str)
    return asegurados


def _evaluar_esquema(asegurados, quasi_identifiers):
    """Mide clases, supresiones y diversidad del atributo sensible."""
    tamanos = asegurados.groupby(quasi_identifiers)["smoker"].transform("size")
    publicados = asegurados[tamanos >= K]
    diversidad = publicados.groupby(quasi_identifiers)["smoker"].transform("nunique")
    clases_publicadas = publicados.groupby(quasi_identifiers)["smoker"].nunique()

    resumen = {
        "quasi_identifiers": quasi_identifiers,
        "equivalence_classes": asegurados.groupby(quasi_identifiers).ngroups,
        "k_before_suppression": int(tamanos.min()),
        "suppressed_records": int((tamanos < K).sum()),
        "published_records": int(len(publicados)),
        "published_classes": int(len(clases_publicadas)),
        "classes_without_smoker_diversity": int((clases_publicadas < 2).sum()),
        "records_without_smoker_diversity": int((diversidad < 2).sum()),
    }
    return resumen, publicados


def pregunta_01():
    """
    Una aseguradora quiere publicar datos de sus afiliados para que un grupo
    de investigación estudie el costo de los seguros, sin que nadie pueda
    reconocer a una persona. El archivo `data/insurance.csv.gz` tiene una fila
    por afiliado con su edad (`age`), sexo (`sex`), índice de masa corporal
    (`bmi`), número de hijos (`children`), si fuma (`smoker`), región
    (`region`) y el costo de su seguro (`charges`).

    El archivo no tiene nombres ni documentos, pero eso no basta: la edad, el
    sexo, el índice de masa corporal, el número de hijos y la región son
    cuasi-identificadores, porque combinados pueden señalar a una persona.
    `smoker` es el atributo sensible que se quiere proteger.

    En este laboratorio usted va a medir el riesgo de reidentificación y a
    decidir qué publicar. Use estas definiciones:

    - Una clase de equivalencia es un grupo de registros con los mismos
      valores en todos los cuasi-identificadores. Un conjunto de datos cumple
      k-anonimato si toda clase tiene al menos k registros. Use k = 5.
    - `age_group`: `18-29`, `30-39`, `40-49` o `50-64`.
    - `bmi_group`: `bajo peso` (menos de 18.5), `normal` (desde 18.5 y menos
      de 25), `sobrepeso` (desde 25 y menos de 30) u `obesidad` (30 o más).
    - `children_group`: `0`, `1-2` o `3+`.

    Evalúe dos esquemas de generalización:

    - `with_children`: `age_group`, `sex`, `bmi_group`, `children_group` y
      `region`.
    - `without_children`: `age_group`, `sex`, `bmi_group` y `region`; el
      número de hijos no se publica.

    En cada esquema, suprima (no publique) los registros de las clases con
    menos de 5 registros. Luego, entre las clases publicadas, identifique las
    que no tienen diversidad en el atributo sensible, es decir, aquellas en
    las que todos los afiliados fuman o ninguno fuma: en esas clases, saber
    que alguien pertenece a ellas revela si fuma.

    Escriba `submission/privacy_report.json` con estas claves:

    - `original_k`: el menor tamaño de clase usando los cuasi-identificadores
      originales, sin generalizar.
    - `original_unique_records`: cuántos registros son los únicos de su clase
      con los cuasi-identificadores originales.
    - `schemes`: un diccionario con una entrada por esquema (`with_children` y
      `without_children`), cada una con las claves `quasi_identifiers` (la
      lista de columnas del esquema), `equivalence_classes` (clases antes de
      suprimir), `k_before_suppression`, `suppressed_records`,
      `published_records`, `published_classes`,
      `classes_without_smoker_diversity` y
      `records_without_smoker_diversity`.
    - `selected_scheme`: el esquema que suprime menos registros.
    - `mean_charges_original` y `mean_charges_published`: el costo promedio
      de todos los afiliados y el de los registros publicados con el esquema
      seleccionado.
    - `smoker_rate_original` y `smoker_rate_published`: la proporción de
      fumadores en ambos casos.

    Escriba también `submission/insurance_published.csv`, sin el índice de
    Pandas, con los registros publicados del esquema seleccionado, en el
    mismo orden del archivo original, y las columnas del esquema seguidas de
    `smoker` y `charges`.

    La función también debe retornar el reporte como un diccionario.

    Ejemplo del formato del reporte:

        {
          "original_k": 1,
          "original_unique_records": 1330,
          "schemes": {
            "with_children": {
              "quasi_identifiers": ["age_group", "sex", ...],
              "equivalence_classes": 278,
              ...
            },
            ...
          },
          ...
        }
    """

    asegurados = _generalizar(pd.read_csv("data/insurance.csv.gz"))

    tamanos_originales = asegurados.groupby(ORIGINAL_QUASI_IDENTIFIERS)[
        "smoker"
    ].transform("size")

    schemes = {}
    publicados_por_esquema = {}
    for nombre, quasi_identifiers in SCHEMES.items():
        resumen, publicados = _evaluar_esquema(asegurados, quasi_identifiers)
        schemes[nombre] = resumen
        publicados_por_esquema[nombre] = publicados

    seleccionado = min(
        schemes, key=lambda nombre: schemes[nombre]["suppressed_records"]
    )
    publicados = publicados_por_esquema[seleccionado]
    columnas = SCHEMES[seleccionado] + ["smoker", "charges"]
    publicados = publicados[columnas]

    report = {
        "original_k": int(tamanos_originales.min()),
        "original_unique_records": int((tamanos_originales == 1).sum()),
        "schemes": schemes,
        "selected_scheme": seleccionado,
        "mean_charges_original": float(asegurados["charges"].mean()),
        "mean_charges_published": float(publicados["charges"].mean()),
        "smoker_rate_original": float((asegurados["smoker"] == "yes").mean()),
        "smoker_rate_published": float((publicados["smoker"] == "yes").mean()),
    }

    submission = Path("submission")
    submission.mkdir(exist_ok=True)
    (submission / "privacy_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    publicados.to_csv(submission / "insurance_published.csv", index=False)

    return report
