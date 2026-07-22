"""Gera carrosséis estilo tweet (X/Twitter) para Instagram, formato fixo @rayssacouto.ia."""

import io
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .classifier import GeneratedContent

MAX_VIDEO_DURATION_SECONDS = 180  # 3 minutos, mesmo limite usado na extração/download de vídeo


def _clean_text(text: str) -> str:
    # Remove emoji / símbolos fora do plano básico (BMP)
    text = re.sub(r'[\U00010000-\U0010FFFF]', '', text, flags=re.UNICODE)
    text = (text
        .replace('—', ',').replace('–', ',').replace('‒', ',').replace('‑', ',')  # travessões -> vírgula
        .replace('“', '"').replace('”', '"')
        .replace('‘', "'").replace('’', "'")
        .replace('…', '...').replace(' ', ' ')
        .replace('•', '-').replace('·', '-')
    )
    text = re.sub(r'[⌀-➿⬀-⯿︀-️]', '', text)
    return text.strip()


# ── Identidade fixa do perfil ───────────────────────────────────────────────
DISPLAY_NAME = "Rayssa Couto"
HANDLE = "@rayssacouto.ia"

ASSETS_DIR = Path(__file__).parent.parent / "assets"
AVATAR_PATH = ASSETS_DIR / "profile" / "avatar.jpg"
FONT_REGULAR_FALLBACK = ASSETS_DIR / "fonts" / "Inter-Regular.ttf"
FONT_BOLD_FALLBACK = ASSETS_DIR / "fonts" / "Inter-Bold.ttf"

# Ordem de preferência de fonte (Regular, Bold) — Liberation/DejaVu instalados via apt na VPS,
# com fallback pra Inter (empacotada) durante desenvolvimento local.
FONT_CANDIDATES = [
    (
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ),
    (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ),
    (
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ),
]

# ── Estilo B: fundo preto, sem destaque de cor ──────────────────────────────
BG_COLOR = (0, 0, 0)
TEXT_COLOR = (231, 233, 234)     # #E7E9EA
HANDLE_COLOR = (113, 118, 123)   # #71767B
VERIFIED_COLOR = (29, 155, 240)  # #1D9BF0

# ── Resolução (2x internamente, exporta em 1080x1350) ──────────────────────
SCALE = 2
CANVAS_W_LOGICAL, CANVAS_H_LOGICAL = 1080, 1350
W, H = CANVAS_W_LOGICAL * SCALE, CANVAS_H_LOGICAL * SCALE

MARGIN_X = 80 * SCALE
CONTENT_W = W - 2 * MARGIN_X

AVATAR_SIZE = 100 * SCALE
NAME_SIZE = 36
BADGE_SIZE = 32 * SCALE
HANDLE_SIZE = 28
TEXT_SIZE = 44
LINE_HEIGHT = 60 * SCALE
HEADER_TEXT_GAP = 32 * SCALE

IMAGE_MAX_W = 920 * SCALE
IMAGE_MAX_H = 600 * SCALE
IMAGE_RADIUS = 24 * SCALE


def _font(size_logical: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for regular_path, bold_path in FONT_CANDIDATES:
        path = bold_path if bold else regular_path
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size_logical * SCALE)
            except Exception:
                pass
    fallback = FONT_BOLD_FALLBACK if bold else FONT_REGULAR_FALLBACK
    if fallback.exists():
        return ImageFont.truetype(str(fallback), size_logical * SCALE)
    return ImageFont.load_default()


def _wrap_text(text: str, font, max_w: int, draw: ImageDraw.Draw) -> list[str]:
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        cur = ""
        for word in words:
            test = f"{cur} {word}".strip()
            if draw.textlength(test, font=font) <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
    return lines or [""]


def _draw_verified_badge(draw: ImageDraw.Draw, x: int, y: int, size: int, color):
    draw.ellipse((x, y, x + size, y + size), fill=color)
    width = max(2, size // 10)
    draw.line([(x + size * 0.25, y + size * 0.52), (x + size * 0.42, y + size * 0.70)], fill="white", width=width)
    draw.line([(x + size * 0.42, y + size * 0.70), (x + size * 0.78, y + size * 0.30)], fill="white", width=width)


def _load_avatar(size: int):
    if AVATAR_PATH.exists():
        avatar = Image.open(AVATAR_PATH).convert("RGB").resize((size, size), Image.LANCZOS)
    else:
        avatar = Image.new("RGB", (size, size), (45, 45, 50))
        draw = ImageDraw.Draw(avatar)
        f = _font(48, bold=True)
        draw.text((size / 2, size / 2), DISPLAY_NAME[:1], font=f, fill=(255, 255, 255), anchor="mm")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    return avatar, mask


def _prepare_rounded_image(path: str):
    try:
        img = Image.open(path).convert("RGB")
    except Exception as e:
        print(f"[carousel] Não foi possível abrir imagem do artigo: {e}")
        return None
    img.thumbnail((IMAGE_MAX_W, IMAGE_MAX_H), Image.LANCZOS)
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([(0, 0), img.size], radius=IMAGE_RADIUS, fill=255)
    rgba = img.convert("RGBA")
    rgba.putalpha(mask)
    return rgba


def _render_slide(text: str, avatar_img: Image.Image, avatar_mask: Image.Image, image_below=None) -> Image.Image:
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_name = _font(NAME_SIZE, bold=True)
    font_handle = _font(HANDLE_SIZE)
    font_text = _font(TEXT_SIZE)

    wrapped_lines = _wrap_text(_clean_text(text), font_text, CONTENT_W, draw)
    text_height = len(wrapped_lines) * LINE_HEIGHT

    header_height = AVATAR_SIZE
    image_block_height = (image_below.height + HEADER_TEXT_GAP) if image_below is not None else 0

    total_block_height = header_height + HEADER_TEXT_GAP + text_height + image_block_height
    start_y = (H - total_block_height) // 2

    # Avatar
    img.paste(avatar_img, (MARGIN_X, start_y), avatar_mask)

    # Nome + selo verificado
    name_x = MARGIN_X + AVATAR_SIZE + 20 * SCALE
    draw.text((name_x, start_y + 10 * SCALE), DISPLAY_NAME, font=font_name, fill=TEXT_COLOR)
    name_w = draw.textlength(DISPLAY_NAME, font=font_name)
    _draw_verified_badge(draw, int(name_x + name_w + 10 * SCALE), start_y + 18 * SCALE, BADGE_SIZE, VERIFIED_COLOR)

    # Handle
    draw.text((name_x, start_y + 50 * SCALE), HANDLE, font=font_handle, fill=HANDLE_COLOR)

    # Corpo do texto
    text_y = start_y + header_height + HEADER_TEXT_GAP
    for line in wrapped_lines:
        draw.text((MARGIN_X, text_y), line, font=font_text, fill=TEXT_COLOR)
        text_y += LINE_HEIGHT

    # Imagem de capa (só no slide 1, quando existir)
    if image_below is not None:
        img_y = text_y + HEADER_TEXT_GAP
        img_x = (W - image_below.width) // 2
        img.paste(image_below, (img_x, img_y), image_below)

    return img


def _safe_name(title: str) -> str:
    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in title[:40])
    return safe.strip().replace(" ", "_")


def render_slide_png(text: str) -> bytes:
    """Renderiza um único slide de texto (mesma identidade visual) e retorna os bytes do PNG.

    Usado pra regenerar/editar um slide isolado (ex: o CTA final) sem refazer o carrossel inteiro.
    """
    avatar_img, avatar_mask = _load_avatar(AVATAR_SIZE)
    img = _render_slide(text, avatar_img, avatar_mask)
    img = img.resize((CANVAS_W_LOGICAL, CANVAS_H_LOGICAL), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _render_slide1_video_overlay(hook_text: str) -> tuple[bytes, tuple[int, int, int, int]]:
    """Gera o PNG do slide 1 (cabeçalho + gancho) com um buraco transparente arredondado
    no lugar da imagem, pra o vídeo aparecer por trás quando composto via ffmpeg.

    Retorna (bytes_png_rgba, (box_x, box_y, box_w, box_h)) já em pixels finais (1080x1350).
    """
    avatar_img, avatar_mask = _load_avatar(AVATAR_SIZE)

    img = Image.new("RGBA", (W, H), (*BG_COLOR, 255))
    draw = ImageDraw.Draw(img)

    font_name = _font(NAME_SIZE, bold=True)
    font_handle = _font(HANDLE_SIZE)
    font_text = _font(TEXT_SIZE)

    wrapped_lines = _wrap_text(_clean_text(hook_text), font_text, CONTENT_W, draw)
    text_height = len(wrapped_lines) * LINE_HEIGHT

    header_height = AVATAR_SIZE
    box_w, box_h = IMAGE_MAX_W, IMAGE_MAX_H
    total_block_height = header_height + HEADER_TEXT_GAP + text_height + HEADER_TEXT_GAP + box_h
    start_y = (H - total_block_height) // 2

    img.paste(avatar_img, (MARGIN_X, start_y), avatar_mask)

    name_x = MARGIN_X + AVATAR_SIZE + 20 * SCALE
    draw.text((name_x, start_y + 10 * SCALE), DISPLAY_NAME, font=font_name, fill=TEXT_COLOR)
    name_w = draw.textlength(DISPLAY_NAME, font=font_name)
    _draw_verified_badge(draw, int(name_x + name_w + 10 * SCALE), start_y + 18 * SCALE, BADGE_SIZE, VERIFIED_COLOR)
    draw.text((name_x, start_y + 50 * SCALE), HANDLE, font=font_handle, fill=HANDLE_COLOR)

    text_y = start_y + header_height + HEADER_TEXT_GAP
    for line in wrapped_lines:
        draw.text((MARGIN_X, text_y), line, font=font_text, fill=TEXT_COLOR)
        text_y += LINE_HEIGHT

    box_x = (W - box_w) // 2
    box_y = text_y + HEADER_TEXT_GAP

    # Corta um buraco arredondado e transparente onde o vídeo vai aparecer
    hole_mask = Image.new("L", (box_w, box_h), 255)
    ImageDraw.Draw(hole_mask).rounded_rectangle([(0, 0), (box_w, box_h)], radius=IMAGE_RADIUS, fill=0)
    alpha = img.split()[3]
    alpha.paste(hole_mask, (box_x, box_y))
    img.putalpha(alpha)

    img = img.resize((CANVAS_W_LOGICAL, CANVAS_H_LOGICAL), Image.LANCZOS)
    ratio = CANVAS_W_LOGICAL / W
    final_box = (round(box_x * ratio), round(box_y * ratio), round(box_w * ratio), round(box_h * ratio))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), final_box


def _compose_video_slide(video_path: str, hook_text: str) -> tuple[str, str]:
    """Compõe o slide 1 como vídeo: cabeçalho + gancho fixos por cima, vídeo tocando na área
    de mídia (mesmo lugar/tamanho onde uma imagem apareceria). Retorna (caminho_mp4, erro).
    """
    try:
        overlay_bytes, (box_x, box_y, box_w, box_h) = _render_slide1_video_overlay(hook_text)

        tmp_dir = tempfile.mkdtemp(prefix="video_slide_")
        overlay_path = Path(tmp_dir) / "overlay.png"
        overlay_path.write_bytes(overlay_bytes)
        output_path = Path(tmp_dir) / "composed.mp4"

        filter_complex = (
            f"[0:v]scale={box_w}:{box_h}:force_original_aspect_ratio=increase,"
            f"crop={box_w}:{box_h},pad=1080:1350:{box_x}:{box_y}:color=black[bgvid];"
            f"[bgvid][1:v]overlay=0:0:format=auto[outv]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-loop", "1", "-i", str(overlay_path),
            "-filter_complex", filter_complex,
            "-map", "[outv]", "-map", "0:a?",
            "-c:v", "libx264", "-c:a", "aac",
            "-t", str(MAX_VIDEO_DURATION_SECONDS),
            "-shortest",
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode != 0 or not output_path.exists():
            return "", f"ffmpeg falhou ao compor o slide com vídeo: {result.stderr[-500:]}"

        return str(output_path), ""
    except Exception as e:
        return "", f"Não foi possível compor o slide com vídeo: {e}"


def generate_carousel(
    content: GeneratedContent,
    output_dir: str,
    image_map: dict[int, str] = None,
    video_path: str = None,
) -> list[str]:
    """Renderiza os slides do carrossel (estilo tweet). Retorna a lista de caminhos (PNGs e,
    se houver vídeo, um .mp4 como primeiro item).

    image_map: {numero_do_slide: caminho_da_imagem} — imagem composta abaixo do texto daquele
    slide (numeração conforme a lista original de slides, antes de qualquer vídeo consumir o
    gancho). Se None, usa o comportamento automático (imagem de content.news.image_path no
    slide 1, se existir) — mantém compatibilidade com o fluxo automático diário.

    video_path: caminho de um vídeo (.mp4) a compor no slide 1 — o cabeçalho e o texto do
    gancho ficam fixos por cima, o vídeo toca na área de mídia (mesmo lugar de uma imagem).
    O gancho não é renderizado de novo como slide de texto separado, já que fica embutido no
    vídeo.
    """
    if content.format != "carrossel" or not content.carousel_slides:
        return []

    safe = _safe_name(content.news.title)
    out_dir = Path(output_dir) / safe
    out_dir.mkdir(parents=True, exist_ok=True)

    text_slides = list(content.carousel_slides)
    slide_number_offset = 0
    paths = []

    if video_path and Path(video_path).exists():
        hook_text = text_slides.pop(0) if text_slides else ""
        composed_path, error = _compose_video_slide(video_path, hook_text)
        if error:
            print(f"[carousel] {error}")
        else:
            dest = out_dir / "slide_01.mp4"
            shutil.copy2(composed_path, dest)
            shutil.rmtree(Path(composed_path).parent, ignore_errors=True)
            paths.append(str(dest))
            slide_number_offset = 1
            print(f"[carousel] Slide 1 composto com vídeo: {dest.name}")

    if image_map is None:
        image_map = {1: content.news.image_path} if content.news.image_path else {}

    avatar_img, avatar_mask = _load_avatar(AVATAR_SIZE)

    total = len(text_slides)
    for offset, text in enumerate(text_slides):
        original_slide_number = offset + 1 + slide_number_offset
        output_num = offset + 1 + slide_number_offset

        image_path = image_map.get(original_slide_number)
        image_below = _prepare_rounded_image(image_path) if image_path and Path(image_path).exists() else None

        img = _render_slide(text, avatar_img, avatar_mask, image_below=image_below)
        img = img.resize((CANVAS_W_LOGICAL, CANVAS_H_LOGICAL), Image.LANCZOS)

        path = out_dir / f"slide_{output_num:02d}.png"
        img.save(str(path), "PNG", optimize=True)
        paths.append(str(path))
        print(f"[carousel] Slide {output_num}/{total + slide_number_offset}: {path.name}")

    return paths
