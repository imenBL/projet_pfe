import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

PAYS = [
    "algerie", "belgique", "tunisie", "canada", "france",
    "Pays-bas", "royaume-uni", "cameroun", "cote-d’ivoire",
    "etats-unis", "maroc", "suisse"
]

YEARS = range(2017, 2027)

BASE_URL = "https://www.exchange-rates.org/fr/metaux-precieux/argent/{}/{}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def scrape_silver():
    all_data = []

    for p in PAYS:

        for y in YEARS:
            url = BASE_URL.format(p, y)

            try:
                response = requests.get(url, headers=HEADERS, timeout=10)
                response.raise_for_status()
            except:
                continue

            soup = BeautifulSoup(response.content, "html.parser")
            table = soup.find("table", class_="metal-history-table")

            if not table:
                continue

            rows = table.find_all("tr")

            for row in rows:
                if "header-row" in row.get("class", []) or "month-row" in row.get("class", []):
                    continue

                date_cell = row.find("td", class_="date")
                rate_cell = row.find("td", class_="rate")

                if date_cell and rate_cell:
                    date = date_cell.text.strip()
                    price = rate_cell.text.strip()

                    all_data.append({
                        "metals" : "silver",
                        "Pays": p,
                        "Année": y,
                        "date": date,
                        "gold_24k": None,
                        "gold_22k": None,
                        "gold_18k": None,
                        "gold_14k": None,
                        "gold_10k": None,
                        "silver_price": price
                    })

    


        time.sleep(1)

    silver_df = pd.DataFrame(all_data)
    return silver_df 
