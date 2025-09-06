import pandas as pd
import numpy as np

df = pd.DataFrame([["Lise Hansen", 28, "HR", 550000], 
                   ["Knut Knutsen", 36, "IT", 780000], 
                   ["Arild Arildsen", 52, "Ledelse", 1020000], 
                   ["Helen Hansen", 43, "Finans", 980000], 
                   ["Stian Stiansen", 39, "Renholder", 510000]], 
                   columns=["Navn", "Alder", "Avdeling", "Lønn"])

df["Sykefraværs_dager"] = np.random.randint(0,11, size=len(df))

if __name__ == "__main__":
    print(df)