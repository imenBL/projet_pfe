import requests
import time
import pandas as pd

Wold_bank_URL = "https://api.worldbank.org/v2/country"

INDICATORS = {
    "inflation": "FP.CPI.TOTL.ZG",
    "interest_rate": "FR.INR.RINR",
    "exchange_rate": "PA.NUS.FCRF"
}

def fetch_indicator(country, indicator):
    url = f"{Wold_bank_URL}/{country}/indicator/{indicator}?format=json&per_page=1000"

    try:
        response = requests.get(url, timeout=10)

        # 🔴 Vérifier status HTTP
        if response.status_code != 200:
            print(f"Erreur HTTP {response.status_code} pour {country}")
            return pd.DataFrame()

        # 🔴 Vérifier contenu vide
        if not response.text.strip():
            print(f"Réponse vide pour {country}")
            return pd.DataFrame()

        # 🔴 Parser JSON
        data = response.json()

    except Exception as e:
        print(f"Erreur API pour {country}: {e}")
        return pd.DataFrame()

    # 🔴 Vérifier structure
    if not isinstance(data, list) or len(data) < 2:
        return pd.DataFrame()

    records = []
    for item in data[1]:
        year = item.get("date")
        value = item.get("value")

        if year is not None:
            records.append({
                "date": int(year),
                "value": value
            })

    df = pd.DataFrame(records)

    # Filtrer à partir de 2000
    df = df[df["date"] >= 2010]

    return df




def build_country_dataset(country):
    dfs = []

    for name, code in INDICATORS.items():
        df = fetch_indicator(country, code)

        if df.empty:
            continue

        df = df.rename(columns={"value": name})
        dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    final_df = dfs[0]

    for df in dfs[1:]:
        final_df = final_df.merge(df, on="date", how="outer")

    final_df["country"] = country

    return final_df


def build_multi_country_dataset(countries):
    all_data = []

    for country in countries:
        print(f"Processing {country}")
        
        df = build_country_dataset(country)

        if not df.empty:
            all_data.append(df)

        time.sleep(0.1)  # 🔥 évite blocage API

    final_dataset = pd.concat(all_data, ignore_index=True)

    return final_dataset


    


