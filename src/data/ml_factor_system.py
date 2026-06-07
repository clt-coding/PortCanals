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

import datetime

def zapisz_wyniki_do_historii(wyniki_walidacji, precision, recall, prob_threshold):
    plik_historia = 'reports/ml/historia_eksperymentow.txt'
    avg_f1 = wyniki_walidacji['F1_RF'].mean()
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(plik_historia, "a", encoding="utf-8") as f:
        f.write(f"\n--- EKSPERYMENT: {timestamp} ---\n")
        f.write(f"PROB_THRESHOLD: {prob_threshold}\n")
        f.write(f"Średnie F1 (walidacja): {avg_f1:.3f}\n")
        f.write(f"Finalne Precision: {precision:.3f}\n")
        f.write(f"Finalne Recall: {recall:.3f}\n")
        f.write("-" * 30 + "\n")
    
    print(f"\n[INFO] Wyniki zapisano do {plik_historia}")
# ── KONFIGURACJA ──────────────────────────────────────────────────────────────

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

STACJE = {
    'Strzyza':        {'max': 'Poziom_wody_max',    'srednia': 'Poziom_wody_średnia'},
    'Martwa_Wisla':   {'max': 'Martwa_Wisla_max',   'srednia': 'Martwa_Wisla_średnia'},
    'Port_Polnocny':  {'max': 'Port_Polnocny_max',  'srednia': 'Port_Polnocny_średnia'},
}

EPIZOD_PERCENTYL = 0.90

# ZMIANA: AND (>=2 stacje) zamiast OR — eliminuje szum od pojedynczych stacji.
# Analiza wykazała, że 28% dni OR to sygnały tylko z 1 stacji; model nie był w stanie
# odróżnić takich przypadków od pogody, stąd niski recall w 2022 i 2025.
EPIZOD_MIN_STACJI = 2

# Minimalna liczba lat treningowych — poniżej tej granicy RF nie ma wystarczającej
# wiedzy o zmienności sezonowej, co skutkuje zdegenerowanymi wynikami (patrz 2022).
MIN_TRAIN_YEARS = 2   # epizod jeśli przynajmniej EPIZOD_MIN_STACJI stacji przekracza próg

RF_PARAMS = {
    'n_estimators':   300,
    'max_depth':      None,
    'min_samples_leaf': 15,
    'class_weight':  'balanced',
    'random_state':   42,
    'n_jobs':        -1,
}

# ZMIANA: 0.50 — przy AND target ma niższą prevalencję (~10%),
# nieco niższy próg poprawia recall bez istotnej utraty precision.
PROB_THRESHOLD = 0.50


# ── 1. PRZYGOTOWANIE DANYCH ───────────────────────────────────────────────────

def _buduj_epizody(df: pd.DataFrame, train_mask: pd.Series) -> pd.DataFrame:
    """
    Tworzy kolumny Epizod_<stacja> używając progu p90 liczonego WYŁĄCZNIE
    na danych treningowych (train_mask). Eliminuje data leakage — poprzednia
    wersja liczyła p90 na całym zbiorze, przez co próg „widział" dane testowe.

    Epizod_rzeczywisty = 1 jeśli przynajmniej EPIZOD_MIN_STACJI stacji przekracza próg.
    """
    for nazwa, kolumny in STACJE.items():
        col_max = kolumny['max']
        if col_max not in df.columns:
            raise ValueError(f"Brak kolumny '{col_max}'. Dostępne: {df.columns.tolist()}")
        threshold = df.loc[train_mask, col_max].quantile(EPIZOD_PERCENTYL)
        df[f'Epizod_{nazwa}'] = (df[col_max] >= threshold).astype(int)
        df[f'Prog_{nazwa}'] = threshold   # zapisujemy próg do diagnostyki

    suma_stacji = sum(df[f'Epizod_{n}'] for n in STACJE)
    df['Epizod_rzeczywisty'] = (suma_stacji >= EPIZOD_MIN_STACJI).astype(int)
    return df


def _przygotuj_dane(final: pd.DataFrame):
    """
    Wersja dla finalnego modelu (trening na całym zbiorze):
    próg p90 liczony na całym zbiorze — nie ma podziału train/test.
    """
    df = final.copy()
    all_mask = pd.Series(True, index=df.index)
    df = _buduj_epizody(df, train_mask=all_mask)

    brakujace = [f for f in FEATURES if f not in df.columns]
    if brakujace:
        raise ValueError(f"Brakujące kolumny cech: {brakujace}")

    X = df[FEATURES]
    y = df['Epizod_rzeczywisty']
    return df, X, y


# ── 2. WALIDACJA CZASOWA (rok po roku) ───────────────────────────────────────

def walidacja_czasowa(final: pd.DataFrame) -> pd.DataFrame:
    """
    Walk-forward validation z prawidłowym rolling threshold:
    progi p90 per stacja liczone TYLKO z danych treningowych danej iteracji.
    Model nigdy nie „widzi" przyszłości przy tworzeniu targetu.
    """
    lata = sorted(final.index.year.unique())
    wyniki = []

    print("=== Walidacja czasowa (walk-forward, rolling threshold) ===")

    for i, rok_test in enumerate(lata):
        if i == 0:
            continue

        maska_train = final.index.year < rok_test
        maska_test  = final.index.year == rok_test

        n_lat_train = len(set(final.index.year[final.index.year < rok_test]))
        if n_lat_train < MIN_TRAIN_YEARS or maska_test.sum() < 10:
            print(f"  {rok_test}: pominięto (tylko {n_lat_train} lat treningowych < MIN_TRAIN_YEARS={MIN_TRAIN_YEARS})")
            continue

        # Kluczowe: budujemy epizody z progiem tylko z lat treningowych
        df_iter = final.copy()
        df_iter = _buduj_epizody(df_iter, train_mask=maska_train)

        X = df_iter[FEATURES]
        y = df_iter['Epizod_rzeczywisty']

        X_train, y_train = X[maska_train], y[maska_train]
        X_test,  y_test  = X[maska_test],  y[maska_test]

        if y_train.sum() < 5:
            continue

        model = RandomForestClassifier(**RF_PARAMS)
        model.fit(X_train, y_train)

        proba  = model.predict_proba(X_test)[:, 1]
        y_pred = (proba >= PROB_THRESHOLD).astype(int)

        prec = precision_score(y_test, y_pred, zero_division=0)
        rec  = recall_score(y_test, y_pred, zero_division=0)

        # benchmark: próg Opad_72h z danych treningowych
        prog_benchmark = X_train['Opad_72h'].quantile(EPIZOD_PERCENTYL)
        y_bench = (X_test['Opad_72h'] >= prog_benchmark).astype(int)
        prec_b = precision_score(y_test, y_bench, zero_division=0)
        rec_b  = recall_score(y_test, y_bench, zero_division=0)

        epizody_per_stacja = {
            n: int(df_iter.loc[maska_test, f'Epizod_{n}'].sum())
            for n in STACJE
        }

        wyniki.append({
            'Rok':          rok_test,
            'Recall_RF':    round(rec,   3),
            'Precision_RF': round(prec,  3),
            'F1_RF':        round(2*rec*prec/(rec+prec) if (rec+prec) > 0 else 0, 3),
            'Recall_bench': round(rec_b, 3),
            'Prec_bench':   round(prec_b, 3),
            'n_epizodow':   int(y_test.sum()),
            'n_dni':        int(maska_test.sum()),
            **{f'epizody_{n}': v for n, v in epizody_per_stacja.items()},
        })

        print(f"  {rok_test}: RF recall={rec:.3f} prec={prec:.3f} F1={wyniki[-1]['F1_RF']:.3f} | "
              f"benchmark recall={rec_b:.3f} prec={prec_b:.3f} | "
              f"epizody(>=2 stacje)={int(y_test.sum())} "
              f"({', '.join(f'{n}={v}' for n, v in epizody_per_stacja.items())})")

    return pd.DataFrame(wyniki)


# ── 3. TRENING FINALNEGO MODELU ───────────────────────────────────────────────

def trenuj_model(X: pd.DataFrame, y: pd.Series) -> RandomForestClassifier:
    model = RandomForestClassifier(**RF_PARAMS)
    model.fit(X, y)
    return model


# ── 4. FEATURE IMPORTANCE ────────────────────────────────────────────────────

def feature_importance_df(model: RandomForestClassifier) -> pd.DataFrame:
    fi = pd.DataFrame({
        'czynnik': FEATURES,
        'waznosc': model.feature_importances_,
    }).sort_values('waznosc', ascending=False).reset_index(drop=True)
    fi['waznosc_pct'] = (fi['waznosc'] * 100).round(2)
    return fi


# ── 5. DIAGNOZA DLA JEDNEJ OBSERWACJI ────────────────────────────────────────

def diagnozuj(obserwacja: pd.Series,
              model: RandomForestClassifier,
              fi: pd.DataFrame, poprzednia_proba=None) -> dict:
    X_obs = obserwacja[FEATURES].to_frame().T
    proba = model.predict_proba(X_obs)[0, 1]

    if poprzednia_proba is None:
        kierunek = 'bez zmian'
    elif proba > poprzednia_proba:
        kierunek = 'wzrost'
    elif proba < poprzednia_proba:
        kierunek = 'spadek'
    else:
        kierunek = 'bez zmian'

    if proba >= 0.65:
        ryzyko = 'wysokie'
    elif proba >= PROB_THRESHOLD:
        ryzyko = 'średnie'
    else:
        ryzyko = 'niskie'

    top3 = fi.head(3)['czynnik'].tolist()
    glowny = top3[0]

    komunikaty = {
        'Opad_72h':           f"Nasycenie zlewni wysokie (opad 72h = {obserwacja.get('Opad_72h', 0):.1f} mm)",
        'Opad_suma':          f"Intensywny opad dzienny ({obserwacja.get('Opad_suma', 0):.1f} mm)",
        'Opad_7d':            f"Długotrwałe opady (suma 7d = {obserwacja.get('Opad_7d', 0):.1f} mm)",
        'Ciśnienie_delta_1d': f"Zmiana ciśnienia ({obserwacja.get('Ciśnienie_delta_1d', 0):+.1f} hPa/dobę)",
        'Temp_średnia':       f"Temperatura {obserwacja.get('Temp_średnia', 0):.1f} °C",
        'Wilgotność_średnia': f"Wilgotność {obserwacja.get('Wilgotność_średnia', 0):.0f}%",
    }
    opis_czynnika = komunikaty.get(glowny, glowny)

    status_stacji = {
        nazwa: bool(obserwacja.get(f'Epizod_{nazwa}', 0))
        for nazwa in STACJE
    }

    komunikat = (
        f"{opis_czynnika} – model ocenia ryzyko wezbrania na {proba:.0%}. "
        f"Kierunek wpływu: {kierunek}. "
        f"Pewność (prawdopodobieństwo z RF): {proba:.0%}."
    )

    return {
        'ryzyko':             ryzyko,
        'prawdopodobienstwo': round(proba, 3),
        'glowny_czynnik':     glowny,
        'top3_czynniki':      top3,
        'kierunek':           kierunek,
        'pewnosc':            round(proba, 3),
        'komunikat':          komunikat,
        'status_stacji':      status_stacji,
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
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    for ax, metryki, tytul in zip(
        axes,
        [('Recall_RF', 'Recall_bench'), ('Precision_RF', 'Prec_bench'), ('F1_RF', None)],
        ['Recall', 'Precision', 'F1 (RF)']
    ):
        ax.plot(wyniki_walidacji['Rok'], wyniki_walidacji[metryki[0]],
                marker='o', label='Random Forest', color='steelblue')
        if metryki[1] and metryki[1] in wyniki_walidacji.columns:
            ax.plot(wyniki_walidacji['Rok'], wyniki_walidacji[metryki[1]],
                    marker='s', label='Benchmark (próg Opad_72h)',
                    color='coral', linestyle='--')
        ax.set_title(f'{tytul}')
        ax.set_xlabel('Rok testowy')
        ax.set_ylabel(tytul)
        ax.legend()
        ax.set_ylim(0, 1)
        ax.axhline(0.5, color='gray', linestyle=':', alpha=0.5)

    plt.suptitle(f'Walidacja czasowa RF (target: ≥{EPIZOD_MIN_STACJI} stacje p{int(EPIZOD_PERCENTYL*100)}, thresh={PROB_THRESHOLD})',
                 fontsize=12)
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
    plt.title(f'Macierz pomyłek – RF (target: ≥{EPIZOD_MIN_STACJI} stacji)')
    plt.xlabel('Predykcja')
    plt.ylabel('Rzeczywistość')
    plt.tight_layout()
    plt.savefig('reports/ml/confusion_matrix_rf.png', dpi=300)
    plt.close()


def _wykres_epizody_per_stacja(df: pd.DataFrame):
    os.makedirs('reports/ml', exist_ok=True)
    roczne = {}
    for nazwa in STACJE:
        col = f'Epizod_{nazwa}'
        if col in df.columns:
            roczne[nazwa] = df.groupby(df.index.year)[col].sum()
    if not roczne:
        return
    roczne['Łącznie (>= 2)'] = df.groupby(df.index.year)['Epizod_rzeczywisty'].sum()
    plot_df = pd.DataFrame(roczne)
    ax = plot_df.plot(kind='bar', figsize=(12, 5), colormap='tab10')
    ax.set_title(f'Liczba epizodów p{int(EPIZOD_PERCENTYL*100)} per stacja i rok')
    ax.set_xlabel('Rok')
    ax.set_ylabel('Liczba dni epizodowych')
    ax.legend(title='Stacja')
    plt.tight_layout()
    plt.savefig('reports/ml/epizody_per_stacja.png', dpi=300)
    plt.close()


# ── 7. PIPELINE GŁÓWNY ────────────────────────────────────────────────────────

def uruchom_system(final: pd.DataFrame) -> pd.DataFrame:
    """
    Główna funkcja modułu. Przyjmuje final z build_main_df() lub wczytany z final.csv.

    Zmiany względem v1 (OR global):
      - target: AND>=2 stacje zamiast OR — eliminuje szum z pojedynczych stacji
        (analiza wykazała 28% dni OR było sygnalizowanych tylko przez 1 stację)
      - rolling threshold: p90 w walidacji liczony wyłącznie z danych treningowych
        (poprzednio: globalny p90 = data leakage w definicji targetu)
      - PROB_THRESHOLD: 0.35 zamiast 0.40 — lepszy recall przy AND target
      - walidacja zwraca teraz F1 obok recall/precision
      - wykres walidacji zawiera 3 panele (recall, precision, F1)
    """
    # Trening finalnego modelu z globalnym progiem (brak podziału train/test)
    df, X, y = _przygotuj_dane(final)

    print(f"=== Epizody wysokiej wody (p{int(EPIZOD_PERCENTYL*100)}, >= {EPIZOD_MIN_STACJI} stacji) ===")
    for nazwa, kolumny in STACJE.items():
        col_epizod = f'Epizod_{nazwa}'
        prog = df[f'Prog_{nazwa}'].iloc[0]
        n = int(df[col_epizod].sum())
        print(f"  {nazwa:20s}: próg={prog:.3f}, epizodów={n} ({100*n/len(df):.1f}%)")
    print(f"  {'Łącznie (>= 2 stacji)':20s}: epizodów={int(y.sum())} ({100*y.mean():.1f}%)")

    # Walidacja czasowa z rolling threshold
    wyniki_walidacji = walidacja_czasowa(final)
    os.makedirs('reports/ml', exist_ok=True)
    wyniki_walidacji.to_csv('reports/ml/walidacja_czasowa.csv', index=False)
    print("\nPodsumowanie walidacji:")
    print(wyniki_walidacji[['Rok','Recall_RF','Precision_RF','F1_RF',
                             'Recall_bench','Prec_bench','n_epizodow']].to_string(index=False))
    avg_recall = wyniki_walidacji['Recall_RF'].mean()
    avg_prec   = wyniki_walidacji['Precision_RF'].mean()
    avg_f1     = wyniki_walidacji['F1_RF'].mean()
    print(f"  Średnie: recall={avg_recall:.3f}, prec={avg_prec:.3f}, F1={avg_f1:.3f}")
    _wykres_walidacja(wyniki_walidacji)
    _wykres_epizody_per_stacja(df)

    # Trening finalnego modelu
    print(f"\n=== Trening finalnego modelu (cały zbiór, target >= {EPIZOD_MIN_STACJI} stacji) ===")
    model = trenuj_model(X, y)

    fi = feature_importance_df(model)
    fi.to_csv('reports/ml/feature_importance.csv', index=False)
    print("\nTop 10 najważniejszych czynników:")
    print(fi.head(10).to_string(index=False))
    _wykres_feature_importance(fi)

    proba_all  = model.predict_proba(X)[:, 1]
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

    # Diagnozy dzienne
    print("=== Generowanie diagnoz dziennych ===")
    wiersze = []
    poprzednia_proba = None
    for data, wiersz in df.iterrows():
        diag = diagnozuj(wiersz, model, fi, poprzednia_proba=poprzednia_proba)
        poprzednia_proba = diag['prawdopodobienstwo']
        wiersz_out = {
            'Data':               data,
            'sezon':              wiersz.get('sezon', ''),
            'ryzyko':             diag['ryzyko'],
            'prawdopodobienstwo': diag['prawdopodobienstwo'],
            'glowny_czynnik':     diag['glowny_czynnik'],
            'kierunek':           diag['kierunek'],
            'pewnosc':            diag['pewnosc'],
            'komunikat':          diag['komunikat'],
            'epizod_rzeczywisty': wiersz['Epizod_rzeczywisty'],
        }
        for nazwa in STACJE:
            wiersz_out[f'epizod_{nazwa}'] = int(wiersz.get(f'Epizod_{nazwa}', 0))
        wiersze.append(wiersz_out)

    diagnozy = pd.DataFrame(wiersze).set_index('Data')
    diagnozy.to_csv('reports/ml/diagnozy_dzienne_rf.csv')
    print("Zapisano -> reports/ml/diagnozy_dzienne_rf.csv")

    ostatnia = df.iloc[-1]
    przedostatnia_proba = diagnozy['prawdopodobienstwo'].iloc[-2] if len(diagnozy) > 1 else None
    diag = diagnozuj(ostatnia, model, fi, poprzednia_proba=przedostatnia_proba)
    print(f"\n=== Przykładowa diagnoza ({df.index[-1].date()}) ===")
    print(f"  Ryzyko             : {diag['ryzyko'].upper()}")
    print(f"  Prawdopodobieństwo : {diag['prawdopodobienstwo']:.0%}")
    print(f"  Główny czynnik     : {diag['glowny_czynnik']}")
    print(f"  Top 3 czynniki     : {diag['top3_czynniki']}")
    print(f"  Status per stacja  : {diag['status_stacji']}")
    print(f"  Komunikat          : {diag['komunikat']}")

    zapisz_wyniki_do_historii(wyniki_walidacji, prec, rec, PROB_THRESHOLD)
    return diagnozy


if __name__ == "__main__":

    final = pd.read_csv(
        "data/processed/final.csv",
        parse_dates=["Data"],
        index_col="Data"
    )

    diagnozy = uruchom_system(final)
    # Analiza fałszywych alarmów
    def przeanalizuj_bledy(diagnozy):
    # Alarm to przypadek, gdy prawdopodobieństwo >= PROB_THRESHOLD
        alarmy = diagnozy[diagnozy['prawdopodobienstwo'] >= PROB_THRESHOLD]
    
    # Fałszywe alarmy: model daje alarm, a epizod_rzeczywisty == 0
        false_positives = alarmy[alarmy['epizod_rzeczywisty'] == 0]
    
        print(f"\n--- ANALIZA FAŁSZYWYCH ALARMÓW ---")
        print(f"Liczba fałszywych alarmów: {len(false_positives)}")
    
        if not false_positives.empty:
            print("\nPrzykładowe 5 dni z fałszywym alarmem:")
            print(false_positives[['prawdopodobienstwo', 'glowny_czynnik', 'komunikat']].head())
        
        # Sprawdźmy, czy te fałszywe alarmy to może "prawie-epizody"
        # Jeśli główny czynnik to często 'Opad_72h', to znaczy, że model reaguje na opad,
        # który NIE spowodował przekroczenia progu (ale był wysoki).
            print("\nNajczęstsze czynniki przy fałszywych alarmach:")
            print(false_positives['glowny_czynnik'].value_counts())

        przeanalizuj_bledy(diagnozy)
    print(diagnozy.head())