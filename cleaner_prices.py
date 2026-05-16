import pandas as pd
import re
from database import get_engine



# -----------------------------
# Mapping mois
# -----------------------------
mois_map = {
    "janv.": "01", "févr.": "02", "mars": "03", "avr.": "04",
    "mai": "05", "juin": "06", "juil.": "07", "août": "08",
    "sept.": "09", "oct.": "10", "nov.": "11", "déc.": "12"
}


# -----------------------------
# LOAD RAW DATA
# -----------------------------
def load_raw_data():
    engine = get_engine()
    return pd.read_sql("SELECT * FROM raw_data", engine)
    return df


# -----------------------------
# DATE
# -----------------------------
def convert_date(row):
    parts = row["date"].split()
    jour = parts[0].zfill(2)
    mois = mois_map.get(parts[1], "01")
    year = str(row["Année"])

    return f"{year}-{mois}-{jour}"
    

# -----------------------------
# EXTRACTION DEVISE
# -----------------------------
def extract_devise(value):
    if pd.isna(value):
        return None

    match = re.search(r"[A-Z]{2,3}", value)
    return match.group(0) if match else None


# -----------------------------
# CLEAN PRIX
# -----------------------------
def clean_price(value):
    if pd.isna(value):
        return None

    # garder uniquement chiffres + . ,
    value = re.sub(r"[^\d,.-]", "", value)

    # virgule → point
    value = value.replace(",", ".")

    try:
        return float(value)
    except:
        return None


# -----------------------------
# CLEAN GLOBAL
# -----------------------------
def clean_data(df: pd.DataFrame):
    # -------- DATE --------
    df["date"] = df.apply(convert_date, axis=1)

    # -------- DEVISE --------
    # gold → gold_24k
    mask_gold = df["metals"] == "gold"
    df.loc[mask_gold, "devise"] = df.loc[mask_gold, "gold_24k"].apply(extract_devise)

    # silver → silver_price
    mask_silver = df["metals"] == "silver"
    df.loc[mask_silver, "devise"] = df.loc[mask_silver, "silver_price"].apply(extract_devise)

    # -------- PRIX --------
    price_cols = ["gold_24k", "gold_22k", "gold_18k", "gold_14k", "gold_10k" , "silver_price"]

    for col in price_cols:
        df[col] = df[col].apply(clean_price)

    df[price_cols] = df[price_cols].fillna(0)

    clean_df = df

    return clean_df 


