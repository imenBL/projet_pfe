import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

base_url = "https://www.exchange-rates.org/fr/metaux-precieux/or/algerie/{}"

start_year = 2017
end_year = 2026
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


for year in range(start_year, end_year + 1):
    print(f"Scraping {year}...")

    url = base_url.format(year)
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Erreur pour {year}")
        continue

    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table", class_="metal-history-table wide-table")

    rows = table.find_all("tr")
    data = []

    
    for row in rows[1:]:  # skip header
        cols = row.find_all("td")

        if len(cols) >= 6:
            date = cols[0].text.strip()

            # récupérer les prix
            prices = [col.text.strip() for col in cols[1:6]]

            data.append({
                "date": date,
                "gold_24k": prices[0],
                "gold_22k": prices[1],
                "gold_18k": prices[2],
                "gold_14k": prices[3],
                "gold_10k": prices[4],
            })

    # convertir en DataFrame
    df = pd.DataFrame(data)

    # sauvegarde CSV
    filename = f"Data collected/gold_{year}_DA.csv"
    df.to_csv(filename, index=False, encoding="utf-8-sig")

    print(f"{filename} enregistré ✅")

    time.sleep(1)