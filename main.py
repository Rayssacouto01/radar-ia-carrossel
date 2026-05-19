"""Ponto de entrada principal do agente de monitoramento de IA."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import anthropic

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MAX_NEWS = int(os.getenv("MAX_NEWS", "1"))
GOOGLE_SA_JSON = os.getenv("GOOGLE_SA_JSON", "")  # conteúdo do JSON da service account

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
    from src.drive_uploader import upload_report

    print("[main] Buscando novidades de IA...")
    news_items = fetch_all_news(hours_back=48, max_per_source=2)
    print(f"[main] {len(news_items)} notícias encontradas.")

    if not news_items:
        print("[main] Nenhuma novidade recente encontrada. Encerrando.")
        return

    news_items = news_items[:MAX_NEWS]

    print("[main] Classificando e gerando conteúdo com Claude...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    contents = classify_and_generate(news_items, client)
    print(f"[main] {len(contents)} itens processados.")

    if not contents:
        print("[main] Nenhum conteúdo gerado. Encerrando.")
        return

    print("[main] Salvando relatório...")
    report_path = save_report(contents, str(OUTPUT_DIR))

    if not report_path:
        print("[main] ❌ Falha ao salvar relatório.")
        return

    print(f"[main] ✅ Relatório salvo: {report_path}")

    print("[main] Fazendo upload para o Google Drive...")
    drive_link = upload_report(report_path, GOOGLE_SA_JSON)

    if drive_link:
        print(f"[main] ✅ Disponível no Drive: {drive_link}")
    else:
        print("[main] ⚠️  Upload para Drive não realizado (GOOGLE_SA_JSON não configurado ou erro).")
        print(f"[main] 📁 Arquivo local: {report_path}")


if __name__ == "__main__":
    run()
