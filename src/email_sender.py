"""Envia o relatório diário via Resend com carrosséis anexados."""

import os
import base64
import resend
from pathlib import Path
from datetime import datetime
from .classifier import GeneratedContent

FORMAT_LABEL = {
    "reels": "🎬 REELS",
    "carrossel": "📸 CARROSSEL",
    "post_estatico": "🖼️ POST ESTÁTICO",
}

FORMAT_COLOR = {
    "reels": "#E53E3E",
    "carrossel": "#FF5722",
    "post_estatico": "#38A169",
}


def _card_html(content: GeneratedContent, carousel_paths: list[str]) -> str:
    fmt = content.format
    label = FORMAT_LABEL.get(fmt, fmt.upper())
    color = FORMAT_COLOR.get(fmt, "#333333")
    news = content.news

    sections = []

    # Cabeçalho do card
    sections.append(f"""
    <div style="border:1px solid #E2E8F0;border-radius:12px;margin:24px 0;overflow:hidden;font-family:Arial,sans-serif;">
      <div style="background:{color};padding:14px 20px;display:flex;align-items:center;gap:12px;">
        <span style="background:rgba(255,255,255,0.2);padding:4px 12px;border-radius:20px;color:#fff;font-size:13px;font-weight:700;">{label}</span>
        <span style="color:#fff;font-size:16px;font-weight:700;">{news.source}</span>
      </div>
      <div style="padding:20px 24px;">
        <h2 style="margin:0 0 8px;font-size:20px;color:#1A1A1A;">{news.title}</h2>
        <a href="{news.url}" style="color:{color};font-size:13px;">Ver artigo original →</a>

        <div style="background:#FFF3F0;border-left:4px solid {color};padding:12px 16px;margin:16px 0;border-radius:0 8px 8px 0;">
          <p style="margin:0;font-size:15px;color:#1A1A1A;font-weight:600;">💡 Gancho: {content.hook}</p>
        </div>

        <div style="background:#F7FAFC;border-radius:8px;padding:12px 16px;margin:12px 0;">
          <p style="margin:0 0 6px;font-size:13px;font-weight:700;color:#718096;text-transform:uppercase;">Para o seu negócio</p>
          <p style="margin:0;font-size:15px;color:#2D3748;">{content.business_application}</p>
        </div>
    """)

    if fmt == "reels":
        sections.append(f"""
        <div style="background:#1A1A1A;border-radius:8px;padding:16px 20px;margin:12px 0;">
          <p style="margin:0 0 8px;font-size:13px;font-weight:700;color:#FF5722;text-transform:uppercase;">Roteiro para gravação</p>
          <pre style="margin:0;color:#E2E8F0;font-family:'Courier New',monospace;font-size:13px;white-space:pre-wrap;line-height:1.6;">{content.reels_script}</pre>
        </div>
        """)

    elif fmt == "carrossel":
        if carousel_paths:
            slides_html = ""
            for path in carousel_paths:
                try:
                    with open(path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()
                    slide_num = Path(path).stem.replace("slide_", "")
                    slides_html += f"""
                    <div style="display:inline-block;margin:4px;vertical-align:top;">
                      <img src="data:image/png;base64,{b64}"
                           style="width:160px;height:160px;border-radius:6px;object-fit:cover;"
                           alt="Slide {slide_num}" />
                      <p style="margin:4px 0 0;text-align:center;font-size:11px;color:#718096;">Slide {slide_num}</p>
                    </div>"""
            sections.append(f"""
            <p style="font-size:14px;font-weight:700;color:#1A1A1A;margin:16px 0 8px;">📷 Slides gerados ({len(carousel_paths)} imagens):</p>
            <div style="text-align:left;">{slides_html}</div>
            """)

        if content.static_caption:
            sections.append(f"""
            <div style="background:#F0FFF4;border-radius:8px;padding:12px 16px;margin:12px 0;">
              <p style="margin:0 0 6px;font-size:13px;font-weight:700;color:#276749;text-transform:uppercase;">Legenda do post</p>
              <p style="margin:0;font-size:14px;color:#2D3748;white-space:pre-wrap;">{content.static_caption}</p>
            </div>
            """)

    elif fmt == "post_estatico":
        if content.static_caption:
            sections.append(f"""
            <div style="background:#F0FFF4;border-radius:8px;padding:12px 16px;margin:12px 0;">
              <p style="margin:0 0 6px;font-size:13px;font-weight:700;color:#276749;text-transform:uppercase;">Legenda</p>
              <p style="margin:0;font-size:14px;color:#2D3748;white-space:pre-wrap;">{content.static_caption}</p>
            </div>
            """)
        if content.static_image_concept:
            sections.append(f"""
            <div style="background:#EBF8FF;border-radius:8px;padding:12px 16px;margin:12px 0;">
              <p style="margin:0 0 6px;font-size:13px;font-weight:700;color:#2C5282;text-transform:uppercase;">Conceito visual (para Canva)</p>
              <p style="margin:0;font-size:14px;color:#2D3748;">{content.static_image_concept}</p>
            </div>
            """)

    sections.append("</div></div>")
    return "".join(sections)


def _build_html(contents_with_paths: list[tuple[GeneratedContent, list[str]]]) -> str:
    today = datetime.now().strftime("%d/%m/%Y")
    total = len(contents_with_paths)
    reels_count = sum(1 for c, _ in contents_with_paths if c.format == "reels")
    carousel_count = sum(1 for c, _ in contents_with_paths if c.format == "carrossel")
    static_count = sum(1 for c, _ in contents_with_paths if c.format == "post_estatico")

    cards = "".join(_card_html(c, paths) for c, paths in contents_with_paths)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#F7F8FA;font-family:Arial,sans-serif;">
  <div style="max-width:700px;margin:0 auto;padding:20px;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#1A1A1A 0%,#2D2D2D 100%);border-radius:16px;padding:32px;margin-bottom:24px;text-align:center;">
      <p style="margin:0 0 4px;color:#FF5722;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:2px;">Radar de IA</p>
      <h1 style="margin:0 0 8px;color:#FFFFFF;font-size:28px;">Novidades de Inteligência Artificial</h1>
      <p style="margin:0;color:#A0AEC0;font-size:15px;">{today} — Curado para empreendedores</p>

      <div style="display:flex;justify-content:center;gap:16px;margin-top:20px;flex-wrap:wrap;">
        <span style="background:#E53E3E;padding:6px 16px;border-radius:20px;color:#fff;font-size:13px;">🎬 {reels_count} Reels</span>
        <span style="background:#FF5722;padding:6px 16px;border-radius:20px;color:#fff;font-size:13px;">📸 {carousel_count} Carrosséis</span>
        <span style="background:#38A169;padding:6px 16px;border-radius:20px;color:#fff;font-size:13px;">🖼️ {static_count} Posts</span>
      </div>
    </div>

    <!-- Cards de conteúdo -->
    {cards}

    <!-- Footer -->
    <div style="text-align:center;padding:24px 0;border-top:1px solid #E2E8F0;margin-top:8px;">
      <p style="margin:0 0 4px;color:#1A1A1A;font-weight:700;">@rayssacouto.ia</p>
      <p style="margin:0;color:#718096;font-size:13px;">Agente de IA para Conteúdo — Gerado automaticamente</p>
    </div>

  </div>
</body>
</html>"""


def send_daily_report(
    contents_with_paths: list[tuple[GeneratedContent, list[str]]],
    to_email: str,
    api_key: str,
) -> bool:
    if not contents_with_paths:
        print("[email] Nenhum conteúdo para enviar.")
        return False

    resend.api_key = api_key
    today = datetime.now().strftime("%d/%m/%Y")
    html = _build_html(contents_with_paths)

    # Anexos: todos os slides de carrossel
    attachments = []
    for content, paths in contents_with_paths:
        if content.format == "carrossel":
            for path in paths:
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                    attachments.append(
                        {
                            "filename": Path(path).name,
                            "content": list(data),
                        }
                    )
                except Exception as e:
                    print(f"[email] Erro ao anexar {path}: {e}")

    params: resend.Emails.SendParams = {
        "from": "Radar IA <onboarding@resend.dev>",
        "to": [to_email],
        "subject": f"🤖 Radar de IA — {today} | {len(contents_with_paths)} novidades para postar",
        "html": html,
    }
    if attachments:
        params["attachments"] = attachments

    try:
        resp = resend.Emails.send(params)
        print(f"[email] Enviado! ID: {resp.get('id', '?')}")
        return True
    except Exception as e:
        print(f"[email] Falha ao enviar: {e}")
        return False
