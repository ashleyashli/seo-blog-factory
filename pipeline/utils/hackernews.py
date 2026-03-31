import requests

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"


def fetch(config):
    """Fetch top-scored stories from Hacker News via Algolia search API."""
    settings = config["sources"]["hackernews"]
    if not settings.get("enabled"):
        return []

    topics = []
    queries = settings.get("search_queries", ["AI agent"])
    top_n = settings.get("top_n", 30)

    for query in queries:
        try:
            resp = requests.get(
                HN_SEARCH_URL,
                params={
                    "query": query,
                    "tags": "story",
                    "hitsPerPage": top_n,
                    "numericFilters": "points>10",
                },
                timeout=15,
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", [])

            for hit in hits:
                title = hit.get("title", "")
                points = hit.get("points", 0)
                topics.append(
                    {
                        "keyword": title,
                        "source": "hackernews",
                        "heat_score": min(points, 100),
                        "context": (
                            f"HN story — {points} points, "
                            f"{hit.get('num_comments', 0)} comments"
                        ),
                        "url": f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                    }
                )
        except Exception as e:
            print(f"  [!] HN error for '{query}': {e}")

    return topics
