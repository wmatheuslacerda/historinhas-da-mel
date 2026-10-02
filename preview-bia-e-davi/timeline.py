"""Gera o áudio final (vozes ElevenLabs + música) e o roteiro.json com tempos para o Remotion."""
import json
import wave
from pathlib import Path

import numpy as np

from montar import SR, ler_wav, musica

AQUI = Path(__file__).parent
SAIDA = AQUI / "saida"
PUB = AQUI / "remotion" / "public"
PUB.mkdir(parents=True, exist_ok=True)
FPS = 30

falas = json.loads((SAIDA / "falas.json").read_text())
audios = [ler_wav(SAIDA / f["arquivo"]) for f in falas]

t = 1.6  # tempo para o título aparecer
inicios = []
for i, (f, a) in enumerate(zip(falas, audios)):
    inicios.append(t)
    prox = falas[i + 1] if i + 1 < len(falas) else None
    pausa = 0.35
    if prox and prox["cena"] != f["cena"]:
        pausa = 0.8
    if f["voz"] == "narrador" and prox and prox["voz"] != "narrador":
        pausa += 0.15
    if f["cena"] == 4 and prox and prox["cena"] == 4 and f["voz"] == "narrador":
        pausa += 0.9  # espaço para a risada
    t += len(a) / SR + pausa
dur = t + 2.6
n = int(round(dur * FPS))

voz = np.zeros(int(dur * SR) + SR, np.float32)
falante = {"narrador": np.zeros(n), "bia": np.zeros(n), "davi": np.zeros(n)}
for f, a, t0 in zip(falas, audios, inicios):
    i = int(t0 * SR)
    voz[i:i + len(a)] += a
    # envelope por quadro (para o personagem "falar")
    for k in range(int(len(a) / SR * FPS)):
        q = int(round(t0 * FPS)) + k
        if q < n:
            seg = a[int(k / FPS * SR):int((k + 1) / FPS * SR)]
            falante[f["voz"]][q] = max(falante[f["voz"]][q], float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0)
voz = voz[: int(dur * SR)]
mus = musica(dur)
env = np.convolve(np.abs(voz), np.ones(int(0.25 * SR)) / int(0.25 * SR), mode="same")
mix = voz * 0.95 + mus * 0.16 * (1 - 0.55 * np.clip(env / 0.05, 0, 1))
mix = mix / max(1.0, np.abs(mix).max() / 0.97)
with wave.open(str(PUB / "audio.wav"), "w") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())

for k in falante:
    v = falante[k]
    if v.max() > 0:
        v = np.clip(v / (np.percentile(v[v > 0], 90) + 1e-6), 0, 1)
    falante[k] = [round(float(x), 2) for x in v]

n_cenas = max(f["cena"] for f in falas) + 1
cenas = []
for c in range(n_cenas):
    prim = next(i for i, f in enumerate(falas) if f["cena"] == c)
    ini = 0.0 if c == 0 else inicios[prim] - 0.45
    cenas.append(ini)
cenas = [{"ini": round(a * FPS), "fim": round((cenas[i + 1] if i + 1 < n_cenas else dur) * FPS)}
         for i, a in enumerate(cenas)]

roteiro = {
    "fps": FPS, "duracao": n,
    "cenas": cenas,
    "falas": [{"voz": f["voz"], "cena": f["cena"], "texto": f["texto"], "ini": round(t0 * FPS),
               "fim": round((t0 + f["duracao"]) * FPS),
               "palavras": [[w, round((t0 + a) * FPS), round((t0 + b) * FPS)] for w, a, b in f["palavras"]]}
              for f, t0 in zip(falas, inicios)],
    "fala": falante,
}
(PUB / "roteiro.json").write_text(json.dumps(roteiro, ensure_ascii=False))
print(f"{dur:.1f}s {n} quadros", [(c["ini"], c["fim"]) for c in cenas])
