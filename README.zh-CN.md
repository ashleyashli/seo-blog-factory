# Blog Factory — AI 驱动的博客生产流水线

简体中文 | [English](README.md)

自动化博客生产流水线：发现热点话题 → 打分筛选 → 生成 SEO 长文。为 [nexu](https://nexu.io) 的内容策略而建，全程由 Cursor 中的 AI Agent 驱动。

## 工作流程

```
发现热点 → 相关性打分 → 人工选题 → 生成文章 → 封面图
```

| 步骤 | 做什么 | 产出 |
|------|--------|------|
| **Discover（发现）** | 从 Google Trends、Hacker News、GitHub Trending、Reddit 抓取热门话题 | `output/topics/{date}-topics.json` |
| **Score（打分）** | LLM 对每个话题做领域相关性打分，筛出 Top N 候选 | `output/scored/{date}-candidates.json` + `.md` |
| **Select（选题）** | 人看候选表格，告诉 AI 选哪几篇（不用跑脚本） | `output/scored/{date}-selected.json` |
| **Produce（生产）** | LLM 用 blog-factory Skill 作为 system prompt，生成完整博客文章 | `output/drafts/{date}/{slug}.md` |
| **Cover（封面）** | 通过 Figma MCP 或图片生成工具制作封面图 | `output/images/{slug}-cover.png` |

## 快速开始

### 1. 克隆 & 配置

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml — 填入你的 LLM API Key
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行流水线

```bash
# 一键发现 + 打分（然后暂停等人工选题）
python pipeline/orchestrator.py run

# 或者分步执行
python pipeline/orchestrator.py discover
python pipeline/orchestrator.py score
python pipeline/orchestrator.py produce
```

### 4. 选题（在 Cursor 中）

不需要跑脚本 — 查看 `output/scored/*-candidates.md` 中的候选表格，告诉 AI 你要选哪几篇，AI 会直接帮你写 `selected.json`。

## 项目结构

```
├── config.example.yaml          # 配置模板（复制为 config.yaml 后使用）
├── requirements.txt             # Python 依赖
├── pipeline/
│   ├── orchestrator.py          # CLI 入口 & 编排器
│   ├── step1_discover.py        # 话题发现（4 个数据源）
│   ├── step2_score.py           # LLM 相关性打分
│   ├── step3_produce.py         # 文章生成
│   └── utils/
│       ├── google_trends.py     # Google Trends（pytrends）
│       ├── hackernews.py        # Hacker News（Algolia API）
│       ├── github_trending.py   # GitHub Trending（网页抓取）
│       ├── reddit.py            # Reddit 帖子
│       └── llm_client.py        # OpenAI 兼容 LLM 客户端
├── .cursor/skills/blog-factory/
│   └── SKILL.md                 # 博客写作 Skill（写作规范 + SEO + 品牌指南）
├── data/
│   └── history.json             # 已写关键词（用于去重）
└── output/                      # 所有生成内容
```

## 技术栈

- **Python 3** — 流水线编排
- **LLM** — 通过 OpenAI 兼容 API（LiteLLM 代理），打分和写作使用不同模型
- **数据源** — Google Trends (`pytrends`)、Hacker News (Algolia)、GitHub Trending (`beautifulsoup4`)、Reddit
- **Cursor Skill** — `SKILL.md` 定义写作人设、文章结构、SEO 规则和品牌融入指南

## 许可证

MIT
