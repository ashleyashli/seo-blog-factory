"""
Step 3: Produce — Generate blog articles for selected topics
using the blog-factory Skill as the system prompt.
"""

import json
import os
import re
from datetime import date

from utils.llm_client import LLMClient

SKILL_FILENAME = os.path.join(".cursor", "skills", "blog-factory", "SKILL.md")


def load_skill():
    """Load the blog-factory SKILL.md from the project root."""
    candidates = [
        os.path.join(os.getcwd(), SKILL_FILENAME),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), SKILL_FILENAME),
    ]
    for path in candidates:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    raise FileNotFoundError(
        f"blog-factory SKILL.md not found. Searched:\n  " + "\n  ".join(candidates)
    )


def load_selected(config, selected_path=None):
    """Load the human-curated selected topics list."""
    if selected_path and os.path.exists(selected_path):
        with open(selected_path, "r", encoding="utf-8") as f:
            return json.load(f)

    scored_dir = os.path.join(config["production"]["output_dir"], "scored")
    today = date.today().isoformat()
    default_path = os.path.join(scored_dir, f"{today}-selected.json")

    if os.path.exists(default_path):
        with open(default_path, "r", encoding="utf-8") as f:
            return json.load(f)

    raise FileNotFoundError(
        f"No selected topics found.\n"
        f"  Run 'python pipeline/orchestrator.py select' first.\n"
        f"  Expected: {default_path}"
    )


def make_slug(title):
    """Turn a title into a URL-friendly slug."""
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:60]


def produce_one(llm, skill_prompt, topic, language, brand_context=""):
    """Generate a single blog article."""
    lang_label = "中文" if language == "zh" else "English"

    brand_ctx = ""
    if brand_context:
        brand_ctx = (
            "\n## 品牌上下文（自然融入，不要硬广）\n"
            f"{brand_context}\n"
        )

    user_prompt = (
        "请根据以下热点话题，按照 Skill 中定义的完整工作流 "
        "(Phase 1 分析 → Phase 2 撰写) 生成一篇完整的博客文章。\n\n"
        "## 话题信息\n"
        f"- **关键词**: {topic.get('keyword', '')}\n"
        f"- **领域匹配**: {topic.get('domain_match', '')}\n"
        f"- **搜索意图**: {topic.get('search_intent', '')}\n"
        f"- **Builder 价值**: {topic.get('builder_value', '')}\n"
        f"- **推荐角度**: {topic.get('suggested_angle', '')}\n"
        f"- **推荐标题**: {topic.get('suggested_title', '')}\n"
        f"- **原始来源**: {topic.get('original_source', '')}\n"
        f"{brand_ctx}\n"
        "## 要求\n"
        "1. 先输出 Phase 1 的 Topic Analysis 表格\n"
        "2. 然后输出完整的 Phase 2 博客文章（含 YAML frontmatter）\n"
        f"3. 语言: {lang_label}\n"
        "4. 封面生成部分 (Phase 3) 跳过 — 只在 frontmatter 中填写 cover_title 和 visual_cues\n"
        "5. 在文章中自然地融入品牌产品（如适用），但不要写成广告\n"
    )
    return llm.write(skill_prompt, user_prompt)


def save_article(content, topic, output_dir):
    """Save generated markdown and return the file path."""
    title = topic.get("suggested_title", topic.get("keyword", "untitled"))
    slug = make_slug(title)
    today = date.today().isoformat()

    drafts_dir = os.path.join(output_dir, "drafts", today)
    os.makedirs(drafts_dir, exist_ok=True)

    filepath = os.path.join(drafts_dir, f"{slug}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath


def update_history(keywords, output_dir):
    """Append produced keywords to history for future dedup."""
    history_path = os.path.normpath(os.path.join(output_dir, "..", "data", "history.json"))
    os.makedirs(os.path.dirname(history_path), exist_ok=True)

    history = {"written_keywords": []}
    if os.path.exists(history_path):
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)

    history["written_keywords"].extend(keywords)

    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def run(config, selected_path=None):
    """Execute Step 3: load selected → generate articles → save."""
    print("\n" + "=" * 60)
    print("STEP 3: PRODUCE — Generating blog articles")
    print("=" * 60)

    llm = LLMClient(config)
    skill_prompt = load_skill()
    selected_data = load_selected(config, selected_path)

    topics = (
        selected_data
        if isinstance(selected_data, list)
        else selected_data.get("topics", selected_data.get("candidates", []))
    )

    output_dir = config["production"]["output_dir"]
    language = config["production"].get("language", "zh")
    brand_context = config.get("domain", {}).get("brand_context", "")

    results = []
    produced_keywords = []
    total = len(topics)

    for i, topic in enumerate(topics):
        keyword = topic.get("keyword", "unknown")
        print(f"\n  [{i + 1}/{total}] {keyword[:60]}...")
        try:
            content = produce_one(llm, skill_prompt, topic, language, brand_context)
            filepath = save_article(content, topic, output_dir)
            results.append({"keyword": keyword, "file": filepath, "status": "success"})
            produced_keywords.append(keyword)
            print(f"    ✓ → {filepath}")
        except Exception as e:
            results.append({"keyword": keyword, "file": None, "status": f"failed: {e}"})
            print(f"    ✗ Failed: {e}")

    if produced_keywords:
        update_history(produced_keywords, output_dir)

    success = sum(1 for r in results if r["status"] == "success")
    print(f"\n  ✓ {success}/{total} articles generated")

    summary_path = os.path.join(output_dir, "drafts", f"{date.today().isoformat()}-summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"    Summary: {summary_path}")

    return results
