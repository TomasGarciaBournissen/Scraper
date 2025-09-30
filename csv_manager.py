import shutil
import pandas as pd
import os
import time


def hacer_copia(origen: str, carpeta_backups: str = "backups", timestamp: bool = True) -> str:
    """
    Crea una copia de un archivo.
    - Si timestamp=True: le agrega fecha y hora al nombre.
    - Si timestamp=False: siempre guarda con el mismo nombre.
    Devuelve la ruta del archivo copia.
    """
    os.makedirs(carpeta_backups, exist_ok=True)
    nombre_archivo = os.path.basename(origen)

    if timestamp:
        marca = time.strftime("%Y%m%d_%H%M%S")
        copia = os.path.join(carpeta_backups, f"{marca}_{nombre_archivo}")
    else:
        copia = os.path.join(carpeta_backups, f"copy_{nombre_archivo}")

    shutil.copy2(origen, copia)
    return copia


def append_a_global(origen: str, global_csv: str) -> None:
    """
    Agrega los datos de un CSV origen a un CSV global acumulativo.
    Si el global no existe, lo crea.
    """
    df_new = pd.read_csv(origen)

    if os.path.exists(global_csv):
        df_global = pd.read_csv(global_csv)
        df_global = pd.concat([df_global, df_new], ignore_index=True)
    else:
        df_global = df_new

    df_global.to_csv(global_csv, index=False)


def procesar_csv(origen: str, global_csv: str = "data_global.csv", carpeta_backups: str = "backups") -> None:
    """
    Pipeline completo:
    1. Hace una copia del archivo origen en backups/
    2. Agrega los datos al global acumulativo.
    """
    copia = hacer_copia(origen, carpeta_backups, timestamp=True)
    print(f"Copia creada en: {copia}")
    
    append_a_global(origen, global_csv)
    print(f"Datos agregados a: {global_csv}")
