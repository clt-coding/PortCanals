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
| Wykryte epizody               | 33 (55,0%) |
| Niewykryte epizody            | 27 (45,0%) |
| Średni błąd początku (onset)  | -2,00 dni  |
| Odchylenie standardowe onset  | 3,66 dni   |
| Mediana onset                 | 0 dni      |
| Średni błąd końca (offset)    | +0,91 dni  |
| Odchylenie standardowe offset | 2,40 dni   |
| Mediana offset                | 0 dni      |

Wnioski:
* ujemny błąd onset oznacza, że model przeciętnie sygnalizuje początek wezbrania około **2 dni wcześniej**  niż występuje ono w rzeczywistości,
* dodatni błąd offset wskazuje, że model utrzymuje alarm średnio o **0,9 dni dłużej** niż rzeczywisty epizod,
* mediana onset równa 0 dni dla obu metryk oznacza, że dla znacznej części epizodów granice zdarzeń zostały określone poprawnie,
* stosunkowo niewielkie odchylenia standardowe świadczą o stabilnym wyznaczaniu początku i końca wezbrań.

## 7.2. Pokrycie zdarzeń (Event Coverage / Recall)
Metryka określa, jaki odsetek rzeczywistych epizodów wysokiej wody został wykryty przez model.

| Metryka                     | Wartość |
| --------------------------- | ------- |
| Rzeczywiste epizody         | 60      |
| Epizody wykryte przez model | 51      |
| Epizody niewykryte          | 9       |
| Event Recall                | 0,850   |

Wnioski:
Model wykrył **85,0% wszystkich rzeczywistych wezbrań**, co świadczy o wysokiej skuteczności identyfikacji zdarzeń. Jedynie 15% epizodów nie zostało rozpoznanych.

---

## 7.3. Fałszywe alarmy (False Alarm Rate)
Metryka ta pozwala ocenić liczbę błędnych alarmów generowanych przez model.

### Poziom dzienny

| Metryka          | Wartość |
| ---------------- | ------- |
| Precision        | 0,581   |
| False Alarm Rate | 0,419   |

Oznacza to, że około **58,1% dni oznaczonych jako epizodowe było poprawnych**, natomiast około **41,9% stanowiły fałszywe wskazania**.

### Poziom zdarzeń

| Metryka                        | Wartość |
| ------------------------------ | ------- |
| Liczba przewidzianych epizodów | 72      |
| Fałszywe epizody               | 27      |
| Event FAR                      | 0,375   |

Interpretacja:
Spośród wszystkich wykrytych epizodów około **37,5% nie znalazło potwierdzenia w danych rzeczywistych**. Model jest więc stosunkowo czuły, ale generuje zauważalną liczbę nadmiarowych alarmów.

## 7.4. Błąd piku wezbrania
Analiza dokładności wskazania momentu oraz wysokości maksymalnego poziomu wody.

| Metryka                          | Wartość    |
| -------------------------------- | ---------- |
| Liczba dopasowanych epizodów     | 33         |
| Średni błąd czasu piku           | -0,39 dnia |
| Odchylenie standardowe           | 3,46 dnia  |
| Średni błąd wysokości piku       | +0,0418    |
| Odchylenie standardowe wysokości | 0,1326     |

Interpretacja:
* maksimum wezbrania jest wskazywane średnio niecałe pół dnia wcześniej niż w rzeczywistości,
* błąd wysokości piku jest niewielki, co oznacza dobrą zgodność modelu z rzeczywistą amplitudą wezbrania.

## 7.5. Zgodność wartości poziomu wody (MAE / RMSE)
Ocena dokładności odwzorowania poziomu wody dla części regresyjnej modelu.

### Dni epizodowe

| Metryka | Wartość |
| ------- | ------- |
| MAE     | 0,3046  |
| RMSE    | 0,3573  |

### Dni poza epizodami

| Metryka | Wartość |
| ------- | ------- |
| MAE     | 0,2938  |
| RMSE    | 0,3388  |

Wnioski:
* Wartości błędów dla okresów wezbrań i okresów spokojnych są bardzo zbliżone. Oznacza to, że model zachowuje podobny poziom dokładności niezależnie od sytuacji hydrologicznej i nie wykazuje znaczącego pogorszenia jakości podczas epizodów wysokiej wody.

## 7.6. Stabilność sezonowa

### Wyniki według sezonów

| Sezon  | Recall | Precision | F1    | Event Recall |
| ------ | ------ | --------- | ----- | ------------ |
| Zima   | 0,962  | 0,570     | 0,716 | 0,964        |
| Wiosna | 0,625  | 0,714     | 0,667 | 0,500        |
| Lato   | 0,417  | 1,000     | 0,588 | 0,500        |

Interpretacja:
Najlepsze wyniki uzyskano zimą, gdzie model osiągnął bardzo wysokie pokrycie zdarzeń (96,4%). Wiosną i latem skuteczność wykrywania spada, co może wynikać z mniejszej liczby epizodów oraz większej zmienności procesów hydrologicznych.

Należy również zauważyć, że sezon letni charakteryzuje się bardzo wysoką precyzją (1,0), jednak kosztem niskiego recallu.

## 7.7. Stabilność rok-po-roku

| Rok  | Recall | Precision | F1    | Event Recall |
| ---- | ------ | --------- | ----- | ------------ |
| 2021 | 0,955  | 0,538     | 0,689 | 0,889        |
| 2022 | 0,909  | 0,755     | 0,825 | 0,846        |
| 2023 | 0,902  | 0,463     | 0,612 | 1,000        |
| 2024 | 0,973  | 0,545     | 0,699 | 0,923        |
| 2025 | 0,750  | 0,692     | 0,720 | 0,688        |

Interpretacja:
Model zachowuje względnie stabilne działanie w kolejnych latach. Średni recall wynosi blisko 90%, co oznacza, że większość zdarzeń jest wykrywana niezależnie od roku. Najwyższą jakość klasyfikacji odnotowano w 2022 roku (F1 = 0,825), natomiast największy spadek skuteczności wystąpił w 2025 roku.


## 7.8. Ocena stabilności wyników w czasie

Różnice pomiędzy latami nie wskazują jednak na systematyczną degradację modelu, dlatego można uznać jego działanie za stabilne czasowo.

## 7.9. Wnioski

Przeprowadzona walidacja wskazuje, że model skutecznie identyfikuje epizody wysokiej wody i osiąga wysokie pokrycie zdarzeń (Event Recall = 0,85). Szczególnie dobrze radzi sobie z wykrywaniem wezbrań zimowych oraz z określaniem momentu wystąpienia maksimum poziomu wody.

Głównym ograniczeniem modelu pozostaje stosunkowo wysoka liczba fałszywych alarmów (Event FAR = 37,5%).

Analiza sezonowa i rok-po-roku potwierdza, że model zachowuje stabilność działania w czasie, a uzyskane wartości F1 oraz recall nie wykazują istotnych trendów pogorszenia jakości.