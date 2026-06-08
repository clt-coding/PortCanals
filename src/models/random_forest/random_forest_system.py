import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
import numpy as np
import pandas as pd
import matplotlib
import datetime
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    precision_score, recall_score, confusion_matrix, classification_report
)

def zapisz_wyniki_do_historii(wyniki_walidacji, precision, recall, prob_threshold):
    os.makedirs('reports/ml/rf', exist_ok=True)
    plik_historia = 'reports/ml/rf/historia_eksperymentow_rf.txt'
    avg_f1 = wyniki_walidacji['F1_RF'].mean()

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(plik_historia, "a", encoding="utf-8") as f:
        f.write(f"\n--- EKSPERYMENT: {timestamp} ---\n")
        f.write(f"PROB_THRESHOLD: {prob_threshold}\n")
        f.write(f"Średnie F1 (walidacja): {avg_f1:.3f}\n")
        f.write(f"Finalne Precision: {precision:.3f}\n")
        f.write(f"Finalne Recall: {recall:.3f}\n")
        f.write("-" * 30 + "\n")

    print(f"Wyniki zapisano do {plik_historia}")

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
    'Strzyza': {'max': 'Poziom_wody_max', 'srednia': 'Poziom_wody_średnia'},
    'Martwa_Wisla': {'max': 'Martwa_Wisla_max', 'srednia': 'Martwa_Wisla_średnia'},
    'Port_Polnocny': {'max': 'Port_Polnocny_max', 'srednia': 'Port_Polnocny_średnia'},
}

EPIZOD_PERCENTYL = 0.90
EPIZOD_MIN_STACJI = 2
MIN_TRAIN_YEARS = 2

RF_PARAMS = {
    'n_estimators': 300,
    'max_depth': None,
    'min_samples_leaf': 15,
    'class_weight': 'balanced',
    'random_state': 42,
    'n_jobs': -1,
}

PROB_THRESHOLD = 0.50

def _buduj_epizody(df: pd.DataFrame, train_mask: pd.Series) -> pd.DataFrame:
    for nazwa, kolumny in STACJE.items():
        col_max = kolumny['max']
        if col_max not in df.columns:
            raise ValueError(f"Brak kolumny '{col_max}'. Dostępne: {df.columns.tolist()}")
        threshold = df.loc[train_mask, col_max].quantile(EPIZOD_PERCENTYL)
        df[f'Epizod_{nazwa}'] = (df[col_max] >= threshold).astype(int)
        df[f'Prog_{nazwa}'] = threshold  # zapisujemy próg do diagnostyki

    suma_stacji = sum(df[f'Epizod_{n}'] for n in STACJE)
    df['Epizod_rzeczywisty'] = (suma_stacji >= EPIZOD_MIN_STACJI).astype(int)
    return df


def _przygotuj_dane(final: pd.DataFrame):
    df = final.copy()
    all_mask = pd.Series(True, index=df.index)
    df = _buduj_epizody(df, train_mask=all_mask)

    brakujace = [f for f in FEATURES if f not in df.columns]
    if brakujace:
        raise ValueError(f"Brakujące kolumny cech: {brakujace}")

    X = df[FEATURES]
    y = df['Epizod_rzeczywisty']
    return df, X, y

def walidacja_czasowa(final: pd.DataFrame) -> pd.DataFrame:
    lata = sorted(final.index.year.unique())
    wyniki = []

    print("Walidacja czasowa (walk-forward, rolling threshold)")

    for i, rok_test in enumerate(lata):
        if i == 0:
            continue

        maska_train = final.index.year < rok_test
        maska_test = final.index.year == rok_test

        n_lat_train = len(set(final.index.year[final.index.year < rok_test]))
        if n_lat_train < MIN_TRAIN_YEARS or maska_test.sum() < 10:
            print(f"  {rok_test}: pominięto (tylko {n_lat_train} lat treningowych < MIN_TRAIN_YEARS={MIN_TRAIN_YEARS})")
            continue

        df_iter = final.copy()
        df_iter = _buduj_epizody(df_iter, train_mask=maska_train)

        X = df_iter[FEATURES]
        y = df_iter['Epizod_rzeczywisty']

        X_train, y_train = X[maska_train], y[maska_train]
        X_test, y_test = X[maska_test], y[maska_test]

        if y_train.sum() < 5:
            continue

        model = RandomForestClassifier(**RF_PARAMS)
        model.fit(X_train, y_train)

        proba = model.predict_proba(X_test)[:, 1]
        y_pred = (proba >= PROB_THRESHOLD).astype(int)

        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)

        prog_benchmark = X_train['Opad_72h'].quantile(EPIZOD_PERCENTYL)
        y_bench = (X_test['Opad_72h'] >= prog_benchmark).astype(int)
        prec_b = precision_score(y_test, y_bench, zero_division=0)
        rec_b = recall_score(y_test, y_bench, zero_division=0)

        epizody_per_stacja = {
            n: int(df_iter.loc[maska_test, f'Epizod_{n}'].sum())
            for n in STACJE
        }

        wyniki.append({
            'Rok': rok_test,
            'Recall_RF': round(rec, 3),
            'Precision_RF': round(prec, 3),
            'F1_RF': round(2 * rec * prec / (rec + prec) if (rec + prec) > 0 else 0, 3),
            'Recall_bench': round(rec_b, 3),
            'Prec_bench': round(prec_b, 3),
            'n_epizodow': int(y_test.sum()),
            'n_dni': int(maska_test.sum()),
            **{f'epizody_{n}': v for n, v in epizody_per_stacja.items()},
        })

        print(f"{rok_test}: RF recall={rec:.3f} prec={prec:.3f} F1={wyniki[-1]['F1_RF']:.3f} | "
              f"benchmark recall={rec_b:.3f} prec={prec_b:.3f} | "
              f"epizody(>=2 stacje)={int(y_test.sum())} "
              f"({', '.join(f'{n}={v}' for n, v in epizody_per_stacja.items())})")

    return pd.DataFrame(wyniki)

def trenuj_model(X: pd.DataFrame, y: pd.Series) -> RandomForestClassifier:
    model = RandomForestClassifier(**RF_PARAMS)
    model.fit(X, y)
    return model

def feature_importance_df(model: RandomForestClassifier) -> pd.DataFrame:
    fi = pd.DataFrame({
        'czynnik': FEATURES,
        'waznosc': model.feature_importances_,
    }).sort_values('waznosc', ascending=False).reset_index(drop=True)
    fi['waznosc_pct'] = (fi['waznosc'] * 100).round(2)
    return fi

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
        'Opad_72h': f"Nasycenie zlewni wysokie (opad 72h = {obserwacja.get('Opad_72h', 0):.1f} mm)",
        'Opad_suma': f"Intensywny opad dzienny ({obserwacja.get('Opad_suma', 0):.1f} mm)",
        'Opad_7d': f"Długotrwałe opady (suma 7d = {obserwacja.get('Opad_7d', 0):.1f} mm)",
        'Ciśnienie_delta_1d': f"Zmiana ciśnienia ({obserwacja.get('Ciśnienie_delta_1d', 0):+.1f} hPa/dobę)",
        'Temp_średnia': f"Temperatura {obserwacja.get('Temp_średnia', 0):.1f} °C",
        'Wilgotność_średnia': f"Wilgotność {obserwacja.get('Wilgotność_średnia', 0):.0f}%",
    }
    opis_czynnika = komunikaty.get(glowny, glowny)

    status_stacji = {
        nazwa: bool(obserwacja.get(f'Epizod_{nazwa}', 0))
        for nazwa in STACJE
    }

    komunikat = (
        f"{opis_czynnika} – models ocenia ryzyko wezbrania na {proba:.0%}. "
        f"Kierunek wpływu: {kierunek}. "
        f"Pewność (prawdopodobieństwo z RF): {proba:.0%}."
    )

    return {
        'ryzyko': ryzyko,
        'prawdopodobienstwo': round(proba, 3),
        'glowny_czynnik': glowny,
        'top3_czynniki': top3,
        'kierunek': kierunek,
        'pewnosc': round(proba, 3),
        'komunikat': komunikat,
        'status_stacji': status_stacji,
    }

def _wykres_feature_importance(fi: pd.DataFrame):
    os.makedirs('reports/ml/rf', exist_ok=True)
    plt.figure(figsize=(10, 6))
    sns.barplot(data=fi.head(15), x='waznosc_pct', y='czynnik',
                hue='czynnik', palette='viridis', legend=False)
    plt.title('Ważność cech – Random Forest (top 15)', fontsize=14)
    plt.xlabel('Ważność [%]')
    plt.ylabel('Czynnik meteorologiczny')
    plt.tight_layout()
    plt.savefig('reports/ml/rf/feature_importance.png', dpi=300)
    plt.close()

def _wykres_walidacja(wyniki_walidacji: pd.DataFrame):
    os.makedirs('reports/ml/rf', exist_ok=True)
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
        ax.set_xticks(wyniki_walidacji['Rok'])
        ax.set_xticklabels(wyniki_walidacji['Rok'].astype(int))  

    plt.suptitle(
        f'Walidacja czasowa RF (target: ≥{EPIZOD_MIN_STACJI} stacje p{int(EPIZOD_PERCENTYL * 100)}, thresh={PROB_THRESHOLD})',
        fontsize=12)
    plt.tight_layout()
    plt.savefig('reports/ml/rf/walidacja_czasowa_rf_vs_benchmark.png', dpi=300)
    plt.close()


def _wykres_confusion(y_true, y_pred):
    os.makedirs('reports/ml/rf', exist_ok=True)
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=['Brak alarmu', 'Alarm'],
                yticklabels=['Brak epizodu', 'Epizod'])
    plt.title(f'Macierz pomyłek – RF (target: >= {EPIZOD_MIN_STACJI} stacji)')
    plt.xlabel('Predykcja')
    plt.ylabel('Rzeczywistość')
    plt.tight_layout()
    plt.savefig('reports/ml/rf/confusion_matrix_rf.png', dpi=300)
    plt.close()


def _wykres_epizody_per_stacja(df: pd.DataFrame):
    os.makedirs('reports/ml/rf', exist_ok=True)
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
    ax.set_title(f'Liczba epizodów p{int(EPIZOD_PERCENTYL * 100)} per stacja i rok')
    ax.set_xlabel('Rok')
    ax.set_ylabel('Liczba dni epizodowych')
    ax.legend(title='Stacja')
    plt.tight_layout()
    plt.savefig('reports/ml/rf/epizody_per_stacja_rf.png', dpi=300)
    plt.close()

def uruchom_system(final: pd.DataFrame) -> pd.DataFrame:
    df, X, y = _przygotuj_dane(final)

    print(f"Epizody wysokiej wody (p{int(EPIZOD_PERCENTYL * 100)}, >= {EPIZOD_MIN_STACJI} stacji)")
    for nazwa, kolumny in STACJE.items():
        col_epizod = f'Epizod_{nazwa}'
        prog = df[f'Prog_{nazwa}'].iloc[0]
        n = int(df[col_epizod].sum())
        print(f"  {nazwa:20s}: próg={prog:.3f}, epizodów={n} ({100 * n / len(df):.1f}%)")
    print(f"  {'Łącznie (>= 2 stacji)':20s}: epizodów={int(y.sum())} ({100 * y.mean():.1f}%)")

    wyniki_walidacji = walidacja_czasowa(final)
    os.makedirs('reports/ml/rf', exist_ok=True)
    wyniki_walidacji.to_csv('reports/ml/rf/walidacja_czasowa.csv', index=False)
    print("\nPodsumowanie walidacji:")
    print(wyniki_walidacji[['Rok', 'Recall_RF', 'Precision_RF', 'F1_RF',
                            'Recall_bench', 'Prec_bench', 'n_epizodow']].to_string(index=False))
    avg_recall = wyniki_walidacji['Recall_RF'].mean()
    avg_prec = wyniki_walidacji['Precision_RF'].mean()
    avg_f1 = wyniki_walidacji['F1_RF'].mean()
    print(f"  Średnie: recall={avg_recall:.3f}, prec={avg_prec:.3f}, F1={avg_f1:.3f}")
    _wykres_walidacja(wyniki_walidacji)
    _wykres_epizody_per_stacja(df)

    print(f"Trening finalnego modelu (cały zbiór, target >= {EPIZOD_MIN_STACJI} stacji)")
    model = trenuj_model(X, y)

    fi = feature_importance_df(model)
    fi.to_csv('reports/ml/rf/feature_importance_rf.csv', index=False)
    print("\nTop 10 najważniejszych czynników:")
    print(fi.head(10).to_string(index=False))
    _wykres_feature_importance(fi)

    proba_all = model.predict_proba(X)[:, 1]
    y_pred_all = (proba_all >= PROB_THRESHOLD).astype(int)
    prec = precision_score(y, y_pred_all, zero_division=0)
    rec = recall_score(y, y_pred_all, zero_division=0)
    print(f"Metryki na całym zbiorze (prog={PROB_THRESHOLD})")
    print(f"Precision : {prec:.3f}")
    print(f"Recall    : {rec:.3f}")
    print(classification_report(y, y_pred_all,
                                target_names=['Brak epizodu', 'Epizod'],
                                zero_division=0))
    _wykres_confusion(y, y_pred_all)

    print("Generowanie diagnoz dziennych")
    wiersze = []
    poprzednia_proba = None
    for data, wiersz in df.iterrows():
        diag = diagnozuj(wiersz, model, fi, poprzednia_proba=poprzednia_proba)
        poprzednia_proba = diag['prawdopodobienstwo']
        wiersz_out = {
            'Data': data,
            'sezon': wiersz.get('sezon', ''),
            'ryzyko': diag['ryzyko'],
            'prawdopodobienstwo': diag['prawdopodobienstwo'],
            'glowny_czynnik': diag['glowny_czynnik'],
            'kierunek': diag['kierunek'],
            'pewnosc': diag['pewnosc'],
            'komunikat': diag['komunikat'],
            'epizod_rzeczywisty': wiersz['Epizod_rzeczywisty'],
        }
        for nazwa in STACJE:
            wiersz_out[f'epizod_{nazwa}'] = int(wiersz.get(f'Epizod_{nazwa}', 0))
        wiersze.append(wiersz_out)

    diagnozy = pd.DataFrame(wiersze).set_index('Data')
    os.makedirs('reports/ml/rf', exist_ok=True)
    diagnozy.to_csv('reports/ml/rf/diagnozy_dzienne_rf.csv')
    print("Zapisano -> reports/ml/rf/diagnozy_dzienne_rf.csv")

    ostatnia = df.iloc[-1]
    przedostatnia_proba = diagnozy['prawdopodobienstwo'].iloc[-2] if len(diagnozy) > 1 else None
    diag = diagnozuj(ostatnia, model, fi, poprzednia_proba=przedostatnia_proba)
    print(f"Przykładowa diagnoza ({df.index[-1].date()}) ===")
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

    def przeanalizuj_bledy(diagnozy):
        alarmy = diagnozy[diagnozy['prawdopodobienstwo'] >= PROB_THRESHOLD]

        false_positives = alarmy[alarmy['epizod_rzeczywisty'] == 0]

        print(f"ANALIZA FAŁSZYWYCH ALARMÓW")
        print(f"Liczba fałszywych alarmów: {len(false_positives)}")

        if not false_positives.empty:
            print("\nPrzykładowe 5 dni z fałszywym alarmem:")
            print(false_positives[['prawdopodobienstwo', 'glowny_czynnik', 'komunikat']].head())

            print("\nNajczęstsze czynniki przy fałszywych alarmach:")
            print(false_positives['glowny_czynnik'].value_counts())

        przeanalizuj_bledy(diagnozy)

    print(diagnozy.head())