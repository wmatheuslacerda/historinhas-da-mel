"""Monta o vídeo vertical do ep. 1 a partir de saida/ (imagens + falas)."""
from __future__ import annotations

import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

AQUI = Path(__file__).parent
SAIDA = AQUI / "saida"
TMP = AQUI / "tmp"
TMP.mkdir(exist_ok=True)
SR = 44100
FPS = 30
W, H = 1080, 1920
FONTES = "/usr/share/fonts/truetype/google-fonts"

CORES = {"narrador": "FFFFFF", "bia": "FFD54F", "davi": "64C8FF"}  # RGB
NOMES = {"bia": "BIA", "davi": "DAVI"}


def ler_wav(p: Path) -> np.ndarray:
    with wave.open(str(p)) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32767
        assert w.getframerate() == SR
    return a


# ------------------------------------------------------------------ música
def nota_piano(f, dur, vol):
    n = int(dur * SR)
    t = np.arange(n) / SR
    env = np.exp(-t * 2.2) * (1 - np.exp(-t * 300))
    s = sum(a * np.sin(2 * np.pi * f * k * t) for k, a in ((1, 1), (2, 0.35), (3, 0.12), (4, 0.05)))
    return (s * env * vol).astype(np.float32)


def nota_pad(f, dur, vol):
    n = int(dur * SR)
    t = np.arange(n) / SR
    env = np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / 1.2)
    s = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.003 * t) + 0.3 * np.sin(2 * np.pi * f * 2 * t)
    return (s * env * vol).astype(np.float32)


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def musica(dur):
    buf = np.zeros(int((dur + 4) * SR), np.float32)

    def add(x, t):
        i = int(t * SR)
        j = min(len(buf), i + len(x))
        buf[i:j] += x[: j - i]

    beat = 60 / 68
    prog = [(60, "M"), (55, "M"), (57, "m"), (53, "M")]  # C G Am F
    t, c = 0.0, 0
    while t < dur + 1:
        raiz, tipo = prog[c % 4]
        ac = [0, 4, 7] if tipo == "M" else [0, 3, 7]
        comp = 4 * beat
        add(nota_pad(hz(raiz - 12), comp + 0.6, 0.05), t)
        add(nota_pad(hz(raiz - 12 + ac[1]), comp + 0.6, 0.035), t)
        add(nota_piano(hz(raiz - 24), comp * 1.1, 0.10), t)
        arp = [0, 1, 2, 1, 2, 1, 2, 1] if c % 2 == 0 else [0, 2, 1, 2, 0, 2, 1, 2]
        for k, g in enumerate(arp):
            add(nota_piano(hz(raiz + ac[g] + (12 if k in (2, 6) else 0)), beat * 2, 0.055), t + k * beat / 2)
        t += comp
        c += 1
    buf = buf[: int(dur * SR)]
    fi, fo = int(1.0 * SR), int(2.5 * SR)
    buf[:fi] *= np.linspace(0, 1, fi)
    buf[-fo:] *= np.linspace(1, 0, fo)
    return buf / (np.abs(buf).max() + 1e-9)


# ------------------------------------------------------------------ legendas ASS
def ts(s):
    s = max(0, s)
    h, r = divmod(s, 3600)
    m, r = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{r:05.2f}"


def bgr(rgb):
    return f"&H00{rgb[4:6]}{rgb[2:4]}{rgb[0:2]}"


def legendas(falas, inicios, dur_total, caminho):
    linhas = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 0", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding",
        "Style: Leg,Poppins,78,&H00FFFFFF,&H00FFFFFF,&H00241A12,&H96000000,1,0,0,0,100,100,0,0,1,7,3,2,90,90,520,1",
        "Style: Nome,Poppins,44,&H00FFFFFF,&H00FFFFFF,&H00241A12,&H96000000,1,0,0,0,100,100,2,0,1,5,2,2,90,90,700,1",
        "Style: Titulo,Poppins,96,&H00FFFFFF,&H00FFFFFF,&H00241A12,&H96000000,1,0,0,0,100,100,1,0,1,8,4,8,60,60,260,1",
        "Style: Sub,Poppins,52,&H0064C8FF,&H00FFFFFF,&H00241A12,&H96000000,1,0,0,0,100,100,2,0,1,5,2,8,60,60,390,1",
        "Style: Marca,Poppins,36,&H80FFFFFF,&H00FFFFFF,&H80241A12,&H00000000,1,0,0,0,100,100,1,0,1,2,0,8,60,60,120,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    ev = linhas.append
    # título do episódio
    ev(f"Dialogue: 2,{ts(0)},{ts(3.2)},Titulo,,0,0,0,,{{\\fad(250,400)}}Bia e Davi")
    ev(f"Dialogue: 2,{ts(0.2)},{ts(3.2)},Sub,,0,0,0,,{{\\fad(250,400)}}EPISÓDIO 1  •  A NOVATA")
    ev(f"Dialogue: 1,{ts(3.2)},{ts(dur_total)},Marca,,0,0,0,,{{\\fad(400,0)}}@biaedaviofc")
    # falas: blocos de até 4 palavras, palavra atual destacada
    for fala, t0 in zip(falas, inicios):
        cor = bgr(CORES[fala["voz"]])
        pal = fala["palavras"]
        blocos, atual = [], []
        for p in pal:
            atual.append(p)
            if len(atual) >= 4 or p[0][-1] in ".!?…":
                blocos.append(atual)
                atual = []
        if atual:
            blocos.append(atual)
        for bi, bloco in enumerate(blocos):
            fim_bloco = (blocos[bi + 1][0][1] if bi + 1 < len(blocos) else fala["duracao"] + 0.25)
            for wi, (w, a, _b) in enumerate(bloco):
                ini = t0 + a
                fim = t0 + (bloco[wi + 1][1] if wi + 1 < len(bloco) else fim_bloco)
                partes = []
                for wj, (w2, _, _) in enumerate(bloco):
                    if wj == wi:
                        partes.append(f"{{\\c{cor}\\fscx112\\fscy112}}{w2}{{\\r}}")
                    else:
                        partes.append(w2)
                txt = " ".join(partes)
                ev(f"Dialogue: 0,{ts(ini)},{ts(fim)},Leg,,0,0,0,,{txt}")
        if fala["voz"] in NOMES:
            ev(f"Dialogue: 0,{ts(t0 + pal[0][1] - 0.05)},{ts(t0 + fala['duracao'] + 0.2)},Nome,,0,0,0,,"
               f"{{\\c{cor}}}{NOMES[fala['voz']]}")
    # fim
    ev(f"Dialogue: 2,{ts(dur_total - 2.6)},{ts(dur_total)},Titulo,,0,0,0,,{{\\fad(300,0)\\pos(540,820)\\an5}}Continua...")
    caminho.write_text("\n".join(linhas), encoding="utf-8")


# ------------------------------------------------------------------ vídeo
def clipe_cena(img: Path, dur: float, idx: int, saida: Path):
    n = int(round(dur * FPS))
    # zoom lento alternando direção; imagem ampliada 2x antes do zoompan para não tremer
    if idx % 2 == 0:
        z = f"1.0+0.10*on/{n}"
    else:
        z = f"1.10-0.10*on/{n}"
    vf = (f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase:flags=lanczos,crop={W * 2}:{H * 2},"
          f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={FPS},"
          f"unsharp=5:5:0.7:5:5:0.0,eq=saturation=1.05,format=yuv420p")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(img), "-vf", vf,
                    "-frames:v", str(n), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(saida)],
                   check=True)


def main():
    falas = json.loads((SAIDA / "falas.json").read_text())
    audios = [ler_wav(SAIDA / f["arquivo"]) for f in falas]

    # linha do tempo das falas
    t = 1.0
    inicios = []
    for i, (f, a) in enumerate(zip(falas, audios)):
        inicios.append(t)
        prox = falas[i + 1] if i + 1 < len(falas) else None
        pausa = 0.35
        if prox and prox["cena"] != f["cena"]:
            pausa = 0.75
        if f["voz"] == "narrador" and prox and prox["voz"] != "narrador":
            pausa += 0.15
        t += len(a) / SR + pausa
    dur_total = t + 2.4

    # áudio: vozes + música abafada sob as falas
    voz = np.zeros(int(dur_total * SR) + SR, np.float32)
    for a, t0 in zip(audios, inicios):
        i = int(t0 * SR)
        voz[i:i + len(a)] += a
    voz = voz[: int(dur_total * SR)]
    mus = musica(dur_total)
    env = np.abs(voz)
    k = int(0.25 * SR)
    env = np.convolve(env, np.ones(k) / k, mode="same")
    duck = 1 - 0.55 * np.clip(env / 0.05, 0, 1)
    mix = voz * 0.95 + mus * 0.16 * duck
    mix = mix / max(1.0, np.abs(mix).max() / 0.97)
    pcm = (mix * 32767).astype(np.int16)
    wav_mix = TMP / "mix.wav"
    with wave.open(str(wav_mix), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())

    # tempo de cada cena
    n_cenas = max(f["cena"] for f in falas) + 1
    ini_cena = []
    for c in range(n_cenas):
        primeira = next(i for i, f in enumerate(falas) if f["cena"] == c)
        ini_cena.append(0.0 if c == 0 else inicios[primeira] - 0.35)
    XF = 0.5
    clipes = []
    for c in range(n_cenas):
        fim = ini_cena[c + 1] if c + 1 < n_cenas else dur_total
        dur = fim - ini_cena[c] + (XF if c + 1 < n_cenas else 0)
        out = TMP / f"c{c}.mp4"
        clipe_cena(SAIDA / f"cena{c + 1}.png", dur, c, out)
        clipes.append((out, dur))
        print(f"cena {c + 1}: {dur:.1f}s", flush=True)

    # encadeia com crossfade
    entradas, filtro, ult, acum = [], [], "0:v", 0.0
    for i, (p, d) in enumerate(clipes):
        entradas += ["-i", str(p)]
    acum = clipes[0][1]
    for i in range(1, len(clipes)):
        off = acum - XF
        lab = f"v{i}"
        filtro.append(f"[{ult}][{i}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[{lab}]")
        ult = lab
        acum = off + clipes[i][1]
    ass = TMP / "leg.ass"
    legendas(falas, inicios, dur_total, ass)
    filtro.append(f"[{ult}]fade=t=in:st=0:d=0.6,fade=t=out:st={dur_total - 0.8:.2f}:d=0.8,"
                  f"subtitles={ass}:fontsdir={FONTES}[vout]")
    final = SAIDA.parent / "bia-e-davi-ep1.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", *entradas, "-i", str(wav_mix),
           "-filter_complex", ";".join(filtro), "-map", "[vout]", "-map", f"{len(clipes)}:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-t", f"{dur_total:.2f}", "-movflags", "+faststart", str(final)]
    subprocess.run(cmd, check=True)
    print(final, f"{dur_total:.1f}s")


if __name__ == "__main__":
    sys.exit(main())
