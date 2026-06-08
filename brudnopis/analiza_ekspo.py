import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# Słowniki pomocnicze do mapowania stacji na ich kolumny w DataFrame
STACJE_MAX = {
    'Strzyża': 'Poziom_wody_max',
    'Martwa Wisła': 'Martwa_Wisla_max',
    'Port Północny': 'Port_Polnocny_max'
}

STACJE_SREDNIA = {
    'Strzyża': 'Poziom_wody_średnia',
    'Martwa Wisła': 'Martwa_Wisla_średnia',
    'Port Północny': 'Port_Polnocny_średnia'
}


# ==========================================
# 1. SEZONOWOŚĆ POZIOMU WODY
# ==========================================

def plot_przebieg_dobowy(df, base_dir='../reports/analiza_ekspolaracyjna/sezonowosc_poziomu_wody/plots'):
    os.makedirs(base_dir, exist_ok=True)
    fig, axes = plt.subplots(3, 1, figsize=(15, 12), sharex=True)

    for ax, (nazwa, col_max) in zip(axes, STACJE_MAX.items()):
        col_srednia = STACJE_SREDNIA[nazwa]
        ax.plot(df.index, df[col_srednia], label='Średni dobowy', color='teal', alpha=0.7)
        ax.plot(df.index, df[col_max], label='Maksymalny dobowy', color='red', alpha=0.5)
        ax.set_title(f'Przebieg poziomu wody: {nazwa}', fontsize=12)
        ax.set_ylabel('Poziom [m]')
        ax.legend()

    axes[-1].set_xlabel('Data')
    plt.suptitle('Przebieg dobowy poziomu wody w latach 2021-2025', fontsize=16, y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(base_dir, 'przebieg_poziomu_wody_dobowo.png'), dpi=300)
    plt.close()


def plot_sezonowosc_pory_roku(df, base_dir='../reports/analiza_ekspolaracyjna/sezonowosc_poziomu_wody/plots'):
    os.makedirs(base_dir, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    for ax, (nazwa, col_srednia) in zip(axes, STACJE_SREDNIA.items()):
        # Zmieniono 'Pora_roku' na 'sezon' aby pasowało do pliku CSV
        sns.boxplot(ax=ax, data=df, x='sezon', y=col_srednia,
                    hue='sezon', order=['wiosna', 'lato', 'jesien', 'zima'],
                    palette='pastel', legend=False)
        ax.set_title(f'{nazwa}', fontsize=12)
        ax.set_ylabel('Średni poziom [m]')
        ax.set_xlabel('Pora roku')

    plt.suptitle('Rozkład średniego dobowego poziomu wody wg pór roku', fontsize=16, y=1.05)
    plt.tight_layout()
    plt.savefig(os.path.join(base_dir, 'sezonowosc_wg_por_roku.png'), dpi=300)
    plt.close()


def plot_sezonowosc_miesiace(df, base_dir='../reports/analiza_ekspolaracyjna/sezonowosc_poziomu_wody/plots'):
    os.makedirs(base_dir, exist_ok=True)
    fig, axes = plt.subplots(3, 1, figsize=(14, 15), sharex=True)

    for ax, (nazwa, col_srednia) in zip(axes, STACJE_SREDNIA.items()):
        # Zmieniono 'Miesiąc' na 'month' aby pasowało do pliku CSV
        sns.boxplot(ax=ax, data=df, x='month', y=col_srednia,
                    hue='month', palette='Set3', legend=False)
        ax.set_title(f'{nazwa}', fontsize=12)
        ax.set_ylabel('Średni poziom [m]')

    axes[-1].set_xlabel('Miesiąc (1=Styczeń, 12=Grudzień)')
    plt.suptitle('Rozkład średniego dobowego poziomu wody w poszczególnych miesiącach', fontsize=16, y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(base_dir, 'sezonowosc_wg_miesiecy.png'), dpi=300)
    plt.close()


# ==========================================
# 2. ZALEŻNOŚCI METEO
# ==========================================

def plot_zaleznosc_opad_woda(df, base_dir='../reports/analiza_ekspolaracyjna/zaleznosci_poziomu_wody/plots'):
    os.makedirs(base_dir, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    for ax, (nazwa, col_max) in zip(axes, STACJE_MAX.items()):
        sns.scatterplot(ax=ax, data=df, x='Opad_72h', y=col_max, alpha=0.5, color='royalblue')
        ax.set_title(f'{nazwa}', fontsize=12)
        ax.set_xlabel('Opad z 3 dni [mm]')
        ax.set_ylabel('Max poziom wody [m]')

    plt.suptitle('Zależność ogólna: Opad skumulowany (72h) a max poziom wody', fontsize=16, y=1.05)
    plt.tight_layout()
    plt.savefig(os.path.join(base_dir, 'zaleznosc_opad_woda_ogolnie.png'), dpi=300)
    plt.close()


def plot_zaleznosc_opad_woda_sezony(df, base_dir='../reports/analiza_ekspolaracyjna/zaleznosci_poziomu_wody/plots'):
    os.makedirs(base_dir, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    for ax, (nazwa, col_max) in zip(axes, STACJE_MAX.items()):
        sns.scatterplot(ax=ax, data=df, x='Opad_72h', y=col_max, hue='sezon',
                        palette='bright', alpha=0.7, s=40)
        ax.set_title(f'{nazwa}', fontsize=12)
        ax.set_xlabel('Opad z 3 dni [mm]')
        ax.set_ylabel('Max poziom wody [m]')
        ax.legend()

    plt.suptitle('Opad skumulowany a poziom wody w różnych porach roku', fontsize=16, y=1.05)
    plt.tight_layout()
    plt.savefig(os.path.join(base_dir, 'zaleznosc_opad_woda_sezony.png'), dpi=300)
    plt.close()


def plot_zaleznosc_cisnienie_woda(df, base_dir='../reports/analiza_ekspolaracyjna/zaleznosci_poziomu_wody/plots'):
    os.makedirs(base_dir, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    for ax, (nazwa, col_max) in zip(axes, STACJE_MAX.items()):
        sns.scatterplot(ax=ax, data=df, x='Ciśnienie_delta_1d', y=col_max, hue='sezon',
                        palette='bright', alpha=0.7, s=40)
        ax.axvline(0, color='grey', linestyle='--')
        ax.set_title(f'{nazwa}', fontsize=12)
        ax.set_xlabel('Zmiana ciśnienia (1d) [hPa]')
        ax.set_ylabel('Max poziom wody [m]')
        ax.legend()

    plt.suptitle('Wpływ zmiany ciśnienia (proxy wiatru/sztormu) na max poziom wody', fontsize=16, y=1.05)
    plt.tight_layout()
    plt.savefig(os.path.join(base_dir, 'zaleznosc_cisnienie_woda_sezony.png'), dpi=300)
    plt.close()


# ==========================================
# 3. ANALIZA OPÓŹNIEŃ (LAGS)
# ==========================================

def plot_korelacja_opoznien(df, base_dir='../reports/analiza_ekspolaracyjna/analiza_opoznien/plots'):
    os.makedirs(base_dir, exist_ok=True)
    lagi_opadu = ['Opad_suma', 'Opad_lag_1d', 'Opad_lag_2d', 'Opad_lag_3d']
    nazwy_lagow = ['W tym samym dniu', '1 dzień po', '2 dni po', '3 dni po']

    dane_plot = []
    for lag_col, lag_nazwa in zip(lagi_opadu, nazwy_lagow):
        for stacja_nazwa, stacja_col in STACJE_MAX.items():
            korelacja = df[lag_col].corr(df[stacja_col])
            dane_plot.append({'Lag': lag_nazwa, 'Stacja': stacja_nazwa, 'Korelacja': korelacja})

    df_corr = pd.DataFrame(dane_plot)

    plt.figure(figsize=(10, 6))
    sns.barplot(data=df_corr, x='Lag', y='Korelacja', hue='Stacja', palette='viridis')
    plt.title('Korelacja (Pearson) między opadem a wodą w zależności od opóźnienia', fontsize=14)
    plt.ylabel('Współczynnik korelacji')
    plt.xlabel('Czas reakcji na opad')
    plt.tight_layout()
    plt.savefig(os.path.join(base_dir, 'korelacja_opoznien_slupki.png'), dpi=300)
    plt.close()


def plot_scatter_opoznienia(df, base_dir='../reports/analiza_ekspolaracyjna/analiza_opoznien/plots'):
    os.makedirs(base_dir, exist_ok=True)
    fig, axes = plt.subplots(3, 3, figsize=(16, 12), sharex=True, sharey='row')

    lagi = [
        ('Opad_suma', 'W tym samym dniu', 'blue'),
        ('Opad_lag_1d', '1 dzień po opadzie', 'orange'),
        ('Opad_lag_2d', '2 dni po opadzie', 'green')
    ]

    for wiersz, (nazwa_stacji, col_max) in enumerate(STACJE_MAX.items()):
        for kolumna, (kolumna_lag, tytul_lag, kolor) in enumerate(lagi):
            ax = axes[wiersz, kolumna]
            sns.scatterplot(ax=ax, data=df, x=kolumna_lag, y=col_max, alpha=0.5, color=kolor)

            if wiersz == 0:
                ax.set_title(tytul_lag)

            if kolumna == 0:
                ax.set_ylabel(f'{nazwa_stacji}\nMax poziom [m]')
            else:
                ax.set_ylabel('')

            if wiersz == 2:
                ax.set_xlabel('Suma opadu [mm]')
            else:
                ax.set_xlabel('')

    plt.suptitle('Reakcja 3 punktów pomiarowych na opad z opóźnieniem', fontsize=16, y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(base_dir, 'scatter_opoznienia_panel.png'), dpi=300)
    plt.close()


# ==========================================
# WYWOŁANIE FUNKCJI
# ==========================================
if __name__ == "__main__":
    sciezka_do_pliku = '../data/processed/final.csv'

    if os.path.exists(sciezka_do_pliku):
        print("Wczytywanie danych...")
        final = pd.read_csv(
            sciezka_do_pliku,
            parse_dates=['Data'],
            index_col='Data'
        )

        # USUWANIE ANOMALII Z PORTU PÓŁNOCNEGO
        print("Filtrowanie błędów aparatury...")
        final.loc[final['Port_Polnocny_max'] < 4.0, 'Port_Polnocny_max'] = np.nan
        final.loc[final['Port_Polnocny_średnia'] < 4.0, 'Port_Polnocny_średnia'] = np.nan

        print("Generowanie i zapisywanie plików do folderów...")

        # 1. Sezonowość
        plot_przebieg_dobowy(final)
        plot_sezonowosc_pory_roku(final)
        plot_sezonowosc_miesiace(final)

        # 2. Zależności meteo
        plot_zaleznosc_opad_woda(final)
        plot_zaleznosc_opad_woda_sezony(final)
        plot_zaleznosc_cisnienie_woda(final)

        # 3. Analiza opóźnień
        plot_korelacja_opoznien(final)
        plot_scatter_opoznienia(final)

        print("Gotowe! Wszystkie wykresy zapisane w folderze ../reports/analiza_ekspolaracyjna/")
    else:
        print(f"Błąd: Nie znaleziono pliku {sciezka_do_pliku}.")