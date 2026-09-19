import os
import re
import unicodedata

import pandas as pd

FOLDER = "PRE_04_limpieza"
INPUT_FILE = f"{FOLDER}/data/ventas.csv"
OUTPUT_FILE = f"{FOLDER}/submission/ventas.csv"

SUPPLIERS = {
    "abbcolombia": "ABB Colombia Ltda.",
    "alpinaproductosalimenticios": "Alpina Productos Alimenticios",
    "amazonwebservicescolombia": "Amazon Web Services Colombia",
    "bancolombia": "Bancolombia S.A.",
    "cementosargos": "Cementos Argos S.A.",
    "clarocolombia": "Claro Colombia",
    "corona": "Corona S.A.S.",
    "ecopetrol": "Ecopetrol S.A.",
    "googlecolombia": "Google Colombia Ltda.",
    "grupoexito": "Grupo Éxito S.A.",
    "ibmcolombia": "IBM Colombia S.A.S.",
    "microsoftcolombia": "Microsoft Colombia Inc.",
    "nutresa": "Nutresa S.A.",
    "oraclecolombia": "Oracle Colombia Ltda.",
    "postobon": "Postobón S.A.",
    "sapcolombia": "SAP Colombia S.A.S.",
    "schneiderelectric": "Schneider Electric",
    "siemens": "Siemens S.A.S.",
    "sura": "Sura S.A.",
    "telefonicacolombia": "Telefónica Colombia",
}

COUNTRIES = {"colombia": "COL", "col": "COL", "co": "COL"}


def strip_accents(text):
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def supplier_key(name):
    text = strip_accents(str(name)).lower()
    text = re.sub(r"[^a-z0-9 ]", "", text)
    words = [w for w in text.split() if w not in {"sa", "sas", "ltda", "inc"}]
    return "".join(words)


def clean_supplier(name):
    if pd.isna(name):
        return name
    key = supplier_key(name)
    return SUPPLIERS.get(key, " ".join(str(name).split()))


def clean_country(value):
    if pd.isna(value):
        return value
    key = strip_accents(str(value)).strip().lower()
    return COUNTRIES.get(key, str(value).strip().upper())


def clean_city(value):
    if pd.isna(value):
        return value
    return strip_accents(" ".join(str(value).split())).title()


def clean_columns(df):
    df.columns = [
        re.sub(r"\s+", "_", strip_accents(c).strip().lower()) for c in df.columns
    ]
    return df


def main():
    df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig", dtype=str)
    df = clean_columns(df)

    df = df.apply(lambda col: col.str.strip())
    df = df.replace({"": pd.NA, "N/A": pd.NA, "sin correo": pd.NA})

    df["supplier"] = df["supplier"].apply(clean_supplier)
    df["country"] = df["country"].apply(clean_country)
    df["city"] = df["city"].apply(clean_city)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)


if __name__ == "__main__":
    main()
