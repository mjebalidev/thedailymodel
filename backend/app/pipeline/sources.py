from __future__ import annotations

# Curated RSS feeds for AI news discovery. Free, no API key required.
# Grouped roughly by type; publisher label is used for attribution in the UI.
RSS_FEEDS: list[tuple[str, str]] = [
    # ── Labs / official blogs ────────────────────────────────────────────
    ("Google AI Blog", "https://blog.google/technology/ai/rss/"),
    ("DeepMind", "https://deepmind.google/blog/rss.xml"),
    ("OpenAI", "https://openai.com/news/rss.xml"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml"),
    ("BAIR (Berkeley)", "https://bair.berkeley.edu/blog/feed.xml"),
    ("MIT News — AI", "https://news.mit.edu/topic/mitartificial-intelligence2-rss.xml"),
    # ── Media / press ────────────────────────────────────────────────────
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("Ars Technica AI", "https://arstechnica.com/ai/feed/"),
    ("MIT Tech Review AI", "https://www.technologyreview.com/topic/artificial-intelligence/feed"),
    # ── Research feeds ───────────────────────────────────────────────────
    ("arXiv cs.AI", "http://export.arxiv.org/rss/cs.AI"),
    ("arXiv cs.LG", "http://export.arxiv.org/rss/cs.LG"),
    ("arXiv cs.CL", "http://export.arxiv.org/rss/cs.CL"),
]

# Queries used for supplementary DuckDuckGo discovery (no API key needed).
WEB_SEARCH_QUERIES: list[str] = [
    "artificial intelligence news",
    "large language model release",
    "AI model announcement",
]
