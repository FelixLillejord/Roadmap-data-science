import pandas as pd
import numpy as np


# -------------------------------------------
# 1. Oppretting av DataFrame med ansatte
# -------------------------------------------

df = pd.DataFrame([["Lise Hansen", 28, "HR", 550000], 
                    ["Knut Knutsen", 36, "IT", 780000], 
                    ["Arild Arildsen", 52, "Ledelse", 1020000], 
                    ["Helen Hansen", 43, "Finans", 980000], 
                    ["Stian Stiansen", 39, "Renholder", 510000]], 
                    columns=["Navn", "Alder", "Avdeling", "Lønn"])

# -------------------------------------------
# 2. Liste med nye ansatte i en ny dataframe
# -------------------------------------------
nye_rader = pd.DataFrame([["Kristoffer Kristoffersen", 47, "HR", 780000], 
                    ["William Williamsen", 23, "IT", 430000], 
                    ["Helen Helensen", 38, "Ledelse", 1090000],
                    ["Boye Bojessen", 33, "IT", 1250000],
                    ["Kaja Kajessen", 29, "Finans", 750000]],
                    columns=["Navn", "Alder", "Avdeling", "Lønn"])

# -------------------------------------------
# 3. Legg til nye ansatte i eksisterende DataFrame
# -------------------------------------------
df = pd.concat([df, nye_rader], ignore_index = True)


# -------------------------------------------
# 4. Legg til syntetiske sykefraværsdager
# -------------------------------------------
# Tilfeldigve tall mellom 0-10 for hver ansatt
df["Sykefraværs_dager"] = np.random.randint(0,11, size=len(df))

# -------------------------------------------
# 5. Funksjoner for analyser
# -------------------------------------------
def gjennomsnitt_lonn(df):
    return df.groupby("Avdeling")["Lønn"].mean()

def sykefravaer_rapport(df):
    return df.groupby("Avdeling").agg({
        "Sykefraværs_dager": ["mean", "sum"]})

def full_rapport(df): 
    return df.groupby("Avdeling").agg({
        "Lønn": ["mean", "max", "min"],
        "Sykefraværs_dager": ["mean", "sum"]
    })

# -------------------------------------------
# 6. Main-blokk: kjøres kun hvis scriptet startes direkte
# -------------------------------------------

# Main-blokken
if __name__ == "__main__":
    print("Gjennomsnittslønn per avdeling: \n", gjennomsnitt_lonn(df), "\n")
    print("Sykefraværsrapport: \n", sykefravaer_rapport(df), "\n")
    print("Full HR-Rapport:\n", full_rapport(df))
