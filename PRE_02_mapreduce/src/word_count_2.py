"""
Simulacion de un proceso MapReduce (al estilo Hadoop) para contar palabras.
"""

# pylint: disable=import-outside-toplevel

import glob
import os
import re
import shutil
from itertools import groupby

DATA_FOLDER = "PRE_02_mapreduce/data"
INPUT_FOLDER = "PRE_02_mapreduce/temp/input"


def initialize_folder(folder):
    """
    Crea la carpeta indicada. Si ya existe, la vacia por completo.
    """

    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)


def delete_folder(folder):
    """
    Elimina la carpeta indicada (y su contenido) si existe.
    """

    if os.path.exists(folder):
        shutil.rmtree(folder)


def generate_file_copies(
    n_copies,
    data_folder=DATA_FOLDER,
    input_folder=INPUT_FOLDER,
):
    """
    Genera n_copies copias de cada archivo de data_folder dentro de
    input_folder, simulando un conjunto de datos de mayor tamano.
    """

    filenames = sorted(glob.glob(f"{data_folder}/*.txt"))
    for i in range(n_copies):
        for filename in filenames:
            basename = os.path.splitext(os.path.basename(filename))[0]
            destination = f"{input_folder}/{basename}_{i}.txt"
            shutil.copyfile(filename, destination)


def mapper(text):
    """
    Funcion map: emite el par (palabra, 1) por cada palabra del texto.
    """

    words = re.findall(r"[a-zA-Z]+", text.lower())
    return [(word, 1) for word in words]


def reducer(key, values):
    """
    Funcion reduce: suma los valores asociados a una misma llave.
    """

    return (key, sum(values))


def hadoop(input_folder, output_folder, mapper_fn, reducer_fn):
    """
    Simula un proceso Hadoop MapReduce de una sola etapa sobre todos los
    archivos de input_folder y escribe el resultado en
    output_folder/part-00000 como lineas "llave\\tvalor".
    """

    # Map
    mapped_values = []
    for filename in sorted(glob.glob(f"{input_folder}/*")):
        with open(filename, "r", encoding="utf-8") as file:
            content = file.read()
        mapped_values.extend(mapper_fn(content))

    # Shuffle and sort
    mapped_values.sort(key=lambda pair: pair[0])

    # Reduce
    os.makedirs(output_folder)
    with open(f"{output_folder}/part-00000", "w", encoding="utf-8") as file:
        for key, group in groupby(mapped_values, key=lambda pair: pair[0]):
            values = [value for _, value in group]
            result_key, result_value = reducer_fn(key, values)
            file.write(f"{result_key}\t{result_value}\n")
