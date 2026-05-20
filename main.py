"""Ponto de entrada principal do agente de monitoramento de IA."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import anthropic

load_dotenv()

ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
MAX_NEWS           = int(os.getenv("MAX_NEWS", "1"))
EVOLUTION_URL      = os.getenv("EVOLUTION_URL", "")
EVOLUTION_API_KEY  = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "")
WHATSAPP_NUMBER    = os.getenv("WHATSAPP_NUMBER", "")

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def validate_env():
    if not ANTHROPIC_API_KEY:
        print("[main] ERRO: ANTHROPIC_API_KEY ausente.")
        sys.exit(1)


def run():
    validate_env()

    from src.scraper import fetch_all_news
    from src.classifier import classify_and_generate
    from src.carousel_generator import generate_carousel, generate_cover
    from src.report_saver import save_report
    from src.whatsapp_sender import send_report

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

    print("[main] Gerando slides de carrossel...")
    contents_with_paths: list[tuple] = []
    for c in contents:
        if c.format == "carrossel":
            paths = generate_carousel(c, str(OUTPUT_DIR))
        else:
            paths = generate_cover(c, str(OUTPUT_DIR))
        contents_with_paths.append((c, paths))

    print("[main] Salvando relatório HTML...")
    report_path = save_report(contents_with_paths, str(OUTPUT_DIR))

    if not report_path:
        print("[main] ❌ Falha ao salvar relatório.")
        return

    print(f"[main] ✅ Relatório salvo: {report_path}")

    if EVOLUTION_URL and EVOLUTION_API_KEY and EVOLUTION_INSTANCE and WHATSAPP_NUMBER:
        print("[main] Enviando para WhatsApp via Evolution API...")
        ok = send_report(
            contents_with_paths,
            report_path,
            EVOLUTION_URL,
            EVOLUTION_API_KEY,
            EVOLUTION_INSTANCE,
            WHATSAPP_NUMBER,
        )
        if ok:
            print(f"[main] ✅ Enviado para WhatsApp: {WHATSAPP_NUMBER}")
        else:
            print("[main] ⚠️  Falha no envio WhatsApp. Relatório local disponível.")
    else:
        print("[main] ⚠️  Variáveis da Evolution API não configuradas — envio WhatsApp pulado.")
        print(f"[main] 📁 Arquivo local: {report_path}")


if __name__ == "__main__":
    run()
