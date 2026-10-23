import re

import pandas as pd


def pregunta_01():
    """
    El archivo `data/clusters_report.txt` es un reporte de clústeres de
    palabras clave pensado para ser leído por una persona, no por un programa:
    los encabezados ocupan varias líneas, las columnas están alineadas con
    espacios y la lista de palabras clave de un clúster continúa en las líneas
    siguientes.

    Su tarea es convertir ese reporte en un DataFrame de Pandas con una fila
    por clúster y las columnas:

    - `cluster`: número del clúster, como entero.
    - `cantidad_de_palabras_clave`: como entero.
    - `porcentaje_de_palabras_clave`: como número decimal; por ejemplo, el
      texto `15,9 %` debe quedar como `15.9`.
    - `principales_palabras_clave`: todas las palabras clave del clúster en un
      solo texto, separadas por una coma y un único espacio.

    Retorne el DataFrame.

    Ejemplo del formato de la respuesta (se omite la última columna):

           cluster  cantidad_de_palabras_clave  porcentaje_de_palabras_clave
        0        1                         105                          15.9
        1        2                         102                          15.4
        ...
    """

    patron = re.compile(r"^\s*(\d+)\s+(\d+)\s+([\d,]+)\s*%\s+(.*)$")

    registros = []
    with open("data/clusters_report.txt", "r", encoding="utf-8") as archivo:
        for linea in archivo:
            if not linea.strip():
                continue
            encabezado = patron.match(linea)
            if encabezado is not None:
                cluster, cantidad, porcentaje, palabras = encabezado.groups()
                registros.append(
                    {
                        "cluster": int(cluster),
                        "cantidad_de_palabras_clave": int(cantidad),
                        "porcentaje_de_palabras_clave": float(
                            porcentaje.replace(",", ".")
                        ),
                        "principales_palabras_clave": [palabras],
                    }
                )
            elif registros:
                registros[-1]["principales_palabras_clave"].append(linea)

    for registro in registros:
        palabras = " ".join(" ".join(registro["principales_palabras_clave"]).split())
        registro["principales_palabras_clave"] = palabras.rstrip(".")

    return pd.DataFrame(registros)
