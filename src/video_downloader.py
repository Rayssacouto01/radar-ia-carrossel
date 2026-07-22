"""Baixa vídeo de um link (YouTube e afins) para uso como item do carrossel."""

import os
import tempfile
from pathlib import Path

import yt_dlp

MAX_DURATION_SECONDS = 180  # 3 minutos — carrossel usa vídeo curto, evita baixar algo enorme por engano

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
