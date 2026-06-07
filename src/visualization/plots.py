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

STACJE = {
    'Strzyża':       'Poziom_wody_max',
    'Martwa Wisła':  'Martwa_Wisla_max',
    'Port Północny': 'Port_Polnocny_max',
}


# Wykres liniowy korelacji opadu z poziomem wody dla lagów 0-14 dni
# dla wszystkich trzech stacji jednocześnie
def plot_korelacja_lag_14dni_wszystkie(df):
    korelacje = {nazwa: [] for nazwa in STACJE}
    markers = {'Strzyża': 'o', 'Martwa Wisła': 's', 'Port Północny': '^'}
    for lag in range(15):
        opad_shifted = df['Opad_suma'].shift(lag)
        for nazwa, col in STACJE.items():
            korelacje[nazwa].append(opad_shifted.corr(df[col]))

    plt.figure(figsize=(10, 5))
    for nazwa, vals in korelacje.items():
        sns.lineplot(x=range(15), y=vals, marker=markers[nazwa], label=nazwa)
    plt.title('Korelacja opadu z poziomem wody w zależności od opóźnienia', fontsize=14)
    plt.xlabel('Opóźnienie (dni)')
    plt.ylabel('Współczynnik korelacji (Pearson)')
    plt.legend()
    plt.tight_layout()
    plt.show()



# Heatmapa korelacji dla wszystkich stacji + zmiennych meteo
def plot_macierz_korelacji_wszystkie(df):
    cols = [
        'Opad_suma', 'Opad_72h', 'Opad_7d',
        'Temp_średnia', 'Wilgotność_średnia', 'Ciśnienie_średnia',
        'Martwa_Wisla_średnia', 'Martwa_Wisla_max',
        'Port_Polnocny_średnia', 'Port_Polnocny_max',
        'Poziom_wody_max',
    ]
    plt.figure(figsize=(10, 8))
    sns.heatmap(df[cols].corr(), annot=True, fmt='.2f', cmap='coolwarm', center=0)
    plt.title('Macierz korelacji')
    plt.tight_layout()
    plt.show()


# Scatter: korelacja między stacjami śródlądowymi a Portem Północnym
def plot_scatter_stacje_port(df):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].scatter(df['Martwa_Wisla_max'], df['Port_Polnocny_max'],
                    alpha=0.2, s=5, color='steelblue')
    axes[0].set_xlabel('Martwa Wisła — poziom wody max [m]')
    axes[0].set_ylabel('Port Północny — poziom wody max [m]')
    axes[0].set_title('Martwa Wisła vs. Port Północny (r = 0.42)')

    axes[1].scatter(df['Poziom_wody_max'], df['Port_Polnocny_max'],
                    alpha=0.2, s=5, color='darkorange')
    axes[1].set_xlabel('Strzyża — poziom wody max [m]')
    axes[1].set_ylabel('Port Północny — poziom wody max [m]')
    axes[1].set_title('Strzyża vs. Port Północny (r = 0.44)')

    plt.suptitle('Zależność między stacjami śródlądowymi a Portem Północnym', y=1.02)
    plt.tight_layout()
    plt.show()

# Regresja liniowa Opad_72h vs poziom wody dla wszystkich stacji
def plot_regresja_opad_woda_wszystkie(df):
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    for ax, (nazwa, col) in zip(axes, STACJE.items()):
        sns.regplot(data=df, x='Opad_72h', y=col,
                    scatter_kws={'alpha': 0.2}, ax=ax)
        ax.set_title(f'Opad 72h a poziom wody — {nazwa}')
        ax.set_xlabel('Opad 72h [mm]')
        ax.set_ylabel('Poziom wody max [m]')
    plt.tight_layout()
    plt.show()

# KDE rozkładu poziomu wody przy małym i dużym opadzie dla wszystkich stacji
def plot_kde_opad_grupy_wszystkie(df):
    q25 = df['Opad_suma'].quantile(0.25)
    q75 = df['Opad_suma'].quantile(0.75)
    maly = df[df['Opad_suma'] <= q25]
    duzy = df[df['Opad_suma'] >= q75]

    fig, axes = plt.subplots(1, 3, figsize=(18, 6), sharey=False)
    for ax, (nazwa, col) in zip(axes, STACJE.items()):
        sns.kdeplot(maly[col], ax=ax, label='Mały opad (≤25%)', fill=True, alpha=0.5)
        sns.kdeplot(duzy[col], ax=ax, label='Duży opad (≥75%)', fill=True, alpha=0.5)
        ax.set_title(nazwa)
        ax.set_xlabel('Poziom wody [m]')
        ax.set_ylabel('Gęstość')
        ax.legend()
    plt.tight_layout()
    plt.show()

# Boxplot poziomu wody przy małym i dużym opadzie dla wszystkich stacji
def plot_boxplot_opad_grupy_wszystkie(df):
    q25 = df['Opad_suma'].quantile(0.25)
    q75 = df['Opad_suma'].quantile(0.75)
    maly = df[df['Opad_suma'] <= q25]
    duzy = df[df['Opad_suma'] >= q75]

    dane_box = pd.concat([
        maly[list(STACJE.values())].rename(columns={v: f'{k} - mały' for k, v in STACJE.items()}),
        duzy[list(STACJE.values())].rename(columns={v: f'{k} - duży' for k, v in STACJE.items()}),
    ], axis=0)

    plt.figure(figsize=(14, 6))
    sns.boxplot(data=dane_box)
    plt.xticks(rotation=30, ha='right')
    plt.ylabel('Poziom wody [m]')
    plt.title('Poziom wody przy małych i dużych opadach — wszystkie stacje')
    plt.tight_layout()
    plt.show()

# Heatmapa korelacji Port Północny + wiatr + ciśnienie
def plot_macierz_port_wiatr_cisnienie(df):
    predyktory_port = [
        'Ciśnienie_średnia', 'Ciśnienie_min', 'Ciśnienie_ampl',
        'Ciśnienie_delta_1d', 'Ciśnienie_delta_2d', 'Ciśnienie_delta_3d',
        'Ciśnienie_trend_3d', 'Ciśnienie_trend_7d',
        'Wiatr_siła_proxy', 'Wiatr_sin_proxy', 'Wiatr_cos_proxy',
        'Port_Polnocny_max'
    ]
    plt.figure(figsize=(12, 10))
    sns.heatmap(df[predyktory_port].corr(), annot=True, fmt='.2f',
                cmap='coolwarm', center=0)
    plt.title('Macierz korelacji — Port Północny: wiatr i ciśnienie')
    plt.tight_layout()
    plt.show()

# Scatter: siła wiatru i zmiana ciśnienia vs poziom wody w Porcie Północnym
def plot_scatter_port_wiatr_cisnienie(df):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].scatter(df['Wiatr_siła_proxy'], df['Port_Polnocny_max'],
                    alpha=0.2, s=5, color='steelblue')
    axes[0].set_xlabel('Siła wiatru (proxy)')
    axes[0].set_ylabel('Port Północny — poziom wody max [m]')
    axes[0].set_title('Siła wiatru vs. poziom wody w porcie')

    axes[1].scatter(df['Ciśnienie_delta_1d'], df['Port_Polnocny_max'],
                    alpha=0.2, s=5, color='darkorange')
    axes[1].set_xlabel('Zmiana ciśnienia 1d [hPa]')
    axes[1].set_ylabel('Port Północny — poziom wody max [m]')
    axes[1].set_title('Dzienna zmiana ciśnienia vs. poziom wody w porcie')

    plt.tight_layout()
    plt.show()

# Boxplot poziomu wody w Porcie Północnym według sektora wiatru
def plot_boxplot_port_sektor_wiatru(df):
    plt.figure(figsize=(10, 5))
    kolejnosc = sorted(df['Wiatr_sektor_proxy'].dropna().unique())
    sns.boxplot(data=df, x='Wiatr_sektor_proxy', y='Port_Polnocny_max', order=kolejnosc)
    plt.title('Poziom wody w Porcie Północnym według sektora wiatru')
    plt.xlabel('Sektor wiatru')
    plt.ylabel('Poziom wody max [m]')
    plt.tight_layout()
    plt.show()

# Boxplot ciśnienia i siły wiatru według reżimu hydrologicznego
# Reżimy: cofka (P10), normalny, spiętrzenie (P90)
def plot_boxplot_port_rezim_atmosfera(df):
    prog_cofka = df['Port_Polnocny_max'].quantile(0.10)
    prog_spietzenie = df['Port_Polnocny_max'].quantile(0.90)

    cofka      = df[df['Port_Polnocny_max'] <= prog_cofka]
    spietzenie = df[df['Port_Polnocny_max'] >= prog_spietzenie]
    normalny   = df[(df['Port_Polnocny_max'] > prog_cofka) &
                    (df['Port_Polnocny_max'] < prog_spietzenie)]

    def do_long(col):
        return pd.concat([
            cofka[[col]].assign(Reżim='Cofka'),
            normalny[[col]].assign(Reżim='Normalny'),
            spietzenie[[col]].assign(Reżim='Spiętrzenie'),
        ], ignore_index=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sns.boxplot(data=do_long('Ciśnienie_średnia'), x='Reżim', y='Ciśnienie_średnia', ax=axes[0])
    axes[0].set_title('Ciśnienie atmosferyczne według reżimu')
    axes[0].set_ylabel('Ciśnienie [hPa]')

    sns.boxplot(data=do_long('Wiatr_siła_proxy'), x='Reżim', y='Wiatr_siła_proxy', ax=axes[1])
    axes[1].set_title('Siła wiatru według reżimu')
    axes[1].set_ylabel('Siła wiatru (proxy)')

    plt.suptitle('Warunki atmosferyczne w trzech reżimach Portu Północnego')
    plt.tight_layout()
    plt.show()