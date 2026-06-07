import pandas as pd
import pandas as pd
import numpy as np
import os
from scipy.stats import shapiro, mannwhitneyu
from sklearn.linear_model import LinearRegression
from sklearn.metrics import confusion_matrix, precision_score, recall_score
import matplotlib.pyplot as plt
import seaborn as sns

final = pd.read_csv(
    'data/processed/final.csv',
    parse_dates=['Data'],
    index_col='Data'
)

# =============================================================================
# ANALIZA STATYSTYCZNA ZALEŻNOŚCI — OPAD vs. POZIOM WODY
# Stacje: Strzyża, Martwa Wisła, Port Północny
# =============================================================================
 
os.makedirs('reports/analiza_statystyczna_zaleznosci', exist_ok=True)
 
# Słownik stacji: nazwa wyświetlana → kolumna w final
STACJE = {
    'Strzyża':       'Poziom_wody_max',
    'Martwa Wisła':  'Martwa_Wisla_max',
    'Port Północny': 'Port_Polnocny_max',
}
 
# %% ── 1. KORELACJA Z OPÓŹNIENIEM (LAG 0–14 DNI) ─────────────────────────────
 
korelacje = {nazwa: [] for nazwa in STACJE}
 
for lag in range(15):
    opad_shifted = final['Opad_suma'].shift(lag)
    for nazwa, col in STACJE.items():
        korelacje[nazwa].append(opad_shifted.corr(final[col]))
 
# Wydruk maksymalnych wartości
for nazwa, vals in korelacje.items():
    print(f"{nazwa}: max r = {np.nanmax(vals):.4f}")
 
# Strzyża:       max r = 0.1958  (lag=0)
# Martwa Wisła:  max r = 0.1573  (lag=0)
# Port Północny: max r = 0.0586  (lag=0)
# → Port Północny reaguje na opad minimalnie — dominują inne czynniki (morskie)
 
plt.figure(figsize=(10, 5))
markers = {'Strzyża': 'o', 'Martwa Wisła': 's', 'Port Północny': '^'}
for nazwa, vals in korelacje.items():
    sns.lineplot(x=range(15), y=vals, marker=markers[nazwa], label=nazwa)
 
plt.title('Korelacja opadu z poziomem wody w zależności od opóźnienia', fontsize=14)
plt.xlabel('Opóźnienie (dni)')
plt.ylabel('Współczynnik korelacji (Pearson)')
plt.legend()
plt.tight_layout()
plt.savefig('reports/analiza_statystyczna_zaleznosci/korelacja_opoznienia.png', dpi=300)
 
# %% ── 2. MACIERZ KORELACJI ───────────────────────────────────────────────────
 
cols = [
    'Opad_suma', 'Opad_72h', 'Opad_7d',
    'Temp_średnia', 'Wilgotność_średnia', 'Ciśnienie_średnia',
    'Martwa_Wisla_średnia', 'Martwa_Wisla_max',
    'Port_Polnocny_średnia', 'Port_Polnocny_max',
    'Poziom_wody_max',
]
 
corr_matrix = final[cols].corr()
 
plt.figure(figsize=(10, 8))
sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', center=0)
plt.title('Macierz korelacji')
plt.tight_layout()
plt.savefig('reports/analiza_statystyczna_zaleznosci/macierz_korelacji.png', dpi=300)
 
# Kluczowe obserwacje:
# - Strzyża ↔ Martwa Wisła: r=0.90–0.94 → jeden spójny system hydrologiczny
# - Port Północny ↔ pozostałe: r≈0.40–0.44 → inny mechanizm (morski)
# - Opad_72h ↔ Opad_7d: r=0.71 → multikolinearność, nie używać jednocześnie w modelu
# - Ciśnienie ujemnie koreluje z opadem i poziomem wody na wszystkich stacjach
 
# %% ── 3. KORELACJA MIĘDZY STACJAMI ──────────────────────────────────────────
 
# Cel: sprawdzić czy Strzyża i Martwa Wisła mogą służyć jako predyktory
# poziomu wody w Porcie Północnym — kluczowe dla algorytmu ostrzegania
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
 
axes[0].scatter(
    final['Martwa_Wisla_max'], final['Port_Polnocny_max'],
    alpha=0.2, s=5, color='steelblue'
)
axes[0].set_xlabel('Martwa Wisła — poziom wody max [m]')
axes[0].set_ylabel('Port Północny — poziom wody max [m]')
axes[0].set_title('Martwa Wisła vs. Port Północny (r = 0.42)')
 
axes[1].scatter(
    final['Poziom_wody_max'], final['Port_Polnocny_max'],
    alpha=0.2, s=5, color='darkorange'
)
axes[1].set_xlabel('Strzyża — poziom wody max [m]')
axes[1].set_ylabel('Port Północny — poziom wody max [m]')
axes[1].set_title('Strzyża vs. Port Północny (r = 0.44)')
 
plt.suptitle('Zależność między stacjami śródlądowymi a Portem Północnym', y=1.02)
plt.tight_layout()
plt.savefig('reports/analiza_statystyczna_zaleznosci/scatter_stacje_port.png', dpi=300)
 
# Wniosek: rozproszenie punktów przy r≈0.42–0.44 wskazuje że Strzyża i Martwa Wisła
# są umiarkowanymi, ale niepewnymi predyktorami Portu Północnego.
# Port Północny wymaga osobnych predyktorów — prawdopodobnie ciśnienie i wiatr.
 
# %% ── 4. PORÓWNANIE KORELACJI: WSZYSTKIE DNI VS. DNI Z OPADEM ───────────────
 
print("=== Wszystkie dni ===")
for col in ['Opad_suma', 'Opad_72h', 'Opad_7d', 'Opad_lag_1d', 'Opad_lag_2d', 'Opad_lag_3d']:
    r = final[col].corr(final['Poziom_wody_max'])
    print(f"  {col:20s}  r = {r:.3f}")
 
print("\n=== Tylko dni z opadem > 0 (Strzyża) ===")
mokre = final[final['Opad_suma'] > 0]
for col in ['Opad_suma', 'Opad_72h', 'Opad_7d']:
    r = mokre[col].corr(mokre['Poziom_wody_max'])
    print(f"  {col:20s}  r = {r:.3f}")
 
# Wyniki (Strzyża):
# Opad_suma    : wszystkie=0.196 | mokre=0.120
# Opad_72h     : wszystkie=0.233 | mokre=0.177  ← najlepszy predyktor liniowy
# Opad_7d      : wszystkie=0.211 | mokre=0.164
# Opad_lag_1d  : 0.152
# Opad_lag_2d  : 0.094
# Opad_lag_3d  : 0.070
#
# Spadek korelacji po ograniczeniu do mokrych dni → progowy charakter odpowiedzi zlewni
 
# %% ── 5. KORELACJA SPEARMANA ─────────────────────────────────────────────────
 
print("\n=== Spearman ρ vs. Pearson r (Opad_suma) ===")
for nazwa, col in STACJE.items():
    rho = final['Opad_suma'].corr(final[col], method='spearman')
    r   = final['Opad_suma'].corr(final[col], method='pearson')
    print(f"  {nazwa:15s}  Pearson r={r:.3f}  Spearman ρ={rho:.3f}  Δ={rho-r:+.3f}")
 
# Strzyża:       r=0.196  ρ=0.292  Δ=+0.096
# Martwa Wisła:  r=0.157  ρ=0.272  Δ=+0.115
# Port Północny: r=0.059  ρ=0.250  Δ=+0.191
#
# Różnica Spearman > Pearson dla wszystkich stacji → zależność nieliniowa
# Największa różnica dla Portu Północnego — silnie nieliniowy, nieprzewidywalny charakter
 
# %% ── 6. REGRESJA LINIOWA ────────────────────────────────────────────────────
 
print("\n=== Regresja liniowa: Opad_72h → Poziom wody ===")
for nazwa, col in STACJE.items():
    X = final[['Opad_72h']].dropna()
    y = final.loc[X.index, col]
    mask = y.notna()
    model = LinearRegression().fit(X[mask], y[mask])
    print(f"  {nazwa:15s}  β = {model.coef_[0]:.5f} m/mm")
 
# Strzyża:       β = 0.00633 m/mm → +0.63 cm na każdy mm opadu 72h
# Martwa Wisła:  β = 0.00544 m/mm → +0.54 cm
# Port Północny: β = 0.00573 m/mm → +0.57 cm
# β zbliżone dla wszystkich stacji, ale scatter plot ujawnia różny charakter danych
 
for nazwa, col in STACJE.items():
    plt.figure(figsize=(8, 5))
    sns.regplot(data=final, x='Opad_72h', y=col, scatter_kws={'alpha': 0.2})
    plt.title(f'Opad skumulowany 72h a poziom wody — {nazwa}')
    plt.xlabel('Opad 72h [mm]')
    plt.ylabel('Poziom wody max [m]')
    plt.tight_layout()
    fname = nazwa.lower().replace(' ', '_').replace('ó', 'o').replace('ł', 'l')
    plt.savefig(f'reports/analiza_statystyczna_zaleznosci/regplot_{fname}.png', dpi=300)
 
# %% ── 7. ANALIZA GRUPOWA: MAŁY VS. DUŻY OPAD ────────────────────────────────
 
q25 = final['Opad_suma'].quantile(0.25)
q75 = final['Opad_suma'].quantile(0.75)
 
maly = final[final['Opad_suma'] <= q25]
duzy = final[final['Opad_suma'] >= q75]
 
print("\n=== Średni poziom wody: mały vs. duży opad ===")
for nazwa, col in STACJE.items():
    m = maly[col].mean()
    d = duzy[col].mean()
    print(f"  {nazwa:15s}  mały={m:.3f} m  duży={d:.3f} m  Δ={d-m:+.3f} m")
 
# Strzyża:       mały=0.122  duży=0.257  Δ=+0.135 m
# Martwa Wisła:  mały=-0.070 duży=0.056  Δ=+0.126 m
# Port Północny: mały=5.171  duży=5.309  Δ=+0.138 m  ← mała różnica względem zakresu
 
# KDE — trzy stacje obok siebie
fig, axes = plt.subplots(1, 3, figsize=(18, 6), sharey=False)
 
for ax, (nazwa, col) in zip(axes, STACJE.items()):
    sns.kdeplot(maly[col], ax=ax, label='Mały opad (≤25%)', fill=True, alpha=0.5)
    sns.kdeplot(duzy[col], ax=ax, label='Duży opad (≥75%)', fill=True, alpha=0.5)
    ax.set_title(nazwa)
    ax.set_xlabel('Poziom wody [m]')
    ax.set_ylabel('Gęstość')
    ax.legend()
 
plt.tight_layout()
plt.savefig('reports/analiza_statystyczna_zaleznosci/kde_porownanie_stacje.png', dpi=300)
 
# Boxplot — wszystkie stacje razem
dane_box = pd.DataFrame({
    f'{nazwa} - mały': maly[col].values[:len(duzy)]
    if len(maly) > len(duzy) else maly[col].values
    for nazwa, col in STACJE.items()
} | {
    f'{nazwa} - duży': duzy[col].values
    for nazwa, col in STACJE.items()
})
 
# Prostszy sposób — bez wyrównywania długości
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
plt.savefig('reports/analiza_statystyczna_zaleznosci/boxplot_opad_woda_wszystkie.png', dpi=300)
 
# %% ── 8. TESTY STATYSTYCZNE ──────────────────────────────────────────────────
 
def analiza_stacji(final, col, nazwa):
    print(f"\n{'='*10} {nazwa} {'='*10}")
 
    maly = final[final['Opad_suma'] <= q25][col].dropna()
    duzy = final[final['Opad_suma'] >= q75][col].dropna()
 
    # Shapiro-Wilk
    _, p_maly = shapiro(maly)
    _, p_duzy = shapiro(duzy)
    print(f"  Shapiro-Wilk — mały opad:  p = {p_maly:.3e}")
    print(f"  Shapiro-Wilk — duży opad:  p = {p_duzy:.3e}")
    print(f"  → Oba rozkłady dalekie od normalności → test nieparametryczny")
 
    # Mann-Whitney U
    _, p_mw = mannwhitneyu(maly, duzy)
    print(f"  Mann-Whitney U:            p = {p_mw:.3e}")
    print(f"  → Różnica {'wysoce ' if p_mw < 1e-10 else ''}istotna statystycznie")
 
for nazwa, col in STACJE.items():
    analiza_stacji(final, col, nazwa)
 
# Wyniki:
# ========== Strzyża ==========
# Shapiro mały: 9.51e-13 | Shapiro duży: 3.95e-09
# Mann-Whitney: 4.64e-31 → różnica wysoce istotna
 
# ========== Martwa Wisła ==========
# Shapiro mały: 2.90e-13 | Shapiro duży: 2.02e-10
# Mann-Whitney: 1.84e-27 → różnica wysoce istotna
 
# ========== Port Północny ==========
# Shapiro mały: 3.40e-51 | Shapiro duży: 4.18e-34
# Mann-Whitney: 5.39e-23 → różnica istotna, ale Δ=0.138m przy zakresie 6m
# → przy dużej próbie test wykrywa nawet małe różnice; sprawdź wielkość efektu

# =============================================================================
# CZĘŚĆ II — ANALIZA PORTU PÓŁNOCNEGO: WIATR I CIŚNIENIE
# =============================================================================
# Port Północny wykazuje minimalną korelację z opadem (r<0.06) i dwa reżimy
# hydrologiczne (normalny + cofki). Ta sekcja bada właściwe predyktory:
# ciśnienie atmosferyczne i wiatr.
 
# %% ── 9. KORELACJA CIŚNIENIA I WIATRU Z POZIOMEM WODY W PORCIE ──────────────
 
predyktory_port = [
    'Ciśnienie_średnia',
    'Ciśnienie_min',
    'Ciśnienie_ampl',
    'Ciśnienie_delta_1d',
    'Ciśnienie_delta_2d',
    'Ciśnienie_delta_3d',
    'Ciśnienie_trend_3d',
    'Ciśnienie_trend_7d',
    'Wiatr_siła_proxy',
    'Wiatr_sin_proxy',
    'Wiatr_cos_proxy',
]
 
print("=== Korelacja z Port_Polnocny_max ===")
print(f"{'Zmienna':28s}  Pearson r   Spearman ρ")
for col in predyktory_port:
    r   = final[col].corr(final['Port_Polnocny_max'], method='pearson')
    rho = final[col].corr(final['Port_Polnocny_max'], method='spearman')
    print(f"  {col:26s}  {r:+.3f}       {rho:+.3f}")
 
# Spodziewane wyniki:
# Ciśnienie_średnia    → r ujemne (niskie ciśnienie = wyższy poziom wody)
# Ciśnienie_delta_1d   → może być silniejsze niż średnia (nagły spadek = spiętrzenie)
# Wiatr_siła_proxy     → dodatnie (silny wiatr = spiętrzenie lub cofka zależnie od kierunku)
# Wiatr_sin/cos_proxy  → ujawni dominujący kierunek wiatru wpływający na port
 
# %% ── 10. MACIERZ KORELACJI — PORT PÓŁNOCNY + WIATR + CIŚNIENIE ─────────────
 
cols_port = predyktory_port + ['Port_Polnocny_max']
 
plt.figure(figsize=(12, 10))
sns.heatmap(
    final[cols_port].corr(),
    annot=True, fmt='.2f', cmap='coolwarm', center=0
)
plt.title('Macierz korelacji — Port Północny: wiatr i ciśnienie')
plt.tight_layout()
plt.savefig('reports/analiza_statystyczna_zaleznosci/macierz_port_wiatr_cisnienie.png', dpi=300)

# %% ── 11. POZIOM WODY W PORCIE vs. SIŁA WIATRU ──────────────────────────────
 
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
 
# Scatter: siła wiatru vs. poziom wody
axes[0].scatter(
    final['Wiatr_siła_proxy'], final['Port_Polnocny_max'],
    alpha=0.2, s=5, color='steelblue'
)
axes[0].set_xlabel('Siła wiatru (proxy)')
axes[0].set_ylabel('Port Północny — poziom wody max [m]')
axes[0].set_title('Siła wiatru vs. poziom wody w porcie')
 
# Scatter: delta ciśnienia (1d) vs. poziom wody
axes[1].scatter(
    final['Ciśnienie_delta_1d'], final['Port_Polnocny_max'],
    alpha=0.2, s=5, color='darkorange'
)
axes[1].set_xlabel('Zmiana ciśnienia 1d [hPa]')
axes[1].set_ylabel('Port Północny — poziom wody max [m]')
axes[1].set_title('Dzienna zmiana ciśnienia vs. poziom wody w porcie')
 
plt.tight_layout()
plt.savefig('reports/analiza_statystyczna_zaleznosci/scatter_port_wiatr_cisnienie.png', dpi=300)
 
# %% ── 12. ANALIZA WEDŁUG SEKTORA WIATRU ─────────────────────────────────────
 
# Boxplot poziomu wody w porcie według sektora wiatru
# Ujawnia który kierunek wiatru sprzyja spiętrzeniu/cofce
 
plt.figure(figsize=(10, 5))
kolejnosc = sorted(final['Wiatr_sektor_proxy'].dropna().unique())
sns.boxplot(
    data=final,
    x='Wiatr_sektor_proxy',
    y='Port_Polnocny_max',
    order=kolejnosc
)
plt.title('Poziom wody w Porcie Północnym według sektora wiatru')
plt.xlabel('Sektor wiatru')
plt.ylabel('Poziom wody max [m]')
plt.tight_layout()
plt.savefig('reports/analiza_statystyczna_zaleznosci/boxplot_port_sektor_wiatru.png', dpi=300)
 
# Wniosek do uzupełnienia po zobaczeniu wykresu:
# Sektory wschodnie/północno-wschodnie → spodziewana cofka (niski poziom)
# Sektory zachodnie/północno-zachodnie → spodziewane spiętrzenie (wysoki poziom)
 
# %% ── 13. IDENTYFIKACJA EPIZODÓW COFKI ──────────────────────────────────────
 
# Cofka = poziom wody w porcie poniżej percentyla 10
prog_cofka = final['Port_Polnocny_max'].quantile(0.10)
prog_spietzenie = final['Port_Polnocny_max'].quantile(0.90)
 
print(f"\nPróg cofki (P10):       {prog_cofka:.3f} m")
print(f"Próg spiętrzenia (P90): {prog_spietzenie:.3f} m")
 
cofka      = final[final['Port_Polnocny_max'] <= prog_cofka]
spietzenie = final[final['Port_Polnocny_max'] >= prog_spietzenie]
normalny   = final[
    (final['Port_Polnocny_max'] > prog_cofka) &
    (final['Port_Polnocny_max'] < prog_spietzenie)
]
 
print(f"\nLiczba dni — cofka:      {len(cofka)}")
print(f"Liczba dni — spiętrzenie:{len(spietzenie)}")
print(f"Liczba dni — normalny:   {len(normalny)}")
 
# Porównanie warunków wiatrowych i ciśnieniowych między reżimami
print("\n=== Średnie wartości predyktorów według reżimu ===")
for col in ['Ciśnienie_średnia', 'Ciśnienie_delta_1d', 'Wiatr_siła_proxy']:
    m_c = cofka[col].mean()
    m_n = normalny[col].mean()
    m_s = spietzenie[col].mean()
    print(f"  {col:26s}  cofka={m_c:.2f}  normalny={m_n:.2f}  spiętrzenie={m_s:.2f}")
 
# %% ── 14. WIZUALIZACJA TRZECH REŻIMÓW ────────────────────────────────────────
 
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
 
# Budujemy długi format (long-form) — działa niezależnie od liczebności grup
def do_long(col):
    return pd.concat([
        cofka[[col]].assign(Reżim='Cofka'),
        normalny[[col]].assign(Reżim='Normalny'),
        spietzenie[[col]].assign(Reżim='Spiętrzenie'),
    ], ignore_index=True)
 
# Ciśnienie według reżimu
sns.boxplot(data=do_long('Ciśnienie_średnia'), x='Reżim', y='Ciśnienie_średnia', ax=axes[0])
axes[0].set_title('Ciśnienie atmosferyczne według reżimu')
axes[0].set_xlabel('')
axes[0].set_ylabel('Ciśnienie [hPa]')
 
# Siła wiatru według reżimu
sns.boxplot(data=do_long('Wiatr_siła_proxy'), x='Reżim', y='Wiatr_siła_proxy', ax=axes[1])
axes[1].set_title('Siła wiatru według reżimu')
axes[1].set_xlabel('')
axes[1].set_ylabel('Siła wiatru (proxy)')
 
plt.suptitle('Warunki atmosferyczne w trzech reżimach Portu Północnego')
plt.tight_layout()
plt.savefig('reports/analiza_statystyczna_zaleznosci/boxplot_port_rezim_atmosfera.png', dpi=300)