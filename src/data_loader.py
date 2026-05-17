import os
import pandas as pd
import numpy as np

def load_data():
    if os.path.exists('data/processed/final.csv'):
        return pd.read_csv('data/processed/final.csv', index_col='Data',parse_dates=True)  # szybka ścieżka
    else:

        meteo_files = [f for f in os.listdir('data/dane-2021-2025/dane-pogodowe-stacja-gora-gradowa-2021-2025') if
                       f.endswith('.xlsx')]
        all_meteo = []

        for file in meteo_files:
            path = os.path.join('data/dane-2021-2025/dane-pogodowe-stacja-gora-gradowa-2021-2025', file)
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
                "Ciśnienie [hPa]": ["mean", "min", "max"],
            })
            df_dobowe.columns = [
                'Opad_suma',
                'Temp_średnia', 'Temp_min', 'Temp_max',
                'Wilgotność_średnia',
                'Ciśnienie_średnia', "Ciśnienie_min", "Ciśnienie_max",
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
        full_meteo = full_meteo.drop(columns=['day'])  # usunięcie kolumny pomocniczej

        print("Ilość dni po poprawkach w danych meteorologicznych:", len(full_meteo))
        print(full_meteo.head())
        print(full_meteo.tail())

        # ------- CECHY SEZONOWE ------
        sezony = {
            12: 'zima', 1: 'zima', 2: 'zima', 3: 'wiosna', 4: 'wiosna', 5: 'wiosna',
            6: 'lato', 7: 'lato', 8: 'lato', 9: 'jesien', 10: 'jesien', 11: 'jesien'
        }

        # dodajemy kolumny:
        # sezon -> lato/jesien/zima/wiosna
        full_meteo['season'] = full_meteo['month'].map(sezony)
        # nr dnia roku -> (1-365)
        full_meteo['doy'] = full_meteo.index.dayofyear
        # sin/cos doy -> zoobrazowuje odległość dni roku, względem jego cyckliczności
        full_meteo['sin_doy'] = np.sin(2 * np.pi * full_meteo['doy'] / 365)
        full_meteo['cos_doy'] = np.cos(2 * np.pi * full_meteo['doy'] / 365)

        # sprawdzenie
        print("\nMETEO:")
        print(full_meteo[['month', 'season', 'sin_doy', 'cos_doy']].head())
        print(full_meteo[['month', 'season', 'sin_doy', 'cos_doy']].tail())

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # dodatkowe wartości ciśnienia
        full_meteo['Ciśnienie_ampl'] = full_meteo['Ciśnienie_max'] - full_meteo[
            'Ciśnienie_min']  # amplituda ciśnienia w ciągu dnia
        full_meteo['Ciśnienie_delta_1d'] = full_meteo[
            'Ciśnienie_średnia'].diff()  # różnica ciśnienia względem poprzedniego dnia
        full_meteo['Ciśnienie_delta_2d'] = full_meteo['Ciśnienie_średnia'] - full_meteo['Ciśnienie_średnia'].shift(
            2)  # różnica ciśnienia względem dwóch dni wcześniej
        full_meteo['Ciśnienie_delta_3d'] = full_meteo['Ciśnienie_średnia'] - full_meteo['Ciśnienie_średnia'].shift(
            3)  # różnica ciśnienia względem trzech dni wcześniej
        full_meteo['Ciśnienie_trend_3d'] = full_meteo['Ciśnienie_średnia'].rolling(3,
                                                                                   min_periods=1).mean()  # średnia ciśnienia z ostatnich 3 dni (w tym obecny)
        full_meteo['Ciśnienie_trend_7d'] = full_meteo['Ciśnienie_średnia'].rolling(7,
                                                                                   min_periods=1).mean()  # średnia ciśnienia z ostatnich 7 dni (w tym obecny)

        # przybliżone cechy wiatru na podstawie ciśnienia
        full_meteo['Wiatr_siła_proxy'] = full_meteo[
            'Ciśnienie_delta_1d'].abs()  # siła wiatru jako bezwzględna zmiana ciśnienia względem poprzedniego dnia (duża zmiana -> silniejszy wiatr)
        full_meteo['Wiatr_kierunek_proxy'] = np.sign(full_meteo[
                                                         'Ciśnienie_delta_1d'])  # kierunek wiatru jako znak zmiany ciśnienia: -1 = spadek ciśnienia (wiatr z kierunku niskiego ciśnienia), 0 = stabilnie, 1 = wzrost ciśnienia (wiatr z kierunku wysokiego ciśnienia)
        full_meteo['Wiatr_sektor_proxy'] = full_meteo['Wiatr_kierunek_proxy'].map({
            -1: 'spadek_cisnienia',
            0: 'stabilnie',
            1: 'wzrost_cisnienia'
        })
        # zamiana kierunku barycznego (-1/0/1) na sztuczny kąt:
        # UWAGA: to NIE są kierunki świata, tylko matematyczna reprezentacja trendu ciśnienia
        angles = {1: 0, 0: 90, -1: 180}
        full_meteo['Wiatr_kąt_proxy'] = full_meteo['Wiatr_kierunek_proxy'].map(
            angles)  # kąt wiatru jako liczba: 0° dla wzrostu ciśnienia, 90° dla stabilności, 180° dla spadku ciśnienia

        # modele ML lepiej uczą się z wartości ciągłych niż z kategorii -1/0/1
        # (sin, cos) NIE oznaczają kierunku geograficznego – tylko pozycję trendu barycznego na okręgu
        full_meteo['Wiatr_sin_proxy'] = np.sin(
            np.deg2rad(full_meteo['Wiatr_kąt_proxy']))  # sinus kąta wiatru jako cecha numeryczna
        full_meteo['Wiatr_cos_proxy'] = np.cos(
            np.deg2rad(full_meteo['Wiatr_kąt_proxy']))  # cosinus kąta wiatru jako cecha numeryczna

        # Wszystkie możliwe kombinacje trendu ciśnienia i odpowiadające im cechy wiatru:
        # Trend ciśnienia	Kąt proxy	Wiatr_sin_proxy	Wiatr_cos_proxy
        # wzrost (+1)	    0°	        0.0	            1.0
        # stabilnie (0)	    90°	        1.0	            0.0
        # spadek (–1)	    180°	    0.0	            –1.0

        # usunięcie NaN
        full_meteo.iloc[0, full_meteo.columns.get_loc('Ciśnienie_delta_1d')] = 0
        full_meteo.iloc[0, full_meteo.columns.get_loc('Ciśnienie_delta_2d')] = 0
        full_meteo.iloc[0, full_meteo.columns.get_loc('Ciśnienie_delta_3d')] = 0
        full_meteo.iloc[0, full_meteo.columns.get_loc('Wiatr_siła_proxy')] = 0
        full_meteo.iloc[0, full_meteo.columns.get_loc('Wiatr_kierunek_proxy')] = 0
        full_meteo.iloc[0, full_meteo.columns.get_loc('Wiatr_sektor_proxy')] = 0
        full_meteo.iloc[0, full_meteo.columns.get_loc('Wiatr_kąt_proxy')] = 0
        full_meteo.iloc[0, full_meteo.columns.get_loc('Wiatr_sin_proxy')] = 0
        full_meteo.iloc[0, full_meteo.columns.get_loc('Wiatr_cos_proxy')] = 0
        full_meteo.loc[full_meteo.index[1], ['Ciśnienie_delta_2d', 'Ciśnienie_delta_3d']] = 0
        full_meteo.loc[full_meteo.index[2], ['Ciśnienie_delta_3d']] = 0

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # POZIOM WODY
        water_level_files = [f for f in os.listdir('data/dane-2021-2025/poziom-wody-ujscie-rzeki-strzyza-2021-2025') if
                             f.endswith('.xlsx')]
        all_water_level = []

        for file in water_level_files:
            path = os.path.join('data/dane-2021-2025/poziom-wody-ujscie-rzeki-strzyza-2021-2025', file)
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
        full_water_level = full_water_level.drop(columns=['day'])  # usunięcie kolumny pomocniczej

        print("Ilość dni po poprawkach w danych poziomu wody:", len(full_water_level))
        print(full_water_level.head())
        print(full_water_level.tail())

        # Opóźnienia (lagi) - przesunięcie danych o 1, 2, 3 dni wstecz
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
        print(full_meteo[['Opad_suma', 'Opad_lag_1d', 'Opad_lag_2d']].head())

        # ------- CECHY SEZONOWE ------

        # dodajemy kolumny:
        # sezon -> lato/jesien/zima/wiosna
        full_water_level['season'] = full_water_level['month'].map(sezony)
        # nr dnia roku -> (1-365)
        full_water_level['doy'] = full_water_level.index.dayofyear
        # sin/cos doy -> zoobrazowuje odległość dni roku, względem jego cyckliczności
        full_water_level['sin_doy'] = np.sin(2 * np.pi * full_water_level['doy'] / 365)
        full_water_level['cos_doy'] = np.cos(2 * np.pi * full_water_level['doy'] / 365)

        # sprawdzenie
        print("\nPOZIOM WODY:")
        print(full_water_level[['month', 'season', 'sin_doy', 'cos_doy']].head())
        print(full_water_level[['month', 'season', 'sin_doy', 'cos_doy']].tail())
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Opady skumulowane jako proxy nasycenia zlewni

        # Window=1 to 24h, Window=3 to 72h, Window=7 to 7 dni
        # rolling - patrzy na obecny dzień oraz dwa dni poprzednie
        full_meteo['Opad_24h'] = full_meteo['Opad_suma'].rolling(window=1).sum()
        full_meteo['Opad_72h'] = full_meteo['Opad_suma'].rolling(window=3).sum()
        full_meteo['Opad_7d'] = full_meteo['Opad_suma'].rolling(window=7).sum()

        full_meteo[['Opad_72h', 'Opad_7d']] = full_meteo[['Opad_72h', 'Opad_7d']].bfill()
        print("Nowe kolumny nasycenia:")
        print(full_meteo[['Opad_suma', 'Opad_24h', 'Opad_72h', 'Opad_7d']].head(10))

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # połączenie w jeden database
        final = full_meteo.join(full_water_level, how='inner')


        os.makedirs('data/processed', exist_ok=True)
        final.to_csv('data/processed/final.csv', index=True)
        print("Zapisano final.csv!")
        return final
