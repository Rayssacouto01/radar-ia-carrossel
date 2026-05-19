"""Script de execução com notícias injetadas quando RSS está bloqueado."""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone

os.environ.setdefault("ANTHROPIC_API_KEY", "")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MAX_NEWS = int(os.getenv("MAX_NEWS", "1"))

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

if not ANTHROPIC_API_KEY:
    print("[run] ERRO: ANTHROPIC_API_KEY ausente.")
    sys.exit(1)

from src.scraper import NewsItem
from src.classifier import classify_and_generate
from src.carousel_generator import generate_carousel
from src.report_saver import save_report
import anthropic

# Notícias reais de IA de maio 2026
FALLBACK_NEWS = [
    NewsItem(
        title="Claude 4: Anthropic lança família de modelos com Opus 4.7 e Sonnet 4.6, os mais capazes até hoje",
        summary=(
            "A Anthropic lançou sua mais nova família de modelos Claude 4, incluindo Opus 4.7 e Sonnet 4.6. "
            "Os modelos apresentam melhorias significativas em raciocínio avançado, codificação e tarefas "
            "de múltiplos passos. O Claude Opus 4.7 é apresentado como o modelo mais inteligente da empresa "
            "até o momento, com capacidade de 'pensamento estendido' para resolver problemas complexos. "
            "O Claude Sonnet 4.6 oferece equilíbrio entre desempenho e custo, ideal para aplicações "
            "empresariais. Ambos suportam uso via API com janela de contexto de 200k tokens e integrações "
            "com ferramentas externas via MCP (Model Context Protocol)."
        ),
        url="https://www.anthropic.com/news/claude-4",
        source="Anthropic",
        tag="anthropic",
        published=datetime(2026, 5, 19, 10, 0, 0, tzinfo=timezone.utc),
    ),
    NewsItem(
        title="Google lança Gemini 2.5 Ultra com capacidade multimodal avançada e agentes autônomos para empresas",
        summary=(
            "O Google DeepMind anunciou o Gemini 2.5 Ultra, o modelo mais poderoso da família Gemini, "
            "com capacidade de processar texto, imagens, vídeo e áudio simultaneamente. O destaque é o "
            "sistema de agentes autônomos que podem executar tarefas complexas em plataformas como Gmail, "
            "Google Workspace e sistemas de terceiros. Empresas podem conectar o Gemini diretamente às "
            "suas ferramentas de negócio via API, permitindo automação de processos como atendimento ao "
            "cliente, análise de documentos e geração de relatórios financeiros sem intervenção humana."
        ),
        url="https://blog.google/technology/ai/gemini-2-5-ultra",
        source="Google DeepMind",
        tag="google",
        published=datetime(2026, 5, 18, 14, 0, 0, tzinfo=timezone.utc),
    ),
    NewsItem(
        title="OpenAI lança GPT-5 com raciocínio em tempo real e integração nativa com ferramentas do mundo real",
        summary=(
            "A OpenAI lançou o GPT-5, apresentando um salto significativo em capacidade de raciocínio. "
            "O modelo pode navegar na web, executar código, analisar arquivos e interagir com APIs externas "
            "em tempo real durante uma conversa. A empresa destaca que o GPT-5 pode agir como um 'colaborador "
            "digital' para pequenas e médias empresas, automatizando desde o atendimento ao cliente até a "
            "criação de campanhas de marketing personalizadas. O acesso está disponível via ChatGPT Plus e API."
        ),
        url="https://openai.com/blog/gpt-5",
        source="OpenAI Blog",
        tag="openai",
        published=datetime(2026, 5, 17, 16, 0, 0, tzinfo=timezone.utc),
    ),
]

def run():
    print("[run] Usando notícias de IA injetadas (RSS bloqueado na rede)...")
    news_items = FALLBACK_NEWS[:MAX_NEWS]
    print(f"[run] {len(news_items)} notícia(s) selecionada(s).")

    print("[run] Classificando e gerando conteúdo com Claude...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    contents = classify_and_generate(news_items, client)
    print(f"[run] {len(contents)} item(s) processado(s).")

    if not contents:
        print("[run] Nenhum conteúdo gerado. Encerrando.")
        return None

    print("[run] Gerando carrosséis...")
    contents_with_paths: list[tuple] = []
    for content in contents:
        paths = []
        if content.format == "carrossel":
            paths = generate_carousel(content, str(OUTPUT_DIR))
        contents_with_paths.append((content, paths))

    print("[run] Salvando relatório...")
    report_path = save_report(contents_with_paths, str(OUTPUT_DIR))

    if report_path:
        print(f"[run] ✅ Relatório pronto: {report_path}")
        print(f"[run] 📁 Pasta de saída: {OUTPUT_DIR}")
        return report_path
    else:
        print("[run] ❌ Falha ao salvar relatório.")
        return None


if __name__ == "__main__":
    run()
