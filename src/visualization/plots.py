# tu beda funkcje do generowania wykresów -> wywoływane w notebookach

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

#Generuje i zapisuje wykres liniowy przebiegu poziomu wody w czasie.
def plot_przebieg_dobowy(df):
    plt.figure(figsize=(15, 5))
    plt.plot(df.index, df['Poziom_wody_średnia'], label='Średni dobowy poziom', color='teal', alpha=0.7)
    plt.plot(df.index, df['Poziom_wody_max'], label='Maksymalny dobowy poziom', color='red', alpha=0.5)
    plt.title('Przebieg poziomu wody na rzece Strzyża w latach 2021-2025', fontsize=14)
    plt.ylabel('Poziom wody [m]')
    plt.xlabel('Data')
    plt.legend()
    plt.tight_layout()

    plt.show()

#Generuje i zapisuje wykres pudełkowy poziomu wody z podziałem na pory roku.
def plot_sezonowosc_pory_roku(df):
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df, x='sezon', y='Poziom_wody_średnia',
                hue='sezon', order=['wiosna', 'lato', 'jesien', 'zima'],
                palette='pastel', legend=False)
    plt.title('Rozkład średniego dobowego poziomu wody w zależności od pory roku', fontsize=14)
    plt.ylabel('Średni poziom wody [m]')
    plt.xlabel('Pora roku')
    plt.tight_layout()

    plt.show()

#Generuje i zapisuje wykres pudełkowy poziomu wody z podziałem na poszczególne miesiące.
def plot_sezonowosc_miesiace(df):
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=df, x='month', y='Poziom_wody_średnia',
                hue='month', palette='Set3', legend=False)
    plt.title('Rozkład średniego dobowego poziomu wody w poszczególnych miesiącach', fontsize=14)
    plt.ylabel('Średni poziom wody [m]')
    plt.xlabel('Miesiąc (1=Styczeń, 12=Grudzień)')
    plt.tight_layout()

    plt.show()

#Generuje wykres punktowy zależności poziomu wody od opadu (bez podziału na sezony).
def plot_zaleznosc_opad_woda(df):
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x='Opad_72h', y='Poziom_wody_max', alpha=0.5, color='royalblue')
    plt.title('Zależność ogólna: Opad skumulowany (72h) a maksymalny poziom wody', fontsize=14)
    plt.xlabel('Opad skumulowany z 3 dni [mm]')
    plt.ylabel('Maksymalny dobowy poziom wody [m]')
    plt.tight_layout()

    plt.show()

#Generuje wykres punktowy poziomu wody od opadu z kolorowaniem po porach roku.
def plot_zaleznosc_opad_woda_sezony(df):
    plt.figure(figsize=(12, 7))
    sns.scatterplot(data=df, x='Opad_72h', y='Poziom_wody_max', hue='sezon',
                    palette='bright', alpha=0.7, s=60)
    plt.title('Zależność: Opad skumulowany a poziom wody w różnych porach roku', fontsize=14)
    plt.xlabel('Opad skumulowany z 3 dni [mm]')
    plt.ylabel('Maksymalny dobowy poziom wody [m]')
    plt.legend(title='Pora roku')
    plt.tight_layout()

    plt.show()

#Generuje wykres punktowy wpływu zmiany ciśnienia (proxy wiatru) na poziom wody.
def plot_zaleznosc_cisnienie_woda(df):
    plt.figure(figsize=(12, 7))
    sns.scatterplot(data=df, x='Ciśnienie_delta_1d', y='Poziom_wody_max', hue='sezon',
                    palette='bright', alpha=0.7, s=60)
    plt.title('Wpływ zmiany ciśnienia (proxy wiatru/sztormu) na poziom wody', fontsize=14)
    plt.xlabel('Zmiana ciśnienia względem poprzedniego dnia [hPa] (Wartości ujemne = spadek/niż)')
    plt.ylabel('Maksymalny dobowy poziom wody [m]')
    plt.axvline(0, color='grey', linestyle='--')
    plt.legend(title='Pora roku')
    plt.tight_layout()

    plt.show()

#Generuje wykres słupkowy korelacji opadów z poziomem wody w różnych opóźnieniach.
def plot_korelacja_opoznien(df):
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

#Generuje panel trzech wykresów punktowych dla lagów opadowych (0, 1 i 2 dni).
def plot_scatter_opoznienia(df):
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


#Wykres liniowy korelacji opadu z poziomem wody dla lagów 0-14 dni.
def plot_korelacja_lag_14dni(df):
    korelacje = []

    for lag in range(15):
        corr = df['Opad_suma'].shift(lag).corr(df['Poziom_wody_max'])
        korelacje.append(corr)

    plt.figure(figsize=(10, 5))
    sns.lineplot(x=range(15), y=korelacje, marker='o', color='purple')
    plt.title('Korelacja między opadem a poziomem wody w zależności od opóźnienia (0-14 dni)', fontsize=14)
    plt.xlabel('Opóźnienie (dni)')
    plt.ylabel('Współczynnik korelacji (Pearson)')
    plt.tight_layout()
    plt.show()


#Heatmapa korelacji między zmiennymi meteorologicznymi a poziomem wody.
def plot_macierz_korelacji(df):
    cols = [
        'Opad_suma',
        'Opad_72h',
        'Opad_7d',
        'Temp_średnia',
        'Wilgotność_średnia',
        'Ciśnienie_średnia',
        'Poziom_wody_max'
    ]
    corr_matrix = df[cols].corr()

    plt.figure(figsize=(10, 8))
    sns.heatmap(
        corr_matrix,
        annot=True,
        fmt='.2f',
        cmap='coolwarm',
        center=0
    )
    plt.title('Macierz korelacji',fontsize=14)
    plt.tight_layout()
    plt.show()


#Wykres regresji liniowej Opad_72h vs poziom wody.
def plot_regresja_opad_woda(df):
    plt.figure(figsize=(10, 6))

    sns.regplot(
        data=df,
        x='Opad_72h',
        y='Poziom_wody_max',
        scatter_kws={'alpha': 0.3}
    )

    plt.title('Opad skumulowany 72h a maksymalny poziom wody')
    plt.xlabel('Opad 72h [mm]')
    plt.ylabel('Poziom wody max [m]')

    plt.tight_layout()
    plt.show()

#KDE rozkładu poziomu wody przy małym i dużym opadzie.
def plot_kde_opad_grupy(df):
    q25 = df['Opad_suma'].quantile(0.25)
    q75 = df['Opad_suma'].quantile(0.75)

    maly_opad = df[df['Opad_suma'] <= q25]['Poziom_wody_max']
    duzy_opad = df[df['Opad_suma'] >= q75]['Poziom_wody_max']

    plt.figure(figsize=(10, 6))
    sns.kdeplot(maly_opad, label='Mały opad (<= 25%)', fill=True, alpha=0.4)
    sns.kdeplot(duzy_opad, label='Duży opad (>= 75%)', fill=True, alpha=0.4)
    plt.title('Porównanie rozkładów poziomu wody przy małym i dużym opadzie', fontsize=14)
    plt.xlabel('Maksymalny poziom wody [m]')
    plt.ylabel('Gęstość')
    plt.legend()
    plt.tight_layout()
    plt.show()

#Boxplot poziomu wody przy małym i dużym opadzie.
def plot_boxplot_opad_grupy(df):
    q25 = df['Opad_suma'].quantile(0.25)
    q75 = df['Opad_suma'].quantile(0.75)

    maly_opad = df[df['Opad_suma'] <= q25]['Poziom_wody_max']
    duzy_opad = df[df['Opad_suma'] >= q75]['Poziom_wody_max']

    min_len = min(len(maly_opad), len(duzy_opad))

    porownanie = pd.DataFrame({
        'Mały opad (<= 25%)': maly_opad[:min_len],
        'Duży opad (>= 75%)': duzy_opad[:min_len]
    })

    plt.figure(figsize=(10, 6))
    sns.boxplot(data=porownanie)
    plt.title('Porównanie rozkładów poziomu wody przy małym i dużym opadzie')
    plt.ylabel('Maksymalny poziom wody [m]')
    plt.tight_layout()
    plt.show()