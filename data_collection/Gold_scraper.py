import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# Configuration
Pays = [
    "algerie", "belgique", "tunisie", "canada", "france",
    "Pays-bas", "royaume-uni", "cameroun", "cote-d’ivoire",
    "etats-unis", "maroc", "suisse"
]

Years = range(2017, 2027)

Site = "https://www.exchange-rates.org/fr/metaux-precieux/or/{}/{}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def scrape_gold():
    all_data = []

    for c in Pays:
        for y in Years:
            url = Site.format(c, y)
            try:
                response = requests.get(url, headers=HEADERS, timeout=10)
                response.raise_for_status()
            except:
                continue

            soup = BeautifulSoup(response.content, "html.parser")
            table = soup.find("table", class_="metal-history-table wide-table")

            if not table:
                print(f"Table non trouvée ({c}-{y})")
                continue

            rows = table.find_all("tr")

            for row in rows:
                # ignorer les lignes inutiles
                if "header-row" in row.get("class", []) or "month-row" in row.get("class", []):
                    continue

                date_cell = row.find("td", class_="date")
                rate_cells = row.find_all("td", class_="rate")

                if date_cell and rate_cells:
                    date = date_cell.text.strip()
                    prices = [cell.text.strip() for cell in rate_cells]

                    all_data.append({
                        "metals": "gold",
                        "country": c,
                        "year": y,
                        "date": date,
                        "gold_24k": prices[0],
                        "gold_22k": prices[1],
                        "gold_18k": prices[2],
                        "gold_14k": prices[3],
                        "gold_10k": prices[4],
                    })

            # éviter de surcharger le site
            time.sleep(1)

    gold_df = pd.DataFrame(all_data)
    return gold_df
