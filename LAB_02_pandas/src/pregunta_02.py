import pandas as pd


def pregunta_02():
    """
    ¿Cuántas columnas tiene la tabla `data/tbl0.tsv`? Retorne la cantidad
    como un número entero.

    Ejemplo del formato de la respuesta:

        4
    """

    tbl0 = pd.read_csv("data/tbl0.tsv", sep="	")
    return len(tbl0.columns)
