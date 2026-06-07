import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")

def build_meteo_dataframe():
    folder = os.path.join(RAW_DIR, "dane-pogodowe-stacja-gora-gradowa-2021-2025")
    meteo_files = [f for f in os.listdir(folder) if
                   f.endswith('.xlsx')]
    all_meteo = []

    for file in meteo_files:
        path = os.path.join(folder, file)
        df = pd.read_excel(path, skipfooter=4)
        df = df.dropna(how='all')
        df.columns = df.columns.str.strip()
        all_meteo.append(df)

    return pd.concat(all_meteo)

def build_strzyza_level_dataframe():
    folder = os.path.join(RAW_DIR, "poziom-wody-ujscie-rzeki-strzyza-2021-2025")
    water_level_files = [f for f in os.listdir(folder) if
                         f.endswith('.xlsx')]
    all_water_level = []

    for file in water_level_files:
        path = os.path.join(folder, file)
        df = pd.read_excel(path, skipfooter=4, usecols=[0, 1])
        df = df.dropna(how='all')
        df.columns = df.columns.str.strip()
        all_water_level.append(df)

    return pd.concat(all_water_level)

def build_martwa_wisla_dataframe():
    df = pd.read_excel('data/raw/poziom-wody-Martwa-Wisla-2021-2015.xlsx', skipfooter=4)
    df = df.dropna(how='all')
    df.columns = df.columns.str.strip()
    return df

def build_port_polnocny_dataframe():
    df = pd.read_excel('data/raw/poziom-wody-port-polnocny-2021-2025.xlsx', skipfooter=4)
    df = df.dropna(how='all')
    df.columns = df.columns.str.strip()
    return df