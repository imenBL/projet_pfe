import logging
import requests
from bs4 import BeautifulSoup
import pandas as pd
from Common.config import PAYS, YEARS, CURRENCY
from Common.db import get_db_connection
import time

# LOGGING
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# CONFIG
BASE_URL = "https://www.exchange-rates.org/fr/metaux-precieux/or/{}/{}"
url = BASE_URL.format(PAYS, YEARS)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

#Create table
def create_table(conn, table_name):
    cursor = conn.cursor()

    query = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,
        date TEXT,
        gold_24k TEXT,
        gold_22k TEXT,
        gold_18k TEXT,
        gold_14k TEXT,
        gold_10k TEXT
    );
    """

    cursor.execute(query)
    conn.commit()
    cursor.close()


#insert data
def insert_data(conn, table_name, df):
    cursor = conn.cursor()

    for _, row in df.iterrows():
        cursor.execute(f"""
            INSERT INTO {table_name} (
                date, gold_24k, gold_22k, gold_18k, gold_14k, gold_10k
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, tuple(row))

    conn.commit()
    cursor.close()



#Scraper
def scrape_gold_country_year(country, year):
    url = BASE_URL.format(country, year)
    logging.info(f"Scraping {country} - {year}")

    try:
        response = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(response.text, "html.parser")

        table = soup.find("table")

        data = []

        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")

            if len(cols) >= 2:
                date = cols[0].text.strip()
                prices = [c.text.strip() for c in cols[1:]]

                data.append({
                    "date": date,
                    "gold_24k": prices[0],
                    "gold_22k": prices[1],
                    "gold_18k": prices[2],
                    "gold_14k": prices[3],
                    "gold_10k": prices[4],
                })

        df = pd.DataFrame(data)
        return df

    except Exception as e:
        logging.error(f"Error scraping {country}-{year}: {e}")
        return pd.DataFrame()
    

#Main logic
def run_scraping():
    conn = get_db_connection("raw")

    for country in PAYS:
        for year in YEARS:

            currency = CURRENCY[country]
            table_name = f"gold_{currency}_{year}"

            print(f"Scraping {table_name} ...")

            try:
                create_table(conn, table_name)

                df = scrape_gold(country, year)

                if not df.empty:
                    insert_data(conn, table_name, df)
                    print(f"Inserted {len(df)} rows into {table_name} ✅")

                time.sleep(1)

            except Exception as e:
                print(f"Error {table_name}: {e}")

    conn.close()


if __name__ == "__main__":
    run_scraping()