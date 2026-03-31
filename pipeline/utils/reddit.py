import xml.etree.ElementTree as ET

import requests

REDDIT_RSS_URL = "https://www.reddit.com/r/{subreddit}/hot/.rss"


def fetch(config):
    """Fetch hot posts from Reddit subreddits via public RSS feed."""
    settings = config["sources"]["reddit"]
    if not settings.get("enabled"):
        return []

    topics = []
    subreddits = settings.get("subreddits", [])
    top_n = settings.get("top_n", 10)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    for sub in subreddits:
        try:
            url = REDDIT_RSS_URL.format(subreddit=sub)
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()

            root = ET.fromstring(resp.content)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall("atom:entry", ns)

            for entry in entries[:top_n]:
                title_el = entry.find("atom:title", ns)
                link_el = entry.find("atom:link", ns)
                if title_el is None:
                    continue

                title = title_el.text or ""
                link = link_el.get("href", "") if link_el is not None else ""

                topics.append(
                    {
                        "keyword": title,
                        "source": f"reddit/r/{sub}",
                        "heat_score": 50,
                        "context": f"r/{sub} hot post",
                        "url": link,
                    }
                )
        except Exception as e:
            print(f"  [!] Reddit error for r/{sub}: {e}")

    return topics
