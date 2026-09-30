"""Publica Reels no Instagram (API do Instagram com login do Instagram).

O Instagram busca o vídeo por link público: usamos o arquivo da release da semana no GitHub.

Uso avulso:
  python -m src.instagram --renovar            # renova o token (vale 60 dias) e salva no GitHub
  python -m src.instagram --release TAG --video X.mp4 --roteiro X.json   # posta o Reel
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


def link_publico(url: str) -> str:
    """Segue o redirecionamento do GitHub até o arquivo final (o Instagram prefere link direto)."""
    try:
        r = requests.head(url, allow_redirects=True, timeout=30)
        return r.url if r.ok else url
    except requests.RequestException:
        return url


def publicar_reel(video_url: str, texto: str, log=print, capa_ms: int = 1500) -> str:
    tok = _token()
    me = _checar(requests.get(f"{API}/me", params={"fields": "user_id,username", "access_token": tok}, timeout=30))
    uid = me.get("user_id") or me["id"]
    log(f"📸 Instagram @{me.get('username')}: criando Reel...")
    cont = _checar(requests.post(f"{API}/{uid}/media", timeout=60, data={
        "media_type": "REELS", "video_url": link_publico(video_url), "caption": texto,
        "share_to_feed": "true", "thumb_offset": str(capa_ms), "access_token": tok}))["id"]
    log("   aguardando o Instagram processar o vídeo...")

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
    ap.add_argument("--video", help="arquivo .mp4 já enviado para a release")
    ap.add_argument("--roteiro")
    ap.add_argument("--release", help="tag da release onde o vídeo está")
    ap.add_argument("--url", help="link público do vídeo (em vez de --release)")
    a = ap.parse_args()
    if a.renovar:
        renovar()
    if a.video:
        rot = json.loads(Path(a.roteiro).read_text(encoding="utf-8")) if a.roteiro else {}
        repo = os.environ.get("GITHUB_REPOSITORY", "wmatheuslacerda/historinhas-da-mel")
        url = a.url or f"https://github.com/{repo}/releases/download/{a.release}/{Path(a.video).name}"
        link = publicar_reel(url, legenda(rot))
        resumo = os.environ.get("GITHUB_STEP_SUMMARY")
        if resumo:
            with open(resumo, "a", encoding="utf-8") as f:
                f.write(f"\n📸 Instagram: {link}\n")


if __name__ == "__main__":
    main()
