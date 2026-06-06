# 7. Walidacja i benchmark

## Cel walidacji

Celem walidacji było sprawdzenie skuteczności prostego systemu wykrywania epizodów wysokiego poziomu wody. System generował alarm na podstawie wartości opadu skumulowanego z ostatnich 72 godzin (`Opad_72h`). Za rzeczywisty epizod wysokiej wody uznano dni, w których maksymalny poziom wody przekraczał 90. percentyl wartości historycznych.

---
## 7.1 Pokrycie zdarzeń (Event Coverage / Recall)
Recall określa, jaki procent rzeczywistych epizodów wysokiej wody został wykryty przez system.

**Wynik:**
* Recall = **0.165** (16,5%)

Oznacza to, że system poprawnie wykrył około 16,5% rzeczywistych epizodów wysokiej wody. Większość wezbrań nie została poprzedzona alarmem wygenerowanym na podstawie przyjętego kryterium opadowego.

---
## 7.2 Trafność alarmów (Precision)
Precision określa, jaki procent wygenerowanych alarmów odpowiadał rzeczywistym epizodom wysokiej wody.

**Wynik:**
* Precision = **0.175** (17,5%)

Oznacza to, że jedynie około 17,5% alarmów było trafnych, natomiast pozostałe alarmy stanowiły fałszywe wskazania.

---
## 7.3 Błąd początku i końca epizodu
Oceniono zgodność czasową pomiędzy rzeczywistymi epizodami wysokiej wody a epizodami wykrytymi przez system.

### Onset Error
Średni błąd początku epizodu:
* **2,54 dnia**
Oznacza to, że system mylił moment rozpoczęcia wezbrania średnio o około 2–3 dni.

### Offset Error
Średni błąd zakończenia epizodu:
* **4,36 dnia**
Oznacza to, że system miał większe trudności z poprawnym określeniem końca wezbrania niż jego początku.

---
## 7.4 Błąd piku wezbrania
Przeanalizowano zgodność momentu wystąpienia maksimum poziomu wody oraz wysokości tego maksimum.
### Peak Timing Error
Średni błąd czasu wystąpienia maksimum:
* **2,43 dnia**
System wskazywał moment kulminacji wezbrania średnio z błędem około 2,5 dnia.

### Peak Height Error
Średni błąd wysokości maksimum:
* **0,061 m**

Oznacza to, że przewidywana wysokość maksymalnego poziomu wody różniła się od rzeczywistej średnio o około 6 cm.
W porównaniu z błędami czasowymi błąd wysokości maksimum można uznać za relatywnie niewielki.

---
## 7.5 Stabilność wyników rok-po-roku

| Rok  | Recall | Precision |
| ---- | ------ | --------- |
| 2021 | 0.045  | 0.034     |
| 2022 | 0.122  | 0.316     |
| 2023 | 0.170  | 0.211     |
| 2024 | 0.256  | 0.216     |
| 2025 | 0.182  | 0.130     |

### Interpretacja

Najniższą skuteczność wykrywania epizodów uzyskano w roku 2021, gdzie wykryto jedynie około 4,5% rzeczywistych zdarzeń.
Najlepsze wyniki osiągnięto w roku 2024, dla którego Recall wyniósł około 25,6%.
Wartości Precision również zmieniały się znacząco między latami. Najwyższą trafność alarmów odnotowano w roku 2022 (31,6%).
Wyniki wskazują na zauważalną zmienność skuteczności systemu w czasie, co sugeruje wpływ specyficznych warunków meteorologicznych i hydrologicznych występujących w poszczególnych latach.

---

## 7.6 Stabilność sezonowa

| Sezon  | Recall | Precision |
| ------ | ------ | --------- |
| Wiosna | 0.000  | 0.000     |
| Lato   | 0.333  | 0.088     |
| Jesień | 0.137  | 0.171     |
| Zima   | 0.158  | 0.563     |

### Interpretacja

Najwyższy poziom wykrywalności epizodów uzyskano latem (Recall = 0.333). Jednocześnie bardzo niska wartość Precision (0.088) oznacza dużą liczbę fałszywych alarmów.
Najwyższą trafność alarmów odnotowano zimą (Precision = 0.563), co oznacza, że ponad połowa alarmów odpowiadała rzeczywistym epizodom wysokiej wody.
Brak wykrytych epizodów wiosną wskazuje, że przyjęty mechanizm oparty wyłącznie na opadzie skumulowanym nie odzwierciedla wszystkich procesów wpływających na poziom wody, takich jak retencja zlewni, wcześniejsze opady czy warunki hydrologiczne.

---
## 7.7 Wnioski
1. Zastosowany benchmark oparty na opadzie skumulowanym z 72 godzin pozwala na częściowe wykrywanie epizodów wysokiej wody, jednak jego skuteczność jest ograniczona.
2. Niskie wartości Recall (16,5%) oraz Precision (17,5%) wskazują, że sam opad nie jest wystarczającym czynnikiem do wiarygodnego prognozowania wezbrań.
3. Pomimo niskiej skuteczności klasyfikacyjnej, błędy czasowe początku i maksimum epizodu pozostają stosunkowo niewielkie (około 2–4 dni), co sugeruje istnienie związku pomiędzy intensywnymi opadami a późniejszym wzrostem poziomu wody.
4. Błąd wysokości maksimum wynoszący około 0,06 m wskazuje, że opad może dobrze wyjaśniać skalę niektórych wezbrań, choć nie zawsze poprawnie identyfikuje moment ich wystąpienia.
5. Widoczna zmienność wyników pomiędzy latami oraz porami roku sugeruje konieczność uwzględnienia dodatkowych zmiennych, takich jak temperatura, wcześniejsze poziomy wody, ciśnienie atmosferyczne oraz bardziej zaawansowane wskaźniki nasycenia zlewni.
6. Uzyskane wyniki stanowią punkt odniesienia (benchmark) dla przyszłych, bardziej zaawansowanych modeli statystycznych lub modeli uczenia maszynowego.