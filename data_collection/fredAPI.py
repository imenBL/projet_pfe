from fredapi import Fred
import pandas as pd


fred = Fred(api_key="7342e6eee30a179de620bbecdf78cd91")

def import_Fred():
    #Tx d'interet CT
    fed_rate = fred.get_series("FEDFUNDS").rename("fed_rate")
    #Tx d'interet réel
    real_rate = fred.get_series("REAINTRATREARAT10Y").rename("real_rate")
    #Inflation:
    cpi = fred.get_series("CPIAUCSL").rename("CPI")
    #PIB 
    gdp = fred.get_series("GDP").rename("GDP")
    #Force du dollar:
    dxy = fred.get_series("DTWEXBGS").rename("DXY")
    #Unemployment rate
    unemployment = fred.get_series("UNRATE").rename("Unemployment")
    import pandas as pd

    df = pd.concat(
        [fed_rate, real_rate, cpi, gdp, dxy, unemployment],
        axis=1
    )
    df = df.reset_index()
    df.rename(columns={"index": "date"}, inplace=True)
    df["date"] = pd.to_datetime(df["date"])

    return df

    



        








