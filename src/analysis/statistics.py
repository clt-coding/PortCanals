import pandas as pd
import numpy as np
from scipy.stats import shapiro, mannwhitneyu
from sklearn.linear_model import LinearRegression


#Korelacja Pearsona między opadem a poziomem wody dla lagów 0-14 dni.
def korelacja_z_lagami(df):
    korelacje = []
    for lag in range(15):
        corr = df['Opad_suma'].shift(lag).corr(df['Poziom_wody_max'])
        korelacje.append(corr)
    return korelacje


#Porównanie korelacji dla wszystkich dni vs tylko dni z opadem > 0.
def korelacja_wszystkie_vs_mokre(df):
    print("=== Wszystkie dni ===")
    for col in ['Opad_suma', 'Opad_72h', 'Opad_7d', 'Opad_lag_1d', 'Opad_lag_2d', 'Opad_lag_3d']:
        r = df[col].corr(df['Poziom_wody_max'])
        print(f"{col:20s}  r = {r:.3f}")

    print("\n=== Tylko dni z opadem > 0 ===")
    mokre = df[df['Opad_suma'] > 0]
    for col in ['Opad_suma', 'Opad_72h', 'Opad_7d']:
        r = mokre[col].corr(mokre['Poziom_wody_max'])
        print(f"{col:20s}  r = {r:.3f}")


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

# regresja liniowa dla Opad_72h i Poziom_wody_max, by sprawdzić czy
# istnieje liniowa zależność i jaki jest jej współczynnik
def regresja_liniowa(df):
    X = df[['Opad_72h']]
    y = df['Poziom_wody_max']
    model = LinearRegression()
    model.fit(X, y)
    print(model.coef_)
    return model

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