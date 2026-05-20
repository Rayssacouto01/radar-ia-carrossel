"""Usa Claude API para classificar notícias e gerar conteúdo por formato."""

import os
import json
import anthropic
from dataclasses import dataclass, field
from typing import Literal, Optional
from .scraper import NewsItem

ContentType = Literal["reels", "carrossel", "post_estatico"]

SYSTEM_PROMPT = """Você é um professor especialista em Inteligência Artificial que ensina empreendedores e donos de negócio brasileiros a usar IA no dia a dia das suas empresas.

Seu estilo é de professor paciente e didático:
- Explica como se o aluno nunca tivesse ouvido falar do assunto
- Usa analogias do cotidiano empresarial (ex: "é como ter um funcionário que...")
- Sempre mostra O QUE É POSSÍVEL FAZER com aquela IA no negócio
- Dá exemplos práticos e concretos de setores reais (restaurante, clínica, loja, agência, academia...)
- Evita termos técnicos — quando precisar usar um, explica imediatamente
- Linguagem leve, próxima, como uma conversa entre colegas

## Regras de classificação:

**REELS** → Escolha quando a novidade:
- É um lançamento bombástico ou breaking news
- Tem potencial de viralizar (surpresa, "nossa, isso existe?!")
- Pode ser demonstrada visualmente em 60-90 segundos
- É uma ferramenta que o empreendedor pode testar hoje mesmo

**CARROSSEL** → Escolha quando a novidade:
- Pode ser ensinada em passos (ex: "5 formas de usar isso no seu negócio")
- Tem múltiplos casos de uso para setores diferentes
- É ideal para salvar e consultar depois
- Requer mais contexto para ser bem aproveitada

**POST_ESTATICO** → Escolha quando a novidade:
- É uma estatística ou dado impactante e isolado
- É uma citação/declaração marcante de um líder de IA
- É uma notícia simples mas relevante que não precisa de mais explicação

## Público-alvo:
Donos de negócio e empreendedores brasileiros — podem ser de qualquer setor. Muitos nunca usaram IA antes. Seu papel é mostrar que é simples, acessível e já está transformando empresas como a deles.

## Formato dos exemplos práticos:
Sempre que gerar conteúdo, inclua pelo menos 2 exemplos de setores diferentes, como:
- "Uma clínica pode usar isso para..."
- "Uma loja de roupas consegue..."
- "Um escritório de advocacia pode..."

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


def _process_item(item: NewsItem, client: anthropic.Anthropic) -> Optional[GeneratedContent]:
    user_message = f"""Você é um professor que vai transformar esta novidade de IA em conteúdo educativo para donos de negócio brasileiros.

**Notícia:**
Título: {item.title}
Fonte: {item.source}
Resumo: {item.summary or 'Sem resumo disponível'}
URL: {item.url}

**Sua missão:**
Explique O QUE É POSSÍVEL FAZER com essa IA no contexto de empresas reais. Use linguagem de professor:
simples, com exemplos do cotidiano, sem jargão técnico. Sempre dê exemplos concretos de setores
diferentes (clínica, loja, restaurante, agência, escritório...).

Responda APENAS com um JSON válido seguindo exatamente este schema:

{{
  "format": "reels" | "carrossel" | "post_estatico",
  "hook": "pergunta ou frase de impacto que faça o dono de negócio parar o scroll (máx 15 palavras)",
  "business_application": "Explique como donos de negócio podem usar isso HOJE. Tom de professor. Cite 2 exemplos de setores diferentes com frases como 'Uma clínica pode...' e 'Uma loja de roupas consegue...'. Máx 3 frases.",

  // Se format == "reels":
  "reels_script": {{
    "duracao_sugerida": "60s | 90s",
    "hook_visual": "o que mostrar nos primeiros 3 segundos — algo que gere curiosidade imediata",
    "roteiro": [
      {{"tempo": "0-5s", "fala": "gancho — pergunta ou afirmação surpreendente", "acao": "o que fazer/mostrar na tela"}},
      {{"tempo": "5-20s", "fala": "explique O QUE É de forma simples, como um professor. Use analogia do dia a dia.", "acao": "..."}},
      {{"tempo": "20-45s", "fala": "dê 2 exemplos práticos de negócios reais usando isso. Fale como se estivesse ensinando um aluno.", "acao": "..."}},
      {{"tempo": "45-60s", "fala": "mostre como começar hoje — passo simples e acessível", "acao": "..."}},
      {{"tempo": "60-75s", "fala": "CTA: salva, segue, comenta o setor do negócio", "acao": "..."}}
    ],
    "legenda_instagram": "caption completa com emojis, linguagem educativa e hashtags relevantes"
  }},

  // Se format == "carrossel":
  "carousel_slides": [
    {{"numero": 1, "tipo": "capa", "titulo": "título que gera curiosidade ou faz uma pergunta ao dono de negócio", "subtitulo": "subtítulo explicando o benefício em linguagem simples", "emoji": "🔥"}},
    {{"numero": 2, "tipo": "conteudo", "titulo": "O que é isso? (explicação simples)", "corpo": "explique como se fosse para um aluno — sem jargão. Use analogia se possível. Máx 120 chars.", "emoji": "💡"}},
    {{"numero": 3, "tipo": "conteudo", "titulo": "Exemplo 1: [nome do setor]", "corpo": "Como uma [tipo de empresa] usa isso hoje. Frase curta e concreta. Máx 120 chars.", "emoji": "🏪"}},
    {{"numero": 4, "tipo": "conteudo", "titulo": "Exemplo 2: [nome do setor]", "corpo": "Como uma [tipo de empresa diferente] usa isso hoje. Frase curta e concreta. Máx 120 chars.", "emoji": "🏥"}},
    {{"numero": 5, "tipo": "aplicacao", "titulo": "Como começar no seu negócio?", "corpo": "Passo simples e prático para testar isso hoje. Acessível para qualquer empreendedor. Máx 120 chars.", "emoji": "🚀"}},
    {{"numero": 6, "tipo": "cta", "titulo": "Salva esse carrossel!", "subtitulo": "Siga @rayssacouto.ia para aprender IA aplicada nos negócios", "emoji": "📌"}}
  ],
  "legenda_carrossel": "caption educativa com emojis — começe com uma pergunta para o leitor, explique o benefício, CTA para salvar e comentar",

  // Se format == "post_estatico":
  "static_caption": "caption educativa: explique a notícia de forma simples, dê 1 exemplo prático para empresas, CTA para comentar. Use emojis e hashtags.",
  "static_image_concept": "descreva o visual ideal para este post estático (cores, texto em destaque, elementos visuais) — para replicar no Canva"
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
