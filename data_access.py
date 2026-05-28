import pandas as pd
from db_settings import get_engine

_TABLES = {
    "raw_prices": "raw_prices",
    "macro_data": "macro_data",
    "vix_oil": "vix_oil_data",
    "geopo": "geopo_data",
    "reserves": "reserves_gold",
    "features": "ml.us_gold_features_daily",
}

_CACHE = {}


def _read_table(table_name, refresh=False):
    if refresh or table_name not in _CACHE:
        _CACHE[table_name] = pd.read_sql(f"SELECT * FROM {table_name}", get_engine())
    return _CACHE[table_name]


def load_raw_prices(refresh=False):
    return _read_table(_TABLES["raw_prices"], refresh)


def load_macro_data(refresh=False):
    return _read_table(_TABLES["macro_data"], refresh)


def load_vix_oil(refresh=False):
    return _read_table(_TABLES["vix_oil"], refresh)


def load_geopo(refresh=False):
    return _read_table(_TABLES["geopo"], refresh)


def load_reserves(refresh=False):
    return _read_table(_TABLES["reserves"], refresh)


def load_features(refresh=False):
    # Phase-2 model-ready table ml.us_gold_features_daily (one row per USA trading day).
    return _read_table(_TABLES["features"], refresh)
