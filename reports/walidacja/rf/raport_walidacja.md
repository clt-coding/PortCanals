# 7. Benchmark i metryki walidacyjne modelu ml

## Cel walidacji
Celem walidacji było określenie skuteczności modelu w wykrywaniu epizodów wysokiej wody oraz ocena stabilności jego działania w czasie. Analizie poddano zarówno zdolność identyfikacji samych zdarzeń, jak i dokładność odwzorowania ich przebiegu oraz wartości poziomu wody.

Parametry walidacji:
* próg klasyfikacji: **0,5**
* tolerancja dopasowania epizodów: **±2 dni**

## 7.1. Błąd początku i końca epizodu (Onset/Offset Error)
Metryka określa, o ile dni model przesuwa początek lub koniec wykrytego wezbrania względem rzeczywistego zdarzenia.

| Metryka                       | Wartość    |
| ----------------------------- | ---------- |
| Liczba epizodów rzeczywistych | 60         |
| Wykryte epizody               | 37 (61,7%) |
| Niewykryte epizody            | 23 (38,3%) |
| Średni błąd początku (onset)  | -3,95 dni  |
| Odchylenie standardowe onset  | 6,53 dni   |
| Mediana onset                 | -1 dzień   |
| Średni błąd końca (offset)    | +2,14 dni  |
| Odchylenie standardowe offset | 4,97 dni   |
| Mediana offset                | 0 dni      |

Wnioski:
* ujemny błąd onset oznacza, że model przeciętnie sygnalizuje początek wezbrania około **4 dni wcześniej** niż występuje ono w rzeczywistości,
* dodatni błąd offset wskazuje, że model utrzymuje alarm średnio o **2 dni dłużej** niż rzeczywisty epizod,
* mediana onset równa -1 dzień sugeruje lekką tendencję do wcześniejszego wykrywania zdarzeń,
* większe odchylenia standardowe wskazują na znaczną zmienność dokładności wyznaczania granic epizodów.

## 7.2. Pokrycie zdarzeń (Event Coverage / Recall)
Metryka określa, jaki odsetek rzeczywistych epizodów wysokiej wody został wykryty przez model.

| Metryka                     | Wartość |
| --------------------------- | ------- |
| Rzeczywiste epizody         | 60      |
| Epizody wykryte przez model | 53      |
| Epizody niewykryte          | 7       |
| Event Recall                | 0,883   |

Wnioski:
Model wykrył **88,3% wszystkich rzeczywistych wezbrań**, co świadczy o wysokiej skuteczności identyfikacji zdarzeń. Jedynie 12% epizodów nie zostało rozpoznanych.

---

## 7.3. Fałszywe alarmy (False Alarm Rate)
Metryka ta pozwala ocenić liczbę błędnych alarmów generowanych przez model.

### Poziom dzienny

| Metryka          | Wartość |
| ---------------- | ------- |
| Precision        | 0,475   |
| False Alarm Rate | 0,525   |

Oznacza to, że około **47,5% dni oznaczonych jako epizodowe było poprawnych**, natomiast około **52,5% stanowiły fałszywe wskazania**.

### Poziom zdarzeń

| Metryka                        | Wartość |
| ------------------------------ | ------- |
| Liczba przewidzianych epizodów | 87      |
| Fałszywe epizody               | 45      |
| Event FAR                      | 0,517   |

Interpretacja:
Spośród wszystkich wykrytych epizodów około **51,7% nie znalazło potwierdzenia w danych rzeczywistych**. Model jest więc stosunkowo czuły i skutecznie wykrywa większość zdarzeń, ale generuje zauważalną liczbę nadmiarowych alarmów.

## 7.4. Błąd piku wezbrania
Analiza dokładności wskazania momentu oraz wysokości maksymalnego poziomu wody.

| Metryka                          | Wartość    |
| -------------------------------- | ---------- |
| Liczba dopasowanych epizodów     | 37         |
| Średni błąd czasu piku           | +0,03 dnia |
| Odchylenie standardowe           | 4,99 dnia  |
| Średni błąd wysokości piku       | +0,0727    |
| Odchylenie standardowe wysokości | 0,1707     |

Interpretacja:
* maksimum wezbrania jest wskazywane niemalże tego samego dnia, co świadczy o dobrej lokalizacji momentu wezbrania
* błąd wysokości piku jest niewielki, co oznacza dobrą zgodność modelu z rzeczywistą amplitudą wezbrania.

## 7.5. Zgodność wartości poziomu wody (MAE / RMSE)
Ocena dokładności odwzorowania poziomu wody dla części regresyjnej modelu.

### Dni epizodowe

| Metryka | Wartość |
| ------- | ------- |
| MAE     | 0,3532  |
| RMSE    | 0,4050  |

### Dni poza epizodami

| Metryka | Wartość |
| ------- | ------- |
| MAE     | 0,2742  |
| RMSE    | 0,3245  |

Wnioski:
* błędy regresyjne są większe podczas epizodów wysokiej wody niż podczas okresów spokojnych,
* Wartości błędów dla okresów wezbrań i okresów spokojnych są bardzo zbliżone. Oznacza to, że model zachowuje podobny poziom dokładności niezależnie od sytuacji hydrologicznej i nie wykazuje znaczącego pogorszenia jakości podczas epizodów wysokiej wody.

## 7.6. Stabilność sezonowa

### Wyniki według sezonów

| Sezon  | Recall | Precision | F1    | Event Recall |
| ------ | ------ | --------- | ----- | ------------ |
| Zima   | 0,991  | 0,475     | 0,642 | 1,000        |
| Wiosna | 0,625  | 0,312     | 0,417 | 0,500        |
| Lato   | 0,667  | 1,000     | 0,800 | 0,500        |

Interpretacja:
Najlepsze wyniki uzyskano zimą, wykrył wszystkie rzeczywiste epizody (Event Recall = 1,0). Wiosną i latem skuteczność wykrywania spada, co może wynikać z mniejszej liczby epizodów oraz większej zmienności procesów hydrologicznych.

Latem model osiągnął najwyższą wartość wskaźnika F1 (0,800) oraz perfekcyjną precyzję (1,0), co oznacza brak fałszywych alarmów.

## 7.7. Stabilność rok-po-roku

| Rok  | Recall | Precision | F1    | Event Recall |
| ---- | ------ | --------- | ----- | ------------ |
| 2021 | 0,955  | 0,356     | 0,519 | 0,889        |
| 2022 | 0,955  | 0,712     | 0,816 | 0,846        |
| 2023 | 1,000  | 0,402     | 0,573 | 1,000        |
| 2024 | 0,973  | 0,424     | 0,590 | 0,923        |
| 2025 | 0,861  | 0,564     | 0,681 | 0,812        |

Interpretacja:
Model zachowuje względnie stabilne działanie w kolejnych latach. Najwyższą jakość klasyfikacji odnotowano w 2022 roku (F1 = 0,816), natomiast najsłabszy wynik odnotowano w roku 2021 (F1 = 0,519). W latach 2023–2024 model charakteryzował się bardzo wysokim recall, jednak kosztem zwiększonej liczby fałszywych alarmów.


## 7.8. Ocena stabilności wyników w czasie

Analiza rok-po-roku wskazuje, że model zachowuje wysoką skuteczność wykrywania epizodów w całym analizowanym okresie.
Brak wyraźnego trendu spadkowego sugeruje, że model nie wykazuje oznak systematycznej degradacji jakości predykcji i może być uznany za stabilny czasowo.

## 7.9. Wnioski

Przeprowadzona walidacja wskazuje, że model skutecznie identyfikuje epizody wysokiej wody i osiąga wysokie pokrycie zdarzeń (Event Recall = 0,883). Szczególnie dobrze radzi sobie z wykrywaniem wezbrań zimowych oraz z określaniem momentu wystąpienia maksimum poziomu wody.

Głównym ograniczeniem modelu pozostaje wysoka liczba fałszywych alarmów (Event FAR = 51,7%), która obniża jego precyzję

Analiza sezonowa i rok-po-roku potwierdza, że model zachowuje stabilność działania w czasie, a uzyskane wartości F1 oraz recall nie wykazują istotnych trendów pogorszenia jakości.