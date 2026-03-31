import requests
from bs4 import BeautifulSoup

GITHUB_TRENDING_URL = "https://github.com/trending"


def fetch(config):
    """Scrape GitHub trending repositories."""
    settings = config["sources"]["github_trending"]
    if not settings.get("enabled"):
        return []

    params = {}
    since = settings.get("since", "daily")
    if since:
        params["since"] = since
    spoken_lang = settings.get("spoken_language", "")
    if spoken_lang:
        params["spoken_language_code"] = spoken_lang

    topics = []

    try:
        resp = requests.get(
            GITHUB_TRENDING_URL,
            params=params,
            headers={"User-Agent": "Mozilla/5.0 (blog-pipeline/1.0)"},
            timeout=15,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for article in soup.select("article.Box-row")[:25]:
            h2 = article.select_one("h2 a")
            if not h2:
                continue

            repo_name = h2.get_text(strip=True).replace("\n", "").replace(" ", "")

            desc_tag = article.select_one("p")
            description = desc_tag.get_text(strip=True) if desc_tag else ""

            stars_today = 0
            stars_span = article.select("span.d-inline-block.float-sm-right")
            if stars_span:
                digits = "".join(filter(str.isdigit, stars_span[0].get_text()))
                stars_today = int(digits) if digits else 0

            lang_tag = article.select_one("span[itemprop='programmingLanguage']")
            language = lang_tag.get_text(strip=True) if lang_tag else ""

            topics.append(
                {
                    "keyword": repo_name,
                    "source": "github_trending",
                    "heat_score": min(stars_today, 100),
                    "context": (
                        f"{description} "
                        f"(Lang: {language}, +{stars_today} stars today)"
                    ),
                    "url": f"https://github.com/{repo_name}",
                }
            )
    except Exception as e:
        print(f"  [!] GitHub Trending error: {e}")

    return topics
