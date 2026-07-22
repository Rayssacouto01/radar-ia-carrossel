"""Usa Claude API para classificar notícias e gerar conteúdo fixo (roteiro ou carrossel)."""

import json
import random
from dataclasses import dataclass, field
from typing import Literal, Optional
from urllib.parse import urlparse

import anthropic

from .scraper import NewsItem, fetch_article_image, fetch_article_text, fetch_article_title

ContentType = Literal["roteiro", "carrossel"]

MODEL = "claude-sonnet-4-6"

# ── CTAs fixos aprovados para o carrossel (sorteados em código, nunca gerados pelo modelo) ──
CTA_OPTIONS = [
    "Segue @rayssacouto.ia para saber mais sobre IA aplicada aos negocios",
    "Segue @rayssacouto.ia e aprenda sobre ia todo dia",
    "Segue @rayssacouto.ia e transforma seu negocio com IA, um post por dia.",
    "Comenta APRENDER que eu te ensino a aplicar isso no seu negocio.",
]

CLASSIFY_SYSTEM_PROMPT = """Você decide se uma notícia de IA deve virar um ROTEIRO de vídeo curto ou um CARROSSEL de slides para Instagram.

ROTEIRO → a notícia é um lançamento pontual e direto, que dá para explicar falando em frente à câmera em 60 segundos.
CARROSSEL → a notícia comporta uma explicação em vários passos ou ideias, melhor lida em slides do que ouvida.

Responda APENAS com um JSON válido: {"format": "roteiro" | "carrossel"}"""


ROTEIRO_SYSTEM_PROMPT = """Você é o agente de roteiro. Dado um tema, entrega um roteiro completo pronto para gravar.

Regras absolutas:
- Responda sempre em português do Brasil.
- O roteiro deve ser falado naturalmente, não lido como texto formal.
- Estrutura obrigatória: gancho → desenvolvimento → CTA.
- O gancho é a primeira frase. Sem introdução.
- Nunca comece com "Hoje vou falar sobre..." ou frases parecidas.
- Duração fixa: 60 segundos, aproximadamente 150 palavras no total (gancho + desenvolvimento + cta).
- Tom: direto, confiante, sem enrolação.

Responda APENAS com um JSON válido seguindo este schema:
{
  "gancho": "a primeira frase do roteiro, direto ao ponto, sem introdução",
  "desenvolvimento": "corpo do roteiro, explicando o tema de forma natural e direta, como se estivesse falando",
  "cta": "chamada para ação final, curta",
  "notas_gravacao": "1-2 frases de instrução de tom/performance para quem for gravar (como falar, onde pausar, onde dar ênfase)"
}"""


CARROSSEL_SYSTEM_PROMPT = """Você gera o texto de carrosséis para Instagram no formato visual de tweet (estilo X/Twitter), para o perfil @rayssacouto.ia.

Regras de copy (invioláveis):
- Português do Brasil, coloquial, direto. Nunca tradução literal do inglês.
- Frases curtas: no máximo 12 palavras por frase.
- NUNCA use travessão (— – ─). No lugar dele, escolha o que soar mais natural e gramaticalmente
  correto em português: vírgula, dois-pontos (quando for introduzir uma explicação ou consequência,
  ex: "Não adianta ter a ferramenta mais poderosa do mundo: se ninguém sabe usar, de nada adianta."),
  ponto final, ou reescreva como duas frases completas.
- NUNCA quebre uma frase no meio com uma quebra de linha. Cada quebra de linha dentro do texto de
  um slide só pode acontecer no fim de uma frase completa e pontuada (terminada em . ou :). Se o
  texto for uma frase só, deixe ela inteira, sem quebra de linha no meio — a quebra visual pro
  tamanho do slide é feita automaticamente por quem renderiza, você não precisa (nem deve) quebrar.
- Sem emoji no corpo do texto.
- Sem hashtag no meio do texto.
- Tom declarativo e opinativo. Não é tutorial passo a passo, é pensamento curto.
- Hooks fortes contradizem expectativa ou provocam. Ex: "A maioria das pessoas quer X, mas evita Y."

Estrutura AIDA obrigatória, distribuída nos slides que você gerar:
- Primeiro slide = ATENÇÃO: hook que para o scroll.
- 1-2 slides seguintes = INTERESSE: aprofunda o problema ou contexto.
- Maioria dos slides = DESEJO: entrega o conteúdo central, a explicação real da notícia.
- 1-2 últimos slides = REFORÇO: resume o aprendizado ou dá um exemplo concreto.

Não gere um slide de CTA/fechamento — isso é adicionado automaticamente pelo sistema depois do seu último slide.

Responda APENAS com um JSON válido: {"slides": ["texto do slide 1 (hook)", "texto do slide 2", "..."]}

Gere entre 5 e 9 slides de conteúdo (o sistema soma 1 slide de CTA no final, totalizando 6 a 10 slides)."""


CARROSSEL_ENSINO_SYSTEM_PROMPT = """Você gera o texto de carrosséis de ENSINO para Instagram no formato visual de tweet (estilo X/Twitter), para o perfil @rayssacouto.ia.

Este carrossel ensina a pessoa a fazer algo prático com IA, relacionado a uma notícia ou novidade. No final, ela precisa conseguir começar a usar aquilo na hora — nada de conceito abstrato, é sempre uma ação concreta.

Regras de copy (invioláveis):
- Português do Brasil, coloquial, direto. Nunca tradução literal do inglês.
- Frases curtas: no máximo 12 palavras por frase.
- NUNCA use travessão (— – ─). No lugar dele, escolha o que soar mais natural e gramaticalmente
  correto em português: vírgula, dois-pontos, ponto final, ou reescreva como duas frases completas.
- NUNCA quebre uma frase no meio com uma quebra de linha. Cada quebra de linha dentro do texto de
  um slide só pode acontecer no fim de uma frase completa e pontuada. A quebra visual pro tamanho
  do slide é feita automaticamente por quem renderiza, você não precisa (nem deve) quebrar.
- Sem emoji no corpo do texto.
- Sem hashtag no meio do texto.

Estrutura obrigatória:
- Slide 1 (GANHO): comece com "Vou te ensinar a [resultado prático e concreto]." O resultado tem
  que estar relacionado à notícia recebida e ser algo que a pessoa aplique sozinha, hoje, com IA.
  Ex: "Vou te ensinar a responder clientes no automático usando o novo recurso do ChatGPT."
- Slide 2 (CONTEXTO): 1-2 frases explicando o que mudou ou surgiu (a notícia) e por que isso
  importa pro dia a dia de quem tem um negócio.
- Slides seguintes (PASSO A PASSO): comece cada um com "Passo 1:", "Passo 2:", "Passo 3:" etc.
  Cada passo é uma instrução clara e simples, que a pessoa consiga seguir sem ajuda técnica.
  Use de 3 a 5 passos.
- Penúltimo slide (RESULTADO): o que a pessoa ganha ao final, de forma tangível e concreta.
  Ex: "Pronto: agora seu negócio responde clientes 24 horas, sem você precisar estar online."

Não gere um slide de CTA/fechamento — isso é adicionado automaticamente pelo sistema depois do seu último slide.

Responda APENAS com um JSON válido: {"slides": ["slide 1 (ganho)", "slide 2 (contexto)", "passo 1", "...", "resultado"]}

Gere entre 6 e 8 slides de conteúdo (o sistema soma 1 slide de CTA no final, totalizando 7 a 9 slides)."""

CopyStyle = Literal["tweet", "ensino"]


@dataclass
class GeneratedContent:
    news: NewsItem
    format: ContentType
    hook: str = ""

    # roteiro
    roteiro_gancho: str = ""
    roteiro_desenvolvimento: str = ""
    roteiro_cta: str = ""
    roteiro_notas_gravacao: str = ""
    roteiro_duracao: str = "60s"

    # carrossel — já inclui o slide de CTA como último item
    carousel_slides: list[str] = field(default_factory=list)


def _call_json(system_prompt: str, user_message: str, client: anthropic.Anthropic) -> Optional[dict]:
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip().rstrip("```").strip()
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[classifier] JSON inválido: {e}")
        return None
    except anthropic.APIError as e:
        print(f"[classifier] Erro de API: {e}")
        return None


def _news_context(item: NewsItem) -> str:
    return (
        f"Título: {item.title}\n"
        f"Fonte: {item.source}\n"
        f"Resumo: {item.summary or item.full_text or 'Sem resumo disponível'}\n"
        f"URL: {item.url}"
    )


def _classify_format(item: NewsItem, client: anthropic.Anthropic) -> ContentType:
    data = _call_json(
        CLASSIFY_SYSTEM_PROMPT,
        f"Notícia:\n\n{_news_context(item)}",
        client,
    )
    fmt = (data or {}).get("format", "carrossel")
    return fmt if fmt in ("roteiro", "carrossel") else "carrossel"


def _generate_roteiro(item: NewsItem, client: anthropic.Anthropic) -> Optional[GeneratedContent]:
    data = _call_json(
        ROTEIRO_SYSTEM_PROMPT,
        f"Tema do roteiro (baseado nesta notícia de IA):\n\n{_news_context(item)}",
        client,
    )
    if not data:
        return None

    gancho = data.get("gancho", "")
    return GeneratedContent(
        news=item,
        format="roteiro",
        hook=gancho,
        roteiro_gancho=gancho,
        roteiro_desenvolvimento=data.get("desenvolvimento", ""),
        roteiro_cta=data.get("cta", ""),
        roteiro_notas_gravacao=data.get("notas_gravacao", ""),
        roteiro_duracao="60s",
    )


def _generate_carrossel(
    item: NewsItem,
    client: anthropic.Anthropic,
    auto_image: bool = True,
    estilo: CopyStyle = "tweet",
) -> Optional[GeneratedContent]:
    system_prompt = CARROSSEL_ENSINO_SYSTEM_PROMPT if estilo == "ensino" else CARROSSEL_SYSTEM_PROMPT
    data = _call_json(
        system_prompt,
        f"Notícia para transformar em carrossel:\n\n{_news_context(item)}",
        client,
    )
    if not data:
        return None

    slides = [s for s in data.get("slides", []) if s]
    if not slides:
        return None

    slides = slides + [random.choice(CTA_OPTIONS)]

    if auto_image and not item.image_path:
        item.image_path = fetch_article_image(item.url)

    return GeneratedContent(
        news=item,
        format="carrossel",
        hook=slides[0],
        carousel_slides=slides,
    )


def classify_and_generate(
    news_items: list[NewsItem], client: anthropic.Anthropic
) -> list[GeneratedContent]:
    results = []
    for item in news_items:
        fmt = _classify_format(item, client)
        content = _generate_roteiro(item, client) if fmt == "roteiro" else _generate_carrossel(item, client)
        if content:
            results.append(content)
    return results


def generate_manual(
    url: str,
    formato: ContentType,
    client: anthropic.Anthropic,
    estilo: CopyStyle = "tweet",
) -> Optional[GeneratedContent]:
    """Gera conteúdo a partir de um link avulso, pulando a classificação automática.

    Usado pela interface web, onde o formato (e, no caso de carrossel, o estilo de copy)
    já vem escolhido pelo usuário.
    """
    title = fetch_article_title(url) or url
    full_text = fetch_article_text(url)
    source = urlparse(url).netloc or "Link manual"

    item = NewsItem(
        title=title,
        summary=full_text[:800],
        url=url,
        source=source,
        tag="manual",
        full_text=full_text,
    )

    if formato == "roteiro":
        return _generate_roteiro(item, client)
    return _generate_carrossel(item, client, auto_image=False, estilo=estilo)
