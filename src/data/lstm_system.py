# Użycie:
#   from src.data.lstm_system import uruchom_system_lstm
#   diagnozy_lstm = uruchom_system_lstm(final)
#
# Moduł jest celowo symetryczny do ml_factor_system.py — te same cechy,
# ten sam target (≥2 stacje p90), ta sama walidacja walk-forward.
# Dzięki temu wyniki są bezpośrednio porównywalne.

import os
import datetime
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.metrics import (
    precision_score, recall_score, confusion_matrix, classification_report
)
from sklearn.preprocessing import StandardScaler

# TensorFlow/Keras — importujemy tu, żeby błąd był widoczny od razu
try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
    from tensorflow.keras.optimizers import Adam
except ImportError as e:
    raise ImportError(
        "TensorFlow nie jest zainstalowany. Uruchom: pip install tensorflow"
    ) from e


# ── KONFIGURACJA (identyczna z ml_factor_system.py) ──────────────────────────

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

EPIZOD_PERCENTYL  = 0.90
EPIZOD_MIN_STACJI = 2
MIN_TRAIN_YEARS   = 2

# ── HIPERPARAMETRY LSTM ───────────────────────────────────────────────────────

# Ile poprzednich dni model „widzi" przy jednej predykcji.
# Wartość 7 oznacza: cechy z dni t-6…t → predykcja na dzień t.
# Dobrana eksperymentalnie: mniejsze okno (<5) gubi trendy sezonowe,
# większe (>14) wydłuża trening i może powodować overfitting na małym zbiorze.
SEQ_LEN = 7

LSTM_PARAMS = {
    'units_1':       64,    # neurony w pierwszej warstwie LSTM
    'units_2':       32,    # neurony w drugiej warstwie LSTM
    'dropout':       0.5,   # dropout między warstwami (regularizacja)
    'learning_rate': 1e-3,
    'batch_size':    32,
    'epochs':        100,   # EarlyStopping zatrzyma wcześniej
    'patience':      10,    # cierpliwość EarlyStopping
}

PROB_THRESHOLD = 0.50       # identyczny z RF dla uczciwego porównania


# ── 1. PRZYGOTOWANIE DANYCH ───────────────────────────────────────────────────

def _buduj_epizody(df: pd.DataFrame, train_mask: pd.Series) -> pd.DataFrame:
    """
    Identyczna logika jak w ml_factor_system.py.
    Próg p90 liczony wyłącznie na danych treningowych → brak data leakage.
    """
    for nazwa, kolumny in STACJE.items():
        col_max = kolumny['max']
        if col_max not in df.columns:
            raise ValueError(f"Brak kolumny '{col_max}'. Dostępne: {df.columns.tolist()}")
        threshold = df.loc[train_mask, col_max].quantile(EPIZOD_PERCENTYL)
        df[f'Epizod_{nazwa}'] = (df[col_max] >= threshold).astype(int)
        df[f'Prog_{nazwa}']   = threshold

    suma_stacji = sum(df[f'Epizod_{n}'] for n in STACJE)
    df['Epizod_rzeczywisty'] = (suma_stacji >= EPIZOD_MIN_STACJI).astype(int)
    return df


def _buduj_sekwencje(X: np.ndarray, y: np.ndarray, seq_len: int):
    """
    Przekształca płaskie tablice (n_dni × n_cech) w 3D tensor (n_sekwencji × seq_len × n_cech).
    Etykieta sekwencji = etykieta ostatniego dnia w oknie.

    Przykład przy seq_len=7:
      sekwencja 0: X[0:7]  → y[6]
      sekwencja 1: X[1:8]  → y[7]
      ...
    """
    Xs, ys = [], []
    for i in range(len(X) - seq_len + 1):
        Xs.append(X[i : i + seq_len])
        ys.append(y[i + seq_len - 1])
    return np.array(Xs, dtype=np.float32), np.array(ys, dtype=np.float32)


def _przygotuj_dane(final: pd.DataFrame):
    """
    Wersja dla finalnego modelu (trening na całym zbiorze).
    Zwraca df, X_arr (3D), y_arr (1D).
    """
    df = final.copy()
    all_mask = pd.Series(True, index=df.index)
    df = _buduj_epizody(df, train_mask=all_mask)

    brakujace = [f for f in FEATURES if f not in df.columns]
    if brakujace:
        raise ValueError(f"Brakujące kolumny cech: {brakujace}")

    X_flat = df[FEATURES].values.astype(np.float32)
    y_flat = df['Epizod_rzeczywisty'].values.astype(np.float32)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_flat)

    X_seq, y_seq = _buduj_sekwencje(X_scaled, y_flat, SEQ_LEN)
    # Daty odpowiadające etykietom (ostatni dzień każdej sekwencji)
    daty_seq = df.index[SEQ_LEN - 1:]

    return df, X_seq, y_seq, daty_seq, scaler


# ── 2. BUDOWA MODELU ──────────────────────────────────────────────────────────

def _buduj_model(n_features: int, p: dict) -> Sequential:
    """
    Architektura:
      LSTM(64, return_sequences=True)
        → BatchNormalization → Dropout(0.5)
      LSTM(32)
        → BatchNormalization → Dropout(0.5)
      Dense(16, relu)
      Dense(1, sigmoid)   ← wyjście: P(epizod)

    Uzasadnienie głębokości:
      - Dwie warstwy LSTM: pierwsza wychwytuje krótkoterminowe wzorce (kolejność deszczy),
        druga — dłuższe trendy sezonowe zakodowane w sin/cos_doy.
      - BatchNorm przyspiesza zbieżność i stabilizuje gradienty.
      - Dropout(0.5) ogranicza overfitting na ~1600 próbkach treningowych.
    """
    model = Sequential([
        LSTM(p['units_1'], input_shape=(SEQ_LEN, n_features), return_sequences=False),
        BatchNormalization(),
        Dropout(p['dropout']),

        Dense(32, activation='relu'),
        Dropout(p['dropout']),
        Dense(1,  activation='sigmoid'),
    ])

    model.compile(
        optimizer=Adam(learning_rate=p['learning_rate']),
        loss='binary_crossentropy',
        metrics=['AUC'],
    )
    return model

# ── 3. WALIDACJA CZASOWA (walk-forward, identyczna z RF) ─────────────────────

def walidacja_czasowa(final: pd.DataFrame) -> pd.DataFrame:
    """
    Walk-forward validation rok-po-roku.
    Dla każdego roku testowego:
      1. Budujemy epizody z progiem p90 tylko z lat treningowych.
      2. Skalujemy cechy TYLKO na danych treningowych (fit na train, transform na obu).
      3. Trenujemy LSTM z EarlyStopping.
      4. Oceniamy na danych testowych.

    Benchmark: próg Opad_72h z danych treningowych (jak w RF).
    """
    lata = sorted(final.index.year.unique())
    wyniki = []

    print("=== Walidacja czasowa LSTM (walk-forward) ===")

    for i, rok_test in enumerate(lata):
        if i == 0:
            continue

        maska_train = final.index.year < rok_test
        maska_test  = final.index.year == rok_test

        n_lat_train = len(set(final.index.year[final.index.year < rok_test]))
        if n_lat_train < MIN_TRAIN_YEARS or maska_test.sum() < SEQ_LEN + 5:
            print(f"  {rok_test}: pominięto ({n_lat_train} lat treningowych)")
            continue

        df_iter = final.copy()
        df_iter = _buduj_epizody(df_iter, train_mask=maska_train)

        X_flat = df_iter[FEATURES].values.astype(np.float32)
        y_flat = df_iter['Epizod_rzeczywisty'].values.astype(np.float32)

        # Skalowanie: fit tylko na train
        idx_train_end = maska_train.sum()
        scaler = StandardScaler()
        X_flat[:idx_train_end] = scaler.fit_transform(X_flat[:idx_train_end])
        X_flat[idx_train_end:] = scaler.transform(X_flat[idx_train_end:])

        X_seq, y_seq = _buduj_sekwencje(X_flat, y_flat, SEQ_LEN)

        # Maska sekwencji: sekwencja należy do testu, jeśli jej ostatni dzień jest testowy
        daty_all = df_iter.index[SEQ_LEN - 1:]
        mask_seq_train = daty_all.year < rok_test
        mask_seq_test  = daty_all.year == rok_test

        X_train_s, y_train_s = X_seq[mask_seq_train], y_seq[mask_seq_train]
        X_test_s,  y_test_s  = X_seq[mask_seq_test],  y_seq[mask_seq_test]

        if y_train_s.sum() < 5 or len(X_test_s) == 0:
            continue

        # Obliczamy class_weight ręcznie, bo Keras nie ma parametru jak sklearn
        n_pos = int(y_train_s.sum())
        n_neg = len(y_train_s) - n_pos
        pos_weight = n_neg / max(n_pos, 1)
        sample_weights = np.where(y_train_s == 1, pos_weight, 1.0)

        model = _buduj_model(len(FEATURES), LSTM_PARAMS)

        callbacks = [
            EarlyStopping(monitor='val_loss', patience=LSTM_PARAMS['patience'],
                          restore_best_weights=True, verbose=0),
            ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, verbose=0),
        ]

        model.fit(
            X_train_s, y_train_s,
            sample_weight=sample_weights,
            validation_split=0.15,
            epochs=LSTM_PARAMS['epochs'],
            batch_size=LSTM_PARAMS['batch_size'],
            callbacks=callbacks,
            verbose=0,
        )

        proba  = model.predict(X_test_s, verbose=0).ravel()
        y_pred = (proba >= PROB_THRESHOLD).astype(int)

        prec = precision_score(y_test_s, y_pred, zero_division=0)
        rec  = recall_score(y_test_s, y_pred, zero_division=0)
        f1   = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0

        # Benchmark (identyczny z RF)
        opad72_train = df_iter.loc[maska_train, 'Opad_72h']
        prog_bench   = opad72_train.quantile(EPIZOD_PERCENTYL)
        opad72_test  = df_iter.loc[maska_test, 'Opad_72h'].values[SEQ_LEN - 1:]
        # Wyrównujemy długość (sekwencje mogą skrócić zbiór)
        min_len = min(len(opad72_test), len(y_test_s))
        y_bench = (opad72_test[:min_len] >= prog_bench).astype(int)
        prec_b = precision_score(y_test_s[:min_len], y_bench, zero_division=0)
        rec_b  = recall_score(y_test_s[:min_len],  y_bench, zero_division=0)

        wyniki.append({
            'Rok':           rok_test,
            'Recall_LSTM':   round(rec,    3),
            'Precision_LSTM':round(prec,   3),
            'F1_LSTM':       round(f1,     3),
            'Recall_bench':  round(rec_b,  3),
            'Prec_bench':    round(prec_b, 3),
            'n_epizodow':    int(y_test_s.sum()),
            'n_dni':         int(mask_seq_test.sum()),
        })

        print(f"  {rok_test}: LSTM recall={rec:.3f} prec={prec:.3f} F1={f1:.3f} | "
              f"benchmark recall={rec_b:.3f} prec={prec_b:.3f} | "
              f"epizody(≥2 stacje)={int(y_test_s.sum())}")

    return pd.DataFrame(wyniki)


# ── 4. TRENING FINALNEGO MODELU ───────────────────────────────────────────────

def trenuj_model(X_seq: np.ndarray, y_seq: np.ndarray) -> Sequential:
    """Trenuje finalny LSTM na całym zbiorze."""
    n_pos = int(y_seq.sum())
    n_neg = len(y_seq) - n_pos
    pos_weight = n_neg / max(n_pos, 1)
    sample_weights = np.where(y_seq == 1, pos_weight, 1.0)

    model = _buduj_model(X_seq.shape[2], LSTM_PARAMS)

    callbacks = [
        EarlyStopping(monitor='val_loss', patience=LSTM_PARAMS['patience'],
                      restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, verbose=0),
    ]

    history = model.fit(
        X_seq, y_seq,
        sample_weight=sample_weights,
        validation_split=0.15,
        epochs=LSTM_PARAMS['epochs'],
        batch_size=LSTM_PARAMS['batch_size'],
        callbacks=callbacks,
        verbose=1,
    )
    return model, history


# ── 5. WYKRESY ────────────────────────────────────────────────────────────────

def _wykres_walidacja(wyniki_walidacji: pd.DataFrame):
    os.makedirs('reports/ml', exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    for ax, metryki, tytul in zip(
        axes,
        [('Recall_LSTM', 'Recall_bench'), ('Precision_LSTM', 'Prec_bench'), ('F1_LSTM', None)],
        ['Recall', 'Precision', 'F1 (LSTM)'],
    ):
        ax.plot(wyniki_walidacji['Rok'], wyniki_walidacji[metryki[0]],
                marker='o', label='LSTM', color='darkorange')
        if metryki[1] and metryki[1] in wyniki_walidacji.columns:
            ax.plot(wyniki_walidacji['Rok'], wyniki_walidacji[metryki[1]],
                    marker='s', label='Benchmark (próg Opad_72h)',
                    color='coral', linestyle='--')
        ax.set_title(tytul)
        ax.set_xlabel('Rok testowy')
        ax.set_ylabel(tytul)
        ax.legend()
        ax.set_ylim(0, 1)
        ax.axhline(0.5, color='gray', linestyle=':', alpha=0.5)

    plt.suptitle(
        f'Walidacja czasowa LSTM (target: ≥{EPIZOD_MIN_STACJI} stacje p{int(EPIZOD_PERCENTYL*100)}, '
        f'thresh={PROB_THRESHOLD}, seq_len={SEQ_LEN})',
        fontsize=11,
    )
    plt.tight_layout()
    plt.savefig('reports/ml/walidacja_czasowa_lstm_vs_benchmark.png', dpi=300)
    plt.close()
    print("Wykres walidacji → reports/ml/walidacja_czasowa_lstm_vs_benchmark.png")


def _wykres_confusion(y_true, y_pred):
    os.makedirs('reports/ml', exist_ok=True)
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Oranges',
                xticklabels=['Brak alarmu', 'Alarm'],
                yticklabels=['Brak epizodu', 'Epizod'])
    plt.title(f'Macierz pomyłek – LSTM (target: ≥{EPIZOD_MIN_STACJI} stacji)')
    plt.xlabel('Predykcja')
    plt.ylabel('Rzeczywistość')
    plt.tight_layout()
    plt.savefig('reports/ml/confusion_matrix_lstm.png', dpi=300)
    plt.close()
    print("Macierz pomyłek → reports/ml/confusion_matrix_lstm.png")


def _wykres_historia_treningu(history):
    os.makedirs('reports/ml', exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    axes[0].plot(history.history['loss'],     label='train loss')
    axes[0].plot(history.history['val_loss'], label='val loss')
    axes[0].set_title('Loss podczas treningu')
    axes[0].set_xlabel('Epoka')
    axes[0].set_ylabel('Binary crossentropy')
    axes[0].legend()

    axes[1].plot(history.history.get('auc', history.history.get('AUC', [])),     label='train AUC')
    axes[1].plot(history.history.get('val_auc', history.history.get('val_AUC', [])), label='val AUC')
    axes[1].set_title('AUC podczas treningu')
    axes[1].set_xlabel('Epoka')
    axes[1].set_ylabel('AUC')
    axes[1].legend()

    plt.tight_layout()
    plt.savefig('reports/ml/lstm_historia_treningu.png', dpi=300)
    plt.close()
    print("Historia treningu → reports/ml/lstm_historia_treningu.png")


def _wykres_porownanie_rf_lstm(wyniki_rf_path: str, wyniki_lstm: pd.DataFrame):
    """
    Wczytuje wyniki RF z CSV i rysuje porównanie F1 RF vs LSTM.
    Jeśli plik RF nie istnieje, pomija wykres.
    """
    if not os.path.exists(wyniki_rf_path):
        print(f"[INFO] Brak {wyniki_rf_path} — pomijam wykres porównawczy RF vs LSTM.")
        return

    wyniki_rf = pd.read_csv(wyniki_rf_path)
    merged = wyniki_lstm.merge(
        wyniki_rf[['Rok', 'Recall_RF', 'Precision_RF', 'F1_RF']],
        on='Rok', how='inner',
    )
    if merged.empty:
        return

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    metryki = [
        ('Recall_LSTM',    'Recall_RF',    'Recall'),
        ('Precision_LSTM', 'Precision_RF', 'Precision'),
        ('F1_LSTM',        'F1_RF',        'F1'),
    ]
    for ax, (col_lstm, col_rf, tytul) in zip(axes, metryki):
        ax.plot(merged['Rok'], merged[col_lstm], marker='o', label='LSTM',         color='darkorange')
        ax.plot(merged['Rok'], merged[col_rf],   marker='s', label='Random Forest', color='steelblue')
        ax.set_title(tytul)
        ax.set_xlabel('Rok testowy')
        ax.set_ylabel(tytul)
        ax.legend()
        ax.set_ylim(0, 1)
        ax.axhline(0.5, color='gray', linestyle=':', alpha=0.5)

    plt.suptitle('Porównanie: LSTM vs Random Forest (walk-forward, ten sam target)', fontsize=12)
    plt.tight_layout()
    plt.savefig('reports/ml/porownanie_lstm_vs_rf.png', dpi=300)
    plt.close()
    print("Wykres porównawczy → reports/ml/porownanie_lstm_vs_rf.png")

def zapisz_wyniki_lstm_do_historii(wyniki_walidacji, prec, rec, prob_threshold, params):
    plik_historia = 'reports/ml/historia_eksperymentow_lstm.txt'
    avg_f1 = wyniki_walidacji['F1_LSTM'].mean()
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(plik_historia, "a", encoding="utf-8") as f:
        f.write(f"\n--- EKSPERYMENT LSTM: {timestamp} ---\n")
        f.write(f"PROB_THRESHOLD: {prob_threshold}\n")
        f.write(f"PARAMETRY: {params}\n")
        f.write(f"Średnie F1 (walidacja): {avg_f1:.3f}\n")
        f.write(f"Finalne Precision: {prec:.3f}\n")
        f.write(f"Finalne Recall: {rec:.3f}\n")
        f.write("-" * 40 + "\n")
    
    print(f"\n[INFO] Wyniki LSTM zapisano do {plik_historia}")

# ── 6. PIPELINE GŁÓWNY ────────────────────────────────────────────────────────

def uruchom_system_lstm(final: pd.DataFrame) -> pd.DataFrame:
    """
    Odpowiednik uruchom_system() z ml_factor_system.py dla LSTM.

    Kolejność działań:
      1. Walidacja czasowa walk-forward (raportuje metryki per rok).
      2. Trening finalnego modelu na całym zbiorze.
      3. Metryki na całym zbiorze (do porównania z RF).
      4. Diagnozy dzienne → CSV.
      5. Wykresy (walidacja, confusion matrix, historia treningu, RF vs LSTM).

    Zwraca DataFrame z diagnozami dziennymi (jak ml_factor_system).
    """
    print(f"\n{'='*60}")
    print(f"  LSTM – system wykrywania epizodów wysokiej wody")
    print(f"  seq_len={SEQ_LEN}, threshold={PROB_THRESHOLD}")
    print(f"  target: ≥{EPIZOD_MIN_STACJI} stacje p{int(EPIZOD_PERCENTYL*100)}")
    print(f"{'='*60}\n")

    os.makedirs('reports/ml', exist_ok=True)

    # -- Walidacja czasowa --
    wyniki_walidacji = walidacja_czasowa(final)
    wyniki_walidacji.to_csv('reports/ml/walidacja_czasowa_lstm.csv', index=False)

    print("\nPodsumowanie walidacji LSTM:")
    print(wyniki_walidacji[['Rok', 'Recall_LSTM', 'Precision_LSTM', 'F1_LSTM',
                             'Recall_bench', 'Prec_bench', 'n_epizodow']].to_string(index=False))

    if not wyniki_walidacji.empty:
        avg_recall = wyniki_walidacji['Recall_LSTM'].mean()
        avg_prec   = wyniki_walidacji['Precision_LSTM'].mean()
        avg_f1     = wyniki_walidacji['F1_LSTM'].mean()
        print(f"  Średnie: recall={avg_recall:.3f}, prec={avg_prec:.3f}, F1={avg_f1:.3f}")
        _wykres_walidacja(wyniki_walidacji)

    # -- Trening finalnego modelu --
    print(f"\n=== Trening finalnego modelu LSTM (cały zbiór) ===")
    df, X_seq, y_seq, daty_seq, scaler = _przygotuj_dane(final)

    print(f"  Epizodów (≥{EPIZOD_MIN_STACJI} stacje): {int(y_seq.sum())} / {len(y_seq)} "
          f"({100*y_seq.mean():.1f}%)")
    for nazwa, kolumny in STACJE.items():
        col_ep = f'Epizod_{nazwa}'
        if col_ep in df.columns:
            n   = int(df[col_ep].sum())
            prg = df[f'Prog_{nazwa}'].iloc[0]
            print(f"  {nazwa:20s}: próg={prg:.3f}, epizodów={n} ({100*n/len(df):.1f}%)")

    model, history = trenuj_model(X_seq, y_seq)

    _wykres_historia_treningu(history)

    proba_all  = model.predict(X_seq, verbose=0).ravel()
    y_pred_all = (proba_all >= PROB_THRESHOLD).astype(int)
    prec = precision_score(y_seq, y_pred_all, zero_division=0)
    rec  = recall_score(y_seq, y_pred_all, zero_division=0)

    print(f"\n=== Metryki na całym zbiorze (próg={PROB_THRESHOLD}) ===")
    print(f"  Precision : {prec:.3f}")
    print(f"  Recall    : {rec:.3f}")
    print(classification_report(y_seq, y_pred_all,
                                target_names=['Brak epizodu', 'Epizod'],
                                zero_division=0))
    _wykres_confusion(y_seq, y_pred_all)

    zapisz_wyniki_lstm_do_historii(wyniki_walidacji, prec, rec, PROB_THRESHOLD, LSTM_PARAMS)

    # -- Diagnozy dzienne --
    print("=== Generowanie diagnoz dziennych ===")
    wiersze = []
    for i, data in enumerate(daty_seq):
        proba_val = float(proba_all[i])

        if proba_val >= 0.65:
            ryzyko = 'wysokie'
        elif proba_val >= PROB_THRESHOLD:
            ryzyko = 'średnie'
        else:
            ryzyko = 'niskie'

        # Kierunek zmiany ryzyka względem poprzedniego dnia
        if i == 0:
            kierunek = '→'
        elif proba_all[i] > proba_all[i - 1]:
            kierunek = '↑'
        elif proba_all[i] < proba_all[i - 1]:
            kierunek = '↓'
        else:
            kierunek = '→'

        wiersz_df = df.loc[data] if data in df.index else {}
        epizod_rzeczywisty = int(y_seq[i])

        wiersze.append({
            'Data':               data,
            'ryzyko':             ryzyko,
            'prawdopodobienstwo': round(proba_val, 3),
            'kierunek':           kierunek,
            'epizod_rzeczywisty': epizod_rzeczywisty,
        })

    diagnozy = pd.DataFrame(wiersze).set_index('Data')
    diagnozy.to_csv('reports/ml/diagnozy_dzienne_lstm.csv')
    print("Zapisano → reports/ml/diagnozy_dzienne_lstm.csv")

    # -- Wykres porównawczy z RF (jeśli dostępny) --
    _wykres_porownanie_rf_lstm('reports/ml/walidacja_czasowa.csv', wyniki_walidacji)

    print(f"\n=== Przykładowa diagnoza LSTM ({daty_seq[-1].date()}) ===")
    ostatnia = diagnozy.iloc[-1]
    print(f"  Ryzyko             : {ostatnia['ryzyko'].upper()}")
    print(f"  Prawdopodobieństwo : {ostatnia['prawdopodobienstwo']:.0%}")
    print(f"  Kierunek           : {ostatnia['kierunek']}")

    return diagnozy


# ── PUNKT WEJŚCIA ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    final = pd.read_csv(
        "data/processed/final.csv",
        parse_dates=["Data"],
        index_col="Data",
    )
    diagnozy_lstm = uruchom_system_lstm(final)
    print(diagnozy_lstm.head())