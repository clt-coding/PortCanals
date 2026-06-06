import os
from typing import final
import pandas as pd
import numpy as np

def clean_meteo_and_day_step(df):
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
        "Ciśnienie [hPa]": ["mean", "min", "max"],
    })

    df_dobowe.columns = [
        'Opad_suma',
        'Temp_średnia', 'Temp_min', 'Temp_max',
        'Wilgotność_średnia',
        'Ciśnienie_średnia', "Ciśnienie_min", "Ciśnienie_max",
    ]

    return df_dobowe

def fix_missing_meteo(df):
    full_range_meteo = pd.date_range(start=df.index.min(), end=df.index.max(), freq='D')
    df = df.reindex(full_range_meteo)
    df.index.name = 'Data'

    df['month'] = df.index.month
    df['day'] = df.index.day
    medians = df.groupby(['month', 'day']).transform('median')
    df = df.fillna(medians)
    df = df.drop(columns=['day'])

    return df

def add_meteo_engineered_features(df):
    seasons = {
        12: 'zima', 1: 'zima', 2: 'zima', 3: 'wiosna', 4: 'wiosna', 5: 'wiosna',
        6: 'lato', 7: 'lato', 8: 'lato', 9: 'jesien', 10: 'jesien', 11: 'jesien'
    }

    df['sezon'] = df['month'].map(seasons)
    df['doy'] = df.index.dayofyear
    # sin/cos doy -> zoobrazowuje odległość dni roku, względem jego cyckliczności
    df['sin_doy'] = np.sin(2 * np.pi * df['doy'] / 365)
    df['cos_doy'] = np.cos(2 * np.pi * df['doy'] / 365)

    # dodatkowe wartości ciśnienia
    df['Ciśnienie_ampl'] = df['Ciśnienie_max'] - df['Ciśnienie_min']  # amplituda ciśnienia w ciągu dnia
    df['Ciśnienie_delta_1d'] = df['Ciśnienie_średnia'].diff()  # różnica ciśnienia względem poprzedniego dnia
    df['Ciśnienie_delta_2d'] = df['Ciśnienie_średnia'] - df['Ciśnienie_średnia'].shift(2)  # różnica ciśnienia względem dwóch dni wcześniej
    df['Ciśnienie_delta_3d'] = df['Ciśnienie_średnia'] - df['Ciśnienie_średnia'].shift(3)  # różnica ciśnienia względem trzech dni wcześniej
    df['Ciśnienie_trend_3d'] = df['Ciśnienie_średnia'].rolling(3, min_periods=1).mean()  # średnia ciśnienia z ostatnich 3 dni (w tym obecny)
    df['Ciśnienie_trend_7d'] = df['Ciśnienie_średnia'].rolling(7,min_periods=1).mean()  # średnia ciśnienia z ostatnich 7 dni (w tym obecny)

    # przybliżone cechy wiatru na podstawie ciśnienia
    df['Wiatr_siła_proxy'] = df['Ciśnienie_delta_1d'].abs()  # siła wiatru jako bezwzględna zmiana ciśnienia względem poprzedniego dnia (duża zmiana -> silniejszy wiatr)
    df['Wiatr_kierunek_proxy'] = np.sign(df['Ciśnienie_delta_1d'])  # kierunek wiatru jako znak zmiany ciśnienia: -1 = spadek ciśnienia (wiatr z kierunku niskiego ciśnienia), 0 = stabilnie, 1 = wzrost ciśnienia (wiatr z kierunku wysokiego ciśnienia)
    df['Wiatr_sektor_proxy'] = df['Wiatr_kierunek_proxy'].map({
        -1: 'spadek_cisnienia',
        0: 'stabilnie',
        1: 'wzrost_cisnienia'
    })
    # zamiana kierunku barycznego (-1/0/1) na sztuczny kąt:
    # UWAGA: to NIE są kierunki świata, tylko matematyczna reprezentacja trendu ciśnienia
    angles = {1: 0, 0: 90, -1: 180}
    df['Wiatr_kąt_proxy'] = df['Wiatr_kierunek_proxy'].map(angles)  # kąt wiatru jako liczba: 0° dla wzrostu ciśnienia, 90° dla stabilności, 180° dla spadku ciśnienia

    # modele ML lepiej uczą się z wartości ciągłych niż z kategorii -1/0/1
    # (sin, cos) NIE oznaczają kierunku geograficznego – tylko pozycję trendu barycznego na okręgu
    df['Wiatr_sin_proxy'] = np.sin(np.deg2rad(df['Wiatr_kąt_proxy']))  # sinus kąta wiatru jako cecha numeryczna
    df['Wiatr_cos_proxy'] = np.cos(np.deg2rad(df['Wiatr_kąt_proxy']))  # cosinus kąta wiatru jako cecha numeryczna

    # Wszystkie możliwe kombinacje trendu ciśnienia i odpowiadające im cechy wiatru:
    # Trend ciśnienia	Kąt proxy	Wiatr_sin_proxy	Wiatr_cos_proxy
    # wzrost (+1)	    0°	        0.0	            1.0
    # stabilnie (0)	    90°	        1.0	            0.0
    # spadek (–1)	    180°	    0.0	            –1.0

    # usunięcie NaN
    df['Ciśnienie_delta_1d'] = df['Ciśnienie_delta_1d'].fillna(0)
    df['Ciśnienie_delta_2d'] = df['Ciśnienie_delta_2d'].fillna(0)
    df['Ciśnienie_delta_3d'] = df['Ciśnienie_delta_3d'].fillna(0)
    df['Wiatr_siła_proxy'] = df['Wiatr_siła_proxy'].fillna(0)
    df['Wiatr_kierunek_proxy'] = df['Wiatr_kierunek_proxy'].fillna(0)
    df['Wiatr_sektor_proxy'] = df['Wiatr_sektor_proxy'].fillna('stabilnie')
    df['Wiatr_kąt_proxy'] = df['Wiatr_kąt_proxy'].fillna(90)
    df['Wiatr_sin_proxy'] = df['Wiatr_sin_proxy'].fillna(0)
    df['Wiatr_cos_proxy'] = df['Wiatr_cos_proxy'].fillna(0)

    for i in range(1, 4):
        df[f'Opad_lag_{i}d'] = df['Opad_suma'].shift(i)
    # Tworzenie opóźnień dla temperatury
    # Może być przydatne zimą (topnienie śniegu)
    df['Temp_średnia_lag_1d'] = df['Temp_średnia'].shift(1)
    # Obsługa wartości NaN powstałych przez przesunięcie - wypełniamy je zerami
    cols_to_fill = [f'Opad_lag_{i}d' for i in range(1, 4)] + ['Temp_średnia_lag_1d']
    df[cols_to_fill] = df[cols_to_fill].fillna(0)

    # Window=1 to 24h, Window=3 to 72h, Window=7 to 7 dni
    # rolling - patrzy na obecny dzień oraz dwa dni poprzednie
    df['Opad_24h'] = df['Opad_suma'].rolling(window=1).sum()
    df['Opad_72h'] = df['Opad_suma'].rolling(window=3).sum()
    df['Opad_7d'] = df['Opad_suma'].rolling(window=7).sum()
    df[['Opad_72h', 'Opad_7d']] = df[['Opad_72h', 'Opad_7d']].bfill()

    return df

def clean_water_level_and_day_step(df):
    df['Poziom wody [m]'] = df['Poziom wody [m]'].astype(str).str.replace(',', '.')
    df['Poziom wody [m]'] = pd.to_numeric(df['Poziom wody [m]'], errors='coerce')

    df.loc[(df['Poziom wody [m]'] < -0.5) | (df['Poziom wody [m]'] > 2.0), 'Poziom wody [m]'] = np.nan

    df = df.dropna(subset=['Poziom wody [m]'])

    df["Data"] = pd.to_datetime(df["Data"])
    df["Dzień"] = df["Data"].dt.date

    df_dobowe = df.groupby("Dzień").agg({
        "Poziom wody [m]": ["mean", "max"],
    })

    df_dobowe.columns = [
        'Poziom_wody_średnia', 'Poziom_wody_max'
    ]

    return df_dobowe

def fix_missing_water_level(df):
    full_range_wl = pd.date_range(start=df.index.min(), end=df.index.max(), freq='D')
    df = df.reindex(full_range_wl)
    df.index.name = 'Data'

    df['month'] = df.index.month
    df['day'] = df.index.day
    medians = df.groupby(['month', 'day']).transform('median')
    df = df.fillna(medians)
    df = df.drop(columns=['day'])

    return df

def add_water_level_engineered_features(df):
    seasons = {
        12: 'zima', 1: 'zima', 2: 'zima',
        3: 'wiosna', 4: 'wiosna', 5: 'wiosna',
        6: 'lato', 7: 'lato', 8: 'lato',
        9: 'jesien', 10: 'jesien', 11: 'jesien'
    }

    df['sezon'] = df['month'].map(seasons)
    df['doy'] = df.index.dayofyear
    # sin/cos doy -> zoobrazowuje odległość dni roku, względem jego cyckliczności
    df['sin_doy'] = np.sin(2 * np.pi * df['doy'] / 365)
    df['cos_doy'] = np.cos(2 * np.pi * df['doy'] / 365)

    return df

# -- zbieranie wszystkiego "do kupy" --
def build_main_df():
    if os.path.exists('data/processed/final.csv'):
        return pd.read_csv('data/processed/final.csv', index_col='Data', parse_dates=True)

    from dataset import build_meteo_dataframe, build_water_level_dataframe

    df_meteo_raw = build_meteo_dataframe()
    full_meteo = clean_meteo_and_day_step(df_meteo_raw)
    full_meteo = fix_missing_meteo(full_meteo)
    full_meteo = add_meteo_engineered_features(full_meteo)

    df_water_raw = build_water_level_dataframe()
    full_water = clean_water_level_and_day_step(df_water_raw)
    full_water = fix_missing_water_level(full_water)
    full_water = add_water_level_engineered_features(full_water)

    cols_to_drop = ['month', 'sezon', 'doy', 'sin_doy', 'cos_doy']
    full_water = full_water.drop(columns=cols_to_drop)

    final = full_meteo.join(full_water, how='inner')

    os.makedirs('data/processed', exist_ok=True)
    final.to_csv('data/processed/final.csv', index=True)
    print("Zapisano final.csv")

    return final