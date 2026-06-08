# tu beda funkcje do generowania wykresów -> wywoływane w notebookach

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

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

#Generuje i zapisuje wykres liniowy przebiegu poziomu wody w czasie.
def plot_przebieg_dobowy(df):
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

    plt.show()

#Generuje i zapisuje wykres pudełkowy poziomu wody z podziałem na pory roku.
def plot_sezonowosc_pory_roku(df):
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

    plt.show()

#Generuje i zapisuje wykres pudełkowy poziomu wody z podziałem na poszczególne miesiące.
def plot_sezonowosc_miesiace(df):
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

    plt.show()

#Generuje wykres punktowy zależności poziomu wody od opadu (bez podziału na sezony).
def plot_zaleznosc_opad_woda(df):
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    for ax, (nazwa, col_max) in zip(axes, STACJE_MAX.items()):
        sns.scatterplot(ax=ax, data=df, x='Opad_72h', y=col_max, alpha=0.5, color='royalblue')
        ax.set_title(f'{nazwa}', fontsize=12)
        ax.set_xlabel('Opad z 3 dni [mm]')
        ax.set_ylabel('Max poziom wody [m]')

    plt.suptitle('Zależność ogólna: Opad skumulowany (72h) a max poziom wody', fontsize=16, y=1.05)
    plt.tight_layout()

    plt.show()

#Generuje wykres punktowy poziomu wody od opadu z kolorowaniem po porach roku.
def plot_zaleznosc_opad_woda_sezony(df):
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

    plt.show()

#Generuje wykres punktowy wpływu zmiany ciśnienia (proxy wiatru) na poziom wody.
def plot_zaleznosc_cisnienie_woda(df):
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

    plt.show()

#Generuje wykres słupkowy korelacji opadów z poziomem wody w różnych opóźnieniach.
def plot_korelacja_opoznien(df):
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

    plt.show()

#Generuje panel trzech wykresów punktowych dla lagów opadowych (0, 1 i 2 dni).
def plot_scatter_opoznienia(df):
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

    plt.show()

# 1. Sezonowość
# plot_przebieg_dobowy(final)
# plot_sezonowosc_pory_roku(final)
# plot_sezonowosc_miesiace(final)
#
# # 2. Zależności meteo
# plot_zaleznosc_opad_woda(final)
# plot_zaleznosc_opad_woda_sezony(final)
# plot_zaleznosc_cisnienie_woda(final)
#
# # 3. Analiza opóźnień
# plot_korelacja_opoznien(final)
# plot_scatter_opoznienia(final)

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

def plot_rezim_cisnienie_wiatr(df):
    prog_cofka = df['Port_Polnocny_max'].quantile(0.10)
    prog_spietzenie = df['Port_Polnocny_max'].quantile(0.90)

    cofka = df[df['Port_Polnocny_max'] <= prog_cofka]
    spietzenie = df[df['Port_Polnocny_max'] >= prog_spietzenie]
    normalny = df[(df['Port_Polnocny_max'] > prog_cofka) &
                  (df['Port_Polnocny_max'] < prog_spietzenie)]

    rezimy = ['Niski poziom (≤ P10)', 'Normalny', 'Wysoki poziom (≥ P90)']
    cisnienia = [cofka['Ciśnienie_średnia'].mean(),
                 normalny['Ciśnienie_średnia'].mean(),
                 spietzenie['Ciśnienie_średnia'].mean()]
    wiatry = [cofka['Wiatr_siła_proxy'].mean(),
              normalny['Wiatr_siła_proxy'].mean(),
              spietzenie['Wiatr_siła_proxy'].mean()]

    fig, ax1 = plt.subplots(figsize=(10, 5))
    color = 'tab:blue'
    ax1.set_xlabel('Reżim hydrologiczny')
    ax1.set_ylabel('Średnie ciśnienie [hPa]', color=color)
    ax1.bar(rezimy, cisnienia, color=color, alpha=0.4, width=0.4)
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.set_ylim(1000, 1025)

    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Średnia siła wiatru', color=color)
    ax2.plot(rezimy, wiatry, color=color, marker='o', linewidth=2, markersize=8)
    ax2.tick_params(axis='y', labelcolor=color)
    ax2.set_ylim(2, 8)

    plt.title('Charakterystyka warunków atmosferycznych w reżimach Portu Północnego')
    fig.tight_layout()
    plt.show()