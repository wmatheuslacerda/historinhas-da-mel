"""Publica Reels no Instagram (API do Instagram com login do Instagram).

Upload "resumable": o vídeo vai direto do GitHub para o Instagram, sem precisar de link público.

Uso avulso:
  python -m src.instagram --renovar            # renova o token (vale 60 dias) e salva no GitHub
  python -m src.instagram --video X.mp4 --roteiro X.json   # posta um Reel manualmente
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

import requests

API = "https://graph.instagram.com/v23.0"
RUPLOAD = "https://rupload.facebook.com/ig-api-upload/v23.0"
HASHTAGS = "#historinhabiblica #bibliaparacriancas #desenhobiblico #historiasbiblicas #criancacrista #educacaocrista #reels"


def _token() -> str:
    tok = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if not tok:
        raise RuntimeError("Falta IG_ACCESS_TOKEN")
    return tok


def _checar(r: requests.Response) -> dict:
    try:
        dados = r.json()
    except ValueError:
        dados = {"texto": r.text[:300]}
    if r.status_code >= 400 or "error" in dados:
        raise RuntimeError(f"Instagram {r.status_code}: {dados.get('error', dados)}")
    return dados


def legenda(roteiro: dict) -> str:
    """Legenda pensada para os pais (quem de fato usa o Instagram)."""
    titulo = roteiro.get("titulo", "").replace("#shorts", "").strip()
    desc = roteiro.get("descricao", "").split("\n\n")[0].strip()
    ref = roteiro.get("referencia", "")
    partes = [f"🐑 {titulo}", desc]
    if ref:
        partes.append(f"📖 {ref}")
    partes.append("👨‍👩‍👧 Assista com seu filho e conte pra gente nos comentários o que ele mais gostou!\n"
                  "💾 Salve para mostrar na hora de dormir • Tem historinha nova todo dia")
    partes.append(HASHTAGS)
    return "\n\n".join(p for p in partes if p)[:2150]


def publicar_reel(caminho: str, texto: str, log=print, capa_ms: int = 1500) -> str:
    tok = _token()
    me = _checar(requests.get(f"{API}/me", params={"fields": "user_id,username", "access_token": tok}, timeout=30))
    uid = me.get("user_id") or me["id"]
    log(f"📸 Instagram @{me.get('username')}: criando Reel...")

    cont = _checar(requests.post(f"{API}/{uid}/media", timeout=60, params={
        "media_type": "REELS", "upload_type": "resumable", "caption": texto,
        "share_to_feed": "true", "thumb_offset": str(capa_ms), "access_token": tok}))["id"]

    tamanho = Path(caminho).stat().st_size
    with open(caminho, "rb") as f:
        _checar(requests.post(f"{RUPLOAD}/{cont}", data=f, timeout=600, headers={
            "Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(tamanho)}))
    log(f"   upload ok ({tamanho / 1e6:.1f} MB), aguardando processamento...")

    for _ in range(60):  # até ~10 min
        st = _checar(requests.get(f"{API}/{cont}", timeout=30,
                                  params={"fields": "status_code,status", "access_token": tok}))
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram recusou o vídeo: {st}")
        time.sleep(10)
    else:
        raise RuntimeError("Instagram demorou demais para processar o vídeo")

    pub = _checar(requests.post(f"{API}/{uid}/media_publish", timeout=60,
                                data={"creation_id": cont, "access_token": tok}))
    link = _checar(requests.get(f"{API}/{pub['id']}", timeout=30,
                                params={"fields": "permalink", "access_token": tok})).get("permalink", "")
    log(f"🎉 Reel publicado: {link or pub['id']}")
    return link or pub["id"]


def renovar(log=print) -> None:
    """Renova o token longo (60 dias) e grava o novo no secret do GitHub."""
    r = _checar(requests.get("https://graph.instagram.com/refresh_access_token", timeout=30,
                             params={"grant_type": "ig_refresh_token", "access_token": _token()}))
    novo = r["access_token"]
    repo = os.environ.get("GITHUB_REPOSITORY")
    if repo and os.environ.get("GH_TOKEN"):
        subprocess.run(["gh", "secret", "set", "IG_ACCESS_TOKEN", "--repo", repo, "--body", novo], check=True)
        log(f"🔑 Token do Instagram renovado (+{r.get('expires_in', 0) // 86400} dias)")
    else:
        log("🔑 Token renovado (não salvei: sem GH_TOKEN/GITHUB_REPOSITORY)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--renovar", action="store_true")
    ap.add_argument("--video")
    ap.add_argument("--roteiro")
    a = ap.parse_args()
    if a.renovar:
        renovar()
    if a.video:
        rot = json.loads(Path(a.roteiro).read_text(encoding="utf-8")) if a.roteiro else {}
        publicar_reel(a.video, legenda(rot))


if __name__ == "__main__":
    main()
