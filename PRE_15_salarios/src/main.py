"""Analítica descriptiva de la estructura salarial de la compañía."""

import os
from pathlib import Path

import pandas as pd

FOLDER = Path(__file__).resolve().parents[1]
INPUT_FILE = f"{FOLDER}/data/salarios.csv"
OUTPUT_DIR = f"{FOLDER}/submission"

HIGH_SALARY_QUANTILE = 0.75
GAP_TOLERANCE = 0.10
SENIORITY_ORDER = ["Analista", "Profesional", "Especialista", "Senior", "Principal"]


def load_data():
    df = pd.read_csv(INPUT_FILE, encoding="utf-8")
    df["categoria"] = pd.Categorical(
        df["categoria"], categories=SENIORITY_ORDER, ordered=True
    )

    # Umbral de salario alto relativo a la trayectoria: comparar directivos con
    # técnicos sobre un único umbral global escondería la brecha de carrera.
    thresholds = df.groupby("trayectoria")["salario_mensual_cop"].quantile(
        HIGH_SALARY_QUANTILE
    )
    df["umbral_salario_alto"] = df["trayectoria"].map(thresholds)
    df["salario_alto"] = df["salario_mensual_cop"] >= df["umbral_salario_alto"]
    df["salario_por_anio_experiencia"] = df["salario_mensual_cop"] / df[
        "experiencia_tecnica_anios"
    ].replace(0, pd.NA)
    return df


def summarize(df, by):
    """Indicadores salariales estándar agrupados por `by`."""
    summary = df.groupby(by, dropna=False, observed=True).agg(
        empleados=("employee_id", "count"),
        salario_mediano=("salario_mensual_cop", "median"),
        salario_promedio=("salario_mensual_cop", "mean"),
        salario_minimo=("salario_mensual_cop", "min"),
        salario_maximo=("salario_mensual_cop", "max"),
        salario_p25=("salario_mensual_cop", lambda values: values.quantile(0.25)),
        salario_p75=("salario_mensual_cop", lambda values: values.quantile(0.75)),
        experiencia_mediana=("experiencia_tecnica_anios", "median"),
        salario_por_anio_experiencia=("salario_por_anio_experiencia", "median"),
        tasa_salario_alto=("salario_alto", "mean"),
    )
    summary["rango_salarial"] = summary["salario_maximo"] - summary["salario_minimo"]
    summary["dispersion_p75_p25"] = summary["salario_p75"] / summary["salario_p25"]
    summary["participacion_empleados"] = summary["empleados"] / len(df)
    return summary.round(4).reset_index()


def department_pay_gap(df):
    """Brecha salarial entre trayectoria directiva y técnica por departamento."""
    base = summarize(df, ["gerencia", "departamento"])
    medians = (
        df.pivot_table(
            index=["gerencia", "departamento"],
            columns="trayectoria",
            values="salario_mensual_cop",
            aggfunc="median",
        )
        .rename(
            columns={
                "Directiva": "salario_mediano_directiva",
                "Técnica": "salario_mediano_tecnica",
            }
        )
        .reset_index()
    )
    counts = (
        df.pivot_table(
            index=["gerencia", "departamento"],
            columns="trayectoria",
            values="employee_id",
            aggfunc="count",
        )
        .rename(
            columns={
                "Directiva": "empleados_directiva",
                "Técnica": "empleados_tecnica",
            }
        )
        .reset_index()
    )

    gap = base.merge(medians, on=["gerencia", "departamento"]).merge(
        counts, on=["gerencia", "departamento"]
    )
    gap["brecha_cop"] = (
        gap["salario_mediano_directiva"] - gap["salario_mediano_tecnica"]
    )
    gap["brecha_pct"] = gap["brecha_cop"] / gap["salario_mediano_tecnica"]

    company_median = df["salario_mensual_cop"].median()
    gap["salario_mediano_compania"] = company_median
    gap["indice_vs_compania"] = gap["salario_mediano"] / company_median
    gap["posicion_vs_compania"] = gap["indice_vs_compania"].map(
        lambda index: "Por encima" if index >= 1 else "Por debajo"
    )

    overall_gap = gap["brecha_pct"].median()
    gap["nivel_brecha"] = gap["brecha_pct"].map(
        lambda value: "Alta" if pd.notna(value) and value > overall_gap else "Baja"
    )
    return (
        gap.sort_values("brecha_pct", ascending=False)
        .round(4)
        .reset_index(drop=True)
    )


def high_salary_by_career(df):
    """Concentración de salarios altos por trayectoria y categoría."""
    high = summarize(df, ["trayectoria", "categoria"])
    thresholds = df.groupby("trayectoria")["salario_mensual_cop"].quantile(
        HIGH_SALARY_QUANTILE
    )
    high["umbral_salario_alto"] = high["trayectoria"].map(thresholds).round(4)

    high_counts = (
        df[df["salario_alto"]]
        .groupby(["trayectoria", "categoria"], observed=True)["employee_id"]
        .count()
    )
    high["empleados_salario_alto"] = (
        high.set_index(["trayectoria", "categoria"])
        .index.map(high_counts)
        .fillna(0)
        .astype(int)
    )

    total_high = int(df["salario_alto"].sum())
    high["participacion_salario_alto"] = (
        high["empleados_salario_alto"] / total_high
    ).round(4)
    high["concentracion"] = high["tasa_salario_alto"].map(
        lambda rate: "Concentrada"
        if rate > (1 - HIGH_SALARY_QUANTILE)
        else "Dispersa"
    )
    return high.sort_values(
        ["trayectoria", "salario_mediano"], ascending=[True, False]
    ).reset_index(drop=True)


def compensation_recommendations(df):
    """Acciones de compensación por segmento frente al referente interno."""
    segments = summarize(
        df, ["gerencia", "departamento", "trayectoria", "categoria"]
    )

    # Referente interno: mediana de la misma trayectoria y categoría en toda la
    # compañía, de modo que la comparación no mezcle niveles de seniority.
    benchmark = (
        df.groupby(["trayectoria", "categoria"], observed=True)[
            "salario_mensual_cop"
        ]
        .median()
        .rename("salario_mediano_referente")
        .reset_index()
    )
    segments = segments.merge(
        benchmark, on=["trayectoria", "categoria"], how="left"
    )
    segments["brecha_vs_referente_cop"] = (
        segments["salario_mediano"] - segments["salario_mediano_referente"]
    )
    segments["brecha_vs_referente_pct"] = (
        segments["brecha_vs_referente_cop"] / segments["salario_mediano_referente"]
    )

    rezagado = segments["brecha_vs_referente_pct"] < -GAP_TOLERANCE
    adelantado = segments["brecha_vs_referente_pct"] > GAP_TOLERANCE
    disperso = (
        segments["dispersion_p75_p25"] > segments["dispersion_p75_p25"].median()
    )

    segments["recomendacion"] = "Mantener"
    segments.loc[rezagado, "recomendacion"] = "Ajustar al alza"
    segments.loc[adelantado, "recomendacion"] = "Contener incrementos"
    segments.loc[
        ~rezagado & ~adelantado & disperso, "recomendacion"
    ] = "Revisar equidad interna"

    segments["prioridad"] = (
        segments["brecha_vs_referente_pct"].abs() * segments["empleados"]
    )
    segments["impacto_mensual_cop"] = (
        -segments["brecha_vs_referente_cop"] * segments["empleados"]
    ).where(rezagado, 0)
    return (
        segments.sort_values("prioridad", ascending=False)
        .round(4)
        .reset_index(drop=True)
    )


def analysis_conclusions(df, gap, high, recommendations):
    """Hallazgos cuantificados que resumen el diagnóstico salarial."""
    directiva = df[df["trayectoria"] == "Directiva"]["salario_mensual_cop"].median()
    tecnica = df[df["trayectoria"] == "Técnica"]["salario_mensual_cop"].median()
    top_gap = gap.iloc[0]
    best_paid = gap.nlargest(1, "salario_mediano").iloc[0]
    ajustes = recommendations[recommendations["recomendacion"] == "Ajustar al alza"]
    correlation = df["experiencia_tecnica_anios"].corr(df["salario_mensual_cop"])
    umbrales = df.groupby("trayectoria")["umbral_salario_alto"].first()

    findings = [
        ("Cobertura", "Empleados analizados", len(df)),
        ("Cobertura", "Departamentos analizados", df["departamento"].nunique()),
        (
            "Nivel salarial",
            "Salario mediano de la compañía (COP)",
            df["salario_mensual_cop"].median(),
        ),
        (
            "Nivel salarial",
            "Salario promedio de la compañía (COP)",
            df["salario_mensual_cop"].mean(),
        ),
        (
            "Brecha de carrera",
            "Salario mediano de la trayectoria directiva (COP)",
            directiva,
        ),
        (
            "Brecha de carrera",
            "Salario mediano de la trayectoria técnica (COP)",
            tecnica,
        ),
        (
            "Brecha de carrera",
            "Brecha directiva vs tecnica (%)",
            (directiva - tecnica) / tecnica,
        ),
        (
            "Brecha por departamento",
            "Departamento con mayor brecha de trayectoria: "
            + str(top_gap["departamento"]),
            top_gap["brecha_pct"],
        ),
        (
            "Brecha por departamento",
            "Departamento mejor pagado: " + str(best_paid["departamento"]),
            best_paid["salario_mediano"],
        ),
        (
            "Brecha por departamento",
            "Departamentos por debajo de la mediana de la compañía",
            int((gap["posicion_vs_compania"] == "Por debajo").sum()),
        ),
        (
            "Salarios altos",
            "Umbral de salario alto de la trayectoria directiva (COP)",
            umbrales["Directiva"],
        ),
        (
            "Salarios altos",
            "Umbral de salario alto de la trayectoria técnica (COP)",
            umbrales["Técnica"],
        ),
        (
            "Salarios altos",
            "Categorias con salarios altos concentrados",
            int((high["concentracion"] == "Concentrada").sum()),
        ),
        ("Experiencia", "Correlacion experiencia-salario", correlation),
        (
            "Experiencia",
            "Experiencia técnica mediana (años)",
            df["experiencia_tecnica_anios"].median(),
        ),
        ("Recomendaciones", "Segmentos con ajuste al alza", len(ajustes)),
        (
            "Recomendaciones",
            "Empleados en segmentos rezagados",
            int(ajustes["empleados"].sum()),
        ),
        (
            "Recomendaciones",
            "Impacto mensual de los ajustes (COP)",
            ajustes["impacto_mensual_cop"].sum(),
        ),
    ]
    conclusions = pd.DataFrame(findings, columns=["tema", "hallazgo", "valor"])
    conclusions["valor"] = conclusions["valor"].astype(float).round(4)
    return conclusions


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = load_data()

    gap = department_pay_gap(df)
    high = high_salary_by_career(df)
    recommendations = compensation_recommendations(df)

    outputs = {
        "department_pay_gap": gap,
        "high_salary_by_career": high,
        "compensation_recommendations": recommendations,
        "analysis_conclusions": analysis_conclusions(
            df, gap, high, recommendations
        ),
    }
    for name, table in outputs.items():
        table.to_csv(f"{OUTPUT_DIR}/{name}.csv", index=False, encoding="utf-8")


if __name__ == "__main__":
    main()
