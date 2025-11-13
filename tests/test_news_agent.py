# tests/test_news_agent.py
from src.agents.news_agent import fetch_news

print("Fetching news for Apple...")
news = fetch_news("Apple earnings", max_results=3)
for n in news:
    print(f"📰 {n['title']} ({n['source']}) - {n['date']}")
print(f"\n✅ Fetched {len(news)} articles successfully.")
