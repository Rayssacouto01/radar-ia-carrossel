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
        "scrape_url": "https://openai.com/news",
        "scrape_selector": "a[href*='/index/']",
        "tag": "openai",
    },
    {
        "name": "Google DeepMind",
        "rss": "https://blog.google/technology/ai/rss/",
        "scrape_url": None,
        "scrape_selector": None,
        "tag": "google",
    },
    {
        "name": "Anthropic",
        "rss": "https://www.anthropic.com/news/rss",
        "scrape_url": "https://www.anthropic.com/news",
        "scrape_selector": "a[href*='/news/']",
        "tag": "anthropic",
    },
    {
        "name": "Hugging Face Blog",
        "rss": "https://huggingface.co/blog/feed.xml",
        "scrape_url": None,
        "scrape_selector": None,
        "tag": "huggingface",
    },
    {
        "name": "arXiv AI",
        "rss": "https://rss.arxiv.org/rss/cs.AI",
        "scrape_url": None,
        "scrape_selector": None,
        "tag": "arxiv",
    },
    {
        "name": "Lovable",
        "rss": "https://lovable.dev/blog/rss.xml",
        "scrape_url": "https://lovable.dev/blog",
        "scrape_selector": "a[href*='/blog/']",
        "tag": "lovable",
    },
    {
        "name": "Manus",
        "rss": None,
        "scrape_url": "https://manus.im/blog",
        "scrape_selector": "a[href*='/blog/']",
        "tag": "manus",
    },
    {
        "name": "Gamma",
        "rss": None,
        "scrape_url": "https://gamma.app/blog",
        "scrape_selector": "a[href*='/blog/']",
        "tag": "gamma",
    },
    {
        "name": "xAI (Grok)",
        "rss": "https://news.google.com/rss/search?q=xAI+Grok+lançamento&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        "scrape_url": None,
        "scrape_selector": None,
        "tag": "grok",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
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
    """Busca via RSS. Só inclui artigos com data conhecida E dentro do período."""
    items: list[NewsItem] = []
    rss_url = source.get("rss")
    if not rss_url:
        return items

    try:
        feed = feedparser.parse(rss_url, request_headers=HEADERS)
        if feed.bozo and not feed.entries:
            print(f"[scraper] RSS inválido ou vazio: {source['name']}")
            return items

        undated_count = 0
        for i, entry in enumerate(feed.entries):
            pub = _parse_date(entry)

            # Artigo com data conhecida e antiga: pula
            if pub is not None and pub < cutoff:
                continue

            # Artigo sem data: aceita só os primeiros 2 de cada fonte
            # (RSS é ordenado do mais recente para o mais antigo)
            if pub is None:
                if undated_count >= 2:
                    continue
                undated_count += 1

            summary = getattr(entry, "summary", "") or ""
            soup = BeautifulSoup(summary, "lxml")
            clean_summary = soup.get_text(" ", strip=True)[:800]
            title = (entry.get("title") or "").strip()
            url = entry.get("link", "")

            if not title or not url:
                continue

            items.append(
                NewsItem(
                    title=title,
                    summary=clean_summary,
                    url=url,
                    source=source["name"],
                    tag=source["tag"],
                    published=pub,
                )
            )
    except Exception as e:
        print(f"[scraper] Erro ao ler RSS {source['name']}: {e}")

    return items


def _fetch_scrape(source: dict) -> list[NewsItem]:
    """Scraping HTML como fallback para fontes sem RSS ou com RSS falho."""
    items: list[NewsItem] = []
    url = source.get("scrape_url")
    selector = source.get("scrape_selector", "a")
    if not url:
        return items

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        links = soup.select(selector) if selector else soup.find_all("a", href=True)

        seen = set()
        base = url.rstrip("/").rsplit("/", 1)[0] if "/blog" in url else url

        for a in links[:15]:
            href = a.get("href", "").strip()
            if not href or href in seen or href == "#":
                continue
            seen.add(href)

            # Normaliza URL
            if href.startswith("http"):
                full_url = href
            elif href.startswith("/"):
                from urllib.parse import urlparse
                parsed = urlparse(url)
                full_url = f"{parsed.scheme}://{parsed.netloc}{href}"
            else:
                continue

            title = a.get_text(" ", strip=True)[:200]
            if len(title) < 10:  # ignora links muito curtos (menus, botões)
                continue

            items.append(
                NewsItem(
                    title=title,
                    summary="",
                    url=full_url,
                    source=source["name"],
                    tag=source["tag"],
                    published=None,  # scraping raramente tem data
                )
            )
    except Exception as e:
        print(f"[scraper] Scraping falhou {source['name']}: {e}")

    return items


def fetch_article_text(url: str, max_chars: int = 3000) -> str:
    """Busca o texto principal de um artigo para enriquecer a análise."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(" ", strip=True)[:max_chars]
    except Exception:
        return ""


def fetch_all_news(hours_back: int = 48, max_per_source: int = 2) -> list[NewsItem]:
    """Retorna notícias recentes de todas as fontes.

    Tenta RSS primeiro; usa scraping como fallback.
    Itens com data são priorizados sobre itens sem data.
    """
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours_back)
    all_items: list[NewsItem] = []

    for source in SOURCES:
        items = _fetch_rss(source, cutoff)

        # Fallback para scraping se RSS vazio ou inexistente
        if not items and source.get("scrape_url"):
            print(f"[scraper] Usando scraping para {source['name']}...")
            items = _fetch_scrape(source)

        # Prioriza itens com data conhecida (mais recentes primeiro)
        dated = sorted(
            [i for i in items if i.published],
            key=lambda x: x.published,
            reverse=True,
        )
        undated = [i for i in items if not i.published]

        combined = (dated + undated)[:max_per_source]
        all_items.extend(combined)

        print(f"[scraper] {source['name']}: {len(combined)} item(s)")
        time.sleep(0.5)

    return all_items
