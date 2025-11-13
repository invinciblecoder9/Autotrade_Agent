# # src/agents/news_agent.py
# """
# Robust DuckDuckGo news fetcher.
# Tries multiple import patterns so it works with duckduckgo-search (older),
# duckduckgo_search.DDGS (newer), or ddgs (alternative package).
# """

# from datetime import datetime, timezone
# import logging

# logger = logging.getLogger(__name__)

# def fetch_news(query: str, max_results: int = 5, region: str = "wt-wt"):
#     """
#     Returns list of dicts: {'title','body','url','source','date'}
#     Tries to use ddg_news, otherwise DDGS().news()
#     """
#     # Try ddg_news (older/simple API)
#     try:
#         from duckduckgo_search import ddg_news  # type: ignore
#         results = ddg_news(query, region=region, max_results=max_results)
#         cleaned = []
#         for r in results or []:
#             cleaned.append({
#                 "title": r.get("title"),
#                 "body": r.get("body", ""),
#                 "source": r.get("source"),
#                 "url": r.get("href") or r.get("url"),
#                 "date": r.get("date") or datetime.now(timezone.utc).isoformat()
#             })
#         return cleaned
#     except Exception as e:
#         logger.debug("ddg_news not available or failed: %s", e)

#     # Try DDGS from duckduckgo_search package (class-based API)
#     try:
#         from duckduckgo_search import DDGS  # type: ignore
#         with DDGS() as ddgs:
#             # many implementations have ddgs.news(...) or ddgs.text(...) backends
#             if hasattr(ddgs, "news"):
#                 results = ddgs.news(query, max_results=max_results, region=region)
#             else:
#                 # fall back to text() and attempt to filter/format as news-like results
#                 results = ddgs.text(query, max_results=max_results, region=region)
#             cleaned = []
#             for r in results or []:
#                 cleaned.append({
#                     "title": r.get("title") or r.get("topic") or None,
#                     "body": r.get("body") or r.get("snippet") or "",
#                     "source": r.get("source") or r.get("href"),
#                     "url": r.get("href") or r.get("url"),
#                     "date": r.get("date") or datetime.now(timezone.utc).isoformat()
#                 })
#             return cleaned
#     except Exception as e:
#         logger.debug("duckduckgo_search.DDGS not available or failed: %s", e)

#     # Try ddgs package (import name 'ddgs')
#     try:
#         from ddgs import DDGS as DDGS2  # type: ignore
#         with DDGS2() as ddgs:
#             if hasattr(ddgs, "news"):
#                 results = ddgs.news(query, max_results=max_results, region=region)
#             else:
#                 results = ddgs.text(query, max_results=max_results, region=region)
#             cleaned = []
#             for r in results or []:
#                 cleaned.append({
#                     "title": r.get("title") or r.get("topic") or None,
#                     "body": r.get("body") or r.get("snippet") or "",
#                     "source": r.get("source") or r.get("href"),
#                     "url": r.get("href") or r.get("url"),
#                     "date": r.get("date") or datetime.now(timezone.utc).isoformat()
#                 })
#             return cleaned
#     except Exception as e:
#         logger.debug("ddgs package not available or failed: %s", e)

#     # As a last resort: simple DuckDuckGo instant answer fallback via web API (limited)
#     try:
#         import requests
#         url = "https://api.duckduckgo.com/"
#         params = {"q": query, "format": "json", "t": "autotrade-agent"}
#         r = requests.get(url, params=params, timeout=10)
#         r.raise_for_status()
#         data = r.json()
#         # The instant answer API is not news-focused, but return something minimal
#         related = data.get("RelatedTopics") or []
#         cleaned = []
#         for item in (related[:max_results] if isinstance(related, list) else []):
#             title = item.get("Text") or item.get("Name")
#             href = item.get("FirstURL")
#             if title:
#                 cleaned.append({
#                     "title": title,
#                     "body": "",
#                     "source": None,
#                     "url": href,
#                     "date": datetime.now(timezone.utc).isoformat()
#                 })
#         if cleaned:
#             return cleaned
#     except Exception as e:
#         logger.debug("DuckDuckGo instant answer fallback failed: %s", e)

#     # If all fails, return empty list
#     logger.warning("Could not fetch news from DuckDuckGo (all methods failed).")
#     return []


# src/agents/news_agent.py (replace fetch_news implementation with this)
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

def fetch_news(query: str, max_results: int = 5) -> List[Dict]:
    """
    Fetch headlines using ddgs (DuckDuckGo Search). Returns a list of dicts:
    { 'title': ..., 'body': ..., 'url': ... }
    If anything fails, returns empty list (so agent remains safe).
    """
    try:
        from ddgs import DDGS
    except Exception as e:
        logger.warning("ddgs import failed: %s", e)
        return []

    try:
        results = []
        with DDGS() as ddgs:
            it = ddgs.text(f"{query} finance news", timelimit=1)
            for i, r in enumerate(it):
                if i >= max_results:
                    break
                title = r.get("title") or r.get("body") or r.get("query") or ""
                results.append({"title": title, "body": r.get("body", ""), "url": r.get("href")})
        return results
    except Exception as e:
        logger.warning("Could not fetch news from DuckDuckGo: %s", e)
        return []
