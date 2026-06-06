# tu beda funkcje do generowania wykresów -> wywoływane w notebookach

import matplotlib.pyplot as plt
import seaborn as sns


def plot_przebieg_dobowy(df):
    """Generuje i zapisuje wykres liniowy przebiegu poziomu wody w czasie."""
    plt.figure(figsize=(15, 5))
    plt.plot(df.index, df['Poziom_wody_średnia'], label='Średni dobowy poziom', color='teal', alpha=0.7)
    plt.plot(df.index, df['Poziom_wody_max'], label='Maksymalny dobowy poziom', color='red', alpha=0.5)
    plt.title('Przebieg poziomu wody na rzece Strzyża w latach 2021-2025', fontsize=14)
    plt.ylabel('Poziom wody [m]')
    plt.xlabel('Data')
    plt.legend()
    plt.tight_layout()

    plt.show()


def plot_sezonowosc_pory_roku(df):
    """Generuje i zapisuje wykres pudełkowy poziomu wody z podziałem na pory roku."""
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df, x='Pora_roku', y='Poziom_wody_średnia',
                hue='Pora_roku', order=['wiosna', 'lato', 'jesien', 'zima'],
                palette='pastel', legend=False)
    plt.title('Rozkład średniego dobowego poziomu wody w zależności od pory roku', fontsize=14)
    plt.ylabel('Średni poziom wody [m]')
    plt.xlabel('Pora roku')
    plt.tight_layout()

    plt.show()


def plot_sezonowosc_miesiace(df):
    """Generuje i zapisuje wykres pudełkowy poziomu wody z podziałem na poszczególne miesiące."""
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=df, x='Miesiąc', y='Poziom_wody_średnia',
                hue='Miesiąc', palette='Set3', legend=False)
    plt.title('Rozkład średniego dobowego poziomu wody w poszczególnych miesiącach', fontsize=14)
    plt.ylabel('Średni poziom wody [m]')
    plt.xlabel('Miesiąc (1=Styczeń, 12=Grudzień)')
    plt.tight_layout()

    plt.show()


def plot_zaleznosc_opad_woda(df):
    """Generuje wykres punktowy zależności poziomu wody od opadu (bez podziału na sezony)."""
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x='Opad_72h', y='Poziom_wody_max', alpha=0.5, color='royalblue')
    plt.title('Zależność ogólna: Opad skumulowany (72h) a maksymalny poziom wody', fontsize=14)
    plt.xlabel('Opad skumulowany z 3 dni [mm]')
    plt.ylabel('Maksymalny dobowy poziom wody [m]')
    plt.tight_layout()

    plt.show()


def plot_zaleznosc_opad_woda_sezony(df):
    """Generuje wykres punktowy poziomu wody od opadu z kolorowaniem po porach roku."""
    plt.figure(figsize=(12, 7))
    sns.scatterplot(data=df, x='Opad_72h', y='Poziom_wody_max', hue='Pora_roku',
                    palette='bright', alpha=0.7, s=60)
    plt.title('Zależność: Opad skumulowany a poziom wody w różnych porach roku', fontsize=14)
    plt.xlabel('Opad skumulowany z 3 dni [mm]')
    plt.ylabel('Maksymalny dobowy poziom wody [m]')
    plt.legend(title='Pora roku')
    plt.tight_layout()

    plt.show()


def plot_zaleznosc_cisnienie_woda(df):
    """Generuje wykres punktowy wpływu zmiany ciśnienia (proxy wiatru) na poziom wody."""
    plt.figure(figsize=(12, 7))
    sns.scatterplot(data=df, x='Ciśnienie_delta_1d', y='Poziom_wody_max', hue='Pora_roku',
                    palette='bright', alpha=0.7, s=60)
    plt.title('Wpływ zmiany ciśnienia (proxy wiatru/sztormu) na poziom wody', fontsize=14)
    plt.xlabel('Zmiana ciśnienia względem poprzedniego dnia [hPa] (Wartości ujemne = spadek/niż)')
    plt.ylabel('Maksymalny dobowy poziom wody [m]')
    plt.axvline(0, color='grey', linestyle='--')
    plt.legend(title='Pora roku')
    plt.tight_layout()

    plt.show()

def plot_korelacja_opoznien(df):
    """Generuje wykres słupkowy korelacji opadów z poziomem wody w różnych opóźnieniach."""
    lagi_opadu = ['Opad_suma', 'Opad_lag_1d', 'Opad_lag_2d', 'Opad_lag_3d']
    korelacje = df[lagi_opadu].apply(lambda x: x.corr(df['Poziom_wody_max']))
    nazwy_lagow = ['W tym samym dniu', '1 dzień po', '2 dni po', '3 dni po']

    plt.figure(figsize=(8, 5))
    sns.barplot(x=nazwy_lagow, y=korelacje.values, hue=nazwy_lagow, palette='viridis', legend=False)
    plt.title('Korelacja między opadem a poziomem wody w zależności od opóźnienia', fontsize=14)
    plt.ylabel('Współczynnik korelacji (Pearson)')
    plt.xlabel('Czas reakcji na opad')
    plt.tight_layout()

    plt.show()

def plot_scatter_opoznienia(df):
    """Generuje panel trzech wykresów punktowych dla lagów opadowych (0, 1 i 2 dni)."""
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=True)

    sns.scatterplot(ax=axes[0], data=df, x='Opad_suma', y='Poziom_wody_max', alpha=0.5, color='blue')
    axes[0].set_title('Opad w tym samym dniu')
    axes[0].set_xlabel('Suma opadu [mm]')
    axes[0].set_ylabel('Maksymalny dobowy poziom wody [m]')

    sns.scatterplot(ax=axes[1], data=df, x='Opad_lag_1d', y='Poziom_wody_max', alpha=0.5, color='orange')
    axes[1].set_title('1 dzień po opadzie')
    axes[1].set_xlabel('Suma opadu (wczoraj) [mm]')

    sns.scatterplot(ax=axes[2], data=df, x='Opad_lag_2d', y='Poziom_wody_max', alpha=0.5, color='green')
    axes[2].set_title('2 dni po opadzie')
    axes[2].set_xlabel('Suma opadu (przedwczoraj) [mm]')

    plt.suptitle('Porównanie reakcji rzeki na opad z opóźnieniem', fontsize=16)
    plt.tight_layout()

    plt.show()

# plot_przebieg_dobowy(final)
# plot_sezonowosc_pory_roku(final)
# plot_sezonowosc_miesiace(final)
# plot_zaleznosc_opad_woda(final)
# plot_zaleznosc_opad_woda_sezony(final)
# plot_zaleznosc_cisnienie_woda(final)