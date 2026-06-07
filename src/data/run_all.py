import pandas as pd
from ml_factor_system import uruchom_system as uruchom_rf
from lstm_system import uruchom_system_lstm as uruchom_lstm

def main():
    # 1. Wczytanie danych
    print("Wczytywanie danych...")
    path = "../../data/processed/final.csv"
    final = pd.read_csv(path, parse_dates=["Data"], index_col="Data")

    # 2. Uruchomienie obu modeli
    print("\n--- Uruchamianie modelu Random Forest ---")
    diagnozy_rf = uruchom_rf(final)
    
    print("\n--- Uruchamianie modelu LSTM ---")
    diagnozy_lstm = uruchom_lstm(final)

    # 3. Agregacja wyników (porównanie)
    print("\nTworzenie zbiorczego raportu...")
    
    # Łączymy diagnozy po dacie
    raport = pd.DataFrame({
        'Ryzyko_RF': diagnozy_rf['ryzyko'],
        'Prawd_RF': diagnozy_rf['prawdopodobienstwo'],
        'Ryzyko_LSTM': diagnozy_lstm['ryzyko'],
        'Prawd_LSTM': diagnozy_lstm['prawdopodobienstwo']
    })

    # Dodajemy kolumnę 'Decyzja_Ekspercka'
    # Prosta logika: jeśli chociaż jeden model widzi wysokie ryzyko, dajemy ostrzeżenie
    raport['Alert_Systemowy'] = raport.apply(lambda row: 'TAK' if 'wysokie' in [row['Ryzyko_RF'], row['Ryzyko_LSTM']] else 'NIE', axis=1)

    # Zapis
    raport.to_csv('reports/ml/raport_agregat.csv')
    
    print("\nGotowe! Raport zbiorczy zapisano do: reports/ml/raport_agregat.csv")
    print("\nOstatnie 5 dni:")
    print(raport.tail(5))

if __name__ == "__main__":
    main()