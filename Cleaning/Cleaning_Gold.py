import pandas as pd
import glob

df = pd.read_csv("gold_2026_TND.csv")

mois = {
    "janv.": "01", "févr.": "02", "mars": "03", "avr.": "04",
    "mai": "05", "juin": "06", "juil.": "07", "août": "08",
    "sept.": "09", "oct.": "10", "nov.": "11", "déc.": "12"
}

def convertir_date(date_str):
    parts = date_str.split()
    jour = parts[0].zfill(2)  # ajoute 0 si nécessaire
    mois_str = parts[1]
    mois_num = mois.get(mois_str, "01")  # fallback sécurité
    annee = "2026"
    return f"{jour}/{mois_num}/{annee}"

df["date"] = df["date"].apply(convertir_date)

colonnes_prix = ["gold_24k", "gold_22k", "gold_18k", "gold_14k", "gold_10k"]


for col in colonnes_prix:
    df[col] = (
        df[col]
        .str.replace(" TND", "", regex=False)  # enlever TND
        .str.replace(",", ".", regex=False)    # virgule → point
        .astype(float)                         # convertir en float
    )


df.to_csv("gold_2026_TND_cleaned.csv", index=False)


fichiers = glob.glob("C:/Users/ibenl/OneDrive/Bureau/Projet PFE/Data cleaned/*.csv")
dfs = []
for fichier in fichiers:
    df=pd.read_csv(fichier)
    dfs.append(df)

df_final = pd.concat(dfs, ignore_index=False)
print("fichiers concatenés")
df_final.to_csv("ALL_Gold_TND.csv")

print("Nombre de lignes :", len(df_final))