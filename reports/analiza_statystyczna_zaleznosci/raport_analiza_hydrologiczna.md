# Analiza statystyczna zależności między opadem atmosferycznym a poziomem wody

---

## 1. Metodyka

Analizę przeprowadzono w następujących etapach dla trzech stacji pomiarowych poziomu wody: **Strzyża**, **Martwa Wisła** i **Port Północny**.

1. **Analiza korelacji krzyżowej z opóźnieniem** — współczynnik Pearsona między dobową sumą opadu a poziomem wody dla opóźnień od 0 do 14 dni, osobno dla każdej stacji.
2. **Macierz korelacji** — analiza współzależności liniowych między wszystkimi zmiennymi meteorologicznymi i hydrologicznymi.
3. **Korelacja między stacjami** — ocena podobieństwa odpowiedzi hydrologicznej między stacjami.
4. **Porównanie agregatów opadu** — zestawienie korelacji Pearsona dla wszystkich dni i wyłącznie dla dni z opadem > 0 mm.
5. **Korelacja Spearmana** — ocena monotonicznej zależności odpornej na rozkład asymetryczny.
6. **Regresja liniowa** — oszacowanie współczynnika kierunkowego dla `Opad_72h` dla każdej stacji.
7. **Analiza grupowa** — porównanie rozkładów poziomu wody w dniach z małym (kwantyl ≤ 25%) i dużym opadem (kwantyl ≥ 75%) za pomocą wykresów KDE i boxplot.
8. **Testy statystyczne** — weryfikacja normalności (Shapiro-Wilk) oraz istotności różnicy między grupami (Mann-Whitney U) dla każdej stacji.

---

## 2. Wyniki

### 2.1 Korelacja krzyżowa z opóźnieniem (lag 0–14 dni)

![Korelacja z opóźnieniem](korelacja_opoznienia.png)

Analiza korelacji z opóźnieniem ujawnia wyraźne różnice między stacjami:

| Stacja        | Maksymalna korelacja (lag=0) |
| ------------- | ---------------------------- |
| Strzyża       | r = 0,196                    |
| Martwa Wisła  | r = 0,157                    |
| Port Północny | r = 0,059                    |

Dla Strzyży i Martwej Wisły najwyższa korelacja występuje przy lag=0 i spada gwałtownie w kolejnych dniach, z lokalną anomalią w dniu 6 (możliwy opóźniony dopływ z wód gruntowych lub efekt retencyjny). Dla obu stacji sygnał zanika dla lag > 7.

Port Północny wykazuje zupełnie inny charakter — korelacja z opadem jest niemal płaska i bliska zeru dla wszystkich opóźnień (r < 0,06). Wskazuje to, że poziom wody w Porcie Północnym jest w minimalnym stopniu uzależniony od opadu atmosferycznego, a dominującą rolę odgrywają inne czynniki — najprawdopodobniej morskie (wiatr, ciśnienie, seisze bałtyckie).

---

### 2.2 Macierz korelacji

![Macierz korelacji](macierz_korelacji.png)

Kluczowe obserwacje:

**Zmienne opadowe** są wzajemnie silnie skorelowane (`Opad_72h` ↔ `Opad_7d`: r = 0,71; `Opad_suma` ↔ `Opad_72h`: r = 0,62), ponieważ są pochodnymi tych samych pomiarów. Przy modelowaniu należy unikać używania ich jednocześnie ze względu na multikolinearność.

**Korelacja opad–poziom wody** jest wyraźnie zróżnicowana między stacjami: Strzyża i Martwa Wisła reagują na opad podobnie (r ≈ 0,14–0,20), podczas gdy Port Północny praktycznie nie reaguje (r ≈ 0,05–0,08).

**Ciśnienie atmosferyczne** koreluje ujemnie zarówno z opadem (r ≈ –0,27), jak i z poziomem wody na Strzyży (r = –0,27) i Martwej Wiśle (r = –0,25), co jest zgodne z fizyką atmosfery — niskie ciśnienie sprzyja opadom i podwyższonemu stanowi wód. Dla Portu Północnego zależność jest słabsza (r = –0,10), co dodatkowo potwierdza odmienność mechanizmów tam działających.

**Temperatura** wykazuje niemal zerową korelację z poziomem wody na wszystkich stacjach (r ≈ –0,09 do –0,17), co może sugerować brak wyraźnego efektu roztopowego w skali całego okresu obserwacji lub jego kompensację przez inne czynniki.

**Korelacja między stacjami** — najważniejszy nowy wynik: Strzyża i Martwa Wisła są silnie skorelowane (r = 0,90–0,94), natomiast Port Północny koreluje z nimi jedynie umiarkowanie (r ≈ 0,40–0,44). Oznacza to, że Strzyża i Martwa Wisła tworzą jeden spójny system hydrologiczny reagujący na opady, podczas gdy Port Północny funkcjonuje według innych zasad.

---

### 2.3 Zależność między stacjami śródlądowymi a Portem Północnym

![Scatter stacje vs Port Północny](scatter_stacje_port.png)

Wykresy rozrzutu ujawniają strukturę zależności między stacjami śródlądowymi (Strzyża, Martwa Wisła) a Portem Północnym, której samo r = 0,42–0,44 nie oddaje w pełni.

Widoczne są dwa wyraźnie odrębne wzorce zachowania:

**Główna chmura punktów** tworzy wąski, wyraźnie liniowy pas biegnący ukośnie przez cały wykres. W tym zakresie, gdy poziom wody na Strzyży i Martwej Wiśle rośnie, poziom wody w Porcie Północnym również rośnie w sposób przewidywalny. Rzeczywista korelacja w tym reżimie jest znacznie wyższa niż globalne r = 0,44.

**Punkty odstające pionowo w dół** — kilkadziesiąt obserwacji, w których przy niskim poziomie wody na stacjach śródlądowych (okolice 0 m) Port Północny spada drastycznie do poziomu 0–3 m. Są to zdarzenia typu **cofka** — silny wiatr z lądu wypycha wodę z portu niezależnie od tego, co dzieje się na Strzyży czy Martwej Wiśle. Zdarzenia te całkowicie rozrywają korelację i zaniżają globalne r.

Obserwacja ta ma kluczowe znaczenie dla projektowanego algorytmu: **Port Północny funkcjonuje w dwóch różnych reżimach hydrologicznych**, które wymagają osobnego podejścia. Dla reżimu normalnego stacje śródlądowe mogą być użytecznym sygnałem pomocniczym, natomiast dla epizodów cofki konieczne będą dane wiatrowe lub barometryczne.

---

### 2.4 Porównanie korelacji — wszystkie dni vs. dni z opadem

Dane dotyczą stacji Strzyża (najsilniejszy sygnał opadowy):

| Zmienna       | Wszystkie dni (r) | Tylko dni z opadem > 0 (r) |
| ------------- | ----------------- | -------------------------- |
| `Opad_suma`   | 0,196             | 0,120                      |
| `Opad_72h`    | 0,233             | 0,177                      |
| `Opad_7d`     | 0,211             | 0,164                      |
| `Opad_lag_1d` | 0,152             | —                          |
| `Opad_lag_2d` | 0,094             | —                          |
| `Opad_lag_3d` | 0,070             | —                          |

Spadek korelacji po ograniczeniu próby do dni z opadem sugeruje **progowy charakter odpowiedzi zlewni** — znaczna część sygnału pochodzi z kontrastu między dniami suchymi a deszczowymi, nie zaś z wewnętrznego zróżnicowania intensywności opadu. Poniżej pewnego progu nasycenia, opad nie przekłada się istotnie na wzrost poziomu wody.

Najsilniejszym predyktorem liniowym pozostaje `Opad_72h` (r = 0,233), co potwierdza że skumulowany opad z ostatnich 3 dni lepiej opisuje stan wód niż opad dobowy.

---

### 2.5 Korelacja Spearmana

| Stacja        | Spearman ρ | Pearson r | Różnica |
| ------------- | ---------- | --------- | ------- |
| Strzyża       | 0,292      | 0,196     | +0,096  |
| Martwa Wisła  | 0,272      | 0,157     | +0,115  |
| Port Północny | 0,250      | 0,059     | +0,191  |

We wszystkich stacjach korelacja Spearmana jest wyższa od Pearsona. Różnica jest szczególnie wyraźna dla Portu Północnego (+0,191), co wskazuje że zależność tam jest silnie nieliniowa — mimo bardzo niskiej korelacji liniowej, istnieje pewna monotoniczna zależność rangowa między opadem a poziomem wody.

---

### 2.6 Regresja liniowa — Opad 72h vs. poziom wody

![Regplot Martwa Wisła](regplot_opad72h_martwa_wisla.png)
![Regplot Port Północny](regplot_opad72h_port_pólnocny.png)

| Stacja        | β (m/mm) | Interpretacja                  |
| ------------- | -------- | ------------------------------ |
| Strzyża       | 0,00633  | +0,63 cm na każdy mm opadu 72h |
| Martwa Wisła  | 0,00544  | +0,54 cm na każdy mm opadu 72h |
| Port Północny | 0,00573  | +0,57 cm na każdy mm opadu 72h |

Współczynniki kierunkowe są zbliżone dla wszystkich trzech stacji, jednak wykresy rozrzutu ujawniają zasadniczo różny charakter danych:

Dla Strzyży i Martwej Wisły widoczny jest rozproszony, ale kierunkowy trend wzrostowy przy rosnącym opadzie. Dla Portu Północnego widoczny jest charakterystyczny "L-kształt" — ogromna masa punktów skupiona przy poziomie 5,0–5,5 m niezależnie od opadu, oraz kilkanaście skrajnych obserwacji przy niskim opadzie z poziomem wody 0–2 m. Te ekstremalne zdarzenia niskiego poziomu przy niskim opadzie to prawdopodobnie cofki przy silnym wietrze z lądu — zupełnie inny mechanizm niż opadowy.

---

### 2.6 Analiza rozkładów grupowych

#### KDE — porównanie stacji

![KDE porównanie stacji](kde_porownanie_stacje.png)

Strzyża i Martwa Wisła wykazują podobny wzorzec: rozkład dla dużego opadu jest przesunięty w prawo względem małego opadu, z wyraźniejszą asymetrią prawostronną sygnalizującą zdarzenia wezbraniowe. Różnica median wynosi odpowiednio +0,135 m (Strzyża: 0,122 → 0,257 m) i +0,126 m (Martwa Wisła: –0,070 → 0,056 m).

Port Północny prezentuje zupełnie inny obraz — rozkłady dla małego i dużego opadu są niemal identyczne i silnie skupione wokół 5,2–5,3 m. Opad praktycznie nie różnicuje poziomów wody w tej stacji (różnica średnich: zaledwie +0,138 m przy zakresie pomiarowym sięgającym 6+ m).

#### Boxplot

![Boxplot wszystkie stacje](boxplot_opad_woda_wszystkie.png)

Boxplot potwierdza obserwacje z KDE. Dla Strzyży i Martwej Wisły pudełka dla dużego opadu są wyraźnie przesunięte w górę względem małego opadu, a rozstęp IQR jest większy — wyższe opady wiążą się z większą zmiennością poziomów wody. Dla Portu Północnego pudełka obu grup zachodzą na siebie w niemal identyczny sposób, co wizualnie potwierdza brak wpływu opadu na tę stację.

---

### 2.7 Testy statystyczne

#### Test normalności Shapiro-Wilka

Wszystkie rozkłady — dla każdej stacji i każdej grupy opadowej — wykazują p << 0,05, co oznacza odrzucenie hipotezy normalności. Uzasadnia to stosowanie testów nieparametrycznych.

| Stacja        | p (mały opad) | p (duży opad) |
| ------------- | ------------- | ------------- |
| Strzyża       | 9,51 × 10⁻¹³  | 3,95 × 10⁻⁹   |
| Martwa Wisła  | 2,90 × 10⁻¹³  | 2,02 × 10⁻¹⁰  |
| Port Północny | 3,40 × 10⁻⁵¹  | 4,18 × 10⁻³⁴  |

#### Test Manna-Whitneya U

| Stacja        | p-value      | Wniosek                |
| ------------- | ------------ | ---------------------- |
| Strzyża       | 4,64 × 10⁻³¹ | Różnica wysoce istotna |
| Martwa Wisła  | 1,84 × 10⁻²⁷ | Różnica wysoce istotna |
| Port Północny | 5,39 × 10⁻²³ | Różnica wysoce istotna |

Dla wszystkich trzech stacji test wykazuje statystycznie istotną różnicę między poziomem wody przy małym i dużym opadzie. Warto jednak pamiętać, że przy dużej liczebności próby nawet bardzo małe różnice dają niskie p-value. Dla Portu Północnego różnica średnich wynosi zaledwie 0,138 m — jest statystycznie istotna, ale jej praktyczne znaczenie w kontekście ryzyka wezbrania jest ograniczone.

---

### 2.8 Port Północny — analiza ciśnienia i wiatru

Wobec minimalnej korelacji z opadem (r < 0,06), przeprowadzono osobną analizę predyktorów atmosferycznych dla Portu Północnego: ciśnienia w różnych agregacjach oraz siły i kierunku wiatru (proxy).

#### Korelacja predyktorów atmosferycznych z poziomem wody w porcie

| Zmienna              | Pearson r | Spearman ρ |
| -------------------- | --------- | ---------- |
| `Ciśnienie_średnia`  | –0,102    | –0,198     |
| `Ciśnienie_min`      | –0,134    | –0,237     |
| `Ciśnienie_ampl`     | +0,182    | +0,222     |
| `Ciśnienie_delta_1d` | +0,054    | +0,128     |
| `Ciśnienie_trend_3d` | –0,132    | –0,273     |
| `Ciśnienie_trend_7d` | –0,147    | –0,297     |
| `Wiatr_siła_proxy`   | +0,136    | +0,148     |
| `Wiatr_sin_proxy`    | –0,040    | –0,099     |
| `Wiatr_cos_proxy`    | +0,040    | +0,100     |

![Macierz korelacji Port Północny](macierz_port_wiatr_cisnienie.png)

Wszystkie korelacje są słabe (r < 0,20), jednak konsekwentnie wyższe dla Spearmana niż Pearsona, co potwierdza nieliniowy charakter zależności. Najsilniejszym predyktorem jest **trend ciśnienia 7-dniowy** (ρ = –0,297) — długotrwale spadające ciśnienie jest lepszym sygnałem spiętrzenia niż chwilowa wartość absolutna. `Ciśnienie_ampl` koreluje dodatnio (ρ = +0,222), co wskazuje że dni z dużą dobową zmiennością ciśnienia wiążą się z wyższym poziomem wody.

#### Scatter: siła wiatru i delta ciśnienia vs. poziom wody

![Scatter wiatr i ciśnienie](scatter_port_wiatr_cisnienie.png)

Oba scatter ploty pokazują ten sam charakterystyczny wzorzec: gęsta chmura punktów przy normalnym poziomie wody (5,0–5,5 m) oraz pionowo opadające punkty odstające przy niskich wartościach siły wiatru i ujemnej delcie ciśnienia. Cofki pojawiają się przy **słabym wietrze i spadającym ciśnieniu** — co sugeruje specyficzny układ synoptyczny (np. przejście frontu z silnym wiatrem lądowym), a nie po prostu "brak wiatru".

#### Poziom wody według sektora wiatru

![Boxplot sektor wiatru](boxplot_port_sektor_wiatru.png)

`Wiatr_sektor_proxy` w danych zawiera kategorie ciśnieniowe (`spadek_cisnienia`, `stabilnie`, `wzrost_cisnienia`), nie geograficzne kierunki wiatru. Boxplot pokazuje że cofki (wartości odstające w dół) pojawiają się zarówno przy spadku jak i wzroście ciśnienia, choć przy spadku ciśnienia są liczniejsze. Brak geograficznego kierunku wiatru stanowi istotne ograniczenie analizy — rzeczywisty kierunek wiatru (wschodni/lądowy vs. zachodni/morski) jest kluczową zmienną dla mechanizmu cofki.

#### Trzy reżimy Portu Północnego

![Reżimy atmosferyczne](boxplot_port_rezim_atmosfera.png)

Podział na trzy reżimy (cofka P10 / normalny / spiętrzenie P90) ujawnił wyraźne różnice warunków atmosferycznych:

| Reżim               | Liczba dni | Ciśnienie [hPa] | Δ ciśnienia 1d [hPa] | Siła wiatru |
| ------------------- | ---------- | --------------- | -------------------- | ----------- |
| Cofka (≤ P10)       | 190        | 1014,75         | –1,49                | 3,69        |
| Normalny            | 1452       | 1011,14         | –0,03                | 4,20        |
| Spiętrzenie (≥ P90) | 184        | 1006,16         | +1,78                | 6,83        |

Wzorzec jest wyraźny i spójny fizycznie: **cofka** wiąże się z wysokim ciśnieniem i lekko spadającą tendencją — klasyczny wyż z wiatrem lądowym wypychającym wodę z portu. **Spiętrzenie** wiąże się z niskim ciśnieniem, rosnącą tendencją (powrót po przejściu niżu) i silnym wiatrem — klasyczny niż bałtycki ze spiętrzeniem sztormowym. Różnica ciśnień między reżimem cofki a spiętrzenia wynosi ~8,6 hPa, a różnica siły wiatru jest niemal dwukrotna (3,69 vs. 6,83).

---

Przeprowadzona analiza ujawnia **wyraźne zróżnicowanie odpowiedzi hydrologicznej** między badanymi stacjami, co ma bezpośrednie implikacje dla celu projektowego — wykrywania ryzyka wezbrania w portach.

**1. Port Północny funkcjonuje w dwóch odrębnych reżimach hydrologicznych**

Analiza scatter plotów (sekcja 2.3) ujawnia, że za pozornie umiarkowaną korelacją stacji śródlądowych z Portem Północnym (r ≈ 0,42–0,44) kryją się dwa jakościowo różne wzorce. W reżimie normalnym poziom wody w porcie podąża za poziomem na Strzyży i Martwej Wiśle w sposób niemal liniowy — rzeczywista korelacja w tym reżimie jest znacznie wyższa niż globalne r. Drugi reżim to epizody cofki, w których silny wiatr z lądu wypycha wodę z portu niezależnie od stanu stacji śródlądowych — te zdarzenia całkowicie rozrywają korelację i dominują obraz statystyczny.

Strzyża i Martwa Wisła tworzą spójny system reagujący na opady (r = 0,90–0,94 między stacjami), natomiast Port Północny wymaga osobnego modelu uwzględniającego czynniki morskie — wiatr, ciśnienie atmosferyczne i seisze bałtyckie.

**2. Opad skumulowany 72h jako najlepszy predyktor opadowy**

`Opad_72h` konsekwentnie wykazuje najwyższą korelację z poziomem wody na Strzyży i Martwej Wiśle (r = 0,233 i r = 0,200), co jest zgodne z hydrologiczną teorią odpowiedzi zlewni. Opad dobowy jest predyktorem słabszym.

**3. Progowy charakter odpowiedzi zlewni**

Spadek korelacji po ograniczeniu analizy do dni z opadem > 0 wskazuje, że dopiero po przekroczeniu progu nasycenia zlewni opad efektywnie przekłada się na wzrost poziomu wody. Potwierdza to sens stosowania metod nieliniowych (np. Random Forest) w kolejnym etapie projektu.

**4. Ciśnienie i wiatr jako predyktory Portu Północnego**

Analiza atmosferyczna (sekcja 2.8) potwierdza że dla Portu Północnego kluczowymi predyktorami są ciśnienie i wiatr, nie opad. Najsilniejszym sygnałem jest **trend ciśnienia 7-dniowy** (ρ = –0,297) — długotrwały spadek ciśnienia poprzedza spiętrzenie skuteczniej niż chwilowa wartość absolutna. Reżim cofki charakteryzuje się wysokim ciśnieniem (~1015 hPa) i słabym wiatrem, reżim spiętrzenia — niskim ciśnieniem (~1006 hPa) i silnym wiatrem. Różnica między reżimami jest wyraźna i fizycznie spójna, co uzasadnia użycie tych zmiennych w algorytmie ostrzegawczym.

**5. Ograniczenia analizy**

Analiza opiera się na zależnościach dwuzmiennych i nie uwzględnia interakcji między predyktorami ani sezonowości. Istotnym ograniczeniem dla Portu Północnego jest brak geograficznego kierunku wiatru — `Wiatr_sektor_proxy` zawiera kategorię ciśnieniową, nie kierunkową, co uniemożliwia bezpośrednie potwierdzenie mechanizmu cofki (wiatr wschodni/lądowy). Uwzględnienie sezonowości oraz rzeczywistego kierunku wiatru jest rekomendowane w kolejnym etapie projektu.

---

## Załącznik — zestawienie wyników

### Korelacja Pearson (lag=0) i Spearman — opad vs. poziom wody

| Miara                 | Strzyża      | Martwa Wisła | Port Północny |
| --------------------- | ------------ | ------------ | ------------- |
| Pearson r (Opad_suma) | 0,196        | 0,157        | 0,059         |
| Pearson r (Opad_72h)  | 0,233        | 0,200        | 0,078         |
| Pearson r (Opad_7d)   | 0,211        | 0,180        | 0,081         |
| Spearman ρ            | 0,292        | 0,272        | 0,250         |
| Pearson r (mokre dni) | 0,120        | 0,071        | 0,017         |
| Regresja β (m/mm)     | 0,00633      | 0,00544      | 0,00573       |
| Mann-Whitney p        | 4,64 × 10⁻³¹ | 1,84 × 10⁻²⁷ | 5,39 × 10⁻²³  |

### Średni poziom wody — mały vs. duży opad

| Stacja        | Mały opad (≤ Q25) | Duży opad (≥ Q75) | Różnica  |
| ------------- | ----------------- | ----------------- | -------- |
| Strzyża       | 0,122 m           | 0,257 m           | +0,135 m |
| Martwa Wisła  | –0,070 m          | 0,056 m           | +0,126 m |
| Port Północny | 5,171 m           | 5,309 m           | +0,138 m |

### Korelacja między stacjami

| Para                               | Pearson r |
| ---------------------------------- | --------- |
| Strzyża ↔ Martwa Wisła (średnia)   | 0,90      |
| Strzyża ↔ Martwa Wisła (max)       | 0,94      |
| Strzyża ↔ Port Północny (max)      | 0,44      |
| Martwa Wisła ↔ Port Północny (max) | 0,42      |
