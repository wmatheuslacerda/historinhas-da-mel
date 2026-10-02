"""Amostra do canal Bia e Davi (ep. 1): gera as imagens das cenas e as vozes.

Roda no GitHub Actions (ramo preview-bia-e-davi). A montagem do vídeo é feita depois.
Imagens: Pollinations (grátis) com reserva no AI Horde. Vozes: ElevenLabs da conta.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.audio import salvar_wav  # noqa: E402
from src.vozes import Vozes  # noqa: E402

AQUI = Path(__file__).parent
SAIDA = AQUI / "saida"
SAIDA.mkdir(exist_ok=True)

ESTILO = ("3D animated feature film still, Pixar Disney style, soft warm cinematic lighting, "
          "gentle pastel colors, heartwarming and hopeful mood, highly detailed, expressive big eyes, "
          "vertical 9:16 composition, no text, no watermark")
BIA = ("Bia, a 7-year-old Brazilian girl with light brown skin, big round brown eyes, "
       "curly shoulder-length dark brown hair with a yellow star hair clip, "
       "wearing yellow pajamas with small white stars, holding a pink plush bunny with long floppy ears")
DAVI = ("Davi, a 9-year-old Brazilian boy with warm tan brown skin, bald head under a blue baseball cap "
        "with a small yellow lightning bolt, big friendly grin with a missing front tooth, wearing blue pajamas")
ALA = "colorful pediatric hospital ward decorated with children's drawings on the walls"

CENAS = [
    f"{BIA}, standing shy and scared at the doorway of a {ALA}, holding her mother's hand tightly, "
    "her mother is a young Brazilian woman with curly hair seen from behind, wide shot, {ESTILO}",
    f"{BIA}, sitting alone on a hospital bed hugging the pink bunny, looking sadly out of a big window, "
    f"in the blurred background a woman cries quietly in the hallway, {ALA}, melancholic soft blue light, {ESTILO}",
    f"{DAVI}, riding an IV drip pole on wheels like a scooter into a hospital room with a huge playful smile, "
    f"motion, joyful, {ALA}, {ESTILO}",
    f"{DAVI}, sitting on the edge of a hospital bed proudly showing his IV drip pole covered in rocket and star stickers, "
    f"next to him {BIA} looking curious, {ALA}, {ESTILO}",
    f"{BIA} and {DAVI} sitting together on a hospital bed laughing out loud, warm golden sunset light "
    f"through the window, {ALA}, {ESTILO}",
    f"{DAVI}, at the doorway of a hospital room looking back and winking with a thumbs up, "
    f"golden sunset light, {ALA}, {ESTILO}",
]
CENAS = [c.replace("{ESTILO}", ESTILO) for c in CENAS]

FALAS = [
    # (cena, voz, texto)
    (0, "narrador", "A Bia tinha sete anos, um coelho chamado Pipoca... e muito, muito medo."),
    (0, "bia", "Mãe... eu vou ter que dormir aqui?"),
    (1, "narrador", "O médico falou uma palavra difícil. A Bia não entendeu... mas viu a mãe chorando no corredor."),
    (2, "davi", "Ei, novata! Você pegou o melhor quarto da ala. Daqui dá pra ver o pôr do sol!"),
    (3, "bia", "Você também tá doente?"),
    (3, "davi", "Aqui a gente não fala doente. A gente fala: em missão. E esse aqui é o meu foguete!"),
    (4, "narrador", "Pela primeira vez naquele dia... a Bia riu."),
    (4, "davi", "Regra número um da missão: ninguém luta sozinho."),
    (5, "davi", "Amanhã eu te conto o segredo do soro de super-herói."),
    (5, "narrador", "Segue a gente pra descobrir o segredo do Davi."),
]

CFG = {"elevenlabs": {
    "modelo": "eleven_multilingual_v2",
    "formato": "mp3_44100_128",
    "vozes": {
        "narrador": {"voice_id": "FIEA0c5UHH9JnvWaQrXS", "tom": 1.0, "velocidade": 0.93,
                     "estabilidade": 0.5, "estilo": 0.45},                       # Michele (BR)
        "bia": {"voice_id": "y9CNRBALdlEecGD3RnmT", "tom": 1.18, "velocidade": 0.98,
                "estabilidade": 0.4, "estilo": 0.5},                             # Carla Playful afinada
        "davi": {"voice_id": "IGmfzACCDHYu8YfQJuVi", "tom": 1.14, "velocidade": 1.0,
                 "estabilidade": 0.4, "estilo": 0.5},                            # Jonas desenho afinado
    },
}}


def pollinations(prompt: str, seed: int) -> bytes | None:
    q = urllib.parse.quote(prompt, safe="")
    params = f"width=864&height=1536&seed={seed}&model=flux&nologo=true&enhance=false"
    for base in ("https://image.pollinations.ai/prompt/", "https://gen.pollinations.ai/image/"):
        for tentativa in range(3):
            try:
                r = requests.get(f"{base}{q}?{params}", timeout=180)
                tipo = r.headers.get("content-type", "")
                print(f"  pollinations {base[:30]}… {r.status_code} {tipo} {len(r.content)}b", flush=True)
                if r.status_code == 200 and tipo.startswith("image") and len(r.content) > 20000:
                    return r.content
            except Exception as e:  # noqa: BLE001
                print("  pollinations erro:", e, flush=True)
            time.sleep(8 * (tentativa + 1))
    return None


def horde(prompt: str, seed: int) -> bytes | None:
    api = "https://aihorde.net/api/v2"
    h = {"apikey": "0000000000", "Client-Agent": "bia-e-davi-preview:1.0:anon"}
    corpo = {"prompt": prompt + " ### text, watermark, deformed, ugly, scary, blood",
             "params": {"width": 576, "height": 1024, "steps": 25, "cfg_scale": 6, "seed": str(seed),
                        "sampler_name": "k_euler_a", "n": 1, "karras": True},
             "models": ["AlbedoBase XL (SDXL)", "Juggernaut XL"], "r2": True, "nsfw": False}
    try:
        r = requests.post(f"{api}/generate/async", json=corpo, headers=h, timeout=60)
        jid = r.json().get("id")
        print("  horde job", r.status_code, jid, flush=True)
        if not jid:
            print(r.text[:300])
            return None
        for _ in range(120):
            time.sleep(10)
            st = requests.get(f"{api}/generate/check/{jid}", timeout=30).json()
            if st.get("done"):
                break
        res = requests.get(f"{api}/generate/status/{jid}", timeout=60).json()
        url = res["generations"][0]["img"]
        return requests.get(url, timeout=120).content
    except Exception as e:  # noqa: BLE001
        print("  horde erro:", e, flush=True)
        return None


def main():
    # Imagens
    for i, prompt in enumerate(CENAS):
        destino = SAIDA / f"cena{i + 1}.jpg"
        if destino.exists():
            continue
        print(f"Cena {i + 1}", flush=True)
        img = pollinations(prompt, seed=4242 + i) or horde(prompt, seed=4242 + i)
        if img:
            destino.write_bytes(img)
        else:
            print(f"  !! cena {i + 1} falhou", flush=True)
        time.sleep(6)

    # Vozes
    vozes = Vozes(CFG, cache=AQUI / ".cache")
    meta = []
    for n, (cena, voz, texto) in enumerate(FALAS):
        print(f"Fala {n + 1} ({voz})", flush=True)
        fala = vozes.falar(texto, voz)
        arq = SAIDA / f"fala{n + 1:02d}.wav"
        salvar_wav(fala.audio, str(arq))
        meta.append({"arquivo": arq.name, "cena": cena, "voz": voz, "texto": texto,
                     "duracao": fala.duracao, "palavras": fala.palavras()})
    (SAIDA / "falas.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print("ok")


if __name__ == "__main__":
    main()
