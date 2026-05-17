import os
import pandas as pd

def build_meteo_dataframe():
    meteo_files = [f for f in os.listdir('data/raw/dane-pogodowe-stacja-gora-gradowa-2021-2025') if
                   f.endswith('.xlsx')]
    all_meteo = []

    for file in meteo_files:
        path = os.path.join('data/raw/dane-pogodowe-stacja-gora-gradowa-2021-2025', file)
        df = pd.read_excel(path, skipfooter=4)
        df = df.dropna(how='all')
        df.columns = df.columns.str.strip()
        all_meteo.append(df)

    return pd.concat(all_meteo)

def build_water_level_dataframe():
    water_level_files = [f for f in os.listdir('data/raw/poziom-wody-ujscie-rzeki-strzyza-2021-2025') if
                         f.endswith('.xlsx')]
    all_water_level = []

    for file in water_level_files:
        path = os.path.join('data/raw/poziom-wody-ujscie-rzeki-strzyza-2021-2025', file)
        df = pd.read_excel(path, skipfooter=4, usecols=[0, 1])
        df = df.dropna(how='all')
        df.columns = df.columns.str.strip()
        all_water_level.append(df)

    return pd.concat(all_water_level)