import hashlib
import os

import pandas as pd

FOLDER = "PRE_05_anonimizacion"
INPUT_FILE = f"{FOLDER}/data/raw.csv"
OUTPUT_FILE = f"{FOLDER}/submission/anonymized.csv"

SALT = "pre05-anonimizacion"
K = 5

DIRECT_IDENTIFIERS = ["name", "document_id", "email", "loyalty_card_number"]

REGIONS = {
    "Medellín": "Antioquia",
    "Bello": "Antioquia",
    "Envigado": "Antioquia",
    "Itagüí": "Antioquia",
    "Rionegro": "Antioquia",
    "Bogotá": "Centro",
    "Bucaramanga": "Centro",
    "Pereira": "Eje Cafetero",
    "Manizales": "Eje Cafetero",
    "Cali": "Pacífico",
    "Barranquilla": "Caribe",
    "Cartagena": "Caribe",
}

SECTORS = {
    "Ingeniero de sistemas": "Tecnología e ingeniería",
    "Técnico electricista": "Tecnología e ingeniería",
    "Arquitecta": "Tecnología e ingeniería",
    "Diseñadora gráfica": "Tecnología e ingeniería",
    "Contadora": "Negocios y finanzas",
    "Analista financiera": "Negocios y finanzas",
    "Administradora": "Negocios y finanzas",
    "Comerciante": "Negocios y finanzas",
    "Abogada": "Negocios y finanzas",
    "Médico": "Salud y educación",
    "Enfermera": "Salud y educación",
    "Docente": "Salud y educación",
}

QUASI_IDENTIFIERS = ["age_range", "region", "sector"]


def pseudonym(document_id):
    digest = hashlib.sha256(f"{SALT}{document_id}".encode("utf-8")).hexdigest()
    return digest[:12]


def age_range(age):
    lower = (int(age) // 10) * 10
    return f"{lower}-{lower + 9}"


def spend_range(value):
    lower = (int(value) // 1_000_000) * 1_000_000
    return f"{lower}-{lower + 999_999}"


def enforce_k_anonymity(df, k):
    sizes = df.groupby(QUASI_IDENTIFIERS)["id"].transform("size")
    return df[sizes >= k].reset_index(drop=True)


def main():
    df = pd.read_csv(INPUT_FILE, encoding="utf-8")

    df.insert(0, "id", df["document_id"].apply(pseudonym))
    df["age_range"] = df["age"].apply(age_range)
    df["region"] = df["city"].map(REGIONS).fillna("Otra")
    df["sector"] = df["occupation"].map(SECTORS).fillna("Otro")
    df["annual_spend_range"] = df["annual_spend"].apply(spend_range)

    df = df.drop(columns=DIRECT_IDENTIFIERS + ["age", "city", "occupation", "annual_spend"])
    df = enforce_k_anonymity(df, K)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)


if __name__ == "__main__":
    main()
