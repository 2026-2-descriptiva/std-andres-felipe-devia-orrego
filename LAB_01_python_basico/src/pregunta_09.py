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


def pregunta_09():
    """
    Cuente cuántas veces aparece cada clave en la quinta columna (`metrics`)
    de todo el archivo. Retorne un diccionario `{clave: cantidad}` con las
    claves en orden alfabético.

    Ejemplo del formato de la respuesta:

        {"aaa": 13, "bbb": 16, "ccc": 23, ...}
    """

    conteo = {}
    for _, _, _, _, metrics in _registros():
        for clave, _ in metrics:
            conteo[clave] = conteo.get(clave, 0) + 1
    return dict(sorted(conteo.items()))
