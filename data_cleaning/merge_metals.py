import pandas as pd
import re


# =========================================================
# Mapping pays -> devise
# =========================================================

currency_mapping = {
    "algerie": "DZD",
    "belgique": "EUR",
    "tunisie": "TND",
    "canada": "CAD",
    "france": "EUR",
    "pays-bas": "EUR",
    "royaume-uni": "GBP",
    "cameroun": "XAF",
    "cote-d’ivoire": "XOF",
    "etats-unis": "USD",
    "maroc": "MAD",
    "suisse": "CHF"
}


# =========================================================
# Colonnes de prix
# =========================================================

price_columns = [
    "gold_24k",
    "gold_22k",
    "gold_18k",
    "gold_14k",
    "gold_10k",
    "silver_price"
]


# =========================================================
# Mapping mois FR -> numéro
# =========================================================

month_mapping = {
    "janv.": "01",
    "févr.": "02",
    "mars": "03",
    "avr.": "04",
    "mai": "05",
    "juin": "06",
    "juil.": "07",
    "août": "08",
    "sept.": "09",
    "oct.": "10",
    "nov.": "11",
    "déc.": "12"
}


# =========================================================
# Nettoyage des prix
# Exemple :
# "85,521 TND" -> 85.521
# =========================================================

def clean_price(value):

    if pd.isna(value):
        return None

    value = str(value)

    # supprimer tous les espaces
    value = re.sub(r"\s+", "", value)

    # remplacer virgule par point
    value = value.replace(",", ".")

    # garder uniquement chiffres + point
    value = re.sub(r"[^0-9.]", "", value)

    try:
        return float(value)
    except:
        return None


# =========================================================
# Construction vraie date
# Exemple :
# "2 janv." + 2017 -> 2017-01-02
# =========================================================

def column_date(df):

    # normalisation texte
    df["date"] = (
        df["date"]
        .astype(str)
        .str.lower()
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )

    # extraction jour + mois
    split_cols = df["date"].str.extract(r"(\d+)\s+([^\s]+)")

    day = split_cols[0].str.zfill(2)
    month_text = split_cols[1]

    # conversion mois texte -> numéro
    month = month_text.map(month_mapping)

    # création date finale
    df["date"] = pd.to_datetime(
        day + "-" + month + "-" + df["year"].astype(str),
        format="%d-%m-%Y",
        errors="coerce"
    )

    return df


# =========================================================
# Nettoyage général dataframe
# =========================================================

def preprocess_dataframe(df):

    df = df.copy()

    # uniformiser noms pays
    df["country"] = (
        df["country"]
        .astype(str)
        .str.lower()
        .str.strip()
    )

    # convertir dates
    df = column_date(df)

    # nettoyer prix
    for col in price_columns:

        if col in df.columns:
            df[col] = df[col].apply(clean_price)

    return df


# =========================================================
# Merge GOLD + SILVER
# =========================================================

def merge_gold_silver(gold_df, silver_df):

    # supprimer colonne metals
    gold_df = gold_df.drop(columns=["metals"], errors="ignore")
    silver_df = silver_df.drop(columns=["metals"], errors="ignore")

    # preprocessing
    gold_df = preprocess_dataframe(gold_df)
    silver_df = preprocess_dataframe(silver_df)

    # merge principal
    merged_df = pd.merge(
        gold_df,
        silver_df,
        on=["date", "country", "year"],
        how="outer",
        suffixes=("_gold", "_silver")
    )

    # renommage colonnes
    rename_map = {
        "gold_24k_gold": "gold_24k",
        "gold_22k_gold": "gold_22k",
        "gold_18k_gold": "gold_18k",
        "gold_14k_gold": "gold_14k",
        "gold_10k_gold": "gold_10k",
        "silver_price_silver": "silver_price"
    }

    merged_df = merged_df.rename(columns=rename_map)

    # ajout devise
    merged_df["devise"] = merged_df["country"].map(currency_mapping)

    # sélection colonnes finales
    columns_order = [
        "date",
        "country",
        "devise",
        "gold_24k",
        "gold_22k",
        "gold_18k",
        "gold_14k",
        "gold_10k",
        "silver_price"
    ]

    merged_df = merged_df[columns_order]

    # tri final
    merged_df = merged_df.sort_values(
        by=["country", "date"]
    ).reset_index(drop=True)

    return merged_df