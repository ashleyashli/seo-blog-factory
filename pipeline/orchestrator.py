"""
Blog Pipeline Orchestrator
==========================

CLI entry point for the three-step blog production pipeline.

Usage (run from project root):

    python pipeline/orchestrator.py discover     # Step 1: fetch trending topics
    python pipeline/orchestrator.py score        # Step 2: LLM relevance scoring
    python pipeline/orchestrator.py select       # Interactive: pick your topics
    python pipeline/orchestrator.py produce      # Step 3: generate blog articles
    python pipeline/orchestrator.py run          # Steps 1+2 then pause for review
"""

import argparse
import json
import os
import sys

# Make pipeline modules importable regardless of CWD
_pipeline_dir = os.path.dirname(os.path.abspath(__file__))
if _pipeline_dir not in sys.path:
    sys.path.insert(0, _pipeline_dir)

import yaml


def load_config(path="config.yaml"):
    if not os.path.exists(path):
        print(f"Error: config file not found at '{path}'")
        print("Make sure you run this command from the project root directory.")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── Commands ────────────────────────────────────────────────


def cmd_discover(args):
    config = load_config(args.config)
    from step1_discover import run
    run(config)


def cmd_score(args):
    config = load_config(args.config)
    from step2_score import run
    run(config, topics_path=getattr(args, "topics", None))


def cmd_select(args):
    """Interactive topic selection from scored candidates."""
    config = load_config(args.config)
    from datetime import date

    scored_dir = os.path.join(config["production"]["output_dir"], "scored")
    today = date.today().isoformat()

    candidates_path = getattr(args, "candidates", None) or os.path.join(
        scored_dir, f"{today}-candidates.json"
    )

    if not os.path.exists(candidates_path):
        print(f"Error: candidates file not found: {candidates_path}")
        print("Run 'discover' and 'score' first.")
        sys.exit(1)

    with open(candidates_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    candidates = data.get("candidates", [])

    print(f"\n{'=' * 60}")
    print(f"SELECT — {len(candidates)} candidates available")
    print(f"{'=' * 60}\n")

    for i, c in enumerate(candidates, 1):
        score = c.get("relevance_score", 0)
        kw = c.get("keyword", "")[:55]
        angle = c.get("suggested_angle", "")[:70]
        src = c.get("original_source", "")
        print(f"  [{i:2d}] (Score: {score:3d} | {src})")
        print(f"       {kw}")
        print(f"       → {angle}\n")

    count = config["production"]["daily_count"]
    print(f"Enter the numbers of topics to select (pick ~{count}, comma-separated):")
    print("Example: 1,3,5,7,9,10,12,14,16,18\n")

    try:
        selection = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        return

    if not selection:
        print("No selection made.")
        return

    indices = []
    for part in selection.split(","):
        part = part.strip()
        if part.isdigit():
            indices.append(int(part) - 1)

    selected = [candidates[i] for i in indices if 0 <= i < len(candidates)]

    selected_path = os.path.join(scored_dir, f"{today}-selected.json")
    with open(selected_path, "w", encoding="utf-8") as f:
        json.dump(
            {"date": today, "total": len(selected), "topics": selected},
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\n  ✓ {len(selected)} topics selected → {selected_path}")
    print("  → Next: run 'python pipeline/orchestrator.py produce'")


def cmd_produce(args):
    config = load_config(args.config)
    from step3_produce import run
    run(config, selected_path=getattr(args, "selected", None))


def cmd_run(args):
    """Run discover + score, then pause for human review."""
    config = load_config(args.config)

    from step1_discover import run as discover
    from step2_score import run as score

    print("\n>>> Phase 1/2: Discovering topics...\n")
    topics_path = discover(config)

    print("\n>>> Phase 2/2: Scoring relevance...\n")
    score(config, topics_path)

    print("\n" + "=" * 60)
    print("PAUSED — Human review required")
    print("=" * 60)
    print("\n  1. Review candidates:  open output/scored/*-candidates.md")
    print("  2. Tell AI which topics to select (e.g. '选 1, 3, 5')")
    print("     AI will write selected.json — no script needed")
    print("  3. Then AI runs 'produce' to generate articles\n")


# ── CLI ─────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Blog Pipeline — Discover → Score → Select → Produce"
    )
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("discover", help="Step 1: Fetch trending topics")

    p_score = sub.add_parser("score", help="Step 2: Score topics with LLM")
    p_score.add_argument("--topics", help="Path to topics JSON (default: latest)")

    p_select = sub.add_parser("select", help="Interactively select topics")
    p_select.add_argument("--candidates", help="Path to candidates JSON")

    p_produce = sub.add_parser("produce", help="Step 3: Generate blog posts")
    p_produce.add_argument("--selected", help="Path to selected JSON")

    sub.add_parser("run", help="Run discover + score, then pause for review")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "discover": cmd_discover,
        "score": cmd_score,
        "select": cmd_select,
        "produce": cmd_produce,
        "run": cmd_run,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
