"""
Step 1: Discover — Fetch trending topics from four data sources,
deduplicate, and save a ranked topic list.
"""

import json
import os
from datetime import date

from utils import google_trends, hackernews, github_trending, reddit


def load_history(output_dir):
    """Load previously written keywords to avoid repeats."""
    path = os.path.join(output_dir, "..", "data", "history.json")
    path = os.path.normpath(path)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return set(k.lower() for k in json.load(f).get("written_keywords", []))
    return set()


def deduplicate(topics):
    """Remove duplicate topics by normalized keyword."""
    seen = {}
    unique = []

    for topic in topics:
        key = topic["keyword"].lower().strip()
        if key in seen:
            if topic["heat_score"] > seen[key]["heat_score"]:
                unique = [t for t in unique if t["keyword"].lower().strip() != key]
                unique.append(topic)
                seen[key] = topic
        else:
            seen[key] = topic
            unique.append(topic)

    return unique


def run(config):
    """Execute Step 1: fetch → deduplicate → filter history → save."""
    print("\n" + "=" * 60)
    print("STEP 1: DISCOVER — Fetching trending topics")
    print("=" * 60)

    output_dir = config["production"]["output_dir"]
    history = load_history(output_dir)
    if history:
        print(f"  (Filtering out {len(history)} previously written keywords)")

    all_topics = []
    sources = [
        ("Google Trends", google_trends),
        ("Hacker News", hackernews),
        ("GitHub Trending", github_trending),
        ("Reddit", reddit),
    ]

    for name, module in sources:
        print(f"\n  → {name}...")
        try:
            topics = module.fetch(config)
            print(f"    {len(topics)} topics")
            all_topics.extend(topics)
        except Exception as e:
            print(f"    [!] Failed: {e}")

    unique = deduplicate(all_topics)

    # Filter out already-written keywords
    if history:
        before = len(unique)
        unique = [t for t in unique if t["keyword"].lower().strip() not in history]
        print(f"\n  Filtered: {before} → {len(unique)} (removed {before - len(unique)} repeats)")

    unique.sort(key=lambda x: x["heat_score"], reverse=True)

    # Save
    topics_dir = os.path.join(output_dir, "topics")
    os.makedirs(topics_dir, exist_ok=True)

    today = date.today().isoformat()
    output_path = os.path.join(topics_dir, f"{today}-topics.json")

    payload = {"date": today, "total": len(unique), "topics": unique}
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"\n  ✓ {len(unique)} unique topics → {output_path}")
    print(f"    (from {len(all_topics)} raw across {len(sources)} sources)")

    return output_path
