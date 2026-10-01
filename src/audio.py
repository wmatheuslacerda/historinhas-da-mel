"""Áudio: conversões com ffmpeg, efeitos de voz, música de fundo original e mixagem."""
from __future__ import annotations

import math
import random
import subprocess
import tempfile
from pathlib import Path

import numpy as np

SR = 44100


def ffmpeg_decode(dados: bytes | None = None, caminho: str | None = None, filtro: str | None = None) -> np.ndarray:
    """Decodifica qualquer áudio para float32 mono 44.1 kHz (opcionalmente aplicando um filtro)."""
    cmd = ["ffmpeg", "-v", "error", "-i", caminho or "pipe:0"]
    if filtro:
        cmd += ["-af", filtro]
    cmd += ["-ac", "1", "-ar", str(SR), "-f", "f32le", "pipe:1"]
    out = subprocess.run(cmd, input=dados, capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32).copy()


def aplicar_filtro(audio: np.ndarray, filtro: str) -> np.ndarray:
    cmd = ["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0",
           "-af", filtro, "-ac", "1", "-ar", str(SR), "-f", "f32le", "pipe:1"]
    out = subprocess.run(cmd, input=audio.astype(np.float32).tobytes(), capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32).copy()


def filtro_voz(tom: float = 1.0, eco: bool = False, velocidade: float = 1.0) -> str | None:
    """tom muda a altura sem mudar a duração; velocidade muda a duração."""
    partes = []
    if abs(tom - 1.0) > 0.01:
        partes += [f"asetrate={SR}*{tom:.4f}", f"aresample={SR}", f"atempo={1 / tom:.4f}"]
    if abs(velocidade - 1.0) > 0.01:
        partes.append(f"atempo={velocidade:.4f}")
    if eco:
        partes.append("aecho=0.85:0.6:70|140:0.28|0.14")
    return ",".join(partes) or None


def salvar_wav(audio: np.ndarray, caminho: str):
    pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0", caminho],
                   input=pcm.tobytes(), check=True)


def aparar(audio: np.ndarray, limiar: float = 0.01):
    """Remove silêncio do início/fim. Retorna (audio, segundos cortados no início)."""
    idx = np.where(np.abs(audio) > limiar)[0]
    if len(idx) == 0:
        return audio, 0.0
    ini = max(0, idx[0] - int(0.03 * SR))
    fim = min(len(audio), idx[-1] + int(0.08 * SR))
    return audio[ini:fim], ini / SR


def normalizar_rms(audio: np.ndarray, alvo_db: float = -17.0) -> np.ndarray:
    rms = np.sqrt(np.mean(audio ** 2)) + 1e-9
    ganho = 10 ** (alvo_db / 20) / rms
    out = audio * ganho
    pico = np.max(np.abs(out)) + 1e-9
    if pico > 0.97:
        out *= 0.97 / pico
    return out


def envelope(audio: np.ndarray, fps: int) -> np.ndarray:
    """Volume (RMS) por quadro de vídeo, 0..1."""
    n = max(1, int(math.ceil(len(audio) / SR * fps)))
    passo = SR / fps
    env = np.zeros(n)
    for i in range(n):
        seg = audio[int(i * passo):int((i + 1) * passo)]
        env[i] = np.sqrt(np.mean(seg ** 2)) if len(seg) else 0
    m = env.max() or 1
    return env / m


# ------------------------------------------------------------ música
NOTAS_MAIOR = [0, 2, 4, 5, 7, 9, 11]


def _hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def _nota(buf, t0, midi, dur, vol, timbre="marimba"):
    i0 = int(t0 * SR)
    n = int(dur * SR)
    if i0 >= len(buf) or n <= 0:
        return
    n = min(n, len(buf) - i0)
    t = np.arange(n) / SR
    f = _hz(midi)
    if timbre == "marimba":
        s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * f * 3.93 * t) * np.exp(-t * 18)
        env = np.exp(-t * 5.5)
    elif timbre == "sino":
        s = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 2.76 * t) + 0.15 * np.sin(2 * np.pi * f * 5.4 * t)
        env = np.exp(-t * 3.2)
    elif timbre == "baixo":
        s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
        env = np.minimum(t / 0.01, 1) * np.exp(-t * 2.2)
    else:  # pad
        s = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.003 * t) + 0.3 * np.sin(2 * np.pi * f * 2 * t)
        env = np.minimum(t / 0.4, 1) * np.minimum((dur - t) / 0.4, 1).clip(0, 1)
    ataque = np.minimum(t / 0.004, 1)
    buf[i0:i0 + n] += (s * env * ataque * vol).astype(np.float32)


def gerar_musica(duracao: float, seed: int) -> np.ndarray:
    """Musiquinha alegre e original (sem direitos autorais), diferente a cada vídeo."""
    rng = random.Random(seed)
    buf = np.zeros(int((duracao + 2) * SR), dtype=np.float32)
    raiz = rng.choice([60, 62, 65, 67, 57])
    bpm = rng.uniform(88, 104)
    beat = 60 / bpm
    progressoes = [[0, 7, 9, 5], [0, 5, 7, 0], [0, 9, 5, 7], [0, 5, 9, 7], [0, 4, 5, 7]]
    prog = rng.choice(progressoes)
    padrao = rng.choice([[0, 1, 2, 1, 0, 1, 2, 1], [0, 2, 1, 2, 0, 2, 1, 2], [0, 1, 2, 3, 2, 1, 0, 1]])
    timbre_arp = rng.choice(["marimba", "marimba", "sino"])
    menor = {9, 4}
    compasso = 4 * beat
    t, i = 0.0, 0
    while t < duracao + 1:
        grau = prog[i % len(prog)]
        base = raiz + grau
        acorde = [0, 3, 7, 12] if grau in menor else [0, 4, 7, 12]
        _nota(buf, t, base - 24, compasso * 0.95, 0.30, "baixo")
        _nota(buf, t, base - 12, compasso, 0.05, "pad")
        _nota(buf, t, base - 12 + acorde[1], compasso, 0.04, "pad")
        for k in range(8):
            _nota(buf, t + k * beat / 2, base + acorde[padrao[k]], beat * 1.2, 0.12 if k % 2 == 0 else 0.08, timbre_arp)
        # melodia simples
        for k in range(0, 4, rng.choice([1, 2])):
            if rng.random() < 0.7:
                nota = base + 12 + rng.choice(acorde[:3])
                _nota(buf, t + k * beat, nota, beat * 1.5, 0.09, "sino")
        # chocalho leve
        for k in range(8):
            if k % 2 == 1:
                i0 = int((t + k * beat / 2) * SR)
                n = int(0.05 * SR)
                if i0 + n < len(buf):
                    ruido = np.random.default_rng(i0).standard_normal(n).astype(np.float32)
                    buf[i0:i0 + n] += ruido * np.exp(-np.arange(n) / SR * 70) * 0.025
        t += compasso
        i += 1
    buf = buf[: int(duracao * SR)]
    # fade in/out
    fi, fo = int(0.3 * SR), int(1.8 * SR)
    buf[:fi] *= np.linspace(0, 1, fi)
    buf[-fo:] *= np.linspace(1, 0, fo)
    return buf / (np.max(np.abs(buf)) + 1e-9)


def efeito_plim(vol=0.18) -> np.ndarray:
    buf = np.zeros(int(0.8 * SR), dtype=np.float32)
    _nota(buf, 0.0, 84, 0.6, vol, "sino")
    _nota(buf, 0.09, 91, 0.6, vol * 0.8, "sino")
    return buf


def mixar(voz: np.ndarray, musica: np.ndarray, efeitos: np.ndarray, vol_musica: float = 0.16) -> np.ndarray:
    n = max(len(voz), len(musica), len(efeitos))
    v = np.pad(voz, (0, n - len(voz)))
    m = np.pad(musica, (0, n - len(musica)))
    e = np.pad(efeitos, (0, n - len(efeitos)))
    # "ducking": abaixa a música quando alguém fala
    ativo = (np.abs(v) > 0.02).astype(np.float32)
    janela = int(0.25 * SR)
    kernel = np.ones(janela, dtype=np.float32) / janela
    suave = np.convolve(ativo, kernel, mode="same")
    suave = np.clip(suave * 3, 0, 1)
    ganho = vol_musica * (1 - 0.55 * suave)
    out = v + m * ganho + e
    pico = np.max(np.abs(out)) + 1e-9
    return (out * (0.95 / pico)).astype(np.float32) if pico > 0.95 else out.astype(np.float32)


def efeito_toc(vol=0.55) -> np.ndarray:
    """Batida de "toc" (madeira/vidro abafado) para a Mel batendo na tela."""
    n = int(0.22 * SR)
    tt = np.arange(n) / SR
    corpo = np.sin(2 * np.pi * 180 * tt) * np.exp(-tt * 38)
    clique = np.sin(2 * np.pi * 1250 * tt) * np.exp(-tt * 140) * 0.5
    ruido = np.random.default_rng(3).standard_normal(n) * np.exp(-tt * 220) * 0.25
    return ((corpo + clique + ruido) * vol).astype(np.float32)
