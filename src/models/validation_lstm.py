"""
Moduł 7: Walidacja i benchmark – pełne metryki jakości modeli (RF / LSTM)
dla wykrywania epizodów wysokiej wody.
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
    "LSTM":      "#ff9800",
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
    s_true, e_true = ep_true
    s_tol = s_true - pd.Timedelta(days=tolerancja_dni)
    e_tol = e_true + pd.Timedelta(days=tolerancja_dni)
    for s_p, e_p in ep_pred_lista:
        if s_p <= e_tol and e_p >= s_tol:
            return True
    return False

@dataclass
class BenchmarkValidator:
    diagnozy: pd.DataFrame
    df_poziomy: Optional[pd.DataFrame] = None
    prob_threshold: float = 0.50
    tolerancja_dni: int = 2
    model_name: str = "rf"  # Dynamiczny wybór subfolderu zapisu ("rf" lub "lstm")
    # wewnętrzne
    _wyniki: Dict = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self):
        # Dynamiczne tworzenie folderu dedykowanego pod konkretny models
        self.target_dir = os.path.join(OUTPUT_DIR, self.model_name)
        os.makedirs(self.target_dir, exist_ok=True)
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
        d = self._d
        ep_true = _znajdz_epizody_ciagłe(d['y_true'])
        ep_pred = _znajdz_epizody_ciagłe(d['y_pred'])

        rekordy = []
        for (st, et) in ep_true:
            najlepszy = None
            max_overlap = pd.Timedelta(0)
            for (sp, ep) in ep_pred:
                overlap = min(et, ep) - max(st, sp)
                if overlap > max_overlap:
                    max_overlap = overlap
                    najlepszy = (sp, ep)

            if najlepszy is None:
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
                    'onset_error_dni': (sp - st).days,
                    'offset_error_dni':(ep - et).days,
                    'pred_start':      sp,
                    'pred_koniec':     ep,
                })

        df_oo = pd.DataFrame(rekordy)
        self._wyniki['onset_offset'] = df_oo
        return df_oo  

    # ── 2. EVENT-LEVEL RECALL (pokrycie) ──────────────────────────────────────

    def event_recall(self, tolerancja_dni: Optional[int] = None) -> Dict:
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
        d = self._d
        ep_true = _znajdz_epizody_ciagłe(d['y_true'])
        ep_pred = _znajdz_epizody_ciagłe(d['y_pred'])

        prec_day = precision_score(d['y_true'], d['y_pred'], zero_division=0)
        far_day  = 1 - prec_day

        fa_epizody = sum(
            1 for ep in ep_pred
            if not _tolerancja_pokrycia(ep, ep_true, self.tolerancja_dni)
        )
        fa_rate_ev = fa_epizody / len(ep_pred) if ep_pred else 0.0

        wynik = {
            'precision_day':     round(prec_day, 3),
            'far_day':           round(far_day, 3),
            'n_pred_epizodow':   len(ep_pred),
            'n_fa_epizodow':     fa_epizody,
            'far_event':         round(fa_rate_ev, 3),
        }
        self._wyniki['false_alarm'] = wynik
        return wynik

    # ── 4. BŁĄD PIKU ──────────────────────────────────────────────────────────

    def peak_error(self, col_poziom: str = 'Poziom_wody_max') -> pd.DataFrame:
        d = self._d
        ep_true = _znajdz_epizody_ciagłe(d['y_true'])
        ep_pred = _znajdz_epizody_ciagłe(d['y_pred'])

        ma_poziomy = (
            self.df_poziomy is not None and
            col_poziom in self.df_poziomy.columns
        )

        rekordy = []
        for (st, et) in ep_true:
            najlepszy = None
            max_overlap = pd.Timedelta(0)
            for (sp, ep) in ep_pred:
                overlap = min(et, ep) - max(st, sp)
                if overlap > max_overlap:
                    max_overlap = overlap
                    najlepszy = (sp, ep)

            if najlepszy is None:
                continue

            sp, ep = najlepszy

            okno_proba = d.loc[sp:ep, 'prawdopodobienstwo']
            dzien_peak_pred = okno_proba.idxmax()
            dzien_peak_true = st + (et - st) / 2

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

    def metryki_regresji(self, col_poziom: str = 'Poziom_wody_max') -> Dict:
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
            'uwaga': f'Metryki oparte na skalowanym P(epizod) dla modelu {self.model_name.upper()}.',
        }
        self._wyniki['regresja'] = wynik
        return wynik

    # ── 6. STABILNOŚĆ SEZONOWA ────────────────────────────────────────────────

    def stabilnosc_sezonowa(self) -> pd.DataFrame:
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
        print(f"\n  MODUL 7: BENCHMARK I METRYKI - WALIDACJA MODELU {self.model_name.upper()}")
        print(f"  prog klasyfikacji: {self.prob_threshold}  |  tolerancja: {self.tolerancja_dni} dni")

        df_oo = self.metryki_onset_offset()
        oo_w  = df_oo[df_oo['wykryty']]
        oo_n  = df_oo[~df_oo['wykryty']]
        print(f"\n=== Blad poczatku/konca epizodu (onset/offset) ===")
        print(f"  Epizodow rzeczywistych : {len(df_oo)}")
        print(f"  Wykrytych              : {len(oo_w)} ({100*len(oo_w)/max(len(df_oo),1):.1f}%)")
        print(f"  Nieykrytych            : {len(oo_n)} ({100*len(oo_n)/max(len(df_oo),1):.1f}%)")
        if len(oo_w) > 0:
            print(f"  Onset error  sr.       : {oo_w['onset_error_dni'].mean():+.2f} dni (std={oo_w['onset_error_dni'].std():.2f}, mediana={oo_w['onset_error_dni'].median():+.1f})")
            print(f"  Offset error sr.       : {oo_w['offset_error_dni'].mean():+.2f} dni (std={oo_w['offset_error_dni'].std():.2f}, mediana={oo_w['offset_error_dni'].median():+.1f})")

        er = self.event_recall()
        print(f"\n=== Pokrycie zdarzen (event-level recall) ===")
        print(f"  Epizodow rzeczywistych : {er['n_epizodow_true']}")
        print(f"  Epizodow predykowanych : {er['n_epizodow_pred']}")
        print(f"  Wykrytych              : {er['n_wykrytych']}")
        print(f"  Nieykrytych            : {er['n_nieykrytych']}")
        print(f"  Event recall           : {er['event_recall']:.3f}")

        fa = self.false_alarm_metrics()
        print(f"\n=== Falszywe alarmy (false alarm rate) ===")
        print(f"  Day-level precision    : {fa['precision_day']:.3f}")
        print(f"  Day-level FAR          : {fa['far_day']:.3f}   (= 1 - precision)")
        print(f"  Pred. epizodow lacznie : {fa['n_pred_epizodow']}")
        print(f"  Falszywe alarmy (ev.)  : {fa['n_fa_epizodow']}  ({100*fa['far_event']:.1f}% pred. epizodow)")
        print(f"  Event FAR              : {fa['far_event']:.3f}")

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

        reg = self.metryki_regresji(col_poziom)
        print(f"\n=== Zgodnosc wartosci poziomu wody (MAE / RMSE) ===")
        if 'MAE_w_epizodzie' in reg:
            print(f"  MAE  w epizodzie       : {reg['MAE_w_epizodzie']}")
            print(f"  RMSE w epizodzie       : {reg['RMSE_w_epizodzie']}")
            print(f"  MAE  poza epizodem     : {reg['MAE_poza_epizodem']}")
            print(f"  RMSE poza epizodem     : {reg['RMSE_poza_epizodem']}")

        df_stab = self.stabilnosc_sezonowa()
        df_rok   = df_stab[df_stab['grupowanie'] == 'rok']
        df_sezon = df_stab[df_stab['grupowanie'] == 'sezon']

        print(f"\n=== Stabilnosc sezonowa ===")
        for _, r in df_sezon.iterrows():
            print(f"  {str(r['klucz']):<10} {r['recall']:>7.3f} {r['precision']:>7.3f} {r['f1']:>7.3f} {r['event_recall']:>9.3f}")

        print(f"\n=== Stabilnosc rok-po-roku ===")
        for _, r in df_rok.iterrows():
            print(f"  {str(r['klucz']):<8} {r['recall']:>7.3f} {r['precision']:>7.3f} {r['f1']:>7.3f} {r['event_recall']:>9.3f}")

        # Zapis do podfolderu dedykowanego pod wybrany models
        df_oo.to_csv(f"{self.target_dir}/onset_offset.csv", index=False)
        df_peak.to_csv(f"{self.target_dir}/peak_error.csv", index=False)
        df_stab.to_csv(f"{self.target_dir}/stabilnosc_sezonowa.csv", index=False)
        pd.DataFrame([fa]).to_csv(f"{self.target_dir}/false_alarm.csv", index=False)
        pd.DataFrame([er]).to_csv(f"{self.target_dir}/event_recall.csv", index=False)
        if 'MAE_w_epizodzie' in reg:
            pd.DataFrame([reg]).to_csv(f"{self.target_dir}/regresja.csv", index=False)
        
        self._rysuj_wszystkie(df_oo, df_stab, df_peak)
        print(f"\nZapisano raporty i wykresy do -> {self.target_dir}/")
        return self._wyniki

    # ── WYKRESY ──────────────────────────────────────────────────────────────

    def _rysuj_wszystkie(self, df_oo, df_stab, df_peak):
        color_theme = KOLORY["LSTM"] if self.model_name == "lstm" else KOLORY["RF"]
        self._wykres_onset_offset(df_oo, color_theme)
        self._wykres_stabilnosc(df_stab, color_theme)
        self._wykres_peak_error(df_peak, color_theme)
        self._wykres_podsumowanie()

    def _wykres_onset_offset(self, df_oo: pd.DataFrame, color_theme: str):
        df_w = df_oo[df_oo['wykryty']].copy()
        if len(df_w) == 0: return
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        for ax, col, tytu in zip(axes, ['onset_error_dni', 'offset_error_dni'], ['Błąd początku epizodu (onset)', 'Błąd końca epizodu (offset)']):
            values = df_w[col].dropna()
            ax.hist(values, bins=15, color=color_theme, edgecolor='white', alpha=0.85)
            ax.axvline(0, color='black', linewidth=1.2, linestyle='--')
            ax.axvline(values.mean(), color=KOLORY["episode"], linewidth=1.5, label=f'Średnia: {values.mean():+.1f} dni')
            ax.set_title(tytu, fontsize=11)
            ax.set_xlabel('Błąd [dni]  (+ = spóźniony, – = za wczesny)')
            ax.set_ylabel('Liczba epizodów')
            ax.legend()
        plt.suptitle(f'Błąd onset/offset ({self.model_name.upper()})', fontsize=12, y=1.01)
        plt.tight_layout()
        plt.savefig(f"{self.target_dir}/onset_offset_error.png", dpi=300, bbox_inches='tight')
        plt.close()

    def _wykres_stabilnosc(self, df_stab: pd.DataFrame, color_theme: str):
        if df_stab.empty: return
        df_rok = df_stab[df_stab['grupowanie'] == 'rok'].copy()
        df_sezon = df_stab[df_stab['grupowanie'] == 'sezon'].copy()
        fig, axes = plt.subplots(2, 3, figsize=(16, 9))
        metryki = [('recall', 'Recall'), ('precision', 'Precision'), ('f1', 'F1')]

        for ax, (col, tytu) in zip(axes[0], metryki):
            ax.bar(df_rok['klucz'], df_rok[col], color=color_theme, alpha=0.85, width=0.5)
            ax.set_title(f'{tytu} – rok-po-roku', fontsize=10)
            ax.set_ylim(0, 1)
            ax.axhline(df_rok[col].mean(), color=KOLORY["episode"], linestyle='--', label=f'Śr. {df_rok[col].mean():.2f}')
            ax.legend(fontsize=8)

        porzadek_sezonow = ["zima", "wiosna", "lato", "jesień"]
        df_sezon['klucz'] = pd.Categorical(df_sezon['klucz'], categories=porzadek_sezonow, ordered=True)
        df_sezon = df_sezon.sort_values('klucz')
        for ax, (col, tytu) in zip(axes[1], metryki):
            ax.bar(df_sezon['klucz'].astype(str), df_sezon[col], color=[color_theme, "#4caf50", "#ff9800", "#9c27b0"][:len(df_sezon)], alpha=0.85, width=0.5)
            ax.set_title(f'{tytu} – sezonowość', fontsize=10)
            ax.set_ylim(0, 1)

        plt.suptitle(f'Stabilność sezonowa i rok-po-roku – {self.model_name.upper()}', fontsize=12)
        plt.tight_layout()
        plt.savefig(f"{self.target_dir}/stabilnosc_sezonowa.png", dpi=300, bbox_inches='tight')
        plt.close()

    def _wykres_peak_error(self, df_peak: pd.DataFrame, color_theme: str):
        if df_peak.empty: return
        fig, ax = plt.subplots(figsize=(8, 4))
        values = df_peak['peak_timing_error_dni'].dropna()
        ax.hist(values, bins=15, color=color_theme, edgecolor='white', alpha=0.85)
        ax.axvline(0, color='black', linewidth=1.2, linestyle='--')
        ax.axvline(values.mean(), color=KOLORY["episode"], linewidth=1.5, label=f'Średnia: {values.mean():+.1f} dni')
        ax.set_title(f'Błąd czasu piku ({self.model_name.upper()})', fontsize=11)
        ax.set_xlabel('Błąd [dni]  (+ = models pokazuje pik za późno)')
        ax.set_ylabel('Liczba epizodów')
        ax.legend()
        plt.tight_layout()
        plt.savefig(f"{self.target_dir}/peak_timing_error.png", dpi=300)
        plt.close()

    def _wykres_podsumowanie(self):
        d = self._d.copy()
        sezony, lata = ["zima", "wiosna", "lato", "jesień"], sorted(d['rok'].unique())
        macierz = pd.DataFrame(index=sezony, columns=lata, dtype=float)
        for rok in lata:
            for sezon in sezony:
                maska = (d['rok'] == rok) & (d['sezon'] == sezon)
                sub = d[maska]
                if len(sub) > 0 and sub['y_true'].sum() > 0:
                    macierz.loc[sezon, rok] = round(f1_score(sub['y_true'], sub['y_pred'], zero_division=0), 2)
        fig, ax = plt.subplots(figsize=(max(6, len(lata) * 1.3), 4))
        sns.heatmap(macierz.astype(float), annot=True, fmt='.2f', cmap='RdYlGn', vmin=0, vmax=1, linewidths=0.5, ax=ax, cbar_kws={'label': 'F1'})
        ax.set_title(f'Mapa stabilności F1 ({self.model_name.upper()})', fontsize=12)
        plt.tight_layout()
        plt.savefig(f"{self.target_dir}/heatmapa_stabilnosci_f1.png", dpi=300)
        plt.close()


# ── POPRAWIONA FUNKCJA WEJŚCIOWA ──────────────────────────────────────────────

def uruchom_benchmark(diagnozy: pd.DataFrame,
                      df_poziomy: Optional[pd.DataFrame] = None,
                      prob_threshold: float = 0.50,
                      col_poziom: str = 'Poziom_wody_max',
                      tolerancja_dni: int = 2,
                      model_name: str = "rf") -> Dict:  # <--- TUTAJ: dodany brakujący parametr przekazywany z maina
    """
    Parametry
    ----------
    diagnozy       : DataFrame zwrócony przez ml_factor_system.uruchom_system() lub lstm_system
    df_poziomy     : opcjonalny DataFrame z kolumnami poziomów wody (index=Data)
    prob_threshold : próg klasyfikacji (domyślnie 0.50)
    col_poziom     : nazwa kolumny poziomu wody w df_poziomy
    tolerancja_dni : tolerancja przy dopasowywaniu epizodów (domyślnie 2 dni)
    model_name     : identyfikator modelu ("rf" lub "lstm") do segregacji wyników
    """
    val = BenchmarkValidator(
        diagnozy=diagnozy,
        df_poziomy=df_poziomy,
        prob_threshold=prob_threshold,
        tolerancja_dni=tolerancja_dni,
        model_name=model_name  # <--- TUTAJ: prawidłowe przekisowanie wartości do klasy dataclass
    )
    return val.pelny_raport(col_poziom=col_poziom)


# ── SPRAWDZONY BLOK URUCHOMIENIA DLA OBU MODELI ───────────────────────────────

if __name__ == "__main__":
    # Wspólny zbiór poziomów wody (final.csv)
    df_final = pd.read_csv(
        os.path.join(_ROOT, "data", "processed", "final.csv"),
        parse_dates=["Data"], index_col="Data"
    )

    # 1. URUCHOMIENIE WALIDACJI DLA RANDOM FOREST
    rf_path = os.path.join(_ROOT, "reports", "ml", "diagnozy_dzienne_rf.csv")
    if os.path.exists(rf_path):
        diagnozy_rf = pd.read_csv(rf_path, parse_dates=["Data"], index_col="Data")
        uruchom_benchmark(diagnozy_rf, df_poziomy=df_final, model_name="rf")
    else:
        print(f"[INFO] Brak pliku {rf_path} - pomijam walidację RF.")

    # 2. URUCHOMIENIE WALIDACJI DLA LSTM
    lstm_path = os.path.join(_ROOT, "reports", "ml", "diagnozy_dzienne_lstm.csv")
    if os.path.exists(lstm_path):
        diagnozy_lstm = pd.read_csv(lstm_path, parse_dates=["Data"], index_col="Data")
        uruchom_benchmark(diagnozy_lstm, df_poziomy=df_final, model_name="lstm")
    else:
        print(f"[INFO] Brak pliku {lstm_path} - pomijam walidację LSTM.")