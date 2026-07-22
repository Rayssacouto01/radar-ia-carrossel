"""Gera carrosséis estilo tweet (X/Twitter) para Instagram, formato fixo @rayssacouto.ia."""

import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .classifier import GeneratedContent


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


def generate_carousel(content: GeneratedContent, output_dir: str) -> list[str]:
    """Renderiza os slides do carrossel (estilo tweet) como PNGs. Retorna a lista de caminhos."""
    if content.format != "carrossel" or not content.carousel_slides:
        return []

    avatar_img, avatar_mask = _load_avatar(AVATAR_SIZE)

    hook_image = None
    if content.news.image_path and Path(content.news.image_path).exists():
        hook_image = _prepare_rounded_image(content.news.image_path)

    safe = _safe_name(content.news.title)
    out_dir = Path(output_dir) / safe
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = []
    total = len(content.carousel_slides)
    for i, text in enumerate(content.carousel_slides, start=1):
        image_for_slide = hook_image if i == 1 else None
        img = _render_slide(text, avatar_img, avatar_mask, image_below=image_for_slide)
        img = img.resize((CANVAS_W_LOGICAL, CANVAS_H_LOGICAL), Image.LANCZOS)

        path = out_dir / f"slide_{i:02d}.png"
        img.save(str(path), "PNG", optimize=True)
        paths.append(str(path))
        print(f"[carousel] Slide {i}/{total}: {path.name}")

    return paths
