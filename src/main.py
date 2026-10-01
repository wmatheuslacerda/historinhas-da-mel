"""Pipeline completo: história → roteiro → vozes → animação → YouTube.

Uso:
  python -m src.main                      # gera e publica (produção / GitHub Actions)
  python -m src.main --nao-postar         # gera o vídeo sem publicar
  python -m src.main --offline --roteiro exemplos/davi_e_golias.json   # teste sem nenhuma chave
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import yaml

from . import audio as A
from .interacoes import enriquecer
from .roteiro import Roteirista, escolher_historia, voz_de, validar
from .video import Renderizador
from .vozes import Vozes

RAIZ = Path(__file__).resolve().parent.parent
FUSO = dt.timezone(dt.timedelta(hours=-3))  # Brasília


def log(msg):
    print(msg, flush=True)


def carregar_env():
    env = RAIZ / ".env"
    if env.exists():
        for linha in env.read_text().splitlines():
            if "=" in linha and not linha.strip().startswith("#"):
                k, v = linha.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))


def ajustar_duracao(falas, roteiro, limite):
    """Se passar do limite, acelera levemente todas as falas (até 15%)."""
    n_falas = sum(len(c["falas"]) for c in roteiro["cenas"])
    n_cenas = len(roteiro["cenas"])
    estimado = sum(f.duracao for f in falas) + 0.28 * n_falas + 0.32 * n_cenas + 0.9
    if estimado <= limite:
        return falas, estimado
    fator = estimado / (limite - 0.3)
    if fator > 1.15:
        raise ValueError(f"vídeo ficaria com {estimado:.0f}s (máx. {limite}s)")
    log(f"⏩ Acelerando as falas em {int((fator - 1) * 100)}% para caber em {limite}s")
    for f in falas:
        f.audio = A.aplicar_filtro(f.audio, f"atempo={fator:.4f}")
        f.inicios = [x / fator for x in f.inicios]
        f.fins = [x / fator for x in f.fins]
    return falas, estimado / fator


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="vozes de teste (espeak), sem gastar créditos")
    ap.add_argument("--roteiro", help="usar um roteiro JSON pronto em vez de pedir ao Claude")
    ap.add_argument("--nao-postar", action="store_true")
    ap.add_argument("--saida", default="saida")
    args = ap.parse_args()
    carregar_env()

    cfg = yaml.safe_load((RAIZ / "config.yaml").read_text())
    arq_estado = RAIZ / "estado" / "historico.json"
    estado = json.loads(arq_estado.read_text()) if arq_estado.exists() else {"postados": []}
    catalogo = json.loads((RAIZ / "dados" / "historias.json").read_text())
    agora = dt.datetime.now(FUSO)
    postar = not (args.nao_postar or args.offline)

    ini = time.time()
    for tentativa in range(3):
        # 1) roteiro
        if args.roteiro:
            roteiro = validar(json.loads(Path(args.roteiro).read_text()), cfg)
            log(f"📄 Roteiro carregado: {roteiro['titulo']}")
        else:
            banco = RAIZ / "dados" / "roteiros"
            usar_api = bool(os.environ.get("ANTHROPIC_API_KEY"))
            cat = catalogo if usar_api else [h for h in catalogo if (banco / f"{h['id']}.json").exists()]
            if not cat:
                raise RuntimeError("Sem ANTHROPIC_API_KEY e sem roteiros prontos em dados/roteiros/")
            historia, abordagem = escolher_historia(cat, estado["postados"], agora.date())
            log(f"📖 História: {historia['titulo']} ({historia['ref']})")
            if usar_api:
                recentes = [p["titulo"] for p in estado["postados"][-12:]]
                roteiro = Roteirista(cfg).criar(historia, abordagem, recentes)
            else:
                roteiro = validar(json.loads((banco / f"{historia['id']}.json").read_text()), cfg)
                roteiro.setdefault("historia_id", historia["id"])
                roteiro.setdefault("referencia", historia["ref"])
            log(f"✍️  Roteiro: {roteiro['titulo']}")
        roteiro = enriquecer(roteiro)

        # 2) vozes
        vozes = Vozes(cfg, offline=args.offline, cache=RAIZ / ".cache" / "vozes")
        falas = []
        for cena in roteiro["cenas"]:
            for f in cena["falas"]:
                falas.append(vozes.falar(f["texto"], voz_de(roteiro, f["quem"])))
        log(f"🗣️  {len(falas)} falas geradas")
        try:
            falas, dur = ajustar_duracao(falas, roteiro, cfg["video"]["duracao_max"])
            break
        except ValueError as e:
            if args.roteiro or tentativa == 2:
                raise
            log(f"↩️  {e} — pedindo um roteiro mais curto")
            cfg["roteiro"]["palavras_max"] = int(cfg["roteiro"]["palavras_max"] * 0.85)
            cfg["roteiro"]["palavras_min"] = int(cfg["roteiro"]["palavras_min"] * 0.85)

    # 3) vídeo
    carimbo = agora.strftime("%Y-%m-%d_%H%M")
    seed = int(hashlib.md5(carimbo.encode()).hexdigest()[:8], 16)
    pasta = RAIZ / args.saida
    pasta.mkdir(parents=True, exist_ok=True)
    nome = f"{carimbo}_{roteiro.get('historia_id', 'video')}"
    mp4 = str(pasta / f"{nome}.mp4")
    Renderizador(roteiro, falas, cfg, seed=seed, log=log).renderizar(mp4, str(RAIZ / ".cache" / "tmp"))
    (pasta / f"{nome}.json").write_text(json.dumps(roteiro, ensure_ascii=False, indent=1))
    log(f"✅ Vídeo pronto: {mp4} ({time.time() - ini:.0f}s)")

    # 4) YouTube
    if postar:
        from .youtube import publicar
        log("📤 Publicando no YouTube...")
        vid = publicar(mp4, roteiro, cfg, log=log)
        url = f"https://youtube.com/shorts/{vid}"
        log(f"🎉 Publicado: {url}")
        estado["postados"].append({
            "data": agora.isoformat(timespec="minutes"), "historia_id": roteiro.get("historia_id"),
            "abordagem": roteiro.get("abordagem"), "titulo": roteiro["titulo"], "video_id": vid, "url": url,
        })
        arq_estado.parent.mkdir(exist_ok=True)
        arq_estado.write_text(json.dumps(estado, ensure_ascii=False, indent=1))
        resumo = os.environ.get("GITHUB_STEP_SUMMARY")
        if resumo:
            with open(resumo, "a") as f:
                f.write(f"### 🐑 {roteiro['titulo']}\n\n{url}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"❌ ERRO: {e}")
        raise
