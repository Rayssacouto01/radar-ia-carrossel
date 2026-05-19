"""Ponto de entrada principal do agente de monitoramento de IA."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import anthropic

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MAX_NEWS = int(os.getenv("MAX_NEWS", "1"))

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def validate_env():
    if not ANTHROPIC_API_KEY:
        print("[main] ERRO: ANTHROPIC_API_KEY ausente. Copie .env.example para .env e preencha.")
        sys.exit(1)


def run():
    validate_env()

    from src.scraper import fetch_all_news
    from src.classifier import classify_and_generate
    from src.report_saver import save_report

    print("[main] Buscando novidades de IA...")
    news_items = fetch_all_news(hours_back=24, max_per_source=3)
    print(f"[main] {len(news_items)} notícias encontradas.")

    if not news_items:
        print("[main] Nenhuma novidade nas últimas 24h. Encerrando.")
        return

    news_items = news_items[:MAX_NEWS]

    print("[main] Classificando e gerando conteúdo com Claude...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    contents = classify_and_generate(news_items, client)
    print(f"[main] {len(contents)} itens processados.")

    print("[main] Salvando relatório...")
    report_path = save_report(contents, str(OUTPUT_DIR))

    if report_path:
        print(f"[main] ✅ Relatório pronto: {report_path}")
        print(f"[main] 📁 Pasta de saída: {OUTPUT_DIR}")
    else:
        print("[main] ❌ Falha ao salvar relatório.")


if __name__ == "__main__":
    run()
