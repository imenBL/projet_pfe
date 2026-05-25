import logging
import pandas as pd
from data_collection.Gold_scraper import scrape_gold
from data_collection.Silver_scraper import scrape_silver
from data_cleaning.merge_metals import merge_gold_silver
from db_settings import init_database, insert_raw_data , insert_gdelt_data, insert_yfinance_data , insert_excel, insert_Fred_Api_data
from data_collection.Gdelt_Project import fetch_geopolitical_indices
from data_collection.yahoo_finance import fetch_vix_oil
from data_collection.fredAPI import import_Fred



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

    #DB
    init_database()


    # Scraping
    logger.info("Lancement Scraping Gold")
    gold_df = scrape_gold()
    logger.info("Scraping gold done")

    logger.info("Lancement Scraping Silver")
    silver_df = scrape_silver()
    logger.info("Scraping silver done")

    prices_df = merge_gold_silver(gold_df, silver_df)

    insert_raw_data(prices_df)
    logger.info("gold and silver raw data inserted")

   
    # Insert DB

    gdelt_df = fetch_geopolitical_indices()
    logger.info("Gdelt Data collected" , len(gdelt_df))

    insert_gdelt_data(gdelt_df)
    logger.info("Gdelt_data inserted")

    yfinance_df = fetch_vix_oil()

    insert_yfinance_data(yfinance_df)
    logger.info("Yahoo Finance data inserted" , len(yfinance_df))

    insert_excel(file_path= r"C:\Users\ibenl\OneDrive\Bureau\Projet PFE\Reserves_Gold.xlsx")
    logger.info("Excel data inserted")

    Fred_df = import_Fred()
    insert_Fred_Api_data(Fred_df)
    logger.info("Fred_API data inserted")



if __name__ == "__main__":
    main()
