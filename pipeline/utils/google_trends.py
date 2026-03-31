import time

from pytrends.request import TrendReq


def fetch(config):
    """Fetch rising queries from Google Trends based on seed keywords."""
    settings = config["sources"]["google_trends"]
    if not settings.get("enabled"):
        return []

    pytrends = TrendReq(hl="en-US", tz=360)
    topics = []

    for keyword in settings.get("seed_keywords", []):
        try:
            pytrends.build_payload(
                [keyword],
                timeframe=settings.get("timeframe", "now 7-d"),
                geo=settings.get("geo", ""),
            )

            related = pytrends.related_queries()
            if keyword in related:
                rising = related[keyword].get("rising")
                if rising is not None:
                    for _, row in rising.head(10).iterrows():
                        topics.append(
                            {
                                "keyword": str(row["query"]),
                                "source": "google_trends",
                                "heat_score": min(int(row["value"]) // 100, 100),
                                "context": f"Rising search related to '{keyword}'",
                                "url": f"https://trends.google.com/trends/explore?q={row['query']}",
                            }
                        )

            time.sleep(2)
        except Exception as e:
            print(f"  [!] Google Trends error for '{keyword}': {e}")

    return topics
