import requests
from bs4 import BeautifulSoup
import pandas as pd

url = "https://www.exchange-rates.org/fr/metaux-precieux/or/tunisie/2026"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()  # vérifie erreur HTTP
    print("✅ Connexion réussie")
except requests.exceptions.Timeout:
    print("⏱️ Timeout - le site ne répond pas")
except requests.exceptions.RequestException as e:
    print("❌ Erreur :", e)


response = requests.get(url, headers=headers, timeout=10)
soup = BeautifulSoup(response.content, "html.parser")

table = soup.find("table", class_="metal-history-table wide-table")

rows = table.find_all("tr")

data = []

for row in rows:
    # ignorer les lignes inutiles
    if "header-row" in row.get("class", []) or "month-row" in row.get("class", []):
        continue

    date_cell = row.find("td", class_="date")
    rate_cells = row.find_all("td", class_="rate")

    if date_cell and rate_cells:
        date = date_cell.text.strip()

        prices = [cell.text.strip() for cell in rate_cells]

        data.append({
            "date": date,
            "gold_24k": prices[0],
            "gold_22k": prices[1],
            "gold_18k": prices[2],
            "gold_14k": prices[3],
            "gold_10k": prices[4],
        })


df = pd.DataFrame(data)


df.to_csv('gold_2026_TND.csv', index=False, encoding='utf-8-sig')

print("Fichier crée")