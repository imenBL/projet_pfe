import psycopg2
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import pandas as pd

# Configuration PostgreSQL
DB_CONFIG = {
    "user": "postgres",
    "password": "admin",
    "host": "localhost",
    "port": "5432"
}

DB_name = "metals_db"


# 🔹 Création de la base
def create_database():
    
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"]
        )
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_name}'")
        exists = cursor.fetchone()

        if not exists:
            cursor.execute(f"CREATE DATABASE {DB_name}")
        cursor.close()
        conn.close()


# 🔹 Connexion SQLAlchemy

def get_engine():
    password = quote_plus(DB_CONFIG["password"])

    return create_engine(
        f"postgresql+psycopg2://{DB_CONFIG['user']}:{password}@"
        f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_name}"
    )


# 🔹 Création des tables
def create_tables():
        engine = get_engine()

        create_raw_table_query = """
            CREATE TABLE raw_prices (
                id SERIAL PRIMARY KEY,
                metals TEXT,
                country TEXT,
                year INT,
                date TEXT,
                gold_24k TEXT,
                gold_22k TEXT,
                gold_18k TEXT,
                gold_14k TEXT,
                gold_10k TEXT,
                silver_price TEXT
            );
            """

        create_clean_table_query = """
            CREATE TABLE cleaned_prices (
                    id SERIAL PRIMARY KEY,
                    metals TEXT,
                    country TEXT,
                    date TEXT,
                    devise TEXT,
                    gold_24k FLOAT,
                    gold_22k FLOAT,
                    gold_18k FLOAT,
                    gold_14k FLOAT,
                    gold_10k FLOAT,
                    silver_price FLOAT
                );
                """

        create_table_gdelt = """
            CREATE TABLE geopolitical_data (
                id SERIAL PRIMARY KEY,
                date DATE,
                country TEXT,
                total_events INTEGER,
                political_events INTEGER,
                war_intensity DOUBLE PRECISION,
                crisis_index DOUBLE PRECISION,
                political_pressure DOUBLE PRECISION
                );
                """
        
        Create_table_yahoo_finance = """
            CREATE TABLE vix_oil_data (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                vix FLOAT,
                oil_price FLOAT
                )"""
        
        Create_table_date = """
            CREATE TABLE Dim_Date (
                date DATE PRIMARY KEY
                )"""
        
        Create_table_reserves_gold = """
            CREATE TABLE IF NOT EXISTS reserves_gold (
                country_name TEXT,
                country_code TEXT,
                year INT,
                value BIGINT
            );"""
        
        Create_table_fred_API = """
            CREATE TABLE macroeconomic_data (
                            date DATE PRIMARY KEY,
                            fed_rate FLOAT,
                            real_rate FLOAT,
                            cpi FLOAT,
                            gdp FLOAT,
                            dxy FLOAT,
                            unemployment FLOAT
                        );
            """
            


        with engine.connect() as conn:
            conn.execute(text(create_raw_table_query))
            conn.execute(text(create_clean_table_query))
            conn.execute(text(create_table_gdelt))
            conn.execute(text(Create_table_yahoo_finance))
            conn.execute(text(Create_table_date))
            conn.execute(text(Create_table_reserves_gold))
            conn.execute(text(Create_table_fred_API))



# Insertion dans raw_data

def insert_raw_data(df):
    
        engine = get_engine()

        df.to_sql(
            "raw_data",
            engine,
            if_exists="append",
            index=False
        )

    
def insert_cleaned_data(df):
    engine = get_engine()

    df.to_sql(
        "cleaned_data",
        engine,
        if_exists="append",
        index=False
    )

def insert_gdelt_data(df):
    engine = get_engine()
    df.to_sql(
        "geopolitical_data",
        engine,
        if_exists="append",   
        index=False
    )

def insert_Fred_Api_data(df):
    engine = get_engine()
    df.to_sql(
        "Macroeconomic_data",
        engine,
        if_exists="append",   
        index=False
    )

def insert_yfinance_data(df):
     engine = get_engine()
     df.to_sql(
        "vix_oil_data",
        engine,
        if_exists="append",   
        index=False
    )
     
def insert_date(start="2016-01-01"):
    engine = get_engine()
    df = pd.DataFrame({
        "date": pd.date_range(start=start, end=pd.Timestamp.today())
    })
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["day"] = df["date"].dt.day
    df["quarter"] = df["date"].dt.quarter
    df["date"] = pd.to_datetime(df["date"])
    df.to_sql(
        "dim_date",
        con=engine,
        if_exists="append",
        index=False
    )


def insert_excel(file_path):
    engine = get_engine()
    df = pd.read_excel(file_path, engine="openpyxl")
    df = df.melt(
        id_vars=["Country Name", "Country Code"],
        var_name="year",
        value_name="value")
    df["year"] = df["year"].astype(int)
    df["value"] = df["value"].astype(int)
    df.columns = ["country_name", "country_code", "year", "value"]
    df.to_sql(
        "reserves_gold",
        con=engine,
        if_exists="append",
        index=False
    )




# 🔹 Initialisation globale
def init_database():
    create_database()
    create_tables()
