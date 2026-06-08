# 7. Benchmark i metryki walidacyjne modelu LSTM

## Cel walidacji
Celem walidacji było określenie skuteczności modelu LSTM w wykrywaniu epizodów wysokiej wody oraz ocena stabilności jego działania w różnych okresach czasu. Analizie poddano zarówno poprawność identyfikacji samych zdarzeń, jak i dokładność określania ich początku, końca oraz maksymalnego poziomu wody.

Parametry walidacji:
* próg klasyfikacji: **0,5**
* tolerancja dopasowania epizodów: **±2 dni**

## 7.1. Błąd początku i końca epizodu (Onset/Offset Error)
Metryka onset/offset określa, o ile dni model myli początek oraz koniec wezbrania względem danych rzeczywistych.

| Metryka                       | Wartość    |
| ----------------------------- | ---------- |
| Liczba epizodów rzeczywistych | 60         |
| Wykryte epizody               | 35 (58,3%) |
| Niewykryte epizody            | 25 (41,7%) |
| Średni błąd początku (onset)  | -8,31 dni  |
| Odchylenie standardowe onset  | 11,10 dni  |
| Mediana onset                 | -2 dni     |
| Średni błąd końca (offset)    | +7,49 dni  |
| Odchylenie standardowe offset | 8,60 dni   |
| Mediana offset                | +4 dni     |

Wnioski:
* ujemna wartość błędu onset oznacza, że model przeciętnie rozpoczyna alarmowanie około **8 dni przed rzeczywistym początkiem wezbrania**. 
* dodatni błąd offset wskazuje, że epizody są utrzymywane średnio o **7,5 dnia dłużej** niż wynika to z danych obserwacyjnych.
* mediana onset równa -2 dni oraz mediana offset równa +4 dni wskazują na systematyczną tendencję do wydłużania czasu trwania wykrywanych zdarzeń,

## 7.2. Pokrycie zdarzeń (Event Coverage / Recall)
Metryka określa, jaki odsetek rzeczywistych epizodów wysokiej wody został wykryty przez model.


| Metryka                     | Wartość |
| --------------------------- | ------- |
| Rzeczywiste epizody         | 60      |
| Epizody wykryte przez model | 52      |
| Epizody niewykryte          | 8       |
| Event Recall                | 0,867   |

Wnioski:
Model wykrył około **86,7% rzeczywistych epizodów wysokiej wody**. Wynik ten należy uznać za dobry, ponieważ większość zdarzeń została poprawnie rozpoznana. Jednocześnie około 13% epizodów pozostało niewykrytych.

## 7.3. Fałszywe alarmy (False Alarm Rate)
Metryka ta pozwala ocenić liczbę błędnych alarmów generowanych przez model.

### Poziom dzienny
Jeśli model przewidział alarm na 8 dni (czyli włączył go 3 dni za wcześnie), to te 3 dni są traktowane jako 3 osobne fałszywe alarmy.

| Metryka          | Wartość |
| ---------------- | ------- |
| Precision        | 0,332   |
| False Alarm Rate | 0,668   |

Wnioski:
* precyzja na poziomie dziennym wynosi jedynie **33,2%**, co oznacza, że mniej niż połowa dni oznaczonych przez model jako epizodowe odpowiada rzeczywistym zdarzeniom.
* wysoki poziom FAR jest bezpośrednio związany z obserwowaną tendencją modelu do przedwczesnego rozpoczynania i zbyt późnego kończenia alarmów.

### Poziom zdarzeń

| Metryka                        | Wartość |
| ------------------------------ | ------- |
| Liczba przewidzianych epizodów | 76      |
| Fałszywe epizody               | 41      |
| Event FAR                      | 0,539   |

Interpretacja:
* wskaźnik **Event FAR = 0,539** oznacza, że prawie **54% wykrytych epizodów stanowiło fałszywe alarmy**. Jest to jedna z głównych słabości modelu LSTM i wskazuje na jego tendencję do nadmiernego generowania alarmów.

## 7.4. Błąd piku wezbrania
Metryka ocenia dokładność określenia momentu wystąpienia maksimum wezbrania oraz wartości maksymalnego poziomu wody.

| Metryka                      | Wartość    |
| ---------------------------- | ---------- |
| Liczba dopasowanych epizodów | 35         |
| Średni błąd czasu piku       | -0,23 dnia |
| Średni błąd wysokości piku   | +0,1466    |

Interpretacja:
* maksimum wezbrania jest wskazywane średnio około **0,2 dnia wcześniej** niż ma to miejsce w rzeczywistości.
* dodatni błąd wysokości piku oznacza tendencję do **przeszacowywania maksymalnego poziomu wody**. Zjawisko to jest zgodne z obserwowaną wcześniej skłonnością modelu do wydłużania epizodów oraz generowania nadmiarowych alarmów.

## 7.5. Zgodność wartości poziomu wody (MAE / RMSE)
Ocena dokładności odwzorowania poziomu wody dla części regresyjnej modelu.

### Dni epizodowe

| Metryka | Wartość |
| ------- | ------- |
| MAE     | 0,4210  |
| RMSE    | 0,4634  |

### Dni poza epizodami

| Metryka | Wartość |
| ------- | ------- |
| MAE     | 0,3349  |
| RMSE    | 0,3890  |

Wnioski:
* Błędy regresyjne są wyraźnie większe podczas rzeczywistych epizodów wysokiej wody niż w okresach spokojnych. 
* Oznacza to, że model poprawnie identyfikuje ogólną tendencję zmian poziomu wody, jednak ma trudności z dokładnym odwzorowaniem wartości podczas dynamicznych sytuacji hydrologicznych.

## 7.6. Stabilność sezonowa

### Wyniki dla poszczególnych sezonów

| Sezon  | Recall | Precision | F1    | Event Recall |
| ------ | ------ | --------- | ----- | ------------ |
| Zima   | 0,981  | 0,502     | 0,665 | 1,000        |
| Wiosna | 0,500  | 0,286     | 0,364 | 0,333        |
| Lato   | 0,583  | 0,125     | 0,206 | 0,500        |
| Jesień | 0,963  | 0,230     | 0,371 | 1,000        |

Interpretacja:
Najlepsze wyniki uzyskano zimą. Model wykrył wszystkie epizody zimowe (Event Recall = 1,0), osiągając bardzo wysoki recall.
Najsłabsze wyniki odnotowano wiosną oraz latem. Szczególnie niski poziom precyzji latem (0,125) oznacza, że większość wykrywanych alarmów nie znajdowała potwierdzenia w danych rzeczywistych.
Jesień również charakteryzuje się pełnym pokryciem zdarzeń, jednak bardzo niską precyzją, co oznacza dużą liczbę fałszywych alarmów.

## 7.7. Stabilność rok-po-roku

| Rok  | Recall | Precision | F1    | Event Recall |
| ---- | ------ | --------- | ----- | ------------ |
| 2021 | 0,909  | 0,303     | 0,455 | 0,889        |
| 2022 | 0,909  | 0,412     | 0,567 | 0,769        |
| 2023 | 1,000  | 0,336     | 0,503 | 1,000        |
| 2024 | 0,973  | 0,273     | 0,426 | 1,000        |
| 2025 | 0,833  | 0,349     | 0,492 | 0,750        |

Interpretacja:
Model utrzymuje wysokie wartości recall w większości lat, co oznacza skuteczne wykrywanie zdarzeń wysokiej wody.
Jednocześnie precyzja pozostaje niska i wykazuje istotne wahania pomiędzy latami. Najwyższą skuteczność klasyfikacji uzyskano w roku 2022 (F1 = 0,567), natomiast najsłabszy wynik wystąpił w roku 2024 (F1 = 0,426).

## 7.8. Ocena stabilności wyników w czasie

Analiza rok-po-roku wskazuje, że model LSTM zachowuje względnie stabilną zdolność wykrywania zdarzeń (wysoki recall), jednak jego precyzja pozostaje niestabilna i zależna od charakterystyki danego roku hydrologicznego.

Brak systematycznego spadku recall sugeruje, że model nie traci zdolności wykrywania zdarzeń wraz z upływem czasu. Jednocześnie utrzymująca się niska precyzja wskazuje, że głównym problemem modelu pozostaje nadmierne alarmowanie.

## 7.9. Wnioski

Przeprowadzona walidacja wykazała, że model LSTM skutecznie identyfikuje większość epizodów wysokiej wody (Event Recall = 0,867), jednak osiąga stosunkowo niską precyzję klasyfikacji.

Głównym ograniczeniem modelu pozostaje stosunkowo wysoka liczba fałszywych alarmów (Event FAR = 53,9%).
