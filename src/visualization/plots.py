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

# plot_przebieg_dobowy(final)
# plot_sezonowosc_pory_roku(final)
# plot_sezonowosc_miesiace(final)