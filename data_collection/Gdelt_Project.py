from google.cloud import bigquery
import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ibenl\OneDrive\Bureau\Projet PFE\gdelt-key.json"

def fetch_geopolitical_indices():
    client = bigquery.Client()

    query = """
    SELECT
        DATE(PARSE_DATE('%Y%m%d', CAST(SQLDATE AS STRING))) AS date,
        Actor1CountryCode AS country,
        COUNT(*) AS total_events,
        SUM(
            CASE 
                WHEN SAFE_CAST(EventCode AS INT64) BETWEEN 100 AND 199 
                THEN 1 ELSE 0 
            END
        ) AS political_events,
        SAFE_DIVIDE(
            SUM(CASE WHEN EventRootCode = '19' THEN 1 ELSE 0 END),
            COUNT(*)
        ) AS war_intensity,
        AVG(GoldsteinScale) AS crisis_index,
        SAFE_DIVIDE(
            SUM(
                CASE 
                    WHEN SAFE_CAST(EventCode AS INT64) BETWEEN 100 AND 199 
                    THEN 1 ELSE 0 
                END
            ),
            COUNT(*)
        ) AS political_pressure

    FROM `gdelt-bq.full.events`

    WHERE 
        Actor1CountryCode IS NOT NULL
        AND SQLDATE IS NOT NULL
        AND EventCode IS NOT NULL
        AND AvgTone IS NOT NULL

    GROUP BY date, country

    HAVING total_events >= 10

    ORDER BY date, country;
    """

    df = client.query(query).to_dataframe()

    return df


