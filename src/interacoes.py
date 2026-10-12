"""Interações da Mel com o público: toc-toc na tela, risada, choro e tchauzinho.

Aplica as interações em qualquer roteiro (banco pronto ou gerado pela API):
- 1ª fala da Mel: bate na tela "Toc, toc!"
- história emocionante (alguém triste/assustado): a Mel se emociona e chora na lição
- senão: a Mel dá risadinha "Hihihi!" antes de se despedir
- última fala da Mel: tchauzinho com a patinha
- falas da Mel com "hihi", "haha"... ou emoção triste ganham risada / choro automaticamente
"""
from __future__ import annotations

import re

RISOS = re.compile(r"\b(hi ?hi|ha ?ha|he ?he|hee ?hee|kkk|risad|cócegas|engraçad|giggl|tickl|funny)", re.I)
TOC = re.compile(r"\b(toc|knock)\b", re.I)
FRASES = {
    "pt": {"toc": "Toc, toc! ", "emo": "Ai, que emocionante! ", "riso": "Hihihi! "},
    "en": {"toc": "Knock, knock! ", "emo": "Aww, that was so special! ", "riso": "Hee hee hee! "},
}


def _falas_mel(roteiro):
    for ci, cena in enumerate(roteiro["cenas"]):
        if "mel" not in cena.get("personagens", []):
            continue
        for fi, f in enumerate(cena["falas"]):
            if f.get("quem") == "mel":
                yield ci, fi, f


def enriquecer(roteiro: dict, idioma: str = "pt") -> dict:
    fr = FRASES.get(idioma, FRASES["pt"])
    falas = list(_falas_mel(roteiro))
    if not falas:
        return roteiro

    # emoções da Mel no meio da fala
    for _, _, f in falas:
        if not f.get("acao") or f["acao"] == "nenhuma":
            if RISOS.search(f["texto"]):
                f["acao"] = "rir"
            elif f.get("emocao") == "triste":
                f["acao"] = "chorar"

    # abertura: toc-toc na tela
    _, _, primeira = falas[0]
    if not TOC.search(primeira["texto"]):
        primeira["texto"] = fr["toc"] + primeira["texto"]
    primeira["acao"] = "toctoc"
    primeira.setdefault("emocao", "feliz")

    # despedida
    ci, fi, ultima = falas[-1]
    if ultima is primeira:
        return roteiro
    emocionante = any(f.get("emocao") in ("triste", "assustado")
                      for c in roteiro["cenas"] for f in c["falas"])
    cena = roteiro["cenas"][ci]
    if emocionante and len(cena["falas"]) >= 2 and cena["falas"][0].get("quem") == "mel" and cena["falas"][0] is not ultima:
        # a lição vem antes do tchau: a Mel se emociona nela
        licao = cena["falas"][0]
        if licao.get("acao") in (None, "nenhuma"):
            licao["acao"] = "chorar"
            licao["emocao"] = "triste"
    elif emocionante and ultima.get("acao") in (None, "nenhuma"):
        ultima["texto"] = fr["emo"] + ultima["texto"]
        ultima["chorinho"] = True        # lágrimas de alegria enquanto acena
    else:
        if not RISOS.search(ultima["texto"]):
            ultima["texto"] = fr["riso"] + ultima["texto"]
        ultima["risadinha"] = True       # ri no começo da fala e depois acena
    ultima["acao"] = "tchau"
    ultima["emocao"] = "feliz"
    return roteiro
