"""Salva o relatório diário e os slides em pasta local organizada por data."""

import os
from pathlib import Path
from datetime import datetime
from .classifier import GeneratedContent

FORMAT_LABEL = {
    "reels": "REELS",
    "carrossel": "CARROSSEL",
    "post_estatico": "POST ESTÁTICO",
}

FORMAT_EMOJI = {
    "reels": "🎬",
    "carrossel": "📸",
    "post_estatico": "🖼️",
}


def _build_html(contents_with_paths: list[tuple[GeneratedContent, list[str]]]) -> str:
    today = datetime.now().strftime("%d/%m/%Y")
    total = len(contents_with_paths)
    reels_count = sum(1 for c, _ in contents_with_paths if c.format == "reels")
    carousel_count = sum(1 for c, _ in contents_with_paths if c.format == "carrossel")
    static_count = sum(1 for c, _ in contents_with_paths if c.format == "post_estatico")

    cards = "".join(_card_html(c, paths) for c, paths in contents_with_paths)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Radar IA — {today}</title>
  <style>
    body {{ margin:0; padding:20px; background:#F7F8FA; font-family:Arial,sans-serif; }}
    .container {{ max-width:800px; margin:0 auto; }}
    .header {{ background:linear-gradient(135deg,#1A1A1A,#2D2D2D); border-radius:16px; padding:32px; margin-bottom:24px; text-align:center; color:#fff; }}
    .header h1 {{ margin:0 0 8px; font-size:28px; }}
    .header p {{ margin:0; color:#A0AEC0; }}
    .badges {{ display:flex; justify-content:center; gap:12px; margin-top:16px; flex-wrap:wrap; }}
    .badge {{ padding:6px 16px; border-radius:20px; font-size:13px; font-weight:700; color:#fff; }}
    .card {{ border:1px solid #E2E8F0; border-radius:12px; margin:24px 0; overflow:hidden; }}
    .card-header {{ padding:14px 20px; color:#fff; font-weight:700; }}
    .card-body {{ padding:20px 24px; }}
    .card-body h2 {{ margin:0 0 6px; font-size:20px; color:#1A1A1A; }}
    .card-body a {{ color:#FF5722; font-size:13px; text-decoration:none; }}
    .hook {{ background:#FFF3F0; border-left:4px solid #FF5722; padding:12px 16px; margin:16px 0; border-radius:0 8px 8px 0; }}
    .biz {{ background:#F7FAFC; border-radius:8px; padding:12px 16px; margin:12px 0; }}
    .label {{ font-size:12px; font-weight:700; text-transform:uppercase; color:#718096; margin-bottom:6px; }}
    .script {{ background:#1A1A1A; color:#E2E8F0; border-radius:8px; padding:16px; font-family:'Courier New',monospace; font-size:13px; white-space:pre-wrap; line-height:1.6; }}
    .caption {{ background:#F0FFF4; border-radius:8px; padding:12px 16px; font-size:14px; white-space:pre-wrap; }}
    .concept {{ background:#EBF8FF; border-radius:8px; padding:12px 16px; font-size:14px; }}
    .slides-grid {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; }}
    .slides-grid img {{ width:150px; height:150px; border-radius:6px; object-fit:cover; }}
    .footer {{ text-align:center; padding:24px 0; border-top:1px solid #E2E8F0; margin-top:8px; color:#718096; font-size:13px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <p style="color:#FF5722;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:2px;margin-bottom:4px;">Radar de IA</p>
      <h1>Novidades de Inteligência Artificial</h1>
      <p>{today} — {total} novidades para empreendedores</p>
      <div class="badges">
        <span class="badge" style="background:#E53E3E;">🎬 {reels_count} Reels</span>
        <span class="badge" style="background:#FF5722;">📸 {carousel_count} Carrosséis</span>
        <span class="badge" style="background:#38A169;">🖼️ {static_count} Posts</span>
      </div>
    </div>
    {cards}
    <div class="footer">
      <strong>@rayssacouto.ia</strong><br>
      Gerado automaticamente pelo Agente de IA para Conteúdo
    </div>
  </div>
</body>
</html>"""


def _card_html(content: GeneratedContent, carousel_paths: list[str]) -> str:
    fmt = content.format
    emoji = FORMAT_EMOJI.get(fmt, "")
    label = FORMAT_LABEL.get(fmt, fmt.upper())
    color = {"reels": "#E53E3E", "carrossel": "#FF5722", "post_estatico": "#38A169"}.get(fmt, "#333")
    news = content.news

    parts = [f"""
    <div class="card">
      <div class="card-header" style="background:{color};">{emoji} {label} — {news.source}</div>
      <div class="card-body">
        <h2>{news.title}</h2>
        <a href="{news.url}" target="_blank">Ver artigo original →</a>
        <div class="hook"><strong>💡 Gancho:</strong> {content.hook}</div>
        <div class="biz"><div class="label">Para o seu negócio</div>{content.business_application}</div>
    """]

    if fmt == "reels":
        parts.append(f'<div class="label" style="margin-top:16px;">Roteiro para gravação</div><div class="script">{content.reels_script}</div>')

    elif fmt == "carrossel":
        if carousel_paths:
            slides_html = "".join(
                f'<div style="text-align:center"><img src="{Path(p).name}" alt="Slide {i+1}"/><br><small>Slide {i+1}</small></div>'
                for i, p in enumerate(carousel_paths)
            )
            parts.append(f'<div class="label" style="margin-top:16px;">Slides ({len(carousel_paths)} imagens)</div><div class="slides-grid">{slides_html}</div>')
        if content.static_caption:
            parts.append(f'<div class="label" style="margin-top:12px;">Legenda</div><div class="caption">{content.static_caption}</div>')

    elif fmt == "post_estatico":
        if content.static_caption:
            parts.append(f'<div class="label" style="margin-top:16px;">Legenda</div><div class="caption">{content.static_caption}</div>')
        if content.static_image_concept:
            parts.append(f'<div class="label" style="margin-top:12px;">Conceito visual (Canva)</div><div class="concept">{content.static_image_concept}</div>')

    parts.append("</div></div>")
    return "".join(parts)


def save_report(
    contents_with_paths: list[tuple[GeneratedContent, list[str]]],
    output_dir: str,
) -> str:
    """Salva HTML do relatório e copia slides para a pasta de saída. Retorna o caminho do HTML."""
    if not contents_with_paths:
        print("[report] Nenhum conteúdo para salvar.")
        return ""

    date_str = datetime.now().strftime("%Y-%m-%d")
    report_dir = Path(output_dir) / date_str
    report_dir.mkdir(parents=True, exist_ok=True)

    # Copia slides para a pasta do relatório
    import shutil
    for content, paths in contents_with_paths:
        if content.format == "carrossel" and paths:
            safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in content.news.title[:30]).strip().replace(" ", "_")
            slide_dir = report_dir / safe
            slide_dir.mkdir(exist_ok=True)
            for src in paths:
                dst = slide_dir / Path(src).name
                shutil.copy2(src, dst)

    # Gera HTML do relatório
    html = _build_html(contents_with_paths)
    html_path = report_dir / f"radar-ia-{date_str}.html"
    html_path.write_text(html, encoding="utf-8")

    print(f"[report] Relatório salvo em: {html_path}")
    return str(html_path)
