"""Gera slides de carrossel como imagens PNG 1080x1080 usando Pillow."""

import os
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .classifier import GeneratedContent

# Paleta
WHITE = "#FFFFFF"
BLACK = "#1A1A1A"
ACCENT = "#FF5722"
GRAY = "#555555"
LIGHT_GRAY = "#F5F5F5"
ACCENT_LIGHT = "#FFF3F0"

SIZE = (1080, 1080)
BRAND = "@rayssacouto.ia"


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates_bold = [
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/SFNSDisplay.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    candidates_regular = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/SFNSText.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    candidates = candidates_bold if bold else candidates_regular
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _draw_rounded_rect(draw: ImageDraw.Draw, xy, radius: int, fill: str):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill)


def _wrap_text(text: str, font, max_width: int, draw: ImageDraw.Draw) -> list[str]:
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _draw_cover(slide: dict, brand: str) -> Image.Image:
    img = Image.new("RGB", SIZE, WHITE)
    draw = ImageDraw.Draw(img)

    # Barra superior colorida
    draw.rectangle([0, 0, 1080, 12], fill=ACCENT)

    # Faixa de cor suave no topo
    draw.rectangle([0, 12, 1080, 350], fill=ACCENT_LIGHT)

    # Emoji grande
    emoji = slide.get("emoji", "🔥")
    font_emoji = _get_font(120, bold=False)
    draw.text((540, 180), emoji, font=font_emoji, fill=ACCENT, anchor="mm")

    # Título principal
    titulo = slide.get("titulo", "")
    font_title = _get_font(72, bold=True)
    lines = _wrap_text(titulo, font_title, 900, draw)
    y = 400
    for line in lines[:3]:
        draw.text((540, y), line, font=font_title, fill=BLACK, anchor="mm")
        y += 85

    # Subtítulo
    subtitulo = slide.get("subtitulo", "")
    if subtitulo:
        font_sub = _get_font(40)
        sub_lines = _wrap_text(subtitulo, font_sub, 860, draw)
        y += 20
        for line in sub_lines[:2]:
            draw.text((540, y), line, font=font_sub, fill=GRAY, anchor="mm")
            y += 52

    # Número do slide
    font_num = _get_font(28)
    draw.text((540, 980), "01", font=font_num, fill=ACCENT, anchor="mm")

    # Barra inferior com marca
    draw.rectangle([0, 1010, 1080, 1080], fill=BLACK)
    font_brand = _get_font(30)
    draw.text((540, 1045), brand, font=font_brand, fill=WHITE, anchor="mm")

    return img


def _draw_content(slide: dict, brand: str) -> Image.Image:
    img = Image.new("RGB", SIZE, WHITE)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, 1080, 12], fill=ACCENT)

    num = slide.get("numero", 1)
    emoji = slide.get("emoji", "")
    titulo = slide.get("titulo", "")
    corpo = slide.get("corpo", "")

    # Número do slide (canto superior direito)
    font_num = _get_font(36, bold=True)
    num_str = f"0{num}" if num < 10 else str(num)
    draw.text((1020, 60), num_str, font=font_num, fill=ACCENT, anchor="rm")

    # Emoji
    if emoji:
        font_emoji = _get_font(80)
        draw.text((90, 120), emoji, font=font_emoji, fill=ACCENT)

    # Linha decorativa
    draw.rectangle([90, 230, 140, 238], fill=ACCENT)

    # Título
    font_title = _get_font(60, bold=True)
    title_lines = _wrap_text(titulo, font_title, 900, draw)
    y = 270
    for line in title_lines[:2]:
        draw.text((90, y), line, font=font_title, fill=BLACK)
        y += 76

    # Corpo do texto
    font_body = _get_font(38)
    body_lines = _wrap_text(corpo, font_body, 900, draw)
    y = max(y + 40, 520)
    for line in body_lines[:6]:
        draw.text((90, y), line, font=font_body, fill=GRAY)
        y += 56

    # Barra inferior com marca
    draw.rectangle([0, 1010, 1080, 1080], fill=BLACK)
    font_brand = _get_font(30)
    draw.text((540, 1045), brand, font=font_brand, fill=WHITE, anchor="mm")

    return img


def _draw_application(slide: dict, brand: str) -> Image.Image:
    img = Image.new("RGB", SIZE, ACCENT_LIGHT)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, 1080, 12], fill=ACCENT)

    emoji = slide.get("emoji", "💰")
    titulo = slide.get("titulo", "Como usar no seu negócio")
    corpo = slide.get("corpo", "")

    font_emoji = _get_font(90)
    draw.text((90, 100), emoji, font=font_emoji)

    font_label = _get_font(28)
    draw.text((90, 220), "APLICAÇÃO PRÁTICA", font=font_label, fill=ACCENT)

    font_title = _get_font(60, bold=True)
    title_lines = _wrap_text(titulo, font_title, 900, draw)
    y = 270
    for line in title_lines[:2]:
        draw.text((90, y), line, font=font_title, fill=BLACK)
        y += 76

    draw.rectangle([90, y + 10, 990, y + 18], fill=ACCENT)
    y += 60

    font_body = _get_font(40)
    body_lines = _wrap_text(corpo, font_body, 900, draw)
    for line in body_lines[:6]:
        draw.text((90, y), line, font=font_body, fill=BLACK)
        y += 58

    draw.rectangle([0, 1010, 1080, 1080], fill=BLACK)
    font_brand = _get_font(30)
    draw.text((540, 1045), brand, font=font_brand, fill=WHITE, anchor="mm")

    return img


def _draw_cta(slide: dict, brand: str) -> Image.Image:
    img = Image.new("RGB", SIZE, BLACK)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, 1080, 12], fill=ACCENT)

    emoji = slide.get("emoji", "📌")
    titulo = slide.get("titulo", "Salva esse carrossel!")
    subtitulo = slide.get("subtitulo", "Siga para mais conteúdo de IA para negócios")

    font_emoji = _get_font(130)
    draw.text((540, 280), emoji, font=font_emoji, fill=WHITE, anchor="mm")

    font_title = _get_font(72, bold=True)
    title_lines = _wrap_text(titulo, font_title, 900, draw)
    y = 440
    for line in title_lines[:2]:
        draw.text((540, y), line, font=font_title, fill=WHITE, anchor="mm")
        y += 90

    font_sub = _get_font(40)
    sub_lines = _wrap_text(subtitulo, font_sub, 860, draw)
    y += 20
    for line in sub_lines[:2]:
        draw.text((540, y), line, font=font_sub, fill=ACCENT, anchor="mm")
        y += 52

    # Botão de seguir estilizado
    _draw_rounded_rect(draw, [300, 780, 780, 860], 40, ACCENT)
    font_btn = _get_font(38, bold=True)
    draw.text((540, 820), f"Seguir {brand}", font=font_btn, fill=WHITE, anchor="mm")

    return img


SLIDE_RENDERERS = {
    "capa": _draw_cover,
    "cta": _draw_cta,
    "aplicacao": _draw_application,
}


def generate_carousel(content: GeneratedContent, output_dir: str) -> list[str]:
    """Gera PNGs para cada slide do carrossel. Retorna lista de caminhos."""
    if content.format != "carrossel":
        return []

    safe_title = "".join(
        c if c.isalnum() or c in " -_" else "_" for c in content.news.title[:40]
    ).strip()
    folder = Path(output_dir) / safe_title.replace(" ", "_")
    folder.mkdir(parents=True, exist_ok=True)

    paths = []
    for slide in content.carousel_slides:
        tipo = slide.get("tipo", "conteudo")
        num = slide.get("numero", len(paths) + 1)

        renderer = SLIDE_RENDERERS.get(tipo, _draw_content)
        img = renderer(slide, BRAND)

        path = folder / f"slide_{num:02d}.png"
        img.save(str(path), "PNG", optimize=True)
        paths.append(str(path))
        print(f"[carousel] Slide {num} gerado: {path}")

    return paths
