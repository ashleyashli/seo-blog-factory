# Blog Factory — AI-Powered Blog Production Pipeline

An automated blog production pipeline that discovers trending topics, scores relevance, and generates long-form articles optimized for SEO. Built for [nexu](https://nexu.io)'s content strategy, driven entirely by AI Agent in Cursor.

## How It Works

```
Discover → Score → Select → Produce → Cover Image
```

| Step | What happens | Output |
|------|-------------|--------|
| **Discover** | Pulls trending topics from Google Trends, Hacker News, GitHub Trending, Reddit | `output/topics/{date}-topics.json` |
| **Score** | LLM scores each topic for domain relevance, filters to Top N candidates | `output/scored/{date}-candidates.json` + `.md` |
| **Select** | Human reviews the candidate table, tells AI which ones to pick (no script needed) | `output/scored/{date}-selected.json` |
| **Produce** | LLM generates full blog articles using the blog-factory Skill as system prompt | `output/drafts/{date}/{slug}.md` |
| **Cover** | Generate cover images via Figma MCP or image generation | `output/images/{slug}-cover.png` |

## Quick Start

### 1. Clone & configure

```bash
cp config.example.yaml config.yaml
# Edit config.yaml — fill in your LLM API key
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the pipeline

```bash
# Discover + Score (then pause for human review)
python pipeline/orchestrator.py run

# Or run steps individually
python pipeline/orchestrator.py discover
python pipeline/orchestrator.py score
python pipeline/orchestrator.py produce
```

### 4. Select topics (in Cursor)

No script needed — review `output/scored/*-candidates.md`, tell the AI which topics to pick, and it writes `selected.json` for you.

## Project Structure

```
├── config.example.yaml          # Template config (copy to config.yaml)
├── requirements.txt             # Python dependencies
├── pipeline/
│   ├── orchestrator.py          # CLI entry point
│   ├── step1_discover.py        # Topic discovery from 4 data sources
│   ├── step2_score.py           # LLM relevance scoring
│   ├── step3_produce.py         # Article generation
│   └── utils/
│       ├── google_trends.py     # Google Trends via pytrends
│       ├── hackernews.py        # Hacker News via Algolia API
│       ├── github_trending.py   # GitHub Trending (scraping)
│       ├── reddit.py            # Reddit posts
│       └── llm_client.py        # OpenAI-compatible LLM client
├── .cursor/skills/blog-factory/
│   └── SKILL.md                 # Blog writing skill (system prompt)
├── data/
│   └── history.json             # Written keywords for dedup
└── output/                      # All generated content
```

## Tech Stack

- **Python 3** — pipeline orchestration
- **LLM** — via OpenAI-compatible API (LiteLLM proxy), separate models for scoring vs writing
- **Data sources** — Google Trends (`pytrends`), Hacker News (Algolia), GitHub Trending (`beautifulsoup4`), Reddit
- **Cursor Skill** — `SKILL.md` defines the writing persona, structure, SEO rules, and brand integration guide

## License

MIT
