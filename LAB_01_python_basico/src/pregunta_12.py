import gzip


def _registros():
    """Lee `data/data.csv.gz` y retorna la lista de registros como tuplas."""
    registros = []
    with gzip.open("data/data.csv.gz", "rt", encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()
            if not linea:
                continue
            letter, value, date, codes, metrics = linea.split("	")
            registros.append(
                (
                    letter,
                    int(value),
                    date,
                    codes.split(","),
                    [par.split(":") for par in metrics.split(",")],
                )
            )
    return registros


def pregunta_12():
    """
    Para cada letra de la primera columna (`letter`), sume todos los valores
    numéricos de los pares `clave:valor` de la quinta columna (`metrics`).
    Retorne un diccionario `{letra: suma}` con las letras en orden alfabético.

    Ejemplo del formato de la respuesta:

        {"A": 177, "B": 187, "C": 114, ...}
    """

    sumas = {}
    for letter, _, _, _, metrics in _registros():
        for _, valor in metrics:
            sumas[letter] = sumas.get(letter, 0) + int(valor)
    return dict(sorted(sumas.items()))
