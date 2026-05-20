"""Faz upload de arquivos para o Google Drive usando Service Account."""

import os
import json
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]
FOLDER_ID = "1rwbAVEVY38MnqdIGqFU2hoqB03yfqhna"  # pasta "Radar IA" com link público de edição

MIME_TYPES = {
    ".html": "text/html",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".pdf": "application/pdf",
}


def _get_service(credentials_json: str):
    """Cria o cliente autenticado via service account."""
    info = json.loads(credentials_json)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def upload_file(service, file_path: str) -> str:
    """Faz upload direto na pasta 'Radar IA' pelo ID fixo. Retorna o link."""
    path = Path(file_path)
    mime = MIME_TYPES.get(path.suffix.lower(), "application/octet-stream")

    metadata = {"name": path.name, "parents": [FOLDER_ID]}
    media = MediaFileUpload(file_path, mimetype=mime, resumable=False)

    file = (
        service.files()
        .create(body=metadata, media_body=media, fields="id,webViewLink")
        .execute()
    )

    link = file.get("webViewLink", "")
    print(f"[drive] Upload: {path.name} → {link}")
    return link


def upload_report(html_path: str, credentials_json: str) -> str:
    """Sobe o relatório HTML para a pasta 'Radar IA' (ID fixo).

    Retorna o link do arquivo ou string vazia em caso de erro.
    """
    if not credentials_json:
        print("[drive] GOOGLE_SA_JSON não configurado — pulando upload.")
        return ""

    try:
        service = _get_service(credentials_json)
        link = upload_file(service, html_path)
        return link
    except Exception as e:
        print(f"[drive] Erro no upload: {e}")
        return ""
