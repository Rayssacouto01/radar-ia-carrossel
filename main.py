"""Ponto de entrada principal do agente de monitoramento de IA."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import anthropic

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
TO_EMAIL = os.getenv("TO_EMAIL", "institutorayssacouto@gmail.com")
MAX_NEWS = int(os.getenv("MAX_NEWS", "5"))

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def validate_env():
    missing = []
    if not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not RESEND_API_KEY:
        missing.append("RESEND_API_KEY")
    if missing:
        print(f"[main] ERRO: Variáveis de ambiente ausentes: {', '.join(missing)}")
        print("[main] Copie .env.example para .env e preencha as chaves.")
        sys.exit(1)


def run():
    validate_env()

    from src.scraper import fetch_all_news
    from src.classifier import classify_and_generate
    from src.carousel_generator import generate_carousel
    from src.email_sender import send_daily_report

    print("[main] Buscando novidades de IA...")
    news_items = fetch_all_news(hours_back=24, max_per_source=3)
    print(f"[main] {len(news_items)} notícias encontradas.")

    if not news_items:
        print("[main] Nenhuma novidade nas últimas 24h. Encerrando.")
        return

    # Limita o total para não explodir a cota da API
    news_items = news_items[:MAX_NEWS]

    print("[main] Classificando e gerando conteúdo com Claude...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    contents = classify_and_generate(news_items, client)
    print(f"[main] {len(contents)} itens processados.")

    print("[main] Gerando carrosséis...")
    contents_with_paths: list[tuple] = []
    for content in contents:
        paths = []
        if content.format == "carrossel":
            paths = generate_carousel(content, str(OUTPUT_DIR))
        contents_with_paths.append((content, paths))

    print("[main] Enviando relatório por email...")
    success = send_daily_report(contents_with_paths, TO_EMAIL, RESEND_API_KEY)

    if success:
        print(f"[main] ✅ Relatório enviado para {TO_EMAIL}")
    else:
        print("[main] ❌ Falha no envio do email.")


if __name__ == "__main__":
    run()
