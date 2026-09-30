"""Publica o vídeo no YouTube pela API oficial (marcado como "feito para crianças")."""
from __future__ import annotations

import os
import time

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]


def credenciais():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    faltando = [k for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN") if not os.environ.get(k)]
    if faltando:
        raise RuntimeError(f"Faltam variáveis do YouTube: {', '.join(faltando)}")
    cred = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"],
                       token_uri="https://oauth2.googleapis.com/token",
                       client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"],
                       scopes=SCOPES)
    cred.refresh(Request())
    return cred


def publicar(caminho: str, roteiro: dict, cfg: dict, log=print) -> str:
    """Publica um Short a partir do roteiro."""
    hashtags = " ".join(cfg["youtube"].get("hashtags", []))
    base = roteiro.get("descricao", "")
    if "📖" not in base and roteiro.get("referencia"):
        base += f"\n\n📖 {roteiro['referencia']}"
    return enviar(caminho, roteiro["titulo"], f"{base}\n\n{hashtags}".strip(), roteiro.get("tags", []), cfg, log=log)


def enviar(caminho: str, titulo: str, descricao: str, tags: list, cfg: dict, capa: str | None = None, log=print) -> str:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    yt_cfg = cfg["youtube"]
    yt = build("youtube", "v3", credentials=credenciais(), cache_discovery=False)
    corpo = {
        "snippet": {
            "title": titulo[:100],
            "description": descricao[:4900],
            "tags": [t[:30] for t in tags][:15],
            "categoryId": str(yt_cfg.get("categoria", "1")),
            "defaultLanguage": yt_cfg.get("idioma", "pt-BR"),
            "defaultAudioLanguage": yt_cfg.get("idioma", "pt-BR"),
        },
        "status": {
            "privacyStatus": yt_cfg.get("privacidade", "public"),
            "selfDeclaredMadeForKids": bool(yt_cfg.get("feito_para_criancas", True)),
            "embeddable": True,
        },
    }
    midia = MediaFileUpload(caminho, mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=corpo, media_body=midia)
    resposta, tentativa = None, 0
    while resposta is None:
        try:
            status, resposta = req.next_chunk()
            if status:
                log(f"   upload {int(status.progress() * 100)}%")
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and tentativa < 5:
                tentativa += 1
                time.sleep(5 * tentativa)
                continue
            raise
    vid = resposta["id"]
    priv = resposta.get("status", {}).get("privacyStatus")
    if priv != yt_cfg.get("privacidade", "public"):
        log(f"⚠️  O YouTube deixou o vídeo como '{priv}'. Isso acontece enquanto o projeto da API "
            "não passa pela auditoria do Google (veja o README).")
    if capa:
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(capa, mimetype="image/png")).execute()
            log("🖼️  Capa enviada")
        except Exception as e:  # canal sem verificação por telefone não aceita capa personalizada
            log(f"⚠️  Não consegui enviar a capa (verifique o canal por telefone em youtube.com/verify): {e}")
    return vid
