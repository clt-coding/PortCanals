# Uruchamianie w folderze głównym projektu: python -W ignore -m src.models.run_all
import pandas as pd
from src.models.random_forest.random_forest_system import uruchom_system as uruchom_rf
from src.models.lstm.lstm_system import uruchom_system_lstm as uruchom_lstm
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "final.csv")

def main():
    print("Wczytywanie danych...")
    final = pd.read_csv(DATA_PATH, parse_dates=["Data"], index_col="Data")

    print("Uruchamianie modelu Random Forest")
    diagnozy_rf = uruchom_rf(final)
    
    print("Uruchamianie modelu LSTM")
    diagnozy_lstm = uruchom_lstm(final)

    print("Tworzenie zbiorczego raportu...")
    
    raport = pd.DataFrame({
        'Ryzyko_RF': diagnozy_rf['ryzyko'],
        'Prawd_RF': diagnozy_rf['prawdopodobienstwo'],
        'Ryzyko_LSTM': diagnozy_lstm['ryzyko'],
        'Prawd_LSTM': diagnozy_lstm['prawdopodobienstwo']
    })

    raport['Alert_Systemowy'] = raport.apply(lambda row: 'TAK' if 'wysokie' in [row['Ryzyko_RF'], row['Ryzyko_LSTM']] else 'NIE', axis=1)

    raport.to_csv('reports/ml/raport_agregat.csv')
    
    print("Raport zbiorczy zapisano do: reports/ml/raport_agregat.csv")
    print("Ostatnie 5 dni:")
    print(raport.tail(5))

if __name__ == "__main__":
    main()