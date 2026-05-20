"""Salva o relatório diário em HTML organizado por data, com link do template Canva."""

from pathlib import Path
from datetime import datetime
from .classifier import GeneratedContent

CANVA_TEMPLATE_URL = "https://canva.link/fnzktb37e7v68a6"

FORMAT_EMOJI = {"reels": "🎬", "carrossel": "📸", "post_estatico": "🖼️"}
FORMAT_LABEL = {"reels": "REELS", "carrossel": "CARROSSEL", "post_estatico": "POST ESTÁTICO"}
FORMAT_COLOR = {"reels": "#E53E3E", "carrossel": "#FF5722", "post_estatico": "#38A169"}


def _slides_html(slides: list[dict]) -> str:
    """Renderiza os slides do carrossel como blocos de copy-paste."""
    parts = []
    for slide in slides:
        num = slide.get("numero", "")
        tipo = slide.get("tipo", "conteudo")
        emoji = slide.get("emoji", "")
        titulo = slide.get("titulo", "")
        corpo = slide.get("corpo", "")
        subtitulo = slide.get("subtitulo", "")

        bg = {
            "capa": "#FFF3F0",
            "cta": "#1A1A1A",
            "aplicacao": "#FFF8F0",
        }.get(tipo, "#F7FAFC")

        title_color = "#FFFFFF" if tipo == "cta" else "#1A1A1A"
        body_color = "#FF5722" if tipo == "cta" else "#555555"

        texto_principal = titulo
        texto_secundario = corpo or subtitulo

        parts.append(f"""
        <div style="border:1px solid #E2E8F0;border-radius:10px;padding:16px 20px;margin:10px 0;background:{bg};">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
            <span style="background:#FF5722;color:#fff;font-size:11px;font-weight:700;padding:3px 10px;border-radius:12px;">SLIDE {num}</span>
            <span style="font-size:13px;color:#718096;text-transform:uppercase;letter-spacing:1px;">{tipo}</span>
          </div>
          <div style="margin-bottom:8px;">
            <div style="font-size:11px;font-weight:700;color:#999;text-transform:uppercase;margin-bottom:4px;">Título / Texto principal</div>
            <div style="background:#fff;border:1px dashed #FF5722;border-radius:6px;padding:10px 14px;font-size:15px;font-weight:700;color:{title_color if tipo != 'cta' else '#1A1A1A'};cursor:text;">{emoji} {texto_principal}</div>
          </div>
          {"" if not texto_secundario else f'''
          <div>
            <div style="font-size:11px;font-weight:700;color:#999;text-transform:uppercase;margin-bottom:4px;">Corpo / Subtítulo</div>
            <div style="background:#fff;border:1px dashed #CBD5E0;border-radius:6px;padding:10px 14px;font-size:14px;color:{body_color};">{texto_secundario}</div>
          </div>'''}
        </div>""")
    return "".join(parts)


def _card_html(content: GeneratedContent, carousel_paths: list[str] = None) -> str:
    fmt = content.format
    emoji = FORMAT_EMOJI.get(fmt, "")
    label = FORMAT_LABEL.get(fmt, fmt.upper())
    color = FORMAT_COLOR.get(fmt, "#333")
    news = content.news

    parts = [f"""
    <div style="border:1px solid #E2E8F0;border-radius:12px;margin:24px 0;overflow:hidden;font-family:Arial,sans-serif;">
      <div style="background:{color};padding:14px 20px;font-weight:700;color:#fff;">{emoji} {label} — {news.source}</div>
      <div style="padding:20px 24px;">
        <h2 style="margin:0 0 6px;font-size:20px;color:#1A1A1A;">{news.title}</h2>
        <a href="{news.url}" target="_blank" style="color:{color};font-size:13px;text-decoration:none;">Ver artigo original →</a>

        <div style="background:#FFF3F0;border-left:4px solid #FF5722;padding:12px 16px;margin:16px 0;border-radius:0 8px 8px 0;">
          <strong>💡 Gancho:</strong> {content.hook}
        </div>

        <div style="background:#F7FAFC;border-radius:8px;padding:12px 16px;margin:12px 0;">
          <div style="font-size:11px;font-weight:700;color:#718096;text-transform:uppercase;margin-bottom:6px;">Para o seu negócio</div>
          <div style="font-size:15px;color:#2D3748;">{content.business_application}</div>
        </div>
    """]

    # --- REELS ---
    if fmt == "reels":
        parts.append(f"""
        <div style="margin-top:16px;">
          <div style="font-size:11px;font-weight:700;color:#718096;text-transform:uppercase;margin-bottom:8px;">Roteiro para gravação</div>
          <div style="background:#1A1A1A;color:#E2E8F0;border-radius:8px;padding:16px 20px;font-family:'Courier New',monospace;font-size:13px;white-space:pre-wrap;line-height:1.7;">{content.reels_script}</div>
        </div>""")

    # --- CARROSSEL ---
    elif fmt == "carrossel":
        slides = content.carousel_slides
        caption = content.static_caption
        paths = carousel_paths or []

        # Slides gerados como PNG
        if paths:
            import base64
            slide_imgs = ""
            for i, p in enumerate(paths):
                try:
                    with open(p, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()
                    slide_imgs += (
                        f'<div style="display:inline-block;margin:4px;vertical-align:top;text-align:center;">'
                        f'<img src="data:image/png;base64,{b64}" '
                        f'style="width:180px;height:240px;border-radius:8px;object-fit:cover;box-shadow:0 2px 8px rgba(0,0,0,0.12);" '
                        f'alt="Slide {i+1}"/>'
                        f'<p style="margin:4px 0 0;font-size:11px;color:#718096;">Slide {i+1}</p>'
                        f'</div>'
                    )
                except Exception:
                    pass

            parts.append(f"""
        <div style="margin-top:20px;">
          <div style="font-size:11px;font-weight:700;color:#718096;text-transform:uppercase;margin-bottom:10px;">
            Slides gerados ({len(paths)}) — prontos para postar
          </div>
          <div style="overflow-x:auto;white-space:nowrap;padding-bottom:8px;">{slide_imgs}</div>
        </div>"""
            )
        else:
            # Fallback: texto dos slides para copy-paste
            parts.append(f"""
        <div style="margin-top:20px;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;flex-wrap:wrap;gap:10px;">
            <div style="font-size:11px;font-weight:700;color:#718096;text-transform:uppercase;">Slides ({len(slides)})</div>
            <a href="{CANVA_TEMPLATE_URL}" target="_blank"
               style="background:#7B2EE0;color:#fff;text-decoration:none;padding:10px 20px;border-radius:8px;font-size:14px;font-weight:700;display:inline-block;">
              🎨 Abrir template no Canva
            </a>
          </div>
          {_slides_html(slides)}
        </div>"""
            )

        if caption:
            parts.append(f"""
        <div style="margin-top:16px;">
          <div style="font-size:11px;font-weight:700;color:#718096;text-transform:uppercase;margin-bottom:6px;">Legenda do post</div>
          <div style="background:#F0FFF4;border-radius:8px;padding:14px 16px;font-size:14px;white-space:pre-wrap;color:#2D3748;">{caption}</div>
        </div>""")

    # --- POST ESTÁTICO ---
    elif fmt == "post_estatico":
        if content.static_caption:
            parts.append(f"""
        <div style="margin-top:16px;">
          <div style="font-size:11px;font-weight:700;color:#718096;text-transform:uppercase;margin-bottom:6px;">Legenda</div>
          <div style="background:#F0FFF4;border-radius:8px;padding:14px 16px;font-size:14px;white-space:pre-wrap;color:#2D3748;">{content.static_caption}</div>
        </div>""")

        if content.static_image_concept:
            parts.append(f"""
        <div style="margin-top:12px;">
          <div style="font-size:11px;font-weight:700;color:#718096;text-transform:uppercase;margin-bottom:6px;">Conceito visual (para criar no Canva)</div>
          <div style="background:#EBF8FF;border-radius:8px;padding:14px 16px;font-size:14px;color:#2D3748;">
            <a href="{CANVA_TEMPLATE_URL}" target="_blank"
               style="background:#7B2EE0;color:#fff;text-decoration:none;padding:8px 16px;border-radius:6px;font-size:13px;font-weight:700;display:inline-block;margin-bottom:10px;">
              🎨 Abrir Canva
            </a><br>
            {content.static_image_concept}
          </div>
        </div>""")

    parts.append("</div></div>")
    return "".join(parts)


def _build_html(contents_with_paths: list[tuple[GeneratedContent, list[str]]]) -> str:
    today = datetime.now().strftime("%d/%m/%Y")
    reels_count    = sum(1 for c, _ in contents_with_paths if c.format == "reels")
    carousel_count = sum(1 for c, _ in contents_with_paths if c.format == "carrossel")
    static_count   = sum(1 for c, _ in contents_with_paths if c.format == "post_estatico")
    cards = "".join(_card_html(c, paths) for c, paths in contents_with_paths)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Radar IA — {today}</title>
</head>
<body style="margin:0;padding:20px;background:#F7F8FA;font-family:Arial,sans-serif;">
  <div style="max-width:800px;margin:0 auto;">

    <div style="background:linear-gradient(135deg,#1A1A1A,#2D2D2D);border-radius:16px;padding:32px;margin-bottom:24px;text-align:center;color:#fff;">
      <p style="margin:0 0 4px;color:#FF5722;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:2px;">Radar de IA</p>
      <h1 style="margin:0 0 8px;font-size:28px;">Novidades de Inteligência Artificial</h1>
      <p style="margin:0;color:#A0AEC0;">{today} — curado para empreendedores</p>
      <div style="display:flex;justify-content:center;gap:12px;margin-top:16px;flex-wrap:wrap;">
        <span style="background:#E53E3E;padding:6px 16px;border-radius:20px;font-size:13px;font-weight:700;">🎬 {reels_count} Reels</span>
        <span style="background:#FF5722;padding:6px 16px;border-radius:20px;font-size:13px;font-weight:700;">📸 {carousel_count} Carrosséis</span>
        <span style="background:#38A169;padding:6px 16px;border-radius:20px;font-size:13px;font-weight:700;">🖼️ {static_count} Posts</span>
      </div>
    </div>

    {cards}

    <div style="text-align:center;padding:24px 0;border-top:1px solid #E2E8F0;margin-top:8px;color:#718096;font-size:13px;">
      <strong style="color:#1A1A1A;">@rayssacouto.ia</strong><br>
      Gerado automaticamente pelo Agente de IA para Conteúdo
    </div>
  </div>
</body>
</html>"""


def save_report(
    contents_with_paths: list[tuple[GeneratedContent, list[str]]],
    output_dir: str,
) -> str:
    """Salva o relatório HTML na pasta output/YYYY-MM-DD/. Retorna o caminho do arquivo."""
    if not contents_with_paths:
        print("[report] Nenhum conteúdo para salvar.")
        return ""

    date_str = datetime.now().strftime("%Y-%m-%d")
    report_dir = Path(output_dir) / date_str
    report_dir.mkdir(parents=True, exist_ok=True)

    # Copia slides para a pasta do relatório
    import shutil
    updated = []
    for content, paths in contents_with_paths:
        new_paths = []
        for src in paths:
            dst = report_dir / Path(src).name
            shutil.copy2(src, dst)
            new_paths.append(str(dst))
        updated.append((content, new_paths))

    html = _build_html(updated)
    html_path = report_dir / f"radar-ia-{date_str}.html"
    html_path.write_text(html, encoding="utf-8")

    print(f"[report] Relatório salvo em: {html_path}")
    return str(html_path)
