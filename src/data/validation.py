"""
Moduł 7: Walidacja i benchmark – pełne metryki jakości modelu RF
dla wykrywania epizodów wysokiej wody.

Metryki zaimplementowane:
  1. Błąd onset/offset epizodu        – o ile dni model myli start/koniec wezbrania
  2. Event-level recall (pokrycie)     – % rzeczywistych epizodów wykrytych
  3. False alarm rate / precision      – % fałszywych alarmów
  4. Błąd piku (peak timing + magnitude) – błąd dnia i wartości maksimum
  5. MAE/RMSE poziomu wody (regresja)  – w epizodzie i poza nim osobno
  6. Stabilność sezonowa               – metryki per sezon i rok-po-roku
"""

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    mean_absolute_error, mean_squared_error,
)

warnings.filterwarnings("ignore", category=FutureWarning)

# ── KONFIGURACJA ──────────────────────────────────────────────────────────────

SEZONY_DEF = {
    "zima":   [12, 1, 2],
    "wiosna": [3, 4, 5],
    "lato":   [6, 7, 8],
    "jesień": [9, 10, 11],
}

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
OUTPUT_DIR = os.path.join(_ROOT, "reports", "walidacja")

KOLORY = {
    "RF":        "#2a7fba",
    "benchmark": "#e05c3a",
    "neutral":   "#999999",
    "episode":   "#d4380d",
    "ok":        "#389e0d",
}


# ── POMOCNICZE ────────────────────────────────────────────────────────────────

def _sezon(miesiac: int) -> str:
    for nazwa, miesiace in SEZONY_DEF.items():
        if miesiac in miesiace:
            return nazwa
    return "?"

def _znajdz_epizody_ciagłe(seria: pd.Series, min_dl: int = 1) -> List[Tuple[pd.Timestamp, pd.Timestamp]]:
    """
    Zwraca listę (start, koniec) ciągłych bloków 1 w serii binarnej.
    Parametr min_dl pozwala filtrować jednodniowe artefakty.
    """
    epizody = []
    w_epizodzie = False
    start = None
    for dt, val in seria.items():
        if val and not w_epizodzie:
            start = dt
            w_epizodzie = True
        elif not val and w_epizodzie:
            if (dt - start).days >= min_dl:
                epizody.append((start, seria.index[seria.index.get_loc(dt) - 1]))
            w_epizodzie = False
    if w_epizodzie and start is not None:
        epizody.append((start, seria.index[-1]))
    return epizody


def _tolerancja_pokrycia(ep_true: Tuple, ep_pred_lista: List[Tuple],
                          tolerancja_dni: int = 2) -> bool:
    """
    Sprawdza, czy epizod rzeczywisty ep_true jest pokryty przez co najmniej
    jeden epizod predykowany (z tolerancją ±tolerancja_dni na granicach).
    """
    s_true, e_true = ep_true
    s_tol = s_true - pd.Timedelta(days=tolerancja_dni)
    e_tol = e_true + pd.Timedelta(days=tolerancja_dni)
    for s_p, e_p in ep_pred_lista:
        # nakładanie się po uwzględnieniu tolerancji
        if s_p <= e_tol and e_p >= s_tol:
            return True
    return False

@dataclass
class BenchmarkValidator:
    diagnozy: pd.DataFrame
    df_poziomy: Optional[pd.DataFrame] = None
    prob_threshold: float = 0.50
    tolerancja_dni: int = 2
    # wewnętrzne
    _wyniki: Dict = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        self._przygotuj_kolumny()

    # ── PRZYGOTOWANIE ─────────────────────────────────────────────────────────

    def _przygotuj_kolumny(self):
        d = self.diagnozy.copy()
        d.index = pd.to_datetime(d.index)

        if 'epizod_rzeczywisty' not in d.columns:
            raise ValueError("Brak kolumny 'epizod_rzeczywisty' w diagnozy.")
        if 'prawdopodobienstwo' not in d.columns:
            raise ValueError("Brak kolumny 'prawdopodobienstwo' w diagnozy.")

        d['y_true'] = d['epizod_rzeczywisty'].astype(int)
        d['y_pred'] = (d['prawdopodobienstwo'] >= self.prob_threshold).astype(int)
        d['rok']    = d.index.year
        d['miesiac']= d.index.month
        if 'sezon' not in d.columns:
            d['sezon'] = d['miesiac'].map(_sezon)

        self._d = d

    # ── 1. BŁĄD ONSET / OFFSET ────────────────────────────────────────────────

    def metryki_onset_offset(self) -> pd.DataFrame:
        """
        Dla każdego rzeczywistego epizodu szuka najbliższego predykowanego,
        oblicza błąd startu (onset_error_dni) i końca (offset_error_dni).
        Wartości dodatnie = model spóźniony; ujemne = model za wczesny.
        """
        d = self._d
        ep_true = _znajdz_epizody_ciagłe(d['y_true'])
        ep_pred = _znajdz_epizody_ciagłe(d['y_pred'])

        rekordy = []
        for (st, et) in ep_true:
            # znajdź predykowany epizod z największym nakładaniem
            najlepszy = None
            max_overlap = pd.Timedelta(0)
            for (sp, ep) in ep_pred:
                overlap = min(et, ep) - max(st, sp)
                if overlap > max_overlap:
                    max_overlap = overlap
                    najlepszy = (sp, ep)

            if najlepszy is None:
                # brak dopasowania – epizod nieykryty
                rekordy.append({
                    'ep_start':        st,
                    'ep_koniec':       et,
                    'dl_dni':          (et - st).days + 1,
                    'wykryty':         False,
                    'onset_error_dni': np.nan,
                    'offset_error_dni':np.nan,
                    'pred_start':      pd.NaT,
                    'pred_koniec':     pd.NaT,
                })
            else:
                sp, ep = najlepszy
                rekordy.append({
                    'ep_start':        st,
                    'ep_koniec':       et,
                    'dl_dni':          (et - st).days + 1,
                    'wykryty':         True,
                    'onset_error_dni': (sp - st).days,    # + = spóźniony
                    'offset_error_dni':(ep - et).days,    # + = za długi
                    'pred_start':      sp,
                    'pred_koniec':     ep,
                })

        df_oo = pd.DataFrame(rekordy)
        self._wyniki['onset_offset'] = df_oo
        return df_oo

    # ── 2. EVENT-LEVEL RECALL (pokrycie) ──────────────────────────────────────

    def event_recall(self, tolerancja_dni: Optional[int] = None) -> Dict:
        """
        Event-level: ile % rzeczywistych epizodów zostało wykrytych
        (co najmniej częściowe nakładanie z predykcją, z tolerancją).
        """
        tol = tolerancja_dni if tolerancja_dni is not None else self.tolerancja_dni
        d = self._d
        ep_true = _znajdz_epizody_ciagłe(d['y_true'])
        ep_pred = _znajdz_epizody_ciagłe(d['y_pred'])

        wykryte = sum(1 for ep in ep_true if _tolerancja_pokrycia(ep, ep_pred, tol))
        recall_ev = wykryte / len(ep_true) if ep_true else 0.0

        wynik = {
            'n_epizodow_true':   len(ep_true),
            'n_epizodow_pred':   len(ep_pred),
            'n_wykrytych':       wykryte,
            'event_recall':      round(recall_ev, 3),
            'n_nieykrytych':     len(ep_true) - wykryte,
        }
        self._wyniki['event_recall'] = wynik
        return wynik

    # ── 3. FALSE ALARM RATE ───────────────────────────────────────────────────

    def false_alarm_metrics(self) -> Dict:
        """
        Day-level: precision, FAR (false alarm rate), liczba FA epizodów.
        Event-level false alarms: predykowane epizody bez nakładania z prawdziwymi.
        """
        d = self._d
        ep_true = _znajdz_epizody_ciagłe(d['y_true'])
        ep_pred = _znajdz_epizody_ciagłe(d['y_pred'])

        prec_day = precision_score(d['y_true'], d['y_pred'], zero_division=0)
        far_day  = 1 - prec_day  # false alarm rate (dzienne)

        # event-level: ile predykowanych epizodów NIE nakłada się z żadnym prawdziwym
        fa_epizody = sum(
            1 for ep in ep_pred
            if not _tolerancja_pokrycia(ep, ep_true, self.tolerancja_dni)
        )
        fa_rate_ev = fa_epizody / len(ep_pred) if ep_pred else 0.0

        wynik = {
            'precision_day':     round(prec_day, 3),
            'far_day':           round(far_day, 3),           # 1-precision
            'n_pred_epizodow':   len(ep_pred),
            'n_fa_epizodow':     fa_epizody,
            'far_event':         round(fa_rate_ev, 3),        # event FAR
        }
        self._wyniki['false_alarm'] = wynik
        return wynik

    # ── 4. BŁĄD PIKU ──────────────────────────────────────────────────────────

    def peak_error(self, col_poziom: str = 'Poziom_wody_max') -> pd.DataFrame:
        """
        Dla każdego wykrytego epizodu oblicza:
          - peak_timing_error_dni : różnica dnia maksimum (pred vs true)
          - peak_magnitude_error  : różnica wartości maksimum (pred vs true), jeśli df_poziomy dostępne
        Wymaga df_poziomy z kolumną col_poziom.
        """
        d = self._d
        ep_true = _znajdz_epizody_ciagłe(d['y_true'])
        ep_pred = _znajdz_epizody_ciagłe(d['y_pred'])

        ma_poziomy = (
            self.df_poziomy is not None and
            col_poziom in self.df_poziomy.columns
        )

        rekordy = []
        for (st, et) in ep_true:
            # znajdź najlepiej nakładający się pred-epizod
            najlepszy = None
            max_overlap = pd.Timedelta(0)
            for (sp, ep) in ep_pred:
                overlap = min(et, ep) - max(st, sp)
                if overlap > max_overlap:
                    max_overlap = overlap
                    najlepszy = (sp, ep)

            if najlepszy is None:
                continue  # nieykryty – pominięty

            sp, ep = najlepszy

            # okno nakładania
            okno_true = d.loc[st:et, 'y_true']
            okno_pred = d.loc[sp:ep, 'y_pred']

            # timing error: dzień max-prawdopodobieństwa w oknie pred vs środek prawdziwego epizodu
            okno_proba = d.loc[sp:ep, 'prawdopodobienstwo']
            dzien_peak_pred = okno_proba.idxmax()
            dzien_peak_true = st + (et - st) / 2  # środek epizodu jako proxy

            timing_error = (dzien_peak_pred - dzien_peak_true).days

            magnitude_error = np.nan
            if ma_poziomy:
                poziomy = self.df_poziomy[col_poziom]
                w_true = poziomy.loc[st:et].dropna()
                w_pred = poziomy.loc[sp:ep].dropna()
                if len(w_true) > 0 and len(w_pred) > 0:
                    magnitude_error = w_pred.max() - w_true.max()

            rekordy.append({
                'ep_start':             st,
                'ep_koniec':            et,
                'pred_start':           sp,
                'pred_koniec':          ep,
                'peak_timing_error_dni':timing_error,
                'peak_magnitude_error': magnitude_error,
            })

        df_peak = pd.DataFrame(rekordy)
        self._wyniki['peak_error'] = df_peak
        return df_peak

    # ── 5. MAE/RMSE POZIOMU WODY ──────────────────────────────────────────────

    def metryki_regresji(self,
                         col_poziom: str = 'Poziom_wody_max') -> Dict:
        """
        Oblicza MAE i RMSE dla kolumny poziomu wody, osobno:
          - w dniach epizodowych (y_true==1)
          - poza epizodami (y_true==0)
        Wykorzystuje 'prawdopodobienstwo' jako prognozę regresyjną LUB porównuje bezpośrednio
        z df_poziomy jeśli dostępne.
        """
        if self.df_poziomy is None or col_poziom not in self.df_poziomy.columns:
            return {'uwaga': f'df_poziomy lub kolumna {col_poziom} niedostępna'}

        d = self._d.copy()
        poziomy = self.df_poziomy[[col_poziom]].copy()
        poziomy.index = pd.to_datetime(poziomy.index)

        merged = d.join(poziomy, how='inner')
        merged = merged.dropna(subset=[col_poziom])

        if len(merged) == 0:
            return {'uwaga': 'Brak wspólnych dat po złączeniu'}

        lvl = merged[col_poziom]
        prob = merged['prawdopodobienstwo']
        lvl_min, lvl_max = lvl.min(), lvl.max()
        prob_skalowany = prob * (lvl_max - lvl_min) + lvl_min

        ep_mask  = merged['y_true'] == 1
        nep_mask = merged['y_true'] == 0

        def _mae_rmse(true, pred):
            if len(true) == 0:
                return np.nan, np.nan
            mae  = mean_absolute_error(true, pred)
            rmse = np.sqrt(mean_squared_error(true, pred))
            return round(mae, 4), round(rmse, 4)

        mae_ep,  rmse_ep  = _mae_rmse(lvl[ep_mask],  prob_skalowany[ep_mask])
        mae_nep, rmse_nep = _mae_rmse(lvl[nep_mask], prob_skalowany[nep_mask])

        wynik = {
            'col_poziom':           col_poziom,
            'n_dni_epizodow':       int(ep_mask.sum()),
            'n_dni_poza':           int(nep_mask.sum()),
            'MAE_w_epizodzie':      mae_ep,
            'RMSE_w_epizodzie':     rmse_ep,
            'MAE_poza_epizodem':    mae_nep,
            'RMSE_poza_epizodem':   rmse_nep,
            'uwaga': (
                'Metryki regresyjne oparte na skalowanym P(epizod) jako proxy '
                'dla poziomu wody. Dla prawdziwej regresji dodaj moduł regresyjny RF.'
            ),
        }
        self._wyniki['regresja'] = wynik
        return wynik

    # ── 6. STABILNOŚĆ SEZONOWA ────────────────────────────────────────────────

    def stabilnosc_sezonowa(self) -> pd.DataFrame:
        """
        Metryki day-level (recall, precision, F1) obliczone:
          a) per sezon (zima/wiosna/lato/jesień)
          b) per rok (rok-po-roku)
        """
        d = self._d

        rekordy = []

        # --- per sezon ---
        for sezon in ["zima", "wiosna", "lato", "jesień"]:
            maska = d['sezon'] == sezon
            sub = d[maska]
            if len(sub) == 0 or sub['y_true'].sum() == 0:
                continue
            rec  = recall_score(sub['y_true'], sub['y_pred'], zero_division=0)
            prec = precision_score(sub['y_true'], sub['y_pred'], zero_division=0)
            f1   = f1_score(sub['y_true'], sub['y_pred'], zero_division=0)
            ep_true = _znajdz_epizody_ciagłe(sub['y_true'])
            ep_pred = _znajdz_epizody_ciagłe(sub['y_pred'])
            wykryte = sum(1 for ep in ep_true if _tolerancja_pokrycia(ep, ep_pred, self.tolerancja_dni))
            rekordy.append({
                'grupowanie':    'sezon',
                'klucz':         sezon,
                'n_dni':         len(sub),
                'n_epizodow':    len(ep_true),
                'n_wykrytych':   wykryte,
                'recall':        round(rec,  3),
                'precision':     round(prec, 3),
                'f1':            round(f1,   3),
                'event_recall':  round(wykryte / len(ep_true), 3) if ep_true else np.nan,
            })

        # --- per rok ---
        for rok in sorted(d['rok'].unique()):
            maska = d['rok'] == rok
            sub = d[maska]
            if len(sub) == 0 or sub['y_true'].sum() == 0:
                continue
            rec  = recall_score(sub['y_true'], sub['y_pred'], zero_division=0)
            prec = precision_score(sub['y_true'], sub['y_pred'], zero_division=0)
            f1   = f1_score(sub['y_true'], sub['y_pred'], zero_division=0)
            ep_true = _znajdz_epizody_ciagłe(sub['y_true'])
            ep_pred = _znajdz_epizody_ciagłe(sub['y_pred'])
            wykryte = sum(1 for ep in ep_true if _tolerancja_pokrycia(ep, ep_pred, self.tolerancja_dni))
            rekordy.append({
                'grupowanie':    'rok',
                'klucz':         str(rok),
                'n_dni':         len(sub),
                'n_epizodow':    len(ep_true),
                'n_wykrytych':   wykryte,
                'recall':        round(rec,  3),
                'precision':     round(prec, 3),
                'f1':            round(f1,   3),
                'event_recall':  round(wykryte / len(ep_true), 3) if ep_true else np.nan,
            })

        df_stab = pd.DataFrame(rekordy)
        self._wyniki['stabilnosc'] = df_stab
        return df_stab

    # ── PEŁNY RAPORT ─────────────────────────────────────────────────────────

    def pelny_raport(self, col_poziom: str = 'Poziom_wody_max') -> Dict:
        print(f"  MODUL 7: BENCHMARK I METRYKI - WALIDACJA WYNIKOW")
        print(f"  prog klasyfikacji: {self.prob_threshold}  |  tolerancja: {self.tolerancja_dni} dni")

        # 1. Onset / Offset
        df_oo = self.metryki_onset_offset()
        oo_w  = df_oo[df_oo['wykryty']]
        oo_n  = df_oo[~df_oo['wykryty']]
        print(f"\n=== Blad poczatku/konca epizodu (onset/offset) ===")
        print(f"  Epizodow rzeczywistych : {len(df_oo)}")
        print(f"  Wykrytych              : {len(oo_w)} ({100*len(oo_w)/max(len(df_oo),1):.1f}%)")
        print(f"  Nieykrytych            : {len(oo_n)} ({100*len(oo_n)/max(len(df_oo),1):.1f}%)")
        if len(oo_w) > 0:
            print(f"  Onset error  sr.       : {oo_w['onset_error_dni'].mean():+.2f} dni"
                  f"  (std={oo_w['onset_error_dni'].std():.2f},"
                  f"  mediana={oo_w['onset_error_dni'].median():+.1f})")
            print(f"  Offset error sr.       : {oo_w['offset_error_dni'].mean():+.2f} dni"
                  f"  (std={oo_w['offset_error_dni'].std():.2f},"
                  f"  mediana={oo_w['offset_error_dni'].median():+.1f})")
            print(f"  (+ = model spozniony, - = za wczesny)")

        # 2. Event recall
        er = self.event_recall()
        print(f"\n=== Pokrycie zdarzen (event-level recall) ===")
        print(f"  Epizodow rzeczywistych : {er['n_epizodow_true']}")
        print(f"  Epizodow predykowanych : {er['n_epizodow_pred']}")
        print(f"  Wykrytych              : {er['n_wykrytych']}")
        print(f"  Nieykrytych            : {er['n_nieykrytych']}")
        print(f"  Event recall           : {er['event_recall']:.3f}")

        # 3. Falszywe alarmy
        fa = self.false_alarm_metrics()
        print(f"\n=== Falszywe alarmy (false alarm rate) ===")
        print(f"  Day-level precision    : {fa['precision_day']:.3f}")
        print(f"  Day-level FAR          : {fa['far_day']:.3f}   (= 1 - precision)")
        print(f"  Pred. epizodow lacznie : {fa['n_pred_epizodow']}")
        print(f"  Falszywe alarmy (ev.)  : {fa['n_fa_epizodow']}  ({100*fa['far_event']:.1f}% pred. epizodow)")
        print(f"  Event FAR              : {fa['far_event']:.3f}")

        # 4. Blad piku
        df_peak = self.peak_error(col_poziom)
        print(f"\n=== Blad piku (peak timing / peak magnitude) ===")
        if len(df_peak) > 0:
            pt = df_peak['peak_timing_error_dni'].dropna()
            print(f"  Epizodow z dopasowaniem: {len(df_peak)}")
            print(f"  Peak timing error sr.  : {pt.mean():+.2f} dni"
                  f"  (std={pt.std():.2f}, mediana={pt.median():+.1f})")
            pm = df_peak['peak_magnitude_error'].dropna()
            if len(pm) > 0:
                print(f"  Peak magnitude error sr.: {pm.mean():+.4f}  (std={pm.std():.4f})")
            else:
                print(f"  Peak magnitude error   : N/A (brak df_poziomy)")
        else:
            print(f"  Brak dopasowanych epizodow.")

        # 5. Regresja
        reg = self.metryki_regresji(col_poziom)
        print(f"\n=== Zgodnosc wartosci poziomu wody (MAE / RMSE) ===")
        if 'MAE_w_epizodzie' in reg:
            print(f"  Kolumna poziomu        : {reg['col_poziom']}")
            print(f"  Dni epizodowych        : {reg['n_dni_epizodow']}")
            print(f"  Dni spokojnych         : {reg['n_dni_poza']}")
            print(f"  MAE  w epizodzie       : {reg['MAE_w_epizodzie']}")
            print(f"  RMSE w epizodzie       : {reg['RMSE_w_epizodzie']}")
            print(f"  MAE  poza epizodem     : {reg['MAE_poza_epizodem']}")
            print(f"  RMSE poza epizodem     : {reg['RMSE_poza_epizodem']}")
        else:
            print(f"  {reg.get('uwaga', 'Brak danych')}")

        # 6. Stabilnosc sezonowa
        df_stab = self.stabilnosc_sezonowa()
        df_rok   = df_stab[df_stab['grupowanie'] == 'rok']
        df_sezon = df_stab[df_stab['grupowanie'] == 'sezon']

        print(f"\n=== Stabilnosc sezonowa ===")
        if not df_sezon.empty:
            print(f"  {'Sezon':<10} {'Recall':>7} {'Prec':>7} {'F1':>7} {'EventRec':>9} {'Epizodow':>9}")
            for _, r in df_sezon.iterrows():
                print(f"  {str(r['klucz']):<10} {r['recall']:>7.3f} {r['precision']:>7.3f}"
                      f" {r['f1']:>7.3f} {r['event_recall']:>9.3f} {int(r['n_epizodow']):>9}")

        print(f"\n=== Stabilnosc rok-po-roku ===")
        if not df_rok.empty:
            print(f"  {'Rok':<8} {'Recall':>7} {'Prec':>7} {'F1':>7} {'EventRec':>9} {'Epizodow':>9} {'Dni':>6}")
            for _, r in df_rok.iterrows():
                print(f"  {str(r['klucz']):<8} {r['recall']:>7.3f} {r['precision']:>7.3f}"
                      f" {r['f1']:>7.3f} {r['event_recall']:>9.3f}"
                      f" {int(r['n_epizodow']):>9} {int(r['n_dni']):>6}")
            print(f"  {'Srednia':<8} {df_rok['recall'].mean():>7.3f} {df_rok['precision'].mean():>7.3f}"
                  f" {df_rok['f1'].mean():>7.3f} {df_rok['event_recall'].mean():>9.3f}")

        # Zapis CSV
        df_oo.to_csv(f"{OUTPUT_DIR}/ml/onset_offset.csv", index=False)
        df_peak.to_csv(f"{OUTPUT_DIR}/ml/peak_error.csv", index=False)
        df_stab.to_csv(f"{OUTPUT_DIR}/ml/stabilnosc_sezonowa.csv", index=False)
        pd.DataFrame([fa]).to_csv(f"{OUTPUT_DIR}/ml/false_alarm.csv", index=False)
        pd.DataFrame([er]).to_csv(f"{OUTPUT_DIR}/ml/event_recall.csv", index=False)
        if 'MAE_w_epizodzie' in reg:
            pd.DataFrame([reg]).to_csv(f"{OUTPUT_DIR}/ml/regresja.csv", index=False)
        print(f"\nZapisano -> {OUTPUT_DIR}/")

        self._rysuj_wszystkie(df_oo, df_stab, df_peak)
        print(f"Wykresy  -> {OUTPUT_DIR}/ml/*.png")

        return self._wyniki

    # ── WYKRESY ──────────────────────────────────────────────────────────────

    def _rysuj_wszystkie(self, df_oo, df_stab, df_peak):
        self._wykres_onset_offset(df_oo)
        self._wykres_stabilnosc(df_stab)
        self._wykres_peak_error(df_peak)
        self._wykres_podsumowanie()

    def _wykres_onset_offset(self, df_oo: pd.DataFrame):
        df_w = df_oo[df_oo['wykryty']].copy()
        if len(df_w) == 0:
            return

        fig, axes = plt.subplots(1, 2, figsize=(12, 4))

        for ax, col, tytu in zip(
            axes,
            ['onset_error_dni', 'offset_error_dni'],
            ['Błąd początku epizodu (onset)', 'Błąd końca epizodu (offset)']
        ):
            values = df_w[col].dropna()
            ax.hist(values, bins=15, color=KOLORY["RF"], edgecolor='white', alpha=0.85)
            ax.axvline(0, color='black', linewidth=1.2, linestyle='--')
            ax.axvline(values.mean(), color=KOLORY["episode"], linewidth=1.5,
                       label=f'Średnia: {values.mean():+.1f} dni')
            ax.set_title(tytu, fontsize=11)
            ax.set_xlabel('Błąd [dni]  (+ = spóźniony, – = za wczesny)')
            ax.set_ylabel('Liczba epizodów')
            ax.legend()

        plt.suptitle('Błąd onset/offset epizodów wysokiej wody', fontsize=12, y=1.01)
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/ml/onset_offset_error.png", dpi=300, bbox_inches='tight')
        plt.close()

    def _wykres_stabilnosc(self, df_stab: pd.DataFrame):
        if df_stab.empty:
            return

        df_rok    = df_stab[df_stab['grupowanie'] == 'rok'].copy()
        df_sezon  = df_stab[df_stab['grupowanie'] == 'sezon'].copy()

        fig, axes = plt.subplots(2, 3, figsize=(16, 9))

        metryki = [('recall', 'Recall'), ('precision', 'Precision'), ('f1', 'F1')]

        # Górny rząd: rok-po-roku
        for ax, (col, tytu) in zip(axes[0], metryki):
            if df_rok.empty:
                ax.set_visible(False)
                continue
            ax.bar(df_rok['klucz'], df_rok[col], color=KOLORY["RF"], alpha=0.85, width=0.5)
            ax.set_title(f'{tytu} – rok-po-roku', fontsize=10)
            ax.set_xlabel('Rok')
            ax.set_ylabel(tytu)
            ax.set_ylim(0, 1)
            ax.axhline(df_rok[col].mean(), color=KOLORY["episode"],
                       linestyle='--', label=f'Śr. {df_rok[col].mean():.2f}')
            ax.legend(fontsize=8)

        # Dolny rząd: per sezon
        porzadek_sezonow = ["zima", "wiosna", "lato", "jesień"]
        df_sezon['klucz'] = pd.Categorical(df_sezon['klucz'], categories=porzadek_sezonow, ordered=True)
        df_sezon = df_sezon.sort_values('klucz')

        for ax, (col, tytu) in zip(axes[1], metryki):
            if df_sezon.empty:
                ax.set_visible(False)
                continue
            bars = ax.bar(df_sezon['klucz'].astype(str), df_sezon[col],
                          color=[KOLORY["RF"], "#4caf50", "#ff9800", "#9c27b0"][:len(df_sezon)],
                          alpha=0.85, width=0.5)
            ax.set_title(f'{tytu} – sezonowość', fontsize=10)
            ax.set_xlabel('Sezon')
            ax.set_ylabel(tytu)
            ax.set_ylim(0, 1)

        plt.suptitle('Stabilność sezonowa i rok-po-roku (metryki day-level)', fontsize=12)
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/ml/stabilnosc_sezonowa.png", dpi=300, bbox_inches='tight')
        plt.close()

    def _wykres_peak_error(self, df_peak: pd.DataFrame):
        if df_peak.empty:
            return

        fig, ax = plt.subplots(figsize=(8, 4))
        values = df_peak['peak_timing_error_dni'].dropna()
        ax.hist(values, bins=15, color=KOLORY["RF"], edgecolor='white', alpha=0.85)
        ax.axvline(0, color='black', linewidth=1.2, linestyle='--')
        ax.axvline(values.mean(), color=KOLORY["episode"], linewidth=1.5,
                   label=f'Średnia: {values.mean():+.1f} dni')
        ax.set_title('Błąd czasu piku (peak timing error)', fontsize=11)
        ax.set_xlabel('Błąd [dni]  (+ = model pokazuje pik za późno)')
        ax.set_ylabel('Liczba epizodów')
        ax.legend()
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/ml/peak_timing_error.png", dpi=300)
        plt.close()

    def _wykres_podsumowanie(self):
        """
        Heatmapa stabilności: sezon × rok → F1.
        """
        d = self._d.copy()
        sezony = ["zima", "wiosna", "lato", "jesień"]
        lata = sorted(d['rok'].unique())

        macierz = pd.DataFrame(index=sezony, columns=lata, dtype=float)

        for rok in lata:
            for sezon in sezony:
                maska = (d['rok'] == rok) & (d['sezon'] == sezon)
                sub = d[maska]
                if len(sub) == 0 or sub['y_true'].sum() == 0:
                    macierz.loc[sezon, rok] = np.nan
                else:
                    macierz.loc[sezon, rok] = round(
                        f1_score(sub['y_true'], sub['y_pred'], zero_division=0), 2
                    )

        fig, ax = plt.subplots(figsize=(max(6, len(lata) * 1.3), 4))
        sns.heatmap(
            macierz.astype(float), annot=True, fmt='.2f',
            cmap='RdYlGn', vmin=0, vmax=1,
            linewidths=0.5, ax=ax, cbar_kws={'label': 'F1'}
        )
        ax.set_title('Mapa stabilności F1 (sezon × rok)', fontsize=12)
        ax.set_xlabel('Rok')
        ax.set_ylabel('Sezon')
        plt.tight_layout()
        plt.savefig(f"{OUTPUT_DIR}/ml/heatmapa_stabilnosci_f1.png", dpi=300)
        plt.close()


# ── FUNKCJA WEJŚCIOWA ─────────────────────────────────────────────────────────

def uruchom_benchmark(diagnozy: pd.DataFrame,
                      df_poziomy: Optional[pd.DataFrame] = None,
                      prob_threshold: float = 0.50,
                      col_poziom: str = 'Poziom_wody_max',
                      tolerancja_dni: int = 2) -> Dict:
    """
    Parametry
    ----------
    diagnozy       : DataFrame zwrócony przez ml_factor_system.uruchom_system()
    df_poziomy     : opcjonalny DataFrame z kolumnami poziomów wody (index=Data)
    prob_threshold : próg klasyfikacji (domyślnie 0.50)
    col_poziom     : nazwa kolumny poziomu wody w df_poziomy
    tolerancja_dni : tolerancja przy dopasowywaniu epizodów (domyślnie 2 dni)
    """
    val = BenchmarkValidator(
        diagnozy=diagnozy,
        df_poziomy=df_poziomy,
        prob_threshold=prob_threshold,
        tolerancja_dni=tolerancja_dni,
    )
    return val.pelny_raport(col_poziom=col_poziom)

if __name__ == "__main__":
    diagnozy = pd.read_csv(
        os.path.join(_ROOT, "reports", "ml", "diagnozy_dzienne_rf.csv"),
        parse_dates=["Data"],
        index_col="Data"
    )
    final = pd.read_csv(
        os.path.join(_ROOT, "data", "processed", "final.csv"),
        parse_dates=["Data"],
        index_col="Data"
    )
    uruchom_benchmark(diagnozy, df_poziomy=final)