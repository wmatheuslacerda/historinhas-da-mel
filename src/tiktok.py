"""Envia os vídeos para o TikTok (Content Posting API).

Modo "rascunho" (padrão enquanto o app não é aprovado pelo TikTok): o vídeo chega na
caixa de entrada/rascunhos do app e o dono toca em Publicar.
Modo "direto": publica sozinho (só fica público depois da aprovação do app).

Uso:
  python -m src.tiktok --video X.mp4 --roteiro X.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

import requests

API = "https://open.tiktokapis.com/v2"
HASHTAGS = "#historinhabiblica #bibliaparacriancas #desenhobiblico #criancacrista #fyp"


def _checar(r: requests.Response) -> dict:
    try:
        d = r.json()
    except ValueError:
        raise RuntimeError(f"TikTok {r.status_code}: {r.text[:300]}")
    erro = d.get("error") or {}
    if r.status_code >= 400 or (erro.get("code") not in (None, "ok")):
        raise RuntimeError(f"TikTok {r.status_code}: {erro or d}")
    return d


def token(log=print) -> str:
    """Troca o refresh token (vale 1 ano) por um access token (vale 24h)."""
    d = requests.post(f"{API}/oauth/token/", timeout=30, data={
        "client_key": os.environ["TT_CLIENT_KEY"], "client_secret": os.environ["TT_CLIENT_SECRET"],
        "grant_type": "refresh_token", "refresh_token": os.environ["TT_REFRESH_TOKEN"]}).json()
    if "access_token" not in d:
        raise RuntimeError(f"TikTok não renovou o acesso: {d}")
    novo = d.get("refresh_token")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if novo and novo != os.environ["TT_REFRESH_TOKEN"] and repo and os.environ.get("GH_TOKEN"):
        subprocess.run(["gh", "secret", "set", "TT_REFRESH_TOKEN", "--repo", repo, "--body", novo], check=False)
        log("🔑 refresh token do TikTok atualizado")
    return d["access_token"]


def legenda(roteiro: dict) -> str:
    titulo = roteiro.get("titulo", "").replace("#shorts", "").split("|")[0].strip()
    ref = roteiro.get("referencia", "")
    partes = [f"🐑 {titulo}", f"📖 {ref}" if ref else "", "Historinha bíblica para crianças de 3 a 6 anos 💛", HASHTAGS]
    return "\n".join(p for p in partes if p)[:2000]


def enviar(caminho: str, texto: str, modo: str = "rascunho", log=print) -> str:
    tok = token(log)
    h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8"}
    tamanho = Path(caminho).stat().st_size
    fonte = {"source": "FILE_UPLOAD", "video_size": tamanho, "chunk_size": tamanho, "total_chunk_count": 1}
    if modo == "direto":
        info = _checar(requests.post(f"{API}/post/publish/creator_info/query/", headers=h, timeout=30))["data"]
        opcoes = info.get("privacy_level_options", [])
        priv = "PUBLIC_TO_EVERYONE" if "PUBLIC_TO_EVERYONE" in opcoes else opcoes[0]
        corpo = {"post_info": {"title": texto, "privacy_level": priv, "disable_comment": False,
                               "disable_duet": False, "disable_stitch": False, "video_cover_timestamp_ms": 1500},
                 "source_info": fonte}
        url = f"{API}/post/publish/video/init/"
    else:
        corpo = {"source_info": fonte}
        url = f"{API}/post/publish/inbox/video/init/"
    d = _checar(requests.post(url, headers=h, json=corpo, timeout=60))["data"]
    pid, up = d["publish_id"], d["upload_url"]
    with open(caminho, "rb") as f:
        r = requests.put(up, data=f, timeout=600, headers={
            "Content-Type": "video/mp4", "Content-Length": str(tamanho),
            "Content-Range": f"bytes 0-{tamanho - 1}/{tamanho}"})
    if r.status_code >= 400:
        raise RuntimeError(f"TikTok upload {r.status_code}: {r.text[:300]}")
    log(f"🎵 TikTok: vídeo enviado ({tamanho / 1e6:.1f} MB), processando...")
    status = "?"
    for _ in range(40):
        time.sleep(8)
        s = _checar(requests.post(f"{API}/post/publish/status/fetch/", headers=h, timeout=30,
                                  json={"publish_id": pid}))["data"]
        status = s.get("status")
        if status in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE"):
            break
        if status == "FAILED":
            raise RuntimeError(f"TikTok recusou o vídeo: {s.get('fail_reason')}")
    msg = {"SEND_TO_USER_INBOX": "chegou nos rascunhos/caixa de entrada do TikTok (toque em Publicar no app)",
           "PUBLISH_COMPLETE": "publicado no TikTok"}.get(status, f"status {status}")
    log(f"🎉 TikTok: {msg}")
    return status


def enviar_foto(urls: list[str], titulo: str, descricao: str, modo: str = "rascunho", log=print) -> str:
    """Post de FOTO. O TikTok baixa a imagem do link, que precisa estar num domínio/URL verificado
    no portal de desenvolvedores (usamos o GitHub Pages do repositório)."""
    tok = token(log)
    h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8"}
    info = {"title": titulo[:90], "description": descricao[:4000]}
    if modo == "direto":
        dados = _checar(requests.post(f"{API}/post/publish/creator_info/query/", headers=h, timeout=30))["data"]
        opcoes = dados.get("privacy_level_options", [])
        info.update({"privacy_level": "PUBLIC_TO_EVERYONE" if "PUBLIC_TO_EVERYONE" in opcoes else opcoes[0],
                     "disable_comment": False, "auto_add_music": True})
    corpo = {"post_info": info, "post_mode": "DIRECT_POST" if modo == "direto" else "MEDIA_UPLOAD",
             "media_type": "PHOTO",
             "source_info": {"source": "PULL_FROM_URL", "photo_images": urls, "photo_cover_index": 0}}
    pid = _checar(requests.post(f"{API}/post/publish/content/init/", headers=h, json=corpo, timeout=60))["data"]["publish_id"]
    status = "?"
    for _ in range(30):
        time.sleep(6)
        s = _checar(requests.post(f"{API}/post/publish/status/fetch/", headers=h, timeout=30,
                                  json={"publish_id": pid}))["data"]
        status = s.get("status")
        if status in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE"):
            break
        if status == "FAILED":
            raise RuntimeError(f"TikTok recusou a foto: {s.get('fail_reason')}")
    log(f"🎉 TikTok (foto): {status}")
    return status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--roteiro")
    ap.add_argument("--modo", default=os.environ.get("TT_MODO", "rascunho"), choices=["rascunho", "direto"])
    a = ap.parse_args()
    rot = json.loads(Path(a.roteiro).read_text(encoding="utf-8")) if a.roteiro else {}
    texto = legenda(rot)
    status = enviar(a.video, texto, a.modo)
    resumo = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumo:
        with open(resumo, "a", encoding="utf-8") as f:
            f.write(f"\n🎵 TikTok ({a.modo}): {status}\n")
            if a.modo == "rascunho":
                f.write(f"\nLegenda para colar:\n\n```\n{texto}\n```\n")


if __name__ == "__main__":
    main()
