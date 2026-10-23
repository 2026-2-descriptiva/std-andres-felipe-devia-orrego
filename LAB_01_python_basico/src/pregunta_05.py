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


def pregunta_05():
    """
    Para cada letra de la primera columna (`letter`), encuentre el valor
    máximo y el valor mínimo de la segunda columna (`value`). Retorne una lista
    de tuplas `(letra, máximo, mínimo)` ordenada alfabéticamente por la letra.

    Ejemplo del formato de la respuesta:

        [("A", 9, 2), ("B", 9, 1), ...]
    """

    rangos = {}
    for letter, value, _, _, _ in _registros():
        if letter in rangos:
            minimo, maximo = rangos[letter]
            rangos[letter] = (min(minimo, value), max(maximo, value))
        else:
            rangos[letter] = (value, value)
    return [(letter, maximo, minimo) for letter, (minimo, maximo) in sorted(rangos.items())]
