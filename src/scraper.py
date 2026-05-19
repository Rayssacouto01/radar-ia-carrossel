"""Busca novidades de IA nas fontes configuradas via RSS e scraping."""

import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Optional
import time

SOURCES = [
    {
        "name": "OpenAI Blog",
        "rss": "https://openai.com/blog/rss.xml",
        "fallback_url": "https://openai.com/blog",
        "tag": "openai",
    },
    {
        "name": "Google DeepMind",
        "rss": "https://blog.google/technology/ai/rss/",
        "fallback_url": None,
        "tag": "google",
    },
    {
        "name": "Anthropic",
        "rss": "https://www.anthropic.com/news/rss",
        "fallback_url": "https://www.anthropic.com/news",
        "tag": "anthropic",
    },
    {
        "name": "Hugging Face Blog",
        "rss": "https://huggingface.co/blog/feed.xml",
        "fallback_url": None,
        "tag": "huggingface",
    },
    {
        "name": "arXiv AI",
        "rss": "https://rss.arxiv.org/rss/cs.AI",
        "fallback_url": None,
        "tag": "arxiv",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


@dataclass
class NewsItem:
    title: str
    summary: str
    url: str
    source: str
    tag: str
    published: Optional[datetime] = None
    full_text: str = ""
    extra_tags: list[str] = field(default_factory=list)


def _parse_date(entry) -> Optional[datetime]:
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _fetch_rss(source: dict, cutoff: datetime) -> list[NewsItem]:
    items: list[NewsItem] = []
    try:
        feed = feedparser.parse(source["rss"], request_headers=HEADERS)
        for entry in feed.entries:
            pub = _parse_date(entry)
            if pub and pub < cutoff:
                continue
            summary = getattr(entry, "summary", "") or ""
            soup = BeautifulSoup(summary, "lxml")
            clean_summary = soup.get_text(" ", strip=True)[:800]

            items.append(
                NewsItem(
                    title=entry.get("title", "").strip(),
                    summary=clean_summary,
                    url=entry.get("link", ""),
                    source=source["name"],
                    tag=source["tag"],
                    published=pub,
                )
            )
    except Exception as e:
        print(f"[scraper] Erro ao ler RSS {source['name']}: {e}")
    return items


def _fetch_anthropic_fallback(cutoff: datetime) -> list[NewsItem]:
    """Fallback HTML scraping para Anthropic caso o RSS falhe."""
    items: list[NewsItem] = []
    try:
        resp = requests.get(
            "https://www.anthropic.com/news", headers=HEADERS, timeout=15
        )
        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.select("a[href*='/news/']")
        seen = set()
        for card in cards[:10]:
            href = card.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)
            url = f"https://www.anthropic.com{href}" if href.startswith("/") else href
            title = card.get_text(" ", strip=True)[:200]
            if not title:
                continue
            items.append(
                NewsItem(
                    title=title,
                    summary="",
                    url=url,
                    source="Anthropic",
                    tag="anthropic",
                )
            )
    except Exception as e:
        print(f"[scraper] Fallback Anthropic falhou: {e}")
    return items


def fetch_article_text(url: str, max_chars: int = 3000) -> str:
    """Busca o texto principal de um artigo para enriquecer a análise."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
        return text[:max_chars]
    except Exception:
        return ""


def fetch_all_news(hours_back: int = 24, max_per_source: int = 3) -> list[NewsItem]:
    """Retorna notícias das últimas `hours_back` horas de todas as fontes."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours_back)
    all_items: list[NewsItem] = []

    for source in SOURCES:
        items = _fetch_rss(source, cutoff)

        # Fallback para Anthropic se RSS retornou vazio
        if not items and source["tag"] == "anthropic":
            items = _fetch_anthropic_fallback(cutoff)

        # Limita por fonte e ordena por data (mais recente primeiro)
        items.sort(key=lambda x: x.published or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        all_items.extend(items[:max_per_source])
        time.sleep(0.5)  # gentileza com os servidores

    return all_items
