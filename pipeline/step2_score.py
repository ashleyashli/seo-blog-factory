"""
Step 2: Score — Evaluate each topic's relevance via LLM,
then output a ranked candidate list for human review.
"""

import json
import os
from datetime import date

from utils.llm_client import LLMClient

SCORING_SYSTEM_PROMPT = """You are a topic relevance scorer for a technology blog.

## Blog Focus
AI Agent ecosystems, open-source frameworks, and business automation
for solo founders / One Person Companies.

## Core Domains (evaluate against these)
{domains}

## Brand: {brand}

## Scoring Rules
- 90-100: Directly about a core domain, high builder value
- 70-89:  Strong connection, can yield actionable insights
- 50-69:  Tangential — only if a unique angle exists
- 0-49:   Unrelated — skip

## Output
Return ONLY a JSON object (no markdown fences):
{{
  "keyword": "the topic keyword",
  "relevance_score": <int 0-100>,
  "domain_match": "which core domain(s) it matches",
  "search_intent": "Build / Buy / Learn",
  "builder_value": "what a solo founder takes away after reading",
  "suggested_angle": "recommended blog angle — one sentence",
  "suggested_title": "a compelling blog title suggestion",
  "skip": <boolean>,
  "skip_reason": "reason if skip is true, empty string otherwise"
}}"""


def _latest_topics_file(output_dir):
    """Find the most recent topics JSON."""
    topics_dir = os.path.join(output_dir, "topics")
    files = sorted(
        [f for f in os.listdir(topics_dir) if f.endswith("-topics.json")],
        reverse=True,
    )
    if not files:
        raise FileNotFoundError(f"No topics files in {topics_dir}. Run 'discover' first.")
    return os.path.join(topics_dir, files[0])


def load_topics(config, topics_path=None):
    """Load topics from a specific file or the most recent one."""
    path = topics_path or _latest_topics_file(config["production"]["output_dir"])
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def score_one(llm, system_prompt, topic):
    """Score a single topic and return parsed JSON."""
    user_msg = (
        f"Score this topic:\n\n"
        f"Keyword: {topic['keyword']}\n"
        f"Source: {topic['source']}\n"
        f"Context: {topic['context']}\n"
        f"Heat Score: {topic['heat_score']}\n"
        f"URL: {topic['url']}"
    )
    raw = llm.score(system_prompt, user_msg)
    return LLMClient.extract_json(raw)


def build_review_markdown(candidates):
    """Human-readable Markdown table for reviewing candidates."""
    lines = [
        "# 📋 Topic Candidates for Review\n",
        f"**Date:** {date.today().isoformat()}\n",
        "Review the list below, then run:\n",
        "```",
        "python pipeline/orchestrator.py select",
        "```\n",
        "| # | Score | Keyword | Domain | Intent | Suggested Angle |",
        "|---|-------|---------|--------|--------|-----------------|",
    ]
    for i, c in enumerate(candidates, 1):
        kw = c.get("keyword", "")[:55]
        dm = c.get("domain_match", "")[:30]
        si = c.get("search_intent", "")
        sa = c.get("suggested_angle", "")[:55]
        sc = c.get("relevance_score", 0)
        lines.append(f"| {i} | {sc} | {kw} | {dm} | {si} | {sa} |")

    return "\n".join(lines)


def run(config, topics_path=None):
    """Execute Step 2: load topics → score each → output candidates."""
    print("\n" + "=" * 60)
    print("STEP 2: SCORE — Evaluating topic relevance")
    print("=" * 60)

    llm = LLMClient(config)
    data = load_topics(config, topics_path)
    topics = data["topics"]

    domains = "\n".join(f"- {area}" for area in config["domain"]["core_areas"])
    system_prompt = SCORING_SYSTEM_PROMPT.format(
        domains=domains,
        brand=config["domain"]["brand"],
    )

    threshold = config["scoring"]["relevance_threshold"]
    top_n = config["scoring"]["top_n_candidates"]

    scored = []
    total = len(topics)

    for i, topic in enumerate(topics):
        label = topic["keyword"][:60]
        print(f"  [{i + 1}/{total}] {label}...")
        try:
            result = score_one(llm, system_prompt, topic)
            result["original_source"] = topic["source"]
            result["original_heat_score"] = topic["heat_score"]
            result["url"] = topic["url"]
            scored.append(result)
        except Exception as e:
            print(f"    [!] Failed: {e}")

    qualified = [s for s in scored if s.get("relevance_score", 0) >= threshold]
    qualified.sort(key=lambda x: x["relevance_score"], reverse=True)
    candidates = qualified[:top_n]

    # Save
    scored_dir = os.path.join(config["production"]["output_dir"], "scored")
    os.makedirs(scored_dir, exist_ok=True)
    today = date.today().isoformat()

    json_path = os.path.join(scored_dir, f"{today}-candidates.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {"date": today, "total": len(candidates), "candidates": candidates},
            f,
            ensure_ascii=False,
            indent=2,
        )

    md_path = os.path.join(scored_dir, f"{today}-candidates.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(build_review_markdown(candidates))

    print(f"\n  ✓ {len(candidates)} candidates (scored {len(scored)}, threshold ≥ {threshold})")
    print(f"    JSON:   {json_path}")
    print(f"    Review: {md_path}")
    print(f"\n  → Next: run 'python pipeline/orchestrator.py select' to pick your topics")

    return json_path
