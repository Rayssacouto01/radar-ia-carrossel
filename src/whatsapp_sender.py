"""Envia o relatório diário via WhatsApp usando Evolution API."""

import requests
import base64
from pathlib import Path
from .classifier import GeneratedContent

CANVA_TEMPLATE_URL = "https://canva.link/fnzktb37e7v68a6"

FORMAT_LABEL = {
    "reels": "🎬 REELS",
    "carrossel": "📸 CARROSSEL",
    "post_estatico": "🖼️ POST ESTÁTICO",
}


def _format_slides(slides: list[dict]) -> str:
    parts = []
    for s in slides:
        num = s.get("numero", "")
        tipo = s.get("tipo", "conteudo").upper()
        emoji = s.get("emoji", "")
        titulo = s.get("titulo", "")
        corpo = s.get("corpo", "") or s.get("subtitulo", "")
        block = f"*SLIDE {num} — {tipo}*\n{emoji} {titulo}"
        if corpo:
            block += f"\n_{corpo}_"
        parts.append(block)
    return "\n\n".join(parts)


def _build_message(content: GeneratedContent) -> str:
    from datetime import datetime
    today = datetime.now().strftime("%d/%m/%Y")
    fmt_label = FORMAT_LABEL.get(content.format, content.format.upper())
    news = content.news

    lines = [
        f"🤖 *Radar IA — {today}*",
        "",
        f"{fmt_label} — {news.source}",
        f"*{news.title}*",
        f"🔗 {news.url}",
        "",
        f"💡 *Gancho:*\n{content.hook}",
        "",
        f"🏢 *Para o seu negócio:*\n{content.business_application}",
    ]

    if content.format == "reels" and content.reels_script:
        lines += ["", "🎬 *Roteiro para gravação:*", content.reels_script]

    elif content.format == "carrossel" and content.carousel_slides:
        lines += [
            "",
            f"📋 *Slides ({len(content.carousel_slides)}):*",
            "",
            _format_slides(content.carousel_slides),
        ]
        if content.static_caption:
            lines += ["", f"📝 *Legenda:*\n{content.static_caption}"]
        lines += ["", f"🎨 Template Canva: {CANVA_TEMPLATE_URL}"]

    elif content.format == "post_estatico":
        if content.static_caption:
            lines += ["", f"📝 *Legenda:*\n{content.static_caption}"]
        if content.static_image_concept:
            lines += ["", f"🖼️ *Conceito visual:*\n{content.static_image_concept}"]
        lines += ["", f"🎨 Template Canva: {CANVA_TEMPLATE_URL}"]

    lines += ["", "—", "_@rayssacouto.ia_"]
    return "\n".join(lines)


def _send_text(text: str, base_url: str, api_key: str, instance: str, number: str) -> bool:
    url = f"{base_url.rstrip('/')}/message/sendText/{instance}"
    payload = {"number": number, "text": text}
    headers = {"apikey": api_key, "Content-Type": "application/json"}
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    if resp.status_code in (200, 201):
        print(f"[whatsapp] Mensagem enviada para {number}")
        return True
    print(f"[whatsapp] Erro ao enviar texto: {resp.status_code} — {resp.text[:200]}")
    return False


def _send_document(file_path: str, base_url: str, api_key: str, instance: str, number: str) -> bool:
    path = Path(file_path)
    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    url = f"{base_url.rstrip('/')}/message/sendMedia/{instance}"
    payload = {
        "number": number,
        "mediatype": "document",
        "mimetype": "text/html",
        "fileName": path.name,
        "media": b64,
        "caption": f"📄 Relatório completo — {path.name}",
    }
    headers = {"apikey": api_key, "Content-Type": "application/json"}
    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    if resp.status_code in (200, 201):
        print(f"[whatsapp] Documento enviado: {path.name}")
        return True
    print(f"[whatsapp] Erro ao enviar documento: {resp.status_code} — {resp.text[:200]}")
    return False


def send_report(
    contents_with_paths: list[tuple[GeneratedContent, list[str]]],
    report_path: str,
    base_url: str,
    api_key: str,
    instance: str,
    number: str,
) -> bool:
    """Envia resumo em texto + arquivo HTML para o WhatsApp."""
    if not contents_with_paths:
        return False

    ok = True
    for content, _ in contents_with_paths:
        msg = _build_message(content)
        if not _send_text(msg, base_url, api_key, instance, number):
            ok = False

    if report_path and Path(report_path).exists():
        if not _send_document(report_path, base_url, api_key, instance, number):
            ok = False

    return ok
