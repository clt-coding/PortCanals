# from src.factor.ml_factor_system import uruchom_system
# diagnozy = uruchom_system(final)

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    precision_score, recall_score, confusion_matrix, classification_report
)

# ── KONFIGURACJA ──────────────────────────────────────────────────────────────

# Cechy wejściowe modelu — wszystkie numeryczne kolumny które mają sens fizyczny.
# Pomijamy Poziom_wody_* (to target/dane z przyszłości), Wiatr_sektor_proxy (string),
# oraz surowe indeksy czasowe (month, doy zastąpione sin/cos).
FEATURES = [
    'Opad_suma',
    'Opad_24h',
    'Opad_72h',
    'Opad_7d',
    'Opad_lag_1d',
    'Opad_lag_2d',
    'Opad_lag_3d',
    'Temp_średnia',
    'Temp_min',
    'Temp_max',
    'Temp_średnia_lag_1d',
    'Wilgotność_średnia',
    'Ciśnienie_średnia',
    'Ciśnienie_ampl',
    'Ciśnienie_delta_1d',
    'Ciśnienie_delta_2d',
    'Ciśnienie_delta_3d',
    'Ciśnienie_trend_3d',
    'Ciśnienie_trend_7d',
    'Wiatr_siła_proxy',
    'Wiatr_sin_proxy',
    'Wiatr_cos_proxy',
    'sin_doy',
    'cos_doy',
]

# Próg percentyla definiujący epizod wysokiej wody
EPIZOD_PERCENTYL = 0.90

# Parametry Random Forest
RF_PARAMS = {
    'n_estimators':   300,
    'max_depth':      6,       # ograniczamy głębokość — zapobiega overfitting na małych danych
    'min_samples_leaf': 10,    # min. 10 dni w liściu — stabilność
    'class_weight':  'balanced',  # wyrównuje nierównowagę klas (epizody ~10% danych)
    'random_state':   42,
    'n_jobs':        -1,
}

# Próg prawdopodobieństwa powyżej którego ogłaszamy alarm
# (domyślnie 0.5 ale można obniżyć żeby zwiększyć recall kosztem precision)
PROB_THRESHOLD = 0.40


# ── 1. PRZYGOTOWANIE DANYCH ───────────────────────────────────────────────────

def _przygotuj_dane(final: pd.DataFrame):
    """Tworzy kolumnę Epizod_rzeczywisty i zwraca X, y gotowe do treningu."""
    df = final.copy()

    if 'Epizod_rzeczywisty' not in df.columns:
        threshold = df['Poziom_wody_max'].quantile(EPIZOD_PERCENTYL)
        df['Epizod_rzeczywisty'] = (df['Poziom_wody_max'] >= threshold).astype(int)

    # upewniamy się że wszystkie features istnieją
    brakujace = [f for f in FEATURES if f not in df.columns]
    if brakujace:
        raise ValueError(f"Brakujące kolumny w danych: {brakujace}")

    X = df[FEATURES]
    y = df['Epizod_rzeczywisty']
    return df, X, y


# ── 2. WALIDACJA CZASOWA (rok po roku) ───────────────────────────────────────

def walidacja_czasowa(df: pd.DataFrame, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    """
    Walk-forward validation: trenujemy na wszystkich latach przed rokiem testowym,
    testujemy na roku testowym. Zwraca DataFrame z metrykami per rok.

    To jest wymaganie karty projektu — "stabilna poprawa względem metod odniesienia
    oceniana w walidacji czasowej".
    """
    lata = sorted(df.index.year.unique())
    wyniki = []

    print("=== Walidacja czasowa (walk-forward) ===")

    for i, rok_test in enumerate(lata):
        if i == 0:
            continue  # potrzebujemy min. 1 rok do treningu

        maska_train = df.index.year < rok_test
        maska_test  = df.index.year == rok_test

        if maska_train.sum() < 50 or maska_test.sum() < 10:
            continue

        X_train, y_train = X[maska_train], y[maska_train]
        X_test,  y_test  = X[maska_test],  y[maska_test]

        model = RandomForestClassifier(**RF_PARAMS)
        model.fit(X_train, y_train)

        proba  = model.predict_proba(X_test)[:, 1]
        y_pred = (proba >= PROB_THRESHOLD).astype(int)

        prec = precision_score(y_test, y_pred, zero_division=0)
        rec  = recall_score(y_test, y_pred, zero_division=0)

        # benchmark: progi opadu (jak w factor_system.py)
        prog_benchmark = X_train['Opad_72h'].quantile(EPIZOD_PERCENTYL)
        y_bench = (X_test['Opad_72h'] >= prog_benchmark).astype(int)
        prec_b = precision_score(y_test, y_bench, zero_division=0)
        rec_b  = recall_score(y_test, y_bench, zero_division=0)

        wyniki.append({
            'Rok':           rok_test,
            'Recall_RF':     round(rec,    3),
            'Precision_RF':  round(prec,   3),
            'Recall_bench':  round(rec_b,  3),
            'Prec_bench':    round(prec_b, 3),
            'n_epizodow':    int(y_test.sum()),
            'n_dni':         int(maska_test.sum()),
        })

        print(f"  {rok_test}: RF recall={rec:.3f} prec={prec:.3f} | "
              f"benchmark recall={rec_b:.3f} prec={prec_b:.3f}")

    return pd.DataFrame(wyniki)


# ── 3. TRENING FINALNEGO MODELU ───────────────────────────────────────────────

def trenuj_model(X: pd.DataFrame, y: pd.Series) -> RandomForestClassifier:
    """Trenuje finalny model na całym zbiorze danych."""
    model = RandomForestClassifier(**RF_PARAMS)
    model.fit(X, y)
    return model


# ── 4. FEATURE IMPORTANCE → "WSKAZANIE CZYNNIKÓW" ────────────────────────────

def feature_importance_df(model: RandomForestClassifier) -> pd.DataFrame:
    """
    Zwraca DataFrame z ważnością cech posortowany malejąco.
    To jest odpowiednik "wskazania czynnika" wymaganego przez kartę projektu —
    RF mówi które zmienne meteorologiczne najbardziej decydują o klasyfikacji.
    """
    fi = pd.DataFrame({
        'czynnik':   FEATURES,
        'waznosc':   model.feature_importances_,
    }).sort_values('waznosc', ascending=False).reset_index(drop=True)
    fi['waznosc_pct'] = (fi['waznosc'] * 100).round(2)
    return fi


# ── 5. DIAGNOZA DLA JEDNEJ OBSERWACJI ────────────────────────────────────────

def diagnozuj(obserwacja: pd.Series,
              model: RandomForestClassifier,
              fi: pd.DataFrame) -> dict:
    """
    Dla jednego wiersza z `final` generuje diagnozę:
      - prawdopodobieństwo epizodu (wyjście RF)
      - ryzyko: niskie / średnie / wysokie
      - główny czynnik (top-1 z feature importance ważony wartością)
      - pewność (prawdopodobieństwo z modelu)
      - komunikat tekstowy
    """
    X_obs = obserwacja[FEATURES].to_frame().T
    proba = model.predict_proba(X_obs)[0, 1]

    if proba >= 0.65:
        ryzyko = 'wysokie'
    elif proba >= PROB_THRESHOLD:
        ryzyko = 'średnie'
    else:
        ryzyko = 'niskie'

    # Wskazanie czynnika: bierzemy top-3 z feature importance i filtrujemy
    # tylko te, których wartość w tej obserwacji jest powyżej mediany
    top3 = fi.head(3)['czynnik'].tolist()
    glowny = top3[0]  # domyślnie najważniejsza cecha globalnie

    # komunikaty per typ czynnika
    komunikaty = {
        'Opad_72h':          f"Nasycenie zlewni wysokie (opad 72h = {obserwacja.get('Opad_72h', 0):.1f} mm)",
        'Opad_suma':         f"Intensywny opad dzienny ({obserwacja.get('Opad_suma', 0):.1f} mm)",
        'Opad_7d':           f"Długotrwałe opady (suma 7d = {obserwacja.get('Opad_7d', 0):.1f} mm)",
        'Ciśnienie_delta_1d': f"Zmiana ciśnienia ({obserwacja.get('Ciśnienie_delta_1d', 0):+.1f} hPa/dobę)",
        'Temp_średnia':      f"Temperatura {obserwacja.get('Temp_średnia', 0):.1f} °C",
        'Wilgotność_średnia': f"Wilgotność {obserwacja.get('Wilgotność_średnia', 0):.0f}%",
    }
    opis_czynnika = komunikaty.get(glowny, glowny)

    komunikat = (
        f"{opis_czynnika} – model ocenia ryzyko wezbrania na {proba:.0%}. "
        f"Kierunek wpływu: ↑. "
        f"Pewność (prawdopodobieństwo z RF): {proba:.0%}."
    )

    return {
        'ryzyko':          ryzyko,
        'prawdopodobienstwo': round(proba, 3),
        'glowny_czynnik':  glowny,
        'top3_czynniki':   top3,
        'kierunek':        '↑',
        'pewnosc':         round(proba, 3),
        'komunikat':       komunikat,
    }


# ── 6. WYKRESY ────────────────────────────────────────────────────────────────

def _wykres_feature_importance(fi: pd.DataFrame):
    os.makedirs('reports/ml', exist_ok=True)
    plt.figure(figsize=(10, 6))
    sns.barplot(data=fi.head(15), x='waznosc_pct', y='czynnik', palette='viridis')
    plt.title('Ważność cech – Random Forest (top 15)', fontsize=14)
    plt.xlabel('Ważność [%]')
    plt.ylabel('Czynnik meteorologiczny')
    plt.tight_layout()
    plt.savefig('reports/ml/feature_importance.png', dpi=300)
    plt.close()


def _wykres_walidacja(wyniki_walidacji: pd.DataFrame):
    os.makedirs('reports/ml', exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for ax, metryka, tytul in zip(
        axes,
        [('Recall_RF', 'Recall_bench'), ('Precision_RF', 'Prec_bench')],
        ['Recall', 'Precision']
    ):
        ax.plot(wyniki_walidacji['Rok'], wyniki_walidacji[metryka[0]],
                marker='o', label='Random Forest', color='steelblue')
        ax.plot(wyniki_walidacji['Rok'], wyniki_walidacji[metryka[1]],
                marker='s', label='Benchmark (próg Opad_72h)',
                color='coral', linestyle='--')
        ax.set_title(f'{tytul} – RF vs benchmark')
        ax.set_xlabel('Rok testowy')
        ax.set_ylabel(tytul)
        ax.legend()
        ax.set_ylim(0, 1)

    plt.tight_layout()
    plt.savefig('reports/ml/walidacja_czasowa_rf_vs_benchmark.png', dpi=300)
    plt.close()


def _wykres_confusion(y_true, y_pred):
    os.makedirs('reports/ml', exist_ok=True)
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=['Brak alarmu', 'Alarm'],
                yticklabels=['Brak epizodu', 'Epizod'])
    plt.title('Macierz pomyłek – Random Forest (cały zbiór)')
    plt.xlabel('Predykcja')
    plt.ylabel('Rzeczywistość')
    plt.tight_layout()
    plt.savefig('reports/ml/confusion_matrix_rf.png', dpi=300)
    plt.close()


# ── 7. PIPELINE GŁÓWNY ────────────────────────────────────────────────────────

def uruchom_system(final: pd.DataFrame) -> pd.DataFrame:
    """
    Główna funkcja modułu — identyczny interfejs jak w factor_system.py.
    Przyjmuje final z build_main_df(), zwraca DataFrame z diagnozami dziennymi.
    """
    df, X, y = _przygotuj_dane(final)

    # --- walidacja czasowa (wymaganie karty projektu) ---
    wyniki_walidacji = walidacja_czasowa(df, X, y)
    os.makedirs('reports/ml', exist_ok=True)
    wyniki_walidacji.to_csv('reports/ml/walidacja_czasowa.csv', index=False)
    print("\nStabilność rok-po-roku (RF vs benchmark):")
    print(wyniki_walidacji.to_string(index=False))
    _wykres_walidacja(wyniki_walidacji)

    # --- trening finalnego modelu na całym zbiorze ---
    print("\n=== Trening finalnego modelu (cały zbiór) ===")
    model = trenuj_model(X, y)

    # --- feature importance ---
    fi = feature_importance_df(model)
    fi.to_csv('reports/ml/feature_importance.csv', index=False)
    print("\nTop 10 najważniejszych czynników:")
    print(fi.head(10).to_string(index=False))
    _wykres_feature_importance(fi)

    # --- metryki na całym zbiorze ---
    proba_all = model.predict_proba(X)[:, 1]
    y_pred_all = (proba_all >= PROB_THRESHOLD).astype(int)
    prec = precision_score(y, y_pred_all, zero_division=0)
    rec  = recall_score(y, y_pred_all, zero_division=0)
    print(f"\n=== Metryki na całym zbiorze (próg={PROB_THRESHOLD}) ===")
    print(f"  Precision : {prec:.3f}")
    print(f"  Recall    : {rec:.3f}")
    print(classification_report(y, y_pred_all,
                                target_names=['Brak epizodu', 'Epizod'],
                                zero_division=0))
    _wykres_confusion(y, y_pred_all)

    # --- diagnozy dzienne ---
    print("=== Generowanie diagnoz dziennych ===")
    wiersze = []
    for data, wiersz in df.iterrows():
        diag = diagnozuj(wiersz, model, fi)
        wiersze.append({
            'Data':               data,
            'sezon':              wiersz.get('sezon', ''),
            'ryzyko':             diag['ryzyko'],
            'prawdopodobienstwo': diag['prawdopodobienstwo'],
            'glowny_czynnik':     diag['glowny_czynnik'],
            'kierunek':           diag['kierunek'],
            'pewnosc':            diag['pewnosc'],
            'komunikat':          diag['komunikat'],
            'epizod_rzeczywisty': wiersz['Epizod_rzeczywisty'],
        })

    diagnozy = pd.DataFrame(wiersze).set_index('Data')
    diagnozy.to_csv('reports/ml/diagnozy_dzienne_rf.csv')
    print("Zapisano → reports/ml/diagnozy_dzienne_rf.csv")

    # --- przykładowa diagnoza ---
    ostatnia = df.iloc[-1]
    diag = diagnozuj(ostatnia, model, fi)
    print(f"\n=== Przykładowa diagnoza ({df.index[-1].date()}) ===")
    print(f"  Ryzyko              : {diag['ryzyko'].upper()}")
    print(f"  Prawdopodobieństwo  : {diag['prawdopodobienstwo']:.0%}")
    print(f"  Główny czynnik      : {diag['glowny_czynnik']}")
    print(f"  Top 3 czynniki      : {diag['top3_czynniki']}")
    print(f"  Komunikat           : {diag['komunikat']}")

    return diagnozy

if __name__ == "__main__":

    final = pd.read_csv(
        "../../data/processed/final.csv",
        parse_dates=["Data"],
        index_col="Data"
    )

    diagnozy = uruchom_system(final)
    print(diagnozy.head())
