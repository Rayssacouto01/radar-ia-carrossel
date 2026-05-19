"""Usa Claude API para classificar notícias e gerar conteúdo por formato."""

import os
import json
import anthropic
from dataclasses import dataclass, field
from typing import Literal
from .scraper import NewsItem

ContentType = Literal["reels", "carrossel", "post_estatico"]

SYSTEM_PROMPT = """Você é um estrategista de conteúdo especializado em IA para redes sociais, com foco em empreendedores e donos de negócio brasileiros.

Seu trabalho é analisar novidades de inteligência artificial e:
1. Classificar o formato ideal de conteúdo
2. Gerar o conteúdo completo pronto para usar

## Regras de classificação:

**REELS** → Escolha quando a novidade:
- É um lançamento bombástico ou breaking news
- Tem potencial de viralizar (reação emocional, surpresa, polêmica)
- Pode ser explicada com demo ou exemplo visual em 60-90 segundos
- É uma ferramenta nova que o empreendedor pode testar hoje

**CARROSSEL** → Escolha quando a novidade:
- É um conceito, guia passo-a-passo ou comparação
- Tem múltiplos casos de uso para diferentes tipos de negócio
- Requer mais contexto para ser aproveitada
- É ideal para salvar e consultar depois

**POST_ESTATICO** → Escolha quando a novidade:
- É uma estatística ou dado isolado impactante
- É uma citação/declaração de um CEO importante
- É simples demais para carrossel mas relevante para o nicho

## Público-alvo:
Empreendedores e donos de negócio brasileiros que querem usar IA para automatizar, escalar e competir melhor. Tom: direto, prático, sem jargão técnico desnecessário.

## Idioma: SEMPRE em português do Brasil."""


@dataclass
class GeneratedContent:
    news: NewsItem
    format: ContentType
    reels_script: str = ""
    carousel_slides: list[dict] = field(default_factory=list)
    static_caption: str = ""
    static_image_concept: str = ""
    hook: str = ""
    business_application: str = ""


def classify_and_generate(
    news_items: list[NewsItem], client: anthropic.Anthropic
) -> list[GeneratedContent]:
    results = []
    for item in news_items:
        content = _process_item(item, client)
        if content:
            results.append(content)
    return results


def _process_item(item: NewsItem, client: anthropic.Anthropic) -> GeneratedContent | None:
    user_message = f"""Analise esta notícia de IA e gere o conteúdo completo:

**Título:** {item.title}
**Fonte:** {item.source}
**Resumo:** {item.summary or 'Sem resumo disponível'}
**URL:** {item.url}

Responda APENAS com um JSON válido seguindo exatamente este schema:

{{
  "format": "reels" | "carrossel" | "post_estatico",
  "hook": "frase de gancho poderosa (máximo 15 palavras) para usar em qualquer formato",
  "business_application": "1 parágrafo explicando como empreendedores podem aplicar isso agora nos negócios",

  // Se format == "reels":
  "reels_script": {{
    "duracao_sugerida": "60s | 90s",
    "hook_visual": "o que mostrar nos primeiros 3 segundos na tela",
    "roteiro": [
      {{"tempo": "0-5s", "fala": "...", "acao": "o que fazer/mostrar"}},
      {{"tempo": "5-20s", "fala": "...", "acao": "..."}},
      {{"tempo": "20-40s", "fala": "...", "acao": "..."}},
      {{"tempo": "40-60s", "fala": "...", "acao": "..."}},
      {{"tempo": "60-70s", "fala": "CTA final", "acao": "..."}}
    ],
    "legenda_instagram": "caption completa com emojis e hashtags"
  }},

  // Se format == "carrossel":
  "carousel_slides": [
    {{"numero": 1, "tipo": "capa", "titulo": "...", "subtitulo": "...", "emoji": "🔥"}},
    {{"numero": 2, "tipo": "conteudo", "titulo": "...", "corpo": "texto do slide (max 120 chars)", "emoji": "💡"}},
    {{"numero": 3, "tipo": "conteudo", "titulo": "...", "corpo": "...", "emoji": "⚡"}},
    {{"numero": 4, "tipo": "conteudo", "titulo": "...", "corpo": "...", "emoji": "🚀"}},
    {{"numero": 5, "tipo": "aplicacao", "titulo": "Como usar no seu negócio", "corpo": "...", "emoji": "💰"}},
    {{"numero": 6, "tipo": "cta", "titulo": "Salva esse carrossel!", "subtitulo": "Siga para mais conteúdo de IA para negócios", "emoji": "📌"}}
  ],
  "legenda_carrossel": "caption para o post do carrossel com emojis e hashtags",

  // Se format == "post_estatico":
  "static_caption": "caption completa com emojis e hashtags",
  "static_image_concept": "descrição visual de como a imagem deve ser criada (para replicar no Canva)"
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text.strip()

        # Remove markdown code fences se presentes
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip().rstrip("```").strip()

        data = json.loads(raw)
        fmt: ContentType = data.get("format", "post_estatico")

        result = GeneratedContent(
            news=item,
            format=fmt,
            hook=data.get("hook", ""),
            business_application=data.get("business_application", ""),
        )

        if fmt == "reels":
            script = data.get("reels_script", {})
            result.reels_script = _format_reels_script(script, item.title)
        elif fmt == "carrossel":
            result.carousel_slides = data.get("carousel_slides", [])
            result.static_caption = data.get("legenda_carrossel", "")
        elif fmt == "post_estatico":
            result.static_caption = data.get("static_caption", "")
            result.static_image_concept = data.get("static_image_concept", "")

        return result

    except json.JSONDecodeError as e:
        print(f"[classifier] JSON inválido para '{item.title}': {e}")
        return None
    except anthropic.APIError as e:
        print(f"[classifier] Erro de API para '{item.title}': {e}")
        return None


def _format_reels_script(script: dict, title: str) -> str:
    lines = [
        f"🎬 ROTEIRO REELS — {title}",
        f"⏱ Duração sugerida: {script.get('duracao_sugerida', '60-90s')}",
        f"📽 Hook visual (primeiros 3s): {script.get('hook_visual', '')}",
        "",
        "--- ROTEIRO ---",
    ]
    for step in script.get("roteiro", []):
        lines.append(f"\n[{step.get('tempo', '')}]")
        lines.append(f"🗣 FALA: {step.get('fala', '')}")
        lines.append(f"📹 AÇÃO: {step.get('acao', '')}")

    caption = script.get("legenda_instagram", "")
    if caption:
        lines += ["", "--- LEGENDA INSTAGRAM ---", caption]

    return "\n".join(lines)
