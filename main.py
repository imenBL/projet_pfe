import logging
import pandas as pd



from Collector.Gold_scraper import scrape_gold
from Collector.Silver_scraper import scrape_silver
from Collector.World_Bank_API import build_multi_country_dataset
from database import init_database, insert_raw_data , insert_cleaned_data, insert_gdelt_data, insert_yfinance_data, insert_date , insert_excel, insert_Fred_Api_data
from cleaner_prices import clean_data
from Collector.Gdelt_Project import fetch_geopolitical_indices
from Collector.yahoo_finance import fetch_vix_oil
from Collector.fredAPI import import_Fred


def setup_logger():
    logger = logging.getLogger("Metals_pipeline")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    file = logging.FileHandler("pipeline.log")
    file.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(console)
        logger.addHandler(file)

    return logger




def main():
    logger = setup_logger()

    logger.info("Lancement de Pipeline")

    # DB
    # init_database()

    insert_date(start="2016-01-01")
    logger.info("Table Dim_Date inserted")


    # # Scraping
    # logger.info("Lancement Scraping Gold")
    # gold_df = scrape_gold()
    # logger.info("Scraping gold done")

    # logger.info("Lancement Scraping Silver")
    # silver_df = scrape_silver()
    # logger.info("Scraping silver done")

    # raw_df = pd.concat([gold_df, silver_df], ignore_index=True)

    # insert_raw_data(raw_df)
    # logger.info("raw_data inserted")

    # # Merge 

    # cleaned_df = clean_data(raw_df)
    # logger.info("Data clean  !")

    # # Insert DB

    
    # insert_cleaned_data(cleaned_df)
    # logger.info("cleaned_data inserted")

    # gdelt_df = fetch_geopolitical_indices()
    # logger.info("Gdelt Data collected" , len(gdelt_df))

    # insert_gdelt_data(gdelt_df)
    # logger.info("Gdelt_data inserted")

    # yfinance_df = fetch_vix_oil()

    # insert_yfinance_data(yfinance_df)
    # logger.info("Yahoo Finance data inserted" , len(yfinance_df))

    # insert_excel(file_path= r"C:\Users\ibenl\OneDrive\Bureau\Projet PFE\Reserves_Gold.xlsx")
    # logger.info("Excel data inserted")

    # Fred_df = import_Fred()
    # insert_Fred_Api_data(Fred_df)
    # logger.info("Fred_API data inserted")



if __name__ == "__main__":
    main()
