# tests/test_sentiment_agent.py
from src.agents.sentiment_agent import score_article

text = "Apple reports strong revenue growth and record profits for Q4."
score = score_article(text)
print(f"🧠 Sentiment score: {score}")
