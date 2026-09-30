"""Posts de imagem "Você sabia?" — curiosidade bíblica para os pais, com a Mel.

3 por dia (10h, 15h e 20h). Gera uma imagem 1080x1350 (4:5, o melhor formato do feed),
publica no Instagram e manda para o TikTok como rascunho (vídeo curtinho com a imagem,
porque o TikTok só aceita FOTO vinda de site verificado).

Uso:
  python -m src.vocesabia                 # gera e publica (GitHub Actions)
  python -m src.vocesabia --nao-postar    # só gera a imagem em saida/
  python -m src.vocesabia --offline       # teste sem chave nenhuma (texto de exemplo)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import subprocess
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFilter

from .cenarios import CENARIOS, desenhar
from .desenho import Pintor, estrela_pts
from .personagens import PRESETS, criar_personagem
from .video import fonte

RAIZ = Path(__file__).resolve().parent.parent
ESTADO = RAIZ / "estado" / "vocesabia.json"
SAIDA = RAIZ / "saida"
FUSO = dt.timezone(dt.timedelta(hours=-3))
W, H = 1080, 1350
TOPO_CENARIO = 420          # recorte do cenário 1080x1920 que vira o fundo
ARROBA = "@historinhasdamelofc"
HASHTAGS = ("#vocesabia #curiosidadesbiblicas #bibliaparacriancas #historinhabiblica "
            "#criancacrista #educacaocrista #maedemenino #maedemenina")
HASHTAGS_TT = "#vocesabia #curiosidadesbiblicas #bibliaparacriancas #criancacrista #fyp"

TIPOS = [
    "um número ou tamanho surpreendente (ex.: medidas da arca, quantos anos alguém viveu)",
    "um costume da época bíblica que explica a história (comida, roupa, casa, profissão)",
    "um animal, planta ou lugar citado na Bíblia e o que ele significa",
    "um detalhe do texto que quase ninguém percebe",
    "o significado de um nome bíblico",
]

SISTEMA = """Você escreve posts "Você sabia?" para o Instagram de um canal infantil cristão, "Historinhas da Mel".
Quem lê são PAIS e MÃES de crianças de 3 a 6 anos. O objetivo: uma curiosidade bíblica VERDADEIRA que
surpreenda o adulto e que ele consiga contar para o filho.

REGRAS
- Seja fiel à Bíblia e a fatos históricos aceitos. Nada de lenda, especulação ou número inventado.
  Se houver dúvida entre estudiosos, escolha outra curiosidade.
- Português do Brasil, tom carinhoso e leve, sem jargão teológico e sem polêmica denominacional.
- Nunca peça para curtir, seguir ou compartilhar (conteúdo infantil). Pode convidar a comentar a resposta do filho.
- Nada assustador. Deus nunca aparece desenhado.
- A curiosidade da imagem precisa ser CURTA: no máximo 22 palavras, começando direto no fato
  (sem repetir "Você sabia que", isso já está no título da arte).

Personagens disponíveis para desenhar ao lado da Mel (use o id): {catalogo}
Cenários de fundo disponíveis: {cenarios}
"""

FERRAMENTA = {
    "name": "entregar_post",
    "description": "Entrega o post Você sabia?.",
    "input_schema": {
        "type": "object",
        "properties": {
            "curiosidade": {"type": "string", "description": "Texto da imagem, até 22 palavras, sem 'Você sabia que'"},
            "explicacao": {"type": "string", "description": "2 a 3 frases para a legenda, explicando para os pais"},
            "conte_ao_filho": {"type": "string", "description": "Como contar isso para uma criança de 4 anos, 1 frase"},
            "pergunta": {"type": "string", "description": "Pergunta simples para os pais fazerem ao filho"},
            "referencia": {"type": "string", "description": "Referência bíblica, ex.: Gênesis 6:15"},
            "personagem": {"type": "string", "description": "id do catálogo que aparece com a Mel (ou 'nenhum')"},
            "cenario": {"type": "string", "enum": CENARIOS},
        },
        "required": ["curiosidade", "explicacao", "conte_ao_filho", "pergunta", "referencia", "personagem", "cenario"],
    },
}

EXEMPLO = {
    "curiosidade": "A arca de Noé tinha uns 135 metros: é mais comprida que um campo de futebol e meio!",
    "explicacao": "A Bíblia diz que a arca tinha 300 côvados de comprimento. Um côvado é a medida do cotovelo até a ponta dos dedos, uns 45 cm.",
    "conte_ao_filho": "Meça com seu filho o braço dele do cotovelo até o dedinho: a arca tinha 300 desses... de gente grande!",
    "pergunta": "Quantos bichinhos você acha que cabiam na arca?",
    "referencia": "Gênesis 6:15",
    "personagem": "noe",
    "cenario": "arca",
    "historia_id": "noe-constroi-arca",
}


# ------------------------------------------------------------ estado
def carregar_estado() -> dict:
    if ESTADO.exists():
        return json.loads(ESTADO.read_text(encoding="utf-8"))
    return {"postados": []}


def salvar_estado(est: dict):
    ESTADO.parent.mkdir(exist_ok=True)
    ESTADO.write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding="utf-8")


def escolher_historia(catalogo: list, postados: list) -> dict:
    """Percorre o catálogo sem repetir até dar a volta; embaralhado mas estável."""
    normais = [h for h in catalogo if not h.get("tag")]
    ordem = normais[:]
    random.Random(7).shuffle(ordem)
    usados = [p["historia_id"] for p in postados]
    ciclo = len(usados) // len(ordem)
    usados_ciclo = set(usados[ciclo * len(ordem):])
    return next((h for h in ordem if h["id"] not in usados_ciclo), ordem[0])


# ------------------------------------------------------------ texto (Claude)
def criar_texto(cfg: dict, historia: dict, recentes: list[str], tipo: str) -> dict:
    import anthropic
    cli = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    catalogo = ", ".join(k for k in PRESETS if k not in ("mel", "homem", "mulher"))
    sistema = SISTEMA.format(catalogo=catalogo, cenarios=", ".join(CENARIOS))
    pedido = (f"História base: {historia['titulo']} ({historia['ref']}) — {historia['ideia']}.\n"
              f"Tipo de curiosidade de hoje: {tipo}.\n"
              f"Curiosidades já postadas (não repita): {' | '.join(recentes[-30:]) or 'nenhuma'}.\n"
              "Entregue com a ferramenta entregar_post.")
    erro = None
    for _ in range(3):
        resp = cli.messages.create(
            model=cfg["roteiro"]["modelo"], max_tokens=1200, system=sistema,
            messages=[{"role": "user", "content": pedido + (f"\nA tentativa anterior falhou: {erro}" if erro else "")}],
            tools=[FERRAMENTA], tool_choice={"type": "tool", "name": "entregar_post"})
        bloco = next((b for b in resp.content if b.type == "tool_use"), None)
        if not bloco:
            erro = "não usou a ferramenta"
            continue
        d = dict(bloco.input)
        d["curiosidade"] = d["curiosidade"].strip()
        for pre in ("Você sabia que ", "você sabia que "):
            if d["curiosidade"].startswith(pre):
                d["curiosidade"] = d["curiosidade"][len(pre):]
        if len(d["curiosidade"].split()) > 26:
            erro = "curiosidade longa demais (máx. 22 palavras)"
            continue
        d["curiosidade"] = d["curiosidade"][0].upper() + d["curiosidade"][1:]
        if d.get("personagem") not in PRESETS or d.get("personagem") == "mel":
            d["personagem"] = "nenhum"
        if d.get("cenario") not in CENARIOS:
            d["cenario"] = "campo"
        d["historia_id"] = historia["id"]
        return d
    raise RuntimeError(f"Não consegui o texto do post: {erro}")


# ------------------------------------------------------------ arte
def _quebrar(draw, texto, f, largura):
    linhas, atual = [], ""
    for p in texto.split():
        teste = (atual + " " + p).strip()
        if draw.textlength(teste, font=f) <= largura:
            atual = teste
        else:
            linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def _texto_ajustado(draw, texto, largura, altura_max, tam=74, minimo=44):
    while tam >= minimo:
        f = fonte(tam)
        linhas = _quebrar(draw, texto, f, largura)
        alt = len(linhas) * int(tam * 1.22)
        if alt <= altura_max:
            return f, linhas, int(tam * 1.22)
        tam -= 4
    f = fonte(minimo)
    return f, _quebrar(draw, texto, f, largura), int(minimo * 1.22)


def _sombra(img: Image.Image, box, raio, forca=90):
    s = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(s).rounded_rectangle((box[0], box[1] + 12, box[2], box[3] + 12), raio, fill=(40, 30, 60, forca))
    img.alpha_composite(s.filter(ImageFilter.GaussianBlur(14)))


def _personagem(preset: str, altura: int, emocao="feliz", espelho=False) -> Image.Image:
    p = criar_personagem({"preset": preset})
    img = p.retrato(emocao)
    bb = img.getbbox()
    img = img.crop(bb) if bb else img
    k = altura / img.height
    img = img.resize((max(1, int(img.width * k)), altura), Image.LANCZOS)
    return img.transpose(Image.FLIP_LEFT_RIGHT) if espelho else img


def desenhar_post(d: dict, seed: int = 1) -> Image.Image:
    fundo, frente, _ = desenhar(d["cenario"], "dia", seed)
    img = fundo.convert("RGBA").crop((0, TOPO_CENARIO, W, TOPO_CENARIO + H))
    if frente is not None:
        img.alpha_composite(frente.crop((0, TOPO_CENARIO, W, TOPO_CENARIO + H)))
    # véu claro no alto para o cartão respirar
    veu = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dv = ImageDraw.Draw(veu)
    for y in range(0, 700):
        dv.line([(0, y), (W, y)], fill=(255, 255, 255, int(110 * (1 - y / 700))))
    img.alpha_composite(veu)
    draw = ImageDraw.Draw(img)

    # selo "VOCÊ SABIA?"
    f_selo = fonte(78)
    txt = "VOCÊ SABIA?"
    tw = draw.textlength(txt, font=f_selo)
    sx0, sy0 = (W - tw) / 2 - 60, 60
    selo = (sx0, sy0, sx0 + tw + 120, sy0 + 124)
    _sombra(img, selo, 62)
    draw.rounded_rectangle(selo, 62, fill="#ff6f91", outline="#ffffff", width=7)
    draw.text((W / 2, sy0 + 60), txt, font=f_selo, fill="#ffffff", anchor="mm",
              stroke_width=3, stroke_fill="#d94f73")
    for cx, cy, r in ((selo[0] - 20, sy0 + 20, 26), (selo[2] + 22, sy0 + 104, 20)):
        draw.polygon(estrela_pts(cx, cy, r, r * 0.45), fill="#ffd54f", outline="#ffffff")

    # cartão com a curiosidade
    cx0, cy0, cx1, cy1 = 70, 225, W - 70, 700
    f_txt, linhas, passo = _texto_ajustado(draw, d["curiosidade"], cx1 - cx0 - 100, cy1 - cy0 - 90)
    alt = len(linhas) * passo
    cy1 = cy0 + alt + 90
    _sombra(img, (cx0, cy0, cx1, cy1), 48)
    draw.rounded_rectangle((cx0, cy0, cx1, cy1), 48, fill="#fffdf7", outline="#ffd54f", width=8)
    y = cy0 + 45 + passo / 2
    for ln in linhas:
        draw.text((W / 2, y), ln, font=f_txt, fill="#3d2b56", anchor="mm")
        y += passo

    # personagens
    base = H - 150
    mel = _personagem("mel", 430, "feliz")
    if d.get("personagem") and d["personagem"] != "nenhum":
        outro = _personagem(d["personagem"], 470, "feliz", espelho=True)
        img.alpha_composite(mel, (150, base - mel.height))
        img.alpha_composite(outro, (W - 150 - outro.width, base - outro.height))
    else:
        img.alpha_composite(mel, ((W - mel.width) // 2, base - mel.height))

    # rodapé
    draw = ImageDraw.Draw(img)
    rod = (0, H - 118, W, H)
    draw.rectangle(rod, fill=(61, 43, 86, 235))
    f_r = fonte(40)
    draw.text((50, H - 59), d.get("referencia", ""), font=f_r, fill="#ffd54f", anchor="lm")
    draw.text((W - 50, H - 59), ARROBA, font=fonte(36, "Medium"), fill="#ffffff", anchor="rm")
    return img.convert("RGB")


# ------------------------------------------------------------ legendas
def legenda_ig(d: dict) -> str:
    partes = [f"💡 Você sabia? {d['curiosidade']}", d["explicacao"],
              f"👨‍👩‍👧 Conte pro seu filho: {d['conte_ao_filho']}",
              f"❓ Pergunte a ele: {d['pergunta']} Conta pra gente nos comentários o que ele respondeu!",
              f"📖 {d['referencia']}", "🐑 Tem historinha nova da Mel todo dia no perfil.", HASHTAGS]
    return "\n\n".join(p for p in partes if p)[:2150]


def legenda_tt(d: dict) -> str:
    return f"💡 Você sabia? {d['curiosidade']}\n📖 {d['referencia']}\n{HASHTAGS_TT}"[:2000]


# ------------------------------------------------------------ publicação
def publicar_instagram(url_img: str, texto: str, log=print) -> str:
    import requests
    from .instagram import API, _checar, _token, link_publico
    tok = _token()
    me = _checar(requests.get(f"{API}/me", params={"fields": "user_id,username", "access_token": tok}, timeout=30))
    uid = me.get("user_id") or me["id"]
    cont = _checar(requests.post(f"{API}/{uid}/media", timeout=60, data={
        "image_url": link_publico(url_img), "caption": texto, "access_token": tok}))["id"]
    import time
    for _ in range(20):
        st = _checar(requests.get(f"{API}/{cont}", timeout=30, params={"fields": "status_code", "access_token": tok}))
        if st.get("status_code") in (None, "FINISHED"):
            break
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram recusou a imagem: {st}")
        time.sleep(5)
    pub = _checar(requests.post(f"{API}/{uid}/media_publish", timeout=60, data={"creation_id": cont, "access_token": tok}))
    link = _checar(requests.get(f"{API}/{pub['id']}", timeout=30,
                                params={"fields": "permalink", "access_token": tok})).get("permalink", "")
    log(f"📸 Post publicado no Instagram: {link or pub['id']}")
    return link or pub["id"]


def imagem_para_video(jpg: Path, mp4: Path, segundos: int = 8):
    """TikTok: vira um vídeo 1080x1920 com zoom suave e a musiquinha do canal."""
    from . import audio as A
    wav = mp4.with_suffix(".wav")
    A.salvar_wav(A.gerar_musica(segundos, seed=len(jpg.name)) * 0.5, str(wav))
    fr = segundos * 30
    filtro = (f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:2[bg];"
              f"[0:v]scale=1080:-2,zoompan=z='min(zoom+0.0006,1.06)':d={fr}:s=1080x1350:fps=30[fg];"
              f"[bg][fg]overlay=0:(H-h)/2,format=yuv420p[v]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-t", str(segundos), "-i", str(jpg),
                    "-i", str(wav), "-filter_complex", filtro, "-map", "[v]", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "128k",
                    "-t", str(segundos), "-shortest", str(mp4)], check=True)
    wav.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nao-postar", action="store_true")
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    cfg = yaml.safe_load((RAIZ / "config.yaml").read_text())
    est = carregar_estado()
    agora = dt.datetime.now(FUSO)

    if a.offline:
        d = dict(EXEMPLO)
    else:
        catalogo = json.loads((RAIZ / "dados" / "historias.json").read_text(encoding="utf-8"))
        hist = escolher_historia(catalogo, est["postados"])
        tipo = TIPOS[len(est["postados"]) % len(TIPOS)]
        d = criar_texto(cfg, hist, [p["curiosidade"] for p in est["postados"]], tipo)
    print(f"💡 {d['curiosidade']} ({d['referencia']})", flush=True)

    SAIDA.mkdir(exist_ok=True)
    nome = f"vocesabia-{agora:%Y%m%d-%H%M}"
    jpg = SAIDA / f"{nome}.jpg"
    desenhar_post(d, seed=len(est["postados"]) + 1).save(jpg, quality=92)
    (SAIDA / f"{nome}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    mp4 = SAIDA / f"{nome}.mp4"
    imagem_para_video(jpg, mp4)
    print(f"🖼️  {jpg}", flush=True)
    if a.nao_postar or a.offline:
        return

    registro = {"data": agora.isoformat(timespec="minutes"), "historia_id": d["historia_id"],
                "curiosidade": d["curiosidade"], "referencia": d["referencia"]}
    resumo = os.environ.get("GITHUB_STEP_SUMMARY")
    tag = os.environ.get("TAG_FOTOS")
    if os.environ.get("IG_ACCESS_TOKEN") and tag:
        subprocess.run(["gh", "release", "upload", tag, str(jpg), "--clobber"], check=True)
        repo = os.environ.get("GITHUB_REPOSITORY", "wmatheuslacerda/historinhas-da-mel")
        try:
            registro["instagram"] = publicar_instagram(
                f"https://github.com/{repo}/releases/download/{tag}/{jpg.name}", legenda_ig(d))
        except Exception as e:  # noqa
            print(f"⚠️ Instagram falhou: {e}", flush=True)
    if os.environ.get("TT_REFRESH_TOKEN"):
        try:
            from .tiktok import enviar
            registro["tiktok"] = enviar(str(mp4), legenda_tt(d), os.environ.get("TT_MODO", "rascunho"))
        except Exception as e:  # noqa
            print(f"⚠️ TikTok falhou: {e}", flush=True)
    if resumo:
        with open(resumo, "a", encoding="utf-8") as f:
            f.write(f"\n💡 {d['curiosidade']}\n\n📸 {registro.get('instagram', '-')} · 🎵 {registro.get('tiktok', '-')}\n"
                    f"\nLegenda TikTok:\n\n```\n{legenda_tt(d)}\n```\n")
    if not registro.get("instagram") and not registro.get("tiktok"):
        raise SystemExit("Nada foi publicado")
    est["postados"].append(registro)
    salvar_estado(est)


if __name__ == "__main__":
    main()
