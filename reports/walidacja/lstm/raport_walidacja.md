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
| Wykryte epizody               | 31 (51,7%) |
| Niewykryte epizody            | 29 (48,3%) |
| Średni błąd początku (onset)  | -7,0 dni   |
| Odchylenie standardowe onset  | 9,0 dni    |
| Mediana onset                 | -3 dni     |
| Średni błąd końca (offset)    | +6,0 dni   |
| Odchylenie standardowe offset | 7,81 dni   |
| Mediana offset                | +3 dni     |

Wnioski:
* ujemna wartość błędu onset oznacza, że model przeciętnie rozpoczyna alarmowanie około **7 dni przed rzeczywistym początkiem wezbrania**. 
* dodatni błąd offset wskazuje, że epizody są utrzymywane średnio o **6 dni dłużej** niż wynika to z danych obserwacyjnych.

Wysokie wartości odchyleń standardowych świadczą o znacznej zmienności dokładności wyznaczania granic epizodów. W porównaniu do klasycznego modelu Random Forest model LSTM wykazuje większą tendencję do rozszerzania czasu trwania zdarzeń.

## 7.2. Pokrycie zdarzeń (Event Coverage / Recall)
Metryka określa, jaki odsetek rzeczywistych epizodów wysokiej wody został wykryty przez model.


| Metryka                     | Wartość |
| --------------------------- | ------- |
| Rzeczywiste epizody         | 60      |
| Epizody wykryte przez model | 49      |
| Epizody niewykryte          | 11      |
| Event Recall                | 0,817   |

Wnioski:
Model wykrył około **81,7% rzeczywistych epizodów wysokiej wody**. Wynik ten należy uznać za dobry, ponieważ większość zdarzeń została poprawnie rozpoznana. Jednocześnie około 18% epizodów pozostało niewykrytych.


## 7.3. Fałszywe alarmy (False Alarm Rate)
Metryka ta pozwala ocenić liczbę błędnych alarmów generowanych przez model.

### Poziom dzienny
Jeśli model przewidział alarm na 8 dni (czyli włączył go 3 dni za wcześnie), to te 3 dni są traktowane jako 3 osobne fałszywe alarmy.

| Metryka             | Wartość |
| ------------------- | ------- |
| Precision           | 0,411   |
| False Alarm Rate    | 0,589   |

Wnioski:
* precyzja na poziomie dziennym wynosi jedynie **41,1%**, co oznacza, że mniej niż połowa dni oznaczonych przez model jako epizodowe odpowiada rzeczywistym zdarzeniom.

### Poziom zdarzeń

| Metryka                        | Wartość |
| ------------------------------ | ------- |
| Liczba przewidzianych epizodów | 61      |
| Fałszywe epizody               | 30      |
| Event FAR                      | 0,492   |

Interpretacja:
* wskaźnik **Event FAR = 0,492** oznacza, że prawie **49% wykrytych epizodów stanowiło fałszywe alarmy**. Jest to jedna z głównych słabości modelu LSTM i wskazuje na jego tendencję do nadmiernego generowania alarmów.

## 7.4. Błąd piku wezbrania
Metryka ocenia dokładność określenia momentu wystąpienia maksimum wezbrania oraz wartości maksymalnego poziomu wody.

| Metryka                          | Wartość    |
| -------------------------------- | ---------- |
| Liczba dopasowanych epizodów     | 31         |
| Średni błąd czasu piku           | -3.58 dni  |
| Średni błąd wysokości piku       | +0,1477    |

Interpretacja:
* maksimum wezbrania jest wskazywane średnio około **3,6 dnia wcześniej** niż ma to miejsce w rzeczywistości.
* dodatni błąd wysokości piku oznacza tendencję do **przeszacowywania maksymalnego poziomu wody**. Zjawisko to jest zgodne z obserwowaną wcześniej skłonnością modelu do wydłużania epizodów oraz generowania nadmiarowych alarmów.

## 7.5. Zgodność wartości poziomu wody (MAE / RMSE)
Ocena dokładności odwzorowania poziomu wody dla części regresyjnej modelu.

### Dni epizodowe

| Metryka | Wartość |
| ------- | ------- |
| MAE     | 0,4843  |
| RMSE    | 0,5254  |

### Dni poza epizodami

| Metryka | Wartość |
| ------- | ------- |
| MAE     | 0,3643  |
| RMSE    | 0,4159  |

Wnioski:
* Błędy regresyjne są wyraźnie większe podczas rzeczywistych epizodów wysokiej wody niż w okresach spokojnych. Oznacza to, że model poprawnie identyfikuje ogólną tendencję zmian poziomu wody, jednak ma trudności z dokładnym odwzorowaniem wartości podczas dynamicznych sytuacji hydrologicznych.

## 7.6. Stabilność sezonowa

### Wyniki dla poszczególnych sezonów

| Sezon  | Recall | Precision | F1    | Event Recall |
| ------ | ------ | --------- | ----- | ------------ |
| Zima   | 0,981  | 0,502     | 0,665 | 1,000        |
| Wiosna | 0,625  | 0,417     | 0,500 | 0,500        |
| Lato   | 0,083  | 0,143     | 0,105 | 0,125        |
| Jesień | 0,907  | 0,304     | 0,456 | 0,947        |

Interpretacja:
Najlepsze wyniki uzyskano zimą. Model wykrył wszystkie epizody zimowe (Event Recall = 1,0), osiągając bardzo wysoki recall.
Znacznie słabsze wyniki występują latem. Recall równy 0,083 oznacza, że model rozpoznał jedynie około 8% dni epizodowych. Niska wartość F1 (0,105) wskazuje na bardzo ograniczoną skuteczność modelu w tym sezonie.
Jesień charakteryzuje się wysokim pokryciem zdarzeń, jednak bardzo niską precyzją, co oznacza dużą liczbę fałszywych alarmów.

## 7.7. Stabilność rok-po-roku

| Rok  | Recall | Precision | F1    | Event Recall |
| ---- | ------ | --------- | ----- | ------------ |
| 2021 | 0,909  | 0,426     | 0,580 | 0,889        |
| 2022 | 0,886  | 0,557     | 0,684 | 0,692        |
| 2023 | 0,951  | 0,411     | 0,574 | 0,900        |
| 2024 | 0,946  | 0,302     | 0,458 | 0,923        |
| 2025 | 0,722  | 0,441     | 0,547 | 0,750        |

Interpretacja:
Model utrzymuje wysokie wartości recall w większości lat, co oznacza skuteczne wykrywanie zdarzeń wysokiej wody.
Jednocześnie obserwowane są znaczne wahania precyzji. Najwyższą skuteczność klasyfikacji uzyskano w roku 2022 (F1 = 0,684), natomiast najsłabszy wynik wystąpił w roku 2024 (F1 = 0,458).
Spadek recall do poziomu 0,722 w roku 2025 sugeruje pogorszenie zdolności wykrywania części epizodów, jednak nie wskazuje na trwałą degradację modelu.

## 7.8. Ocena stabilności wyników w czasie

Analiza rok-po-roku wskazuje, że model LSTM zachowuje względnie stabilną zdolność wykrywania zdarzeń (wysoki recall), jednak jego precyzja pozostaje niestabilna i zależna od charakterystyki danego roku hydrologicznego.

Największe różnice pomiędzy latami dotyczą liczby generowanych fałszywych alarmów, a nie samego wykrywania epizodów. Oznacza to, że model jest bardziej podatny na nadmierne alarmowanie niż na pomijanie rzeczywistych zdarzeń.

---

## 7.9. Wnioski

Przeprowadzona walidacja wykazała, że model LSTM skutecznie identyfikuje większość epizodów wysokiej wody (Event Recall = 0,817), jednak osiąga stosunkowo niską precyzję klasyfikacji.

Głównym ograniczeniem modelu pozostaje stosunkowo wysoka liczba fałszywych alarmów (Event FAR = 49,2%).
