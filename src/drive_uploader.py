"""Faz upload de arquivos para o Google Drive usando Service Account."""

import os
import json
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
FOLDER_NAME = "Radar IA"

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


def _get_or_create_folder(service, folder_name: str) -> str:
    """Retorna o ID da pasta no Drive, criando-a se não existir."""
    query = (
        f"name='{folder_name}' "
        f"and mimeType='application/vnd.google-apps.folder' "
        f"and trashed=false"
    )
    results = service.files().list(q=query, fields="files(id,name)").execute()
    files = results.get("files", [])

    if files:
        folder_id = files[0]["id"]
        print(f"[drive] Pasta encontrada: '{folder_name}' (id={folder_id})")
        return folder_id

    # Cria a pasta
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    folder = service.files().create(body=metadata, fields="id").execute()
    folder_id = folder["id"]
    print(f"[drive] Pasta criada: '{folder_name}' (id={folder_id})")
    return folder_id


def upload_file(service, file_path: str, folder_id: str) -> str:
    """Faz upload de um arquivo e retorna o link público."""
    path = Path(file_path)
    mime = MIME_TYPES.get(path.suffix.lower(), "application/octet-stream")

    metadata = {"name": path.name, "parents": [folder_id]}
    media = MediaFileUpload(file_path, mimetype=mime, resumable=False)

    file = (
        service.files()
        .create(body=metadata, media_body=media, fields="id,webViewLink")
        .execute()
    )

    # Torna o arquivo acessível por quem tem o link
    service.permissions().create(
        fileId=file["id"],
        body={"type": "anyone", "role": "reader"},
    ).execute()

    link = file.get("webViewLink", "")
    print(f"[drive] Upload: {path.name} → {link}")
    return link


def upload_report(html_path: str, credentials_json: str) -> str:
    """Ponto de entrada principal: sobe o relatório HTML para a pasta 'Radar IA'.

    Retorna o link público do arquivo ou string vazia em caso de erro.
    """
    if not credentials_json:
        print("[drive] GOOGLE_SA_JSON não configurado — pulando upload.")
        return ""

    try:
        service = _get_service(credentials_json)
        folder_id = _get_or_create_folder(service, FOLDER_NAME)
        link = upload_file(service, html_path, folder_id)
        return link
    except Exception as e:
        print(f"[drive] Erro no upload: {e}")
        return ""
