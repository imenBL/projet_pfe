import requests

url = "https://newsapi.org/v2/everything"

params = {
    "q": " OR politics OR inflation OR war OR economy OR covid OR climate",
    "from": "2026-04-20",
    "sortBy": "relevancy",
    "language": "en",
    "apiKey": "d3d48042e5d04b61a8f1ab968c5c2ffa"
}

response = requests.get(url, params=params)

data = response.json()

articles = []

for article in data["articles"]:
    articles.append({
        "date": article["publishedAt"],
        "title": article["title"],
        "description": article["description"],
        "source": article["source"]["name"]
    })

# Test affichage
for a in articles[:5]:
    print(a)
