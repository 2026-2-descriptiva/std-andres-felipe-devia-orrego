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


def pregunta_01():
    """
    Calcule la suma de los valores de la segunda columna (`value`) del
    archivo `data/data.csv.gz` y retorne el resultado como un número entero.

    Ejemplo del formato de la respuesta:

        214
    """

    total = 0
    for _, value, _, _, _ in _registros():
        total += value
    return total
