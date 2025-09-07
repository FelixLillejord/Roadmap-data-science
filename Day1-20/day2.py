import pandas as pd

# Opprette DataFrame
df = pd.DataFrame(
    [
        ["Lise Hansen", 28, "HR", 550000], 
        ["Knut Knutsen", 36, "IT", 780000], 
        ["Arild Arildsen", 52, "Ledelse", 1020000], 
        ["Helen Hansen", 43, "Finans", 980000], 
        ["Stian Stiansen", 39, "Renholder", 510000]
    ], 
    columns=["Navn", "Alder", "Avdeling", "Lønn"]
)

# Funksjoner
def filter_hr(df):
    return df.loc[df["Avdeling"] == "HR"]

def filter_finans(df):
    return df.loc[df["Avdeling"] == "Finans"]

def filter_loenn_og_alder(df):
    return df.loc[(df["Lønn"] > 550000) & (df["Alder"] > 37)]

# Main-blokken
if __name__ == "__main__":
    print("HR-ansatte:")
    print(filter_hr(df), "\n")

    print("Finans-ansatte:")
    print(filter_finans(df), "\n")

    print("Ansatte med lønn > 550000 og alder > 37:")
    print(filter_loenn_og_alder(df))