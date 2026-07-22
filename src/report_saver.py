"""Salva o relatório diário em HTML organizado por data."""

from pathlib import Path
from datetime import datetime
from .classifier import GeneratedContent

FORMAT_EMOJI = {"roteiro": "🎬", "carrossel": "📸"}
FORMAT_LABEL = {"roteiro": "ROTEIRO", "carrossel": "CARROSSEL"}
FORMAT_COLOR = {"roteiro": "#E53E3E", "carrossel": "#FF5722"}


def _roteiro_text(content: GeneratedContent) -> str:
    lines = [
        f"⏱ Duração: {content.roteiro_duracao}",
        "",
        f"[GANCHO]\n{content.roteiro_gancho}",
        "",
        f"[DESENVOLVIMENTO]\n{content.roteiro_desenvolvimento}",
        "",
        f"[CTA]\n{content.roteiro_cta}",
    ]
    if content.roteiro_notas_gravacao:
        lines += ["", f"Notas de gravação: {content.roteiro_notas_gravacao}"]
    return "\n".join(lines)


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
    """]

    # --- ROTEIRO ---
    if fmt == "roteiro":
        parts.append(f"""
        <div style="margin-top:16px;">
          <div style="font-size:11px;font-weight:700;color:#718096;text-transform:uppercase;margin-bottom:8px;">Roteiro para gravação</div>
          <div style="background:#1A1A1A;color:#E2E8F0;border-radius:8px;padding:16px 20px;font-family:'Courier New',monospace;font-size:13px;white-space:pre-wrap;line-height:1.7;">{_roteiro_text(content)}</div>
        </div>""")

    # --- CARROSSEL ---
    elif fmt == "carrossel":
        paths = carousel_paths or []

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
                        f'style="width:180px;height:225px;border-radius:8px;object-fit:cover;box-shadow:0 2px 8px rgba(0,0,0,0.12);" '
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

        if content.carousel_caption:
            parts.append(f"""
        <div style="margin-top:16px;">
          <div style="font-size:11px;font-weight:700;color:#718096;text-transform:uppercase;margin-bottom:6px;">Legenda do post</div>
          <div style="background:#F0FFF4;border-radius:8px;padding:14px 16px;font-size:14px;white-space:pre-wrap;color:#2D3748;">{content.carousel_caption}</div>
        </div>""")

    parts.append("</div></div>")
    return "".join(parts)


def _build_html(contents_with_paths: list[tuple[GeneratedContent, list[str]]]) -> str:
    today = datetime.now().strftime("%d/%m/%Y")
    roteiro_count  = sum(1 for c, _ in contents_with_paths if c.format == "roteiro")
    carousel_count = sum(1 for c, _ in contents_with_paths if c.format == "carrossel")
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
        <span style="background:#E53E3E;padding:6px 16px;border-radius:20px;font-size:13px;font-weight:700;">🎬 {roteiro_count} Roteiros</span>
        <span style="background:#FF5722;padding:6px 16px;border-radius:20px;font-size:13px;font-weight:700;">📸 {carousel_count} Carrosséis</span>
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
