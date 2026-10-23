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


def pregunta_10():
    """
    Para cada registro del archivo, en el mismo orden en que aparecen,
    retorne una tupla con la letra de la primera columna (`letter`), la
    cantidad de elementos de la cuarta columna (`codes`) y la cantidad de
    pares de la quinta columna (`metrics`). El resultado es una lista con una
    tupla por registro.

    Ejemplo del formato de la respuesta:

        [("E", 3, 5), ("A", 3, 4), ("B", 4, 4), ...]
    """

    return [
        (letter, len(codes), len(metrics))
        for letter, _, _, codes, metrics in _registros()
    ]
