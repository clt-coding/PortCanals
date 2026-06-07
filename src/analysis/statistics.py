import pandas as pd
import numpy as np
from scipy.stats import shapiro, mannwhitneyu
from sklearn.linear_model import LinearRegression

STACJE = {
    'Strzyża':       'Poziom_wody_max',
    'Martwa Wisła':  'Martwa_Wisla_max',
    'Port Północny': 'Port_Polnocny_max',
}

#Korelacja Pearsona między opadem a poziomem wody dla lagów 0-14 dni.
# dla wszystkich trzech stacji pomiarowych (Strzyża, Martwa Wisła, Port Północny)
def korelacja_z_lagami_wszystkie(df):
    korelacje = {nazwa: [] for nazwa in STACJE}
    for lag in range(15):
        opad_shifted = df['Opad_suma'].shift(lag)
        for nazwa, col in STACJE.items():
            korelacje[nazwa].append(opad_shifted.corr(df[col]))
    for nazwa, vals in korelacje.items():
        print(f"{nazwa}: max r = {np.nanmax(vals):.4f}")
    return korelacje


# Porównanie korelacji Spearmana i Pearsona dla wszystkich stacji
# Spearman lepiej wykrywa nieliniowe zależności monotonicznie
def korelacja_spearmana_wszystkie(df):
    print(f"\n=== Spearman ρ vs. Pearson r (Opad_suma) ===")
    for nazwa, col in STACJE.items():
        rho = df['Opad_suma'].corr(df[col], method='spearman')
        r   = df['Opad_suma'].corr(df[col], method='pearson')
        print(f"  {nazwa:15s}  Pearson r={r:.3f}  Spearman ρ={rho:.3f}  Δ={rho-r:+.3f}")


# Regresja liniowa Opad_72h → poziom wody dla wszystkich stacji
# Współczynnik β oznacza wzrost poziomu wody [m] na każdy mm opadu 72h
def regresja_liniowa_wszystkie(df):
    print("\n=== Regresja liniowa: Opad_72h → Poziom wody ===")
    for nazwa, col in STACJE.items():
        X = df[['Opad_72h']].dropna()
        y = df.loc[X.index, col]
        mask = y.notna()
        model = LinearRegression().fit(X[mask], y[mask])
        print(f"  {nazwa:15s}  β = {model.coef_[0]:.5f} m/mm")

# Testy statystyczne dla jednej stacji:
# Shapiro-Wilk (normalność) + Mann-Whitney U (różnica między grupami)
# col - kolumna poziomu wody, nazwa - nazwa stacji do wydruku
def analiza_stacji(df, col, nazwa):
    q25 = df['Opad_suma'].quantile(0.25)
    q75 = df['Opad_suma'].quantile(0.75)
    maly = df[df['Opad_suma'] <= q25][col].dropna()
    duzy = df[df['Opad_suma'] >= q75][col].dropna()
    print(f"\n{'='*10} {nazwa} {'='*10}")
    _, p_maly = shapiro(maly)
    _, p_duzy = shapiro(duzy)
    print(f"  Shapiro-Wilk — mały opad:  p = {p_maly:.3e}")
    print(f"  Shapiro-Wilk — duży opad:  p = {p_duzy:.3e}")
    _, p_mw = mannwhitneyu(maly, duzy)
    print(f"  Mann-Whitney U:            p = {p_mw:.3e}")


# Korelacja predyktorów ciśnienia i wiatru z poziomem wody w Porcie Północnym
# Port Północny reaguje głównie na warunki morskie, nie opadowe
def korelacja_port_wiatr_cisnienie(df):
    predyktory_port = [
        'Ciśnienie_średnia', 'Ciśnienie_min', 'Ciśnienie_ampl',
        'Ciśnienie_delta_1d', 'Ciśnienie_delta_2d', 'Ciśnienie_delta_3d',
        'Ciśnienie_trend_3d', 'Ciśnienie_trend_7d',
        'Wiatr_siła_proxy', 'Wiatr_sin_proxy', 'Wiatr_cos_proxy',
    ]
    print("=== Korelacja z Port_Polnocny_max ===")
    print(f"{'Zmienna':28s}  Pearson r   Spearman ρ")
    for col in predyktory_port:
        r   = df[col].corr(df['Port_Polnocny_max'], method='pearson')
        rho = df[col].corr(df['Port_Polnocny_max'], method='spearman')
        print(f"  {col:26s}  {r:+.3f}       {rho:+.3f}")


# korelacja Spearmana (nieparametryczna) między opadem a poziomem wody by sprawdzić czy
# istnieje monotoniczna zależność, nawet jeśli nie jest liniowa
def korelacja_spearmana(df):
    rho = df['Opad_suma'].corr(df['Poziom_wody_max'], method='spearman')
    print(rho)
    return rho

# korelacja Pearsona dla dni z opadem > 0,
# by sprawdzić liniową zależność tylko w dniach, gdy wystąpił opad
def korelacja_pearsona_mokre(df):
    mokre = df[df['Opad_suma'] > 0]
    r = mokre['Opad_suma'].corr(mokre['Poziom_wody_max'])
    print(r)
    return r


#sprawdzenie normalności rozkładów (shapiro-wilka)
def test_normalnosci(df):
    q25 = df['Opad_suma'].quantile(0.25)
    q75 = df['Opad_suma'].quantile(0.75)

    maly_opad = df[df['Opad_suma'] <= q25]['Poziom_wody_max']
    duzy_opad = df[df['Opad_suma'] >= q75]['Poziom_wody_max']

    stat, p = shapiro(maly_opad)
    print(p)

    stat, p = shapiro(duzy_opad)
    print(p)

    return maly_opad, duzy_opad


#Test Manna-Whitneya między grupą małego i dużego opadu.
def test_manna_whitneya(df):
    q25 = df['Opad_suma'].quantile(0.25)
    q75 = df['Opad_suma'].quantile(0.75)

    maly_opad = df[df['Opad_suma'] <= q25]['Poziom_wody_max']
    duzy_opad = df[df['Opad_suma'] >= q75]['Poziom_wody_max']

    stat, p = mannwhitneyu(maly_opad, duzy_opad)
    print(p)
    return p

# Porównanie korelacji Pearsona dla wszystkich dni vs tylko dni z opadem > 0
# Ujawnia progowy charakter odpowiedzi zlewni na opad
def korelacja_wszystkie_vs_mokre_wszystkie(df):
    print("=== Wszystkie dni ===")
    for col in ['Opad_suma', 'Opad_72h', 'Opad_7d', 'Opad_lag_1d', 'Opad_lag_2d', 'Opad_lag_3d']:
        r = df[col].corr(df['Poziom_wody_max'])
        print(f"  {col:20s}  r = {r:.3f}")

    print("\n=== Tylko dni z opadem > 0 (Strzyża) ===")
    mokre = df[df['Opad_suma'] > 0]
    for col in ['Opad_suma', 'Opad_72h', 'Opad_7d']:
        r = mokre[col].corr(mokre['Poziom_wody_max'])
        print(f"  {col:20s}  r = {r:.3f}")

# Identyfikacja trzech reżimów hydrologicznych Portu Północnego
# Cofka (P10), normalny, spiętrzenie (P90)
# Porównanie warunków atmosferycznych między reżimami
def identyfikacja_rezimow_portu(df):
    prog_cofka = df['Port_Polnocny_max'].quantile(0.10)
    prog_spietzenie = df['Port_Polnocny_max'].quantile(0.90)

    cofka = df[df['Port_Polnocny_max'] <= prog_cofka]
    spietzenie = df[df['Port_Polnocny_max'] >= prog_spietzenie]
    normalny = df[
        (df['Port_Polnocny_max'] > prog_cofka) &
        (df['Port_Polnocny_max'] < prog_spietzenie)
    ]

    print(f"Próg cofki (P10):       {prog_cofka:.3f} m")
    print(f"Próg spiętrzenia (P90): {prog_spietzenie:.3f} m")
    print(f"\nLiczba dni — cofka:      {len(cofka)}")
    print(f"Liczba dni — spiętrzenie:{len(spietzenie)}")
    print(f"Liczba dni — normalny:   {len(normalny)}")

    print("\n=== Średnie wartości predyktorów według reżimu ===")
    for col in ['Ciśnienie_średnia', 'Ciśnienie_delta_1d', 'Wiatr_siła_proxy']:
        m_c = cofka[col].mean()
        m_n = normalny[col].mean()
        m_s = spietzenie[col].mean()
        print(f"  {col:26s}  cofka={m_c:.2f}  normalny={m_n:.2f}  spiętrzenie={m_s:.2f}")

    return cofka, normalny, spietzenie