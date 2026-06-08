import pandas as pd
import numpy as np
import os
from scipy.stats import shapiro, mannwhitneyu
from sklearn.linear_model import LinearRegression
from sklearn.metrics import confusion_matrix, precision_score, recall_score

#METEOROLOGICZNE
meteo_files = [f for f in os.listdir('../data/raw/dane-pogodowe-stacja-gora-gradowa-2021-2025') if f.endswith('.xlsx')]
all_meteo = []

for file in meteo_files:
    path = os.path.join('../data/raw/dane-pogodowe-stacja-gora-gradowa-2021-2025', file)
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
full_meteo['Miesiąc'] = full_meteo.index.month
full_meteo['Dzień'] = full_meteo.index.day

# print(full_meteo.isna().sum())

# mediana dla każdego dnia w roku (np. mediana ze wszystkich 15 lipca)
medians = full_meteo.groupby(['Miesiąc', 'Dzień']).transform('median')
full_meteo = full_meteo.fillna(medians)
full_meteo = full_meteo.drop(columns=['Dzień'])  # usunięcie kolumny pomocniczej

print("Ilość dni po poprawkach w danych meteorologicznych:", len(full_meteo))
print(full_meteo.head())
print(full_meteo.tail())

#------- CECHY SEZONOWE ------
sezony = {
    12: 'zima',  1: 'zima',  2: 'zima', 3: 'wiosna', 4: 'wiosna', 5: 'wiosna',
    6: 'lato',   7: 'lato',   8: 'lato', 9: 'jesien', 10: 'jesien', 11: 'jesien'
}

#dodajemy kolumny:
#sezon -> lato/jesien/zima/wiosna
full_meteo['Pora_roku'] = full_meteo['Miesiąc'].map(sezony)
#nr dnia roku -> (1-365)
full_meteo['Nr_dnia_roku'] = full_meteo.index.dayofyear
#sin/cos doy -> zoobrazowuje odległość dni roku, względem jego cyckliczności
full_meteo['Sin_nr_dnia_roku'] = np.sin(2 * np.pi * full_meteo['Nr_dnia_roku'] / 365)
full_meteo['Cos_nr_dnia_roku'] = np.cos(2 * np.pi * full_meteo['Nr_dnia_roku'] / 365)

#sprawdzenie
print("\nMETEO:")
print(full_meteo[['Miesiąc', 'Pora_roku', 'Sin_nr_dnia_roku', 'Cos_nr_dnia_roku']].head())
print(full_meteo[['Miesiąc', 'Pora_roku', 'Sin_nr_dnia_roku', 'Cos_nr_dnia_roku']].tail())

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# dodatkowe wartości ciśnienia
full_meteo['Ciśnienie_ampl'] = full_meteo['Ciśnienie_max'] - full_meteo['Ciśnienie_min'] # amplituda ciśnienia w ciągu dnia
full_meteo['Ciśnienie_delta_1d'] = full_meteo['Ciśnienie_średnia'].diff() # różnica ciśnienia względem poprzedniego dnia
full_meteo['Ciśnienie_delta_2d'] = full_meteo['Ciśnienie_średnia'] - full_meteo['Ciśnienie_średnia'].shift(2) # różnica ciśnienia względem dwóch dni wcześniej
full_meteo['Ciśnienie_delta_3d'] = full_meteo['Ciśnienie_średnia'] - full_meteo['Ciśnienie_średnia'].shift(3) # różnica ciśnienia względem trzech dni wcześniej
full_meteo['Ciśnienie_trend_3d'] = full_meteo['Ciśnienie_średnia'].rolling(3, min_periods=1).mean() # średnia ciśnienia z ostatnich 3 dni (w tym obecny)
full_meteo['Ciśnienie_trend_7d'] = full_meteo['Ciśnienie_średnia'].rolling(7, min_periods=1).mean() # średnia ciśnienia z ostatnich 7 dni (w tym obecny)

# przybliżone cechy wiatru na podstawie ciśnienia
full_meteo['Wiatr_siła_proxy'] = full_meteo['Ciśnienie_delta_1d'].abs() # siła wiatru jako bezwzględna zmiana ciśnienia względem poprzedniego dnia (duża zmiana -> silniejszy wiatr)
full_meteo['Wiatr_kierunek_proxy'] = np.sign(full_meteo['Ciśnienie_delta_1d']) # kierunek wiatru jako znak zmiany ciśnienia: -1 = spadek ciśnienia (wiatr z kierunku niskiego ciśnienia), 0 = stabilnie, 1 = wzrost ciśnienia (wiatr z kierunku wysokiego ciśnienia)
full_meteo['Wiatr_sektor_proxy'] = full_meteo['Wiatr_kierunek_proxy'].map({
    -1: 'spadek_cisnienia',
     0: 'stabilnie',
     1: 'wzrost_cisnienia'
}) 
# zamiana kierunku barycznego (-1/0/1) na sztuczny kąt:
# UWAGA: to NIE są kierunki świata, tylko matematyczna reprezentacja trendu ciśnienia
angles = {1: 0, 0: 90, -1: 180}
full_meteo['Wiatr_kąt_proxy'] = full_meteo['Wiatr_kierunek_proxy'].map(angles) # kąt wiatru jako liczba: 0° dla wzrostu ciśnienia, 90° dla stabilności, 180° dla spadku ciśnienia

# modele ML lepiej uczą się z wartości ciągłych niż z kategorii -1/0/1
# (sin, cos) NIE oznaczają kierunku geograficznego – tylko pozycję trendu barycznego na okręgu
full_meteo['Wiatr_sin_proxy'] = np.sin(np.deg2rad(full_meteo['Wiatr_kąt_proxy'])) # sinus kąta wiatru jako cecha numeryczna
full_meteo['Wiatr_cos_proxy'] = np.cos(np.deg2rad(full_meteo['Wiatr_kąt_proxy'])) # cosinus kąta wiatru jako cecha numeryczna

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
full_meteo.iloc[0, full_meteo.columns.get_loc('Wiatr_sektor_proxy')] = 'stabilnie'
full_meteo.iloc[0, full_meteo.columns.get_loc('Wiatr_kąt_proxy')] = 0
full_meteo.iloc[0, full_meteo.columns.get_loc('Wiatr_sin_proxy')] = 0
full_meteo.iloc[0, full_meteo.columns.get_loc('Wiatr_cos_proxy')] = 0
full_meteo.loc[full_meteo.index[1], ['Ciśnienie_delta_2d', 'Ciśnienie_delta_3d']] = 0
full_meteo.loc[full_meteo.index[2], ['Ciśnienie_delta_3d']] = 0

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#POZIOM WODY
water_level_files = [f for f in os.listdir('../data/raw/poziom-wody-ujscie-rzeki-strzyza-2021-2025') if f.endswith('.xlsx')]
all_water_level = []

for file in water_level_files:
    path = os.path.join('../data/raw/poziom-wody-ujscie-rzeki-strzyza-2021-2025', file)
    df = pd.read_excel(path, skipfooter=4, usecols=[0, 1])
    df = df.dropna(how='all')
    df.columns = df.columns.str.strip()

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
    all_water_level.append(df_dobowe)

# połączenie wszystkich plików excel
full_water_level = pd.concat(all_water_level).sort_index()
# pełny kalendarz od początku do końca pomiarów
full_range_wl = pd.date_range(start=full_water_level.index.min(), end=full_water_level.index.max(), freq='D')
full_water_level = full_water_level.reindex(full_range_wl)
full_water_level.index.name = 'Data'

# kolumny pomocnicze
full_water_level['Miesiąc'] = full_water_level.index.month
full_water_level['Dzień'] = full_water_level.index.day

# print(full_water_level.isna().sum())

# mediana dla każdego dnia w roku (np. mediana ze wszystkich 15 lipca)
medians = full_water_level.groupby(['Miesiąc', 'Dzień']).transform('median')
full_water_level = full_water_level.fillna(medians)
full_water_level = full_water_level.drop(columns=['Dzień'])  # usunięcie kolumny pomocniczej

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

#------- CECHY SEZONOWE ------

#dodajemy kolumny:
#sezon -> lato/jesien/zima/wiosna
full_water_level['Pora_roku'] = full_water_level['Miesiąc'].map(sezony)
#nr dnia roku -> (1-365)
full_water_level['Nr_dnia_roku'] = full_water_level.index.dayofyear
#sin/cos doy -> zoobrazowuje odległość dni roku, względem jego cyckliczności
full_water_level['Sin_nr_dnia_roku'] = np.sin(2 * np.pi * full_water_level['Nr_dnia_roku'] / 365)
full_water_level['Cos_nr_dnia_roku'] = np.cos(2 * np.pi * full_water_level['Nr_dnia_roku'] / 365)

#sprawdzenie
print("\nPOZIOM WODY:")
print(full_water_level[['Miesiąc', 'Pora_roku', 'Sin_nr_dnia_roku', 'Cos_nr_dnia_roku']].head())
print(full_water_level[['Miesiąc', 'Pora_roku', 'Sin_nr_dnia_roku', 'Cos_nr_dnia_roku']].tail())
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Opady skumulowane jako proxy nasycenia zlewni

# 24h to Opad_suma, Window=3 to 72h, Window=7 to 7 dni
# rolling - patrzy na obecny dzień oraz dwa dni poprzednie
full_meteo['Opad_72h'] = full_meteo['Opad_suma'].rolling(window=3).sum()
full_meteo['Opad_7d'] = full_meteo['Opad_suma'].rolling(window=7).sum()

full_meteo[['Opad_72h', 'Opad_7d']] = full_meteo[['Opad_72h', 'Opad_7d']].bfill()
print("Nowe kolumny nasycenia:")
print(full_meteo[['Opad_suma', 'Opad_72h', 'Opad_7d']].head(10))

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# połączenie w jeden database, usuwamy zduplikowane kolumny z poziomu wody przed połączeniem
kolumny_do_usuniecia = ['Miesiąc', 'Pora_roku', 'Nr_dnia_roku', 'Sin_nr_dnia_roku', 'Cos_nr_dnia_roku']
final = full_meteo.join(full_water_level.drop(columns=kolumny_do_usuniecia), how='inner')

# wyświetlanie wszystkich kolumn
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

print(final)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ WIZUALIZACJE ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# ~~~~~~~~~~~~ SEZONOWOŚĆ ~~~~~~~~~~~~~~~

import matplotlib.pyplot as plt
import seaborn as sns

# Ustawienie estetycznego stylu dla wykresów
sns.set_theme(style="whitegrid")


# PRZEBIEG POZIOMU WODY W CZASIE (DOBOWO)
plt.figure(figsize=(15, 5))
plt.plot(final.index, final['Poziom_wody_średnia'], label='Średni dobowy poziom', color='teal', alpha=0.7)
plt.plot(final.index, final['Poziom_wody_max'], label='Maksymalny dobowy poziom', color='red', alpha=0.5)
plt.title('Przebieg poziomu wody na rzece Strzyża w latach 2021-2025', fontsize=14)
plt.ylabel('Poziom wody [m]')
plt.xlabel('Data')
plt.legend()
plt.tight_layout()
plt.savefig('reports/sezonowosc_poziomu_wody/przebieg_poziomu_wody_dobowo', dpi=300)


# SEZONOWOŚĆ WEDŁUG PÓR ROKU (BOXPLOT)
plt.figure(figsize=(10, 6))
sns.boxplot(data=final, x='Pora_roku', y='Poziom_wody_średnia',
            hue='Pora_roku', order=['wiosna', 'lato', 'jesien', 'zima'],
            palette='pastel', legend=False)
plt.title('Rozkład średniego dobowego poziomu wody w zależności od pory roku', fontsize=14)
plt.ylabel('Średni poziom wody [m]')
plt.xlabel('Pora roku')
plt.tight_layout()
plt.savefig('reports/sezonowosc_poziomu_wody/sezonowosc_wg_por_roku', dpi=300)


# SEZONOWOŚĆ WEDŁUG MIESIĘCY (BOXPLOT)
plt.figure(figsize=(12, 6))
sns.boxplot(data=final, x='Miesiąc', y='Poziom_wody_średnia',
            hue='Miesiąc', palette='Set3', legend=False)
plt.title('Rozkład średniego dobowego poziomu wody w poszczególnych miesiącach', fontsize=14)
plt.ylabel('Średni poziom wody [m]')
plt.xlabel('Miesiąc (1=Styczeń, 12=Grudzień)')
plt.tight_layout()
plt.savefig('reports/sezonowosc_poziomu_wody/sezonowosc_wg_miesiecy', dpi=300)


# ~~~~~~~~~~~~ ZALEŻNOŚCI ~~~~~~~~~~~~~~~

# ZALEŻNOŚCI METEO - POZIOM WODY (OGÓLNIE)
plt.figure(figsize=(10, 6))
# Używamy Opad_72h jako proxy nasycenia ziemi i sumy deszczu
sns.scatterplot(data=final, x='Opad_72h', y='Poziom_wody_max', alpha=0.5, color='royalblue')
plt.title('Zależność ogólna: Opad skumulowany (72h) a maksymalny poziom wody', fontsize=14)
plt.xlabel('Opad skumulowany z 3 dni [mm]')
plt.ylabel('Maksymalny dobowy poziom wody [m]')
plt.tight_layout()
plt.savefig('reports/zaleznosci_poziom_wody/zaleznosc_opad_woda_ogolnie.png', dpi=300)


# ZALEŻNOŚCI METEO - POZIOM WODY (Z PODZIAŁEM NA SEZONY)
plt.figure(figsize=(12, 7))
sns.scatterplot(data=final, x='Opad_72h', y='Poziom_wody_max', hue='Pora_roku',
                palette='bright', alpha=0.7, s=60)
plt.title('Zależność: Opad skumulowany a poziom wody w różnych porach roku', fontsize=14)
plt.xlabel('Opad skumulowany z 3 dni [mm]')
plt.ylabel('Maksymalny dobowy poziom wody [m]')
plt.legend(title='Pora roku')
plt.tight_layout()
plt.savefig('reports/zaleznosci_poziom_wody/zaleznosc_opad_woda_sezony.png', dpi=300)


# ZALEŻNOŚĆ CIŚNIENIA (PROXY WIATRU/COFKI) A POZIOM WODY
plt.figure(figsize=(12, 7))
sns.scatterplot(data=final, x='Ciśnienie_delta_1d', y='Poziom_wody_max', hue='Pora_roku',
                palette='bright', alpha=0.7, s=60)
plt.title('Wpływ zmiany ciśnienia (proxy wiatru/sztormu) na poziom wody', fontsize=14)
plt.xlabel('Zmiana ciśnienia względem poprzedniego dnia [hPa] (Wartości ujemne = spadek/niż)')
plt.ylabel('Maksymalny dobowy poziom wody [m]')
plt.axvline(0, color='grey', linestyle='--') # Linia oddzielająca spadki od wzrostów ciśnienia
plt.legend(title='Pora roku')
plt.tight_layout()
plt.savefig('reports/zaleznosci_poziom_wody/zaleznosc_cisnienie_woda_sezony.png', dpi=300)

# ~~~~~~~~~~~~ ANALIZA OPÓŹNIEŃ ~~~~~~~~~~~~~~~

# ANALIZA OPÓŹNIEŃ (KORELACJA Z LAGAMI)
# Obliczamy korelację między maksymalnym poziomem wody a opadami z różnych dni
lagi_opadu = ['Opad_suma', 'Opad_lag_1d', 'Opad_lag_2d', 'Opad_lag_3d']
korelacje = final[lagi_opadu].apply(lambda x: x.corr(final['Poziom_wody_max']))
nazwy_lagow = ['W tym samym dniu', '1 dzień po', '2 dni po', '3 dni po']

plt.figure(figsize=(8, 5))
sns.barplot(x=nazwy_lagow, y=korelacje.values, hue=nazwy_lagow, palette='viridis', legend=False)
plt.title('Korelacja między opadem a poziomem wody w zależności od opóźnienia', fontsize=14)
plt.ylabel('Współczynnik korelacji (Pearson)')
plt.xlabel('Czas reakcji na opad')
plt.tight_layout()
plt.savefig('reports/analiza_opoznien/korelacja_opoznien_slupki.png', dpi=300)

# ANALIZA OPÓŹNIEŃ (WYKRESY PUNKTOWE)
fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=True)

# Dzień zero
sns.scatterplot(ax=axes[0], data=final, x='Opad_suma', y='Poziom_wody_max', alpha=0.5, color='blue')
axes[0].set_title('Opad w tym samym dniu')
axes[0].set_xlabel('Suma opadu [mm]')
axes[0].set_ylabel('Maksymalny dobowy poziom wody [m]')

# 1 dzień opóźnienia
sns.scatterplot(ax=axes[1], data=final, x='Opad_lag_1d', y='Poziom_wody_max', alpha=0.5, color='orange')
axes[1].set_title('1 dzień po opadzie')
axes[1].set_xlabel('Suma opadu (wczoraj) [mm]')

# 2 dni opóźnienia
sns.scatterplot(ax=axes[2], data=final, x='Opad_lag_2d', y='Poziom_wody_max', alpha=0.5, color='green')
axes[2].set_title('2 dni po opadzie')
axes[2].set_xlabel('Suma opadu (przedwczoraj) [mm]')

plt.suptitle('Porównanie reakcji rzeki na opad z opóźnieniem', fontsize=16)
plt.tight_layout()
plt.savefig('reports/analiza_opoznien/scatter_opoznienia_panel.png', dpi=300)


#~~~~~~~~~~~~~~~~~~~~~~~ANALIZA STATYSTYCZNA ZALEŻNOŚCI~~~~~~~~~~~~~~~~~~~~~
korelacje = []

for lag in range(15):
    corr = final['Opad_suma'].shift(lag).corr(
        final['Poziom_wody_max']
    )
    korelacje.append(corr)

plt.figure(figsize=(10, 5))
sns.lineplot(x=range(15), y=korelacje, marker='o', color='purple')
plt.title('Korelacja między opadem a poziomem wody w zależności od opóźnienia (0-14 dni)', fontsize=14)
plt.xlabel('Opóźnienie (dni)')
plt.ylabel('Współczynnik korelacji (Pearson)')
plt.tight_layout()
plt.savefig('reports/analiza_opoznien/korelacja_opoznienia.png', dpi=300)

#z wykresu korelacji opóźnienia widać że największy wpływ na poziom wody ma opad z tego samego dnia w którym mierzymy poziom
#Później poziom korelacji spada aż do dnia 6, gdzie wyjątkowo jest wyższy niż w dniu 5.
#Ogólnie poziom korelacji dla każdego dnia jest niski (poniżej 0.3), co sugeruje że opad jest tylko jednym z wielu 
# czynników wpływających na poziom wody, a jego wpływ jest rozproszony w czasie i może być modulowany przez inne czynniki 
# (np. nasycenie gleby, topografia, zarządzanie wodą). Może to także wskazywać na to na istnienie silnej korelacji nieliniowej, 
# przy wartości r równej lub bliskiej 0


cols = [
    'Opad_suma',
    'Opad_72h',
    'Opad_7d',
    'Temp_średnia',
    'Wilgotność_średnia',
    'Ciśnienie_średnia',
    'Poziom_wody_max'
]

corr_matrix = final[cols].corr()

plt.figure(figsize=(8,6))
sns.heatmap(
    corr_matrix,
    annot=True,
    cmap='coolwarm',
    center=0
)
plt.title('Macierz korelacji')
plt.savefig('reports/analiza_opoznien/macierz_korelacji', dpi=300)

# Porównanie korelacji: wszystkie dni vs mokre dni
print("=== Wszystkie dni ===")
for col in ['Opad_suma', 'Opad_72h', 'Opad_7d', 'Opad_lag_1d', 'Opad_lag_2d', 'Opad_lag_3d']:
    r = final[col].corr(final['Poziom_wody_max'])
    print(f"{col:20s}  r = {r:.3f}")

print("\n=== Tylko dni z opadem > 0 ===")
mokre = final[final['Opad_suma'] > 0]
for col in ['Opad_suma', 'Opad_72h', 'Opad_7d']:
    r = mokre[col].corr(mokre['Poziom_wody_max'])
    print(f"{col:20s}  r = {r:.3f}")

# === Wszystkie dni ===
# Opad_suma             r = 0.196
# Opad_72h              r = 0.233
# Opad_7d               r = 0.211
# Opad_lag_1d           r = 0.152
# Opad_lag_2d           r = 0.094
# Opad_lag_3d           r = 0.070

# === Tylko dni z opadem > 0 ===
# Opad_suma             r = 0.120
# Opad_72h              r = 0.177
# Opad_7d               r = 0.164

plt.figure(figsize=(8,6))

sns.regplot(
    data=final,
    x='Opad_72h',
    y='Poziom_wody_max',
    scatter_kws={'alpha':0.3}
)

plt.title('Opad skumulowany 72h a maksymalny poziom wody')
plt.xlabel('Opad 72h [mm]')
plt.ylabel('Poziom wody max [m]')

plt.savefig('reports/regplot_opad72h_woda.png', dpi=300)

#porównanie rozkłdów
q25 = final['Opad_suma'].quantile(0.25)
q75 = final['Opad_suma'].quantile(0.75)

maly_opad = final[final['Opad_suma'] <= q25]['Poziom_wody_max']
duzy_opad = final[final['Opad_suma'] >= q75]['Poziom_wody_max']

plt.figure(figsize=(10,6))
sns.kdeplot(maly_opad, label='Mały opad (<= 25%)', fill=True, alpha=0.5)
sns.kdeplot(duzy_opad, label='Duży opad (>= 75%)', fill=True, alpha=0.5)
plt.title('Porównanie rozkładów poziomu wody przy małym i dużym opadzie')
plt.xlabel('Maksymalny poziom wody [m]')
plt.ylabel('Gęstość')
plt.legend()
plt.savefig('reports/kdeplot_opad_woda.png', dpi=300)

porownanie = pd.DataFrame({
    'Mały opad': maly_opad,
    'Duży opad': duzy_opad
})

sns.boxplot(data=porownanie)
plt.title('Porównanie rozkładów poziomu wody przy małym i dużym opadzie (boxplot)')
plt.ylabel('Maksymalny poziom wody [m]')
plt.savefig('reports/boxplot_opad_woda.png', dpi=300)

#sprawdzenie normalności rozkładów
stat, p = shapiro(maly_opad)
print(p)

stat, p = shapiro(duzy_opad)
print(p)

#9.51234775806283e-13 < 0.05
#3.948999373313471e-09 < 0.05
# oba rozkłady są dalekie od normalności, więc testujemy różnice testem nieparametrycznym
stat, p = mannwhitneyu(maly_opad, duzy_opad)
print(p)
#4.639356621361877e-31 < 0.05
# różnica między grupami jest statystycznie istotna, co sugeruje że poziom wody jest istotnie wyższy w dniach z 
# dużym opadem w porównaniu do dni z małym opadem.

# korelacja Spearmana (nieparametryczna) między opadem a poziomem wody by sprawdzić czy istnieje monotoniczna zależność, nawet jeśli nie jest liniowa
print(final['Opad_suma'].corr(final['Poziom_wody_max'], method='spearman'))
#0.287 - umiarkowana dodatnia korelacja monotoniczna, co sugeruje że wyższe wartości opadu są generalnie związane z wyższymi poziomami wody, ale z dużą zmiennością i innymi czynnikami wpływającymi na poziom wody.

# korelacja Pearsona dla dni z opadem > 0, by sprawdzić liniową zależność tylko w dniach, gdy wystąpił opad
mokre = final[final['Opad_suma'] > 0]
print(mokre['Opad_suma'].corr(mokre['Poziom_wody_max'])) 
#0.12 - słaba dodatnia korelacja liniowa między sumą opadu a poziomem wody w dniach, gdy wystąpił opad, co sugeruje że nawet w tych dniach opad jest tylko jednym z wielu czynników wpływających na poziom wody, a jego wpływ jest rozproszony i może być modulowany przez inne czynniki (np. nasycenie gleby, topografia, zarządzanie wodą).

# regresja liniowa dla Opad_72h i Poziom_wody_max, by sprawdzić czy istnieje liniowa zależność i jaki jest jej współczynnik
X = final[['Opad_72h']]
y = final['Poziom_wody_max']
model = LinearRegression()
model.fit(X, y)
print(model.coef_)
# 0.00632912 - oznacza że każda dodatkowa jednostka opadu skumulowanego z ostatnich 72h jest związana ze średnim wzrostem 
# maksymalnego poziomu wody o około 0.0063 metra, przy założeniu liniowej zależności i braku innych 
# czynników zakłócających. Jednakże, biorąc pod uwagę niską korelację i rozproszenie danych, ten współczynnik 
# powinien być interpretowany ostrożnie, ponieważ opad jest tylko jednym z wielu czynników wpływających na poziom wody.

'''
============================================


        DO TEGO MOMENTU UPORZADKOWANE
                !!!!!!!!!1
            !!!!!!!!!!!!!!!!!!!



===========================================
'''

# --------------------WALIDACJA I BENCHMARK--------------------------


#----------------WALIDACJA I BENCHMARK-------------------
threshold = final['Poziom_wody_max'].quantile(0.90)
final['Epizod_rzeczywisty'] = (final['Poziom_wody_max'] >= threshold).astype(int)

rain_threshold = final['Opad_72h'].quantile(0.90)
final['Alarm'] = (final['Opad_72h'] >= rain_threshold).astype(int)

from sklearn.metrics import confusion_matrix

# confusion matrix
cm = confusion_matrix(
    final['Epizod_rzeczywisty'],
    final['Alarm']
)
plt.figure(figsize=(6, 5))
sns.heatmap(
    cm,
    annot=True,
    fmt='d',
    cmap='Blues',
    xticklabels=['Brak alarmu', 'Alarm'],
    yticklabels=['Brak epizodu', 'Epizod']
)
plt.title('Macierz pomyłek systemu alarmowego')
plt.xlabel('Predykcja')
plt.ylabel('Rzeczywistość')
plt.tight_layout()
plt.savefig('reports/walidacja/confusion_matrix.png',dpi=300)
plt.show()

# recall - jaki procent rzeczywistych momentów krytycznych został wykryty
coverage = recall_score(
    final['Epizod_rzeczywisty'],
    final['Alarm']
)
print("Event coverage:", coverage)

#precision - jaki procent alarmów był trafny
precision = precision_score(
    final['Epizod_rzeczywisty'],
    final['Alarm']
)
print("Precision:", precision)

#
events = (
    final['Epizod_rzeczywisty']
    .ne(final['Epizod_rzeczywisty'].shift())
    .cumsum()
)

events_real = (
    final['Epizod_rzeczywisty']
    .ne(final['Epizod_rzeczywisty'].shift())
    .cumsum()
)

real_events = []

for _, grp in final.groupby(events_real):
    if grp['Epizod_rzeczywisty'].iloc[0] == 1:
        real_events.append({
            'start': grp.index.min(),
            'end': grp.index.max(),
            'peak_time': grp['Poziom_wody_max'].idxmax(),
            'peak_value': grp['Poziom_wody_max'].max()
        })

events_alarm = (
    final['Alarm']
    .ne(final['Alarm'].shift())
    .cumsum()
)

alarm_events = []

for _, grp in final.groupby(events_alarm):
    if grp['Alarm'].iloc[0] == 1:
        alarm_events.append({
            'start': grp.index.min(),
            'end': grp.index.max(),
            'peak_time': grp['Opad_72h'].idxmax(),
            'peak_value': grp['Poziom_wody_max'].max()
        })

onset_errors = []
offset_errors = []
peak_timing_errors = []
peak_height_errors = []
# n = min(len(real_events), len(alarm_events))

# for i in range(len(real_events)):
#     onset_errors.append(
#         (alarm_events[i]['start']
#          - real_events[i]['start']).days
#     )
#     offset_errors.append(
#         (alarm_events[i]['end']
#          - real_events[i]['end']).days
#     )

# mean_onset = np.mean(np.abs(onset_errors))
# mean_offset = np.mean(np.abs(offset_errors))

# print("Średni onset error:", mean_onset)
# print("Średni offset error:", mean_offset)

# peak_timing_errors = []

# for i in range(n):
#     peak_timing_errors.append(abs((alarm_events[i]['peak_time'] - real_events[i]['peak_time']).days))

# mean_peak_timing = np.mean(peak_timing_errors)
# print("Peak timing error:", mean_peak_timing)

# peak_height_errors = []
# for i in range(n):
#     peak_height_errors.append(
#         abs(
#             alarm_events[i]['peak_value']
#             -
#             real_events[i]['peak_value']
#         )
#     )
# mean_peak_height = np.mean(peak_height_errors)
# print("Peak height error:", mean_peak_height)

# n = min(len(real_events), len(alarm_events))
# print(f"real_events: {len(real_events)}, alarm_events: {len(alarm_events)}, n: {n}")

# if n == 0:
#     print("UWAGA: brak dopasowanych par epizodów – pomijam onset/offset/peak timing.")
#     mean_onset = float('nan')
#     mean_offset = float('nan')
#     mean_peak_timing = float('nan')
#     mean_peak_height = float('nan')
# else:
#     onset_errors = []
#     offset_errors = []
#     for i in range(n):
#         onset_errors.append((alarm_events[i]['start'] - real_events[i]['start']).days)
#         offset_errors.append((alarm_events[i]['end'] - real_events[i]['end']).days)
#     mean_onset = np.mean(np.abs(onset_errors))
#     mean_offset = np.mean(np.abs(offset_errors))

#     peak_timing_errors = []
#     for i in range(n):
#         peak_timing_errors.append(abs((alarm_events[i]['peak_time'] - real_events[i]['peak_time']).days))
#     mean_peak_timing = np.mean(peak_timing_errors)

#     peak_height_errors = []
#     for i in range(n):
#         peak_height_errors.append(abs(alarm_events[i]['peak_value'] - real_events[i]['peak_value']))
#     mean_peak_height = np.mean(peak_height_errors)

for real in real_events:
    # szukamy alarmu który nakłada się czasowo z rzeczywistym epizoderm
    # lub zaczyna się w ciągu 7 dni przed/po
    best_alarm = None
    best_dist = float('inf')

    for alarm in alarm_events:
        overlap = (alarm['start'] <= real['end']) and (alarm['end'] >= real['start'])
        dist = abs((alarm['start'] - real['start']).days)

        if overlap or dist <= 7:
            if dist < best_dist:
                best_dist = dist
                best_alarm = alarm

    if best_alarm is not None:
        onset_errors.append((best_alarm['start'] - real['start']).days)
        offset_errors.append((best_alarm['end'] - real['end']).days)
        peak_timing_errors.append(abs((best_alarm['peak_time'] - real['peak_time']).days))
        peak_height_errors.append(abs(best_alarm['peak_value'] - real['peak_value']))

n = len(onset_errors)
if n == 0:
    print("UWAGA: brak dopasowanych par – sprawdź dane wejściowe.")
    mean_onset = float('nan')
    mean_offset = float('nan')
    mean_peak_timing = float('nan')
    mean_peak_height = float('nan')
else:
    mean_onset = np.mean(np.abs(onset_errors))
    mean_offset = np.mean(np.abs(offset_errors))
    mean_peak_timing = np.mean(peak_timing_errors)
    mean_peak_height = np.mean(peak_height_errors)

print("Średni onset error:", mean_onset)
print("Średni offset error:", mean_offset)
print("Peak timing error:", mean_peak_timing)
print("Peak height error:", mean_peak_height)
# -----------------------------------------------------------------

years = sorted(final.index.year.unique())
year_results = []
for year in years:
    tmp = final[final.index.year == year]
    rec = recall_score(
        tmp['Epizod_rzeczywisty'],
        tmp['Alarm']
    )
    prec = precision_score(
        tmp['Epizod_rzeczywisty'],
        tmp['Alarm'],
        zero_division=0
    )
    year_results.append({
        "Rok": year,
        "Recall": rec,
        "Precision": prec
    })
year_results = pd.DataFrame(year_results)
print("\nStabilność rok-po-roku:")
print(year_results)

plt.figure(figsize=(8,5))
plt.plot(
    year_results['Rok'],
    year_results['Recall'],
    marker='o',
    label='Recall'
)
plt.plot(
    year_results['Rok'],
    year_results['Precision'],
    marker='o',
    label='Precision'
)
plt.legend()
plt.title('Stabilność systemu rok-po-roku')
plt.savefig(
    'reports/walidacja/stabilnosc_rok_po_roku.png',
    dpi=300
)

season_results = []

for season in ['wiosna','lato','jesien','zima']:
    tmp = final[final['Pora_roku'] == season]
    rec = recall_score(
        tmp['Epizod_rzeczywisty'],
        tmp['Alarm']
    )
    prec = precision_score(
        tmp['Epizod_rzeczywisty'],
        tmp['Alarm'],
        zero_division=0
    )
    season_results.append({
        'Sezon': season,
        'Recall': rec,
        'Precision': prec
    })
season_results = pd.DataFrame(season_results)
print("\nStabilność sezonowa:")
print(season_results)