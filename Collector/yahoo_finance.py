import yfinance as yf
import pandas as pd


def fetch_vix_oil(start="2016-01-01"):
        # 📡 Download
    vix = yf.download("^VIX", start=start)
    oil = yf.download("CL=F", start=start)

    # 🧠 Toujours récupérer Close proprement
    def extract_close(df, name):
        # Si MultiIndex (cas yfinance récent)
        if isinstance(df.columns, pd.MultiIndex):
            df = df["Close"]
        
        # Si encore DataFrame (1 colonne)
        if isinstance(df, pd.DataFrame):
            df = df.iloc[:, 0]

        # Maintenant c’est une Series → OK
        df = df.rename(name)

        return df

    vix = extract_close(vix, "vix")
    oil = extract_close(oil, "oil")

    # Fusion sur les dates (outer join = toutes les dates)
    df = pd.concat([vix, oil], axis=1)

    # Reset index pour avoir une colonne date
    df = df.reset_index()

    return df