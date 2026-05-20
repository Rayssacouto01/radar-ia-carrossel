"""Gera slides de carrossel usando o template real da Rayssa como base."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .classifier import GeneratedContent

# ── Caminhos ───────────────────────────────────────────────────────────────
ASSETS_DIR = Path(__file__).parent.parent / "assets"
TEMPLATE_PATH = ASSETS_DIR / "slide_template.png"

# ── Layout do template 1080×1440 ───────────────────────────────────────────
W, H = 1080, 1440

# Área de conteúdo (zona central limpa)
CONTENT_TOP    = 420
CONTENT_BOTTOM = 1210
CONTENT_LEFT   = 80
CONTENT_RIGHT  = 1000
CONTENT_W      = CONTENT_RIGHT - CONTENT_LEFT   # 920px

# Dots de navegação
DOT_Y        = 1275
DOT_CX       = 540   # centro horizontal da imagem
DOT_SPACING  = 40
DOT_R_ACTIVE = 11
DOT_R_IDLE   = 7
DOT_R_LAST   = 5
COLOR_ACTIVE = (0, 152, 253)
COLOR_IDLE   = (219, 223, 228)

# Paleta de texto
TEXT_DARK   = (45,  45,  50)
TEXT_GRAY   = (110, 110, 120)
TEXT_ACCENT = (0,   152, 253)   # mesmo azul dos dots


# ── Fontes ─────────────────────────────────────────────────────────────────
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        [
            "/System/Library/Fonts/HelveticaNeue.ttc",
            "/Library/Fonts/Arial Bold.ttf",
            "/System/Library/Fonts/SFNSDisplay.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        if bold
        else [
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/SFNSText.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    )
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


# ── Helpers ────────────────────────────────────────────────────────────────
def _wrap(text: str, font, max_w: int, draw: ImageDraw.Draw) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for word in words:
        test = f"{cur} {word}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _draw_text_block(
    draw: ImageDraw.Draw,
    text: str,
    x: int,
    y: int,
    font,
    color,
    max_w: int,
    line_gap: int = 10,
    align: str = "left",
) -> int:
    """Desenha texto com quebra de linha. Retorna o y final."""
    lines = _wrap(text, font, max_w, draw)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        if align == "center":
            lx = x + (max_w - lw) // 2
        else:
            lx = x
        draw.text((lx, y), line, font=font, fill=color)
        y += bbox[3] - bbox[1] + line_gap
    return y


# ── Dots ───────────────────────────────────────────────────────────────────
def _draw_dots(draw: ImageDraw.Draw, slide_num: int, total: int):
    # Apaga a faixa original dos dots
    draw.rectangle([200, DOT_Y - 25, 880, DOT_Y + 25], fill=(255, 255, 255))

    offset = -(total - 1) * DOT_SPACING / 2
    for i in range(total):
        cx = int(DOT_CX + offset + i * DOT_SPACING)
        active = i == slide_num - 1
        last   = i == total - 1 and not active
        r = DOT_R_ACTIVE if active else (DOT_R_LAST if last else DOT_R_IDLE)
        c = COLOR_ACTIVE if active else COLOR_IDLE
        draw.ellipse([cx - r, DOT_Y - r, cx + r, DOT_Y + r], fill=c)


# ── Conteúdo por tipo de slide ─────────────────────────────────────────────
def _render_capa(draw: ImageDraw.Draw, slide: dict):
    emoji  = slide.get("emoji", "")
    titulo = slide.get("titulo", "")
    sub    = slide.get("subtitulo", "")

    total_h = CONTENT_BOTTOM - CONTENT_TOP
    cy = CONTENT_TOP + total_h // 4

    if emoji:
        fe = _font(96)
        draw.text((CONTENT_LEFT + CONTENT_W // 2, cy), emoji, font=fe,
                  fill=COLOR_ACTIVE, anchor="mm")
        cy += 120

    ft = _font(64, bold=True)
    cy = _draw_text_block(draw, titulo, CONTENT_LEFT, cy, ft, TEXT_DARK,
                          CONTENT_W, line_gap=14, align="center")
    cy += 20

    if sub:
        fs = _font(40)
        _draw_text_block(draw, sub, CONTENT_LEFT, cy, fs, TEXT_GRAY,
                         CONTENT_W, align="center")


def _render_content(draw: ImageDraw.Draw, slide: dict):
    emoji  = slide.get("emoji", "")
    titulo = slide.get("titulo", "")
    corpo  = slide.get("corpo", "")

    y = CONTENT_TOP + 40

    if emoji:
        fe = _font(72)
        draw.text((CONTENT_LEFT, y), emoji, font=fe, fill=COLOR_ACTIVE)
        y += 95

    # Linha decorativa
    draw.rectangle([CONTENT_LEFT, y, CONTENT_LEFT + 60, y + 6],
                   fill=COLOR_ACTIVE)
    y += 30

    ft = _font(54, bold=True)
    y = _draw_text_block(draw, titulo, CONTENT_LEFT, y, ft, TEXT_DARK,
                         CONTENT_W, line_gap=12)
    y += 30

    if corpo:
        fb = _font(40)
        _draw_text_block(draw, corpo, CONTENT_LEFT, y, fb, TEXT_GRAY,
                         CONTENT_W, line_gap=14)


def _render_aplicacao(draw: ImageDraw.Draw, slide: dict):
    emoji  = slide.get("emoji", "💰")
    titulo = slide.get("titulo", "Como usar no seu negócio")
    corpo  = slide.get("corpo", "")

    y = CONTENT_TOP + 40

    if emoji:
        fe = _font(72)
        draw.text((CONTENT_LEFT, y), emoji, font=fe, fill=COLOR_ACTIVE)
        y += 100

    # Label destaque
    fl = _font(26)
    draw.text((CONTENT_LEFT, y), "APLICAÇÃO PRÁTICA", font=fl,
              fill=COLOR_ACTIVE)
    y += 42

    ft = _font(50, bold=True)
    y = _draw_text_block(draw, titulo, CONTENT_LEFT, y, ft, TEXT_DARK,
                         CONTENT_W, line_gap=12)
    y += 24

    draw.rectangle([CONTENT_LEFT, y, CONTENT_RIGHT - 20, y + 4],
                   fill=COLOR_IDLE)
    y += 28

    if corpo:
        fb = _font(40)
        _draw_text_block(draw, corpo, CONTENT_LEFT, y, fb, TEXT_GRAY,
                         CONTENT_W, line_gap=14)


def _render_cta(draw: ImageDraw.Draw, slide: dict):
    emoji  = slide.get("emoji", "📌")
    titulo = slide.get("titulo", "Salva esse carrossel!")
    sub    = slide.get("subtitulo", "")

    total_h = CONTENT_BOTTOM - CONTENT_TOP
    cy = CONTENT_TOP + total_h // 5

    if emoji:
        fe = _font(110)
        draw.text((CONTENT_LEFT + CONTENT_W // 2, cy), emoji, font=fe,
                  fill=TEXT_DARK, anchor="mm")
        cy += 140

    ft = _font(60, bold=True)
    cy = _draw_text_block(draw, titulo, CONTENT_LEFT, cy, ft, TEXT_DARK,
                          CONTENT_W, line_gap=14, align="center")
    cy += 20

    if sub:
        fs = _font(38)
        _draw_text_block(draw, sub, CONTENT_LEFT, cy, fs, COLOR_ACTIVE,
                         CONTENT_W, align="center")


RENDERERS = {
    "capa":      _render_capa,
    "cta":       _render_cta,
    "aplicacao": _render_aplicacao,
}


# ── Gerador principal ──────────────────────────────────────────────────────
def generate_carousel(content: GeneratedContent, output_dir: str) -> list[str]:
    """Gera PNGs usando o template da Rayssa como base. Retorna lista de caminhos."""
    if content.format != "carrossel":
        return []

    if not TEMPLATE_PATH.exists():
        print(f"[carousel] Template não encontrado: {TEMPLATE_PATH}")
        return []

    template = Image.open(TEMPLATE_PATH).convert("RGB")
    slides = content.carousel_slides
    total = len(slides)

    safe = "".join(
        c if c.isalnum() or c in " -_" else "_"
        for c in content.news.title[:40]
    ).strip().replace(" ", "_")

    out_dir = Path(output_dir) / safe
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = []
    for slide in slides:
        num  = slide.get("numero", len(paths) + 1)
        tipo = slide.get("tipo", "conteudo")

        img  = template.copy()
        draw = ImageDraw.Draw(img)

        # Limpa área de conteúdo
        draw.rectangle(
            [CONTENT_LEFT - 10, CONTENT_TOP, CONTENT_RIGHT + 10, CONTENT_BOTTOM],
            fill=(255, 255, 255),
        )

        # Renderiza conteúdo do slide
        renderer = RENDERERS.get(tipo, _render_content)
        renderer(draw, slide)

        # Atualiza dots
        _draw_dots(draw, num, total)

        path = out_dir / f"slide_{num:02d}.png"
        img.save(str(path), "PNG", optimize=True)
        paths.append(str(path))
        print(f"[carousel] Slide {num}/{total}: {path.name}")

    return paths
