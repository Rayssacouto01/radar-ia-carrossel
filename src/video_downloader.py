"""Baixa vídeo de um link (YouTube e afins) para uso como item do carrossel."""

import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urljoin

import requests
import yt_dlp
from bs4 import BeautifulSoup

from .scraper import HEADERS

MAX_DURATION_SECONDS = 180  # 3 minutos — carrossel usa vídeo curto, evita baixar algo enorme por engano
MAX_DIRECT_VIDEO_BYTES = 60 * 1024 * 1024  # 60MB — mesmo limite do upload manual

VIDEO_FILE_RE = re.compile(r'https?://[^\s"\'<>]+\.(?:mp4|webm|mov|m3u8)(?:\?[^\s"\'<>]*)?', re.IGNORECASE)
YOUTUBE_EMBED_RE = re.compile(r'https?://(?:www\.)?(?:youtube(?:-nocookie)?\.com/embed/[\w-]+|youtu\.be/[\w-]+)')
VIMEO_EMBED_RE = re.compile(r'https?://(?:www\.)?player\.vimeo\.com/video/\d+')

# Caminho opcional de um cookies.txt (formato Netscape) exportado de um navegador logado no
# YouTube. Alguns servidores/VPS levam bloqueio anti-bot do YouTube sem isso — ver
# https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp
YOUTUBE_COOKIES_FILE = os.getenv("YOUTUBE_COOKIES_FILE", "")


def _base_opts() -> dict:
    opts = {"extractor_args": {"youtube": {"player_client": ["android", "web"]}}}
    if YOUTUBE_COOKIES_FILE and Path(YOUTUBE_COOKIES_FILE).exists():
        opts["cookiefile"] = YOUTUBE_COOKIES_FILE
    return opts


def download_video(url: str) -> tuple[str, str]:
    """Baixa o vídeo do link. Retorna (caminho_local, erro). Em sucesso, erro == ""."""
    try:
        probe_opts = {"quiet": True, "skip_download": True, "noplaylist": True, **_base_opts()}
        with yt_dlp.YoutubeDL(probe_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        duration = info.get("duration") or 0
        if duration > MAX_DURATION_SECONDS:
            minutos = MAX_DURATION_SECONDS // 60
            return "", f"Vídeo tem {int(duration)}s — o limite pra carrossel é {minutos} minutos."

        tmp_dir = tempfile.mkdtemp(prefix="youtube_video_")
        outtmpl = str(Path(tmp_dir) / "video.%(ext)s")
        download_opts = {
            "quiet": True,
            "noplaylist": True,
            "format": "best[ext=mp4][height<=720]/bestvideo[height<=720]+bestaudio/best[height<=720]/best",
            "merge_output_format": "mp4",
            "outtmpl": outtmpl,
            **_base_opts(),
        }
        with yt_dlp.YoutubeDL(download_opts) as ydl:
            ydl.download([url])

        final_path = Path(tmp_dir) / "video.mp4"
        if not final_path.exists():
            candidates = list(Path(tmp_dir).glob("video.*"))
            if not candidates:
                return "", "O download não gerou nenhum arquivo de vídeo."
            final_path = candidates[0]

        return str(final_path), ""
    except Exception as e:
        return "", f"Não foi possível baixar o vídeo: {e}"


def _find_direct_video_url(html: str, page_url: str) -> str:
    """Procura um vídeo hospedado direto (tag <video>, og:video, ou link .mp4/.webm no HTML)."""
    soup = BeautifulSoup(html, "lxml")

    for video_tag in soup.find_all("video"):
        src = video_tag.get("src")
        if src:
            return urljoin(page_url, src)
        for source_tag in video_tag.find_all("source"):
            src = source_tag.get("src")
            if src:
                return urljoin(page_url, src)

    for prop in ("og:video:secure_url", "og:video:url", "og:video"):
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if tag and tag.get("content"):
            return urljoin(page_url, tag["content"])

    match = VIDEO_FILE_RE.search(html)
    return match.group(0) if match else ""


def _find_embed_url(html: str) -> str:
    """Procura um embed de YouTube ou Vimeo na página."""
    match = YOUTUBE_EMBED_RE.search(html) or VIMEO_EMBED_RE.search(html)
    return match.group(0) if match else ""


def extract_video_from_page(page_url: str) -> tuple[str, str]:
    """Encontra e baixa o vídeo de uma página de artigo. Retorna (caminho_local, erro).

    Tenta primeiro um vídeo hospedado direto (download simples via requests, sem depender do
    yt-dlp). Se não achar, procura um embed de YouTube/Vimeo e usa download_video() para esse caso.
    """
    try:
        resp = requests.get(page_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        html = resp.text

        direct_url = _find_direct_video_url(html, page_url)
        if direct_url:
            video_resp = requests.get(direct_url, headers=HEADERS, timeout=60, stream=True)
            video_resp.raise_for_status()

            tmp_dir = tempfile.mkdtemp(prefix="article_video_")
            ext = Path(direct_url.split("?")[0]).suffix or ".mp4"
            path = Path(tmp_dir) / f"video{ext}"

            total = 0
            with open(path, "wb") as f:
                for chunk in video_resp.iter_content(chunk_size=1 << 16):
                    total += len(chunk)
                    if total > MAX_DIRECT_VIDEO_BYTES:
                        return "", "O vídeo da página é maior que 60MB — baixe manualmente e faça upload."
                    f.write(chunk)

            return str(path), ""

        embed_url = _find_embed_url(html)
        if embed_url:
            return download_video(embed_url)

        return "", "Não encontrei nenhum vídeo nessa página."
    except Exception as e:
        return "", f"Não foi possível extrair o vídeo da página: {e}"
