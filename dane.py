import pandas as pd
import numpy as np
import os

#METEOROLOGICZNE
meteo_files = [f for f in os.listdir('dane-2021-2025/dane-pogodowe-stacja-gora-gradowa-2021-2025') if f.endswith('.xlsx')]
all_meteo = []

for file in meteo_files:
    path = os.path.join('dane-2021-2025/dane-pogodowe-stacja-gora-gradowa-2021-2025', file)
    df = pd.read_excel(path, skipfooter=4)
    df = df.dropna(how='all')
    df.columns = df.columns.str.strip()

    cols_to_fix = ['Opad [mm]', 'Temperatura [C]', 'Wilgotność [%]', 'Ciśnienie [hPa]']

    for col in cols_to_fix:
        df[col] = df[col].astype(str).str.replace(',', '.')
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df.loc[(df['Opad [mm]'] < 0) | (df['Opad [mm]'] > 100), 'Opad [mm]'] = np.nan
    df.loc[(df['Temperatura [C]'] < -30) | (df['Temperatura [C]'] > 40), 'Temperatura [C]'] = np.nan
    df.loc[(df['Wilgotność [%]'] < 0) | (df['Wilgotność [%]'] > 100), 'Wilgotność [%]'] = np.nan
    df.loc[(df['Ciśnienie [hPa]'] < 950) | (df['Ciśnienie [hPa]'] >= 1050), 'Ciśnienie [hPa]'] = np.nan

    df = df.dropna(subset=cols_to_fix)

    df["Data"] = pd.to_datetime(df["Data"])
    df["Dzień"] = df["Data"].dt.normalize()

    df_dobowe = df.groupby("Dzień").agg({
        "Opad [mm]": "sum",
        "Temperatura [C]": ["mean", "min", "max"],
        "Wilgotność [%]": "mean",
        "Ciśnienie [hPa]": "mean"
    })
    df_dobowe.columns = [
        'Opad_suma',
        'Temp_średnia', 'Temp_min', 'Temp_max',
        'Wilgotność_średnia',
        'Ciśnienie_średnia'
    ]
    all_meteo.append(df_dobowe)

# połączenie wszystkich plików excel
full_meteo = pd.concat(all_meteo).sort_index()
# pełny kalendarz od początku do końca pomiarów
full_range_meteo = pd.date_range(start=full_meteo.index.min(), end=full_meteo.index.max(), freq='D')
full_meteo = full_meteo.reindex(full_range_meteo)
full_meteo.index.name = 'Data'

# kolumny pomocnicze
full_meteo['month'] = full_meteo.index.month
full_meteo['day'] = full_meteo.index.day

# mediana dla każdego dnia w roku (np. mediana ze wszystkich 15 lipca)
medians = full_meteo.groupby(['month', 'day']).transform('median')
full_meteo = full_meteo.fillna(medians)
full_meteo = full_meteo.drop(columns=['month', 'day'])  # usunięcie kolumn pomocniczych

print("Ilość dni po poprawkach w danych meteorologicznych:", len(full_meteo))
print(full_meteo.head())
print(full_meteo.tail())

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#POZIOM WODY
water_level_files = [f for f in os.listdir('dane-2021-2025/poziom-wody-ujscie-rzeki-strzyza-2021-2025') if f.endswith('.xlsx')]
all_water_level = []

for file in water_level_files:
    path = os.path.join('dane-2021-2025/poziom-wody-ujscie-rzeki-strzyza-2021-2025', file)
    df = pd.read_excel(path, skipfooter=4, usecols=[0, 1])
    df = df.dropna(how='all')
    df.columns = df.columns.str.strip()

    df['Poziom wody [m]'] = df['Poziom wody [m]'].astype(str).str.replace(',', '.')
    df['Poziom wody [m]'] = pd.to_numeric(df['Poziom wody [m]'], errors='coerce')

    # df.loc[(df[nazwa_kolumny] < -10) | (df[nazwa_kolumny] > 10), nazwa_kolumny] = np.nan

    df = df.dropna(subset=['Poziom wody [m]'])

    df["Data"] = pd.to_datetime(df["Data"])
    df["Dzień"] = df["Data"].dt.date

    df_dobowe = df.groupby("Dzień").agg({
        "Poziom wody [m]": ["mean", "max"],
    })
    df_dobowe.columns = [
        'Poziom_wody_średnia', 'Poziom_wody_max'
    ]
    all_water_level.append(df_dobowe)

# połączenie wszystkich plików excel
full_water_level = pd.concat(all_water_level).sort_index()
# pełny kalendarz od początku do końca pomiarów
full_range_wl = pd.date_range(start=full_water_level.index.min(), end=full_water_level.index.max(), freq='D')
full_water_level = full_water_level.reindex(full_range_wl)
full_water_level.index.name = 'Data'

# kolumny pomocnicze
full_water_level['month'] = full_water_level.index.month
full_water_level['day'] = full_water_level.index.day

# mediana dla każdego dnia w roku (np. mediana ze wszystkich 15 lipca)
medians = full_water_level.groupby(['month', 'day']).transform('median')
full_water_level = full_water_level.fillna(medians)
full_water_level = full_water_level.drop(columns=['month', 'day'])  # usunięcie kolumn pomocniczych

print("Ilość dni po poprawkach w danych poziomu wody:", len(full_water_level))
print(full_water_level.head())
print(full_water_level.tail())

#Opóźnienia (lagi) - przesunięcie danych o 1, 2, 3 dni wstecz
# Tworzenie opóźnień dla sumy opadu (np. od 1 do 3 dni)
for i in range(1, 4):
    full_meteo[f'Opad_lag_{i}d'] = full_meteo['Opad_suma'].shift(i)

# Tworzenie opóźnień dla temperatury
# Może być przydatne zimą (topnienie śniegu)
full_meteo['Temp_średnia_lag_1d'] = full_meteo['Temp_średnia'].shift(1)

# Obsługa wartości NaN powstałych przez przesunięcie - wypełniamy je zerami
cols_to_fill = [f'Opad_lag_{i}d' for i in range(1, 4)] + ['Temp_średnia_lag_1d']
full_meteo[cols_to_fill] = full_meteo[cols_to_fill].fillna(0)

print("Dane z opóźnieniami:")
print(full_meteo[[ 'Opad_suma', 'Opad_lag_1d', 'Opad_lag_2d']].head())

# Opady skumulowane jako proxy nasycenia zlewni

# Window=1 to 24h, Window=3 to 72h, Window=7 to 7 dni
# rolling - patrzy na obecny dzień oraz dwa dni poprzednie
full_meteo['Opad_24h'] = full_meteo['Opad_suma'].rolling(window=1).sum()
full_meteo['Opad_72h'] = full_meteo['Opad_suma'].rolling(window=3).sum()
full_meteo['Opad_7d'] = full_meteo['Opad_suma'].rolling(window=7).sum()

full_meteo[['Opad_72h', 'Opad_7d']] = full_meteo[['Opad_72h', 'Opad_7d']].bfill()
print("Nowe kolumny nasycenia:")
print(full_meteo[['Opad_suma', 'Opad_24h', 'Opad_72h', 'Opad_7d']].head(10))