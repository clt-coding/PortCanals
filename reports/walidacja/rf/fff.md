## 7.1. Błąd początku i końca epizodu (Onset/Offset Error)

Metryka onset/offset określa, o ile dni model myli początek oraz koniec wezbrania względem danych rzeczywistych.

| Metryka                       | Wartość    |
| ----------------------------- | ---------- |
| Liczba epizodów rzeczywistych | 60         |
| Wykryte epizody               | 32 (53,3%) |
| Niewykryte epizody            | 28 (46,7%) |
| Średni błąd początku (onset)  | -12,94 dni |
| Odchylenie standardowe onset  | 15,66 dni  |
| Mediana onset                 | -8,5 dnia  |
| Średni błąd końca (offset)    | +12,22 dni |
| Odchylenie standardowe offset | 14,51 dni  |
| Mediana offset                | +5,5 dnia  |

Wnioski:

* ujemna wartość błędu onset oznacza, że model przeciętnie rozpoczyna alarmowanie około **13 dni przed rzeczywistym początkiem wezbrania**,
* dodatni błąd offset wskazuje, że epizody są utrzymywane średnio o **12 dni dłużej** niż wynika to z danych obserwacyjnych,
* mediana onset równa -8,5 dnia oraz mediana offset równa +5,5 dnia wskazują na silną tendencję do wydłużania czasu trwania wykrywanych zdarzeń,
* bardzo wysokie wartości odchyleń standardowych świadczą o dużej niestabilności wyznaczania granic epizodów.

## 7.2. Pokrycie zdarzeń (Event Coverage / Recall)

Metryka określa, jaki odsetek rzeczywistych epizodów wysokiej wody został wykryty przez model.

| Metryka                     | Wartość |
| --------------------------- | ------- |
| Rzeczywiste epizody         | 60      |
| Epizody wykryte przez model | 49      |
| Epizody niewykryte          | 11      |
| Event Recall                | 0,817   |

Wnioski:

Model wykrył około **81,7% rzeczywistych epizodów wysokiej wody**. Wynik ten należy uznać za dobry, jednak oznacza również, że niemal co piąte rzeczywiste wezbranie nie zostało wykryte.

## 7.3. Fałszywe alarmy (False Alarm Rate)

Metryka ta pozwala ocenić liczbę błędnych alarmów generowanych przez model.

### Poziom dzienny

Jeśli model przewidział alarm na 8 dni (czyli włączył go 3 dni za wcześnie), to te 3 dni są traktowane jako 3 osobne fałszywe alarmy.

| Metryka          | Wartość |
| ---------------- | ------- |
| Precision        | 0,343   |
| False Alarm Rate | 0,657   |

Wnioski:

* precyzja na poziomie dziennym wynosi jedynie **34,3%**, co oznacza, że większość dni oznaczonych przez model jako epizodowe nie odpowiada rzeczywistym zdarzeniom,
* wysoki poziom FAR jest bezpośrednio związany z obserwowaną tendencją modelu do znacznie wcześniejszego rozpoczynania i późniejszego kończenia alarmów.

### Poziom zdarzeń

| Metryka                        | Wartość |
| ------------------------------ | ------- |
| Liczba przewidzianych epizodów | 57      |
| Fałszywe epizody               | 29      |
| Event FAR                      | 0,509   |

Interpretacja:

* wskaźnik **Event FAR = 0,509** oznacza, że około **51% wykrytych epizodów stanowiło fałszywe alarmy**,
* model nadal wykazuje silną tendencję do nadmiernego alarmowania.

## 7.4. Błąd piku wezbrania

Metryka ocenia dokładność określenia momentu wystąpienia maksimum wezbrania oraz wartości maksymalnego poziomu wody.

| Metryka                               | Wartość    |
| ------------------------------------- | ---------- |
| Liczba dopasowanych epizodów          | 32         |
| Średni błąd czasu piku                | -1,28 dnia |
| Odchylenie standardowe czasu piku     | 10,25 dnia |
| Średni błąd wysokości piku            | +0,1806    |
| Odchylenie standardowe wysokości piku | 0,2475     |

Interpretacja:

* maksimum wezbrania jest wskazywane średnio około **1,3 dnia wcześniej** niż ma to miejsce w rzeczywistości,
* dodatni błąd wysokości piku oznacza tendencję do **przeszacowywania maksymalnego poziomu wody**,
* wysoka zmienność błędu czasowego wskazuje na niestabilność lokalizacji kulminacji wezbrania.

## 7.5. Zgodność wartości poziomu wody (MAE / RMSE)

Ocena dokładności odwzorowania poziomu wody dla części regresyjnej modelu.

### Dni epizodowe

| Metryka | Wartość |
| ------- | ------- |
| MAE     | 0,4340  |
| RMSE    | 0,4766  |

### Dni poza epizodami

| Metryka | Wartość |
| ------- | ------- |
| MAE     | 0,3384  |
| RMSE    | 0,3959  |

Wnioski:

* błędy regresyjne są wyraźnie większe podczas rzeczywistych epizodów wysokiej wody niż poza nimi,
* model poprawnie odwzorowuje ogólną dynamikę zmian poziomu wody, jednak ma trudności z dokładnym prognozowaniem wartości podczas intensywnych wezbrań.

## 7.6. Stabilność sezonowa

### Wyniki dla poszczególnych sezonów

| Sezon  | Recall | Precision | F1    | Event Recall |
| ------ | ------ | --------- | ----- | ------------ |
| Zima   | 0,991  | 0,417     | 0,587 | 1,000        |
| Wiosna | 0,500  | 0,167     | 0,250 | 0,333        |
| Lato   | 0,083  | 0,167     | 0,111 | 0,125        |
| Jesień | 0,944  | 0,271     | 0,421 | 1,000        |

Interpretacja:

Najlepsze wyniki uzyskano zimą, gdzie model wykrył wszystkie rzeczywiste epizody (Event Recall = 1,0).

Najsłabsze wyniki występują latem. Recall równy 0,083 oznacza, że model rozpoznał jedynie około 8% dni epizodowych. Bardzo niskie wartości precision i F1 wskazują na ograniczoną skuteczność modelu w tym sezonie.

Jesień charakteryzuje się pełnym pokryciem zdarzeń, jednak bardzo niską precyzją, co oznacza dużą liczbę fałszywych alarmów.

## 7.7. Stabilność rok-po-roku

| Rok  | Recall | Precision | F1    | Event Recall |
| ---- | ------ | --------- | ----- | ------------ |
| 2021 | 0,909  | 0,282     | 0,430 | 0,889        |
| 2022 | 0,909  | 0,440     | 0,593 | 0,769        |
| 2023 | 0,976  | 0,354     | 0,519 | 1,000        |
| 2024 | 0,946  | 0,278     | 0,429 | 0,923        |
| 2025 | 0,722  | 0,377     | 0,495 | 0,625        |

Interpretacja:

Model utrzymuje wysokie wartości recall w większości lat, co oznacza skuteczne wykrywanie zdarzeń wysokiej wody.

Jednocześnie precyzja pozostaje niska i wykazuje istotne wahania pomiędzy latami. Najwyższą skuteczność klasyfikacji uzyskano w roku 2022 (F1 = 0,593), natomiast najsłabsze wyniki odnotowano w latach 2021 oraz 2024.

W roku 2025 zauważalny jest spadek zarówno recall, jak i Event Recall, co wskazuje na pogorszenie zdolności wykrywania części epizodów.

## 7.8. Ocena stabilności wyników w czasie

Analiza rok-po-roku wskazuje, że model LSTM zachowuje względnie stabilną zdolność wykrywania zdarzeń, jednak jego precyzja pozostaje niska i silnie zależy od charakterystyki danego roku hydrologicznego.

Największe problemy modelu dotyczą liczby fałszywych alarmów oraz niedokładnego określania początku i końca epizodów. Brak systematycznego spadku recall sugeruje jednak, że model nie traci całkowicie zdolności wykrywania zdarzeń wraz z upływem czasu.

## 7.9. Wnioski

Przeprowadzona walidacja wykazała, że model LSTM skutecznie identyfikuje większość epizodów wysokiej wody (Event Recall = 0,817), jednak osiąga stosunkowo niską precyzję klasyfikacji.

Głównym ograniczeniem modelu pozostaje wysoka liczba fałszywych alarmów (Event FAR = 50,9%) oraz bardzo duże błędy wyznaczania początku i końca epizodów (średnio około ±12 dni).

W porównaniu z modelem Random Forest model LSTM wykazuje większą tendencję do wydłużania czasu trwania wezbrań, generowania fałszywych alarmów oraz przeszacowywania maksymalnych poziomów wody.

Analiza sezonowa i rok-po-roku potwierdza, że model zachowuje zdolność wykrywania większości zdarzeń, jednak jego dokładność operacyjna pozostaje wyraźnie niższa niż w przypadku modelu RF.
