"""Vozes: ElevenLabs (produção) ou espeak-ng (pré-visualização sem gastar créditos).

Cada fala retorna o áudio + o tempo de cada letra (usado para mexer a boca
dos personagens e destacar as palavras na legenda).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import requests

from .audio import SR, ffmpeg_decode, aplicar_filtro, filtro_voz, aparar, normalizar_rms

API = "https://api.elevenlabs.io/v1"


@dataclass
class Fala:
    audio: np.ndarray
    letras: list = field(default_factory=list)   # caracteres
    inicios: list = field(default_factory=list)  # segundos
    fins: list = field(default_factory=list)

    @property
    def duracao(self):
        return len(self.audio) / SR

    def palavras(self):
        """[(palavra, inicio, fim)]"""
        out, atual, ini, fim = [], "", None, None
        for c, a, b in zip(self.letras, self.inicios, self.fins):
            if c.isspace():
                if atual:
                    out.append((atual, ini, fim))
                atual, ini = "", None
                continue
            if ini is None:
                ini = a
            atual += c
            fim = b
        if atual:
            out.append((atual, ini, fim))
        return out


def _alinhamento_estimado(texto: str, dur: float, margem=0.05):
    """Sem timestamps (modo offline): distribui as letras ao longo do áudio."""
    pesos = [0.35 if c.isspace() else (2.2 if c in ",.!?;:" else 1.0) for c in texto]
    total = sum(pesos) or 1
    util = max(dur - 2 * margem, 0.1)
    t = margem
    ini, fim = [], []
    for p in pesos:
        d = util * p / total
        ini.append(t)
        fim.append(t + d)
        t += d
    return list(texto), ini, fim


class Vozes:
    def __init__(self, cfg: dict, offline: bool = False, cache: str | Path = ".cache/vozes"):
        self.cfg = cfg["elevenlabs"]
        self.offline = offline
        self.cache = Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.chave = os.environ.get("ELEVENLABS_API_KEY", "")
        if not offline and not self.chave:
            raise RuntimeError("ELEVENLABS_API_KEY não definida (coloque nos Secrets do GitHub ou no .env)")

    def config_voz(self, tipo: str) -> dict:
        vozes = self.cfg["vozes"]
        return vozes.get(tipo) or vozes.get("homem") or next(iter(vozes.values()))

    def falar(self, texto: str, tipo: str) -> Fala:
        vc = self.config_voz(tipo)
        if self.offline:
            fala = self._espeak(texto, tipo)
        else:
            fala = self._elevenlabs(texto, vc)
        filtro = filtro_voz(vc.get("tom", 1.0), vc.get("eco", False))
        if filtro:
            fala.audio = aplicar_filtro(fala.audio, filtro)
        fala.audio, corte = aparar(fala.audio)
        fala.inicios = [max(0.0, x - corte) for x in fala.inicios]
        fala.fins = [max(0.0, x - corte) for x in fala.fins]
        fala.audio = normalizar_rms(fala.audio)
        return fala

    # ------------------------------------------------ ElevenLabs
    def _elevenlabs(self, texto: str, vc: dict) -> Fala:
        corpo = {
            "text": texto,
            "model_id": self.cfg.get("modelo", "eleven_multilingual_v2"),
            "language_code": "pt",
            "voice_settings": {
                "stability": vc.get("estabilidade", 0.45),
                "similarity_boost": vc.get("similaridade", 0.8),
                "style": vc.get("estilo", 0.35),
                "use_speaker_boost": True,
                "speed": float(vc.get("velocidade", 1.0)),
            },
        }
        chave = hashlib.sha1(json.dumps([vc["voice_id"], corpo], sort_keys=True).encode()).hexdigest()
        arq = self.cache / f"{chave}.json"
        if arq.exists():
            dados = json.loads(arq.read_text())
        else:
            url = f"{API}/text-to-speech/{vc['voice_id']}/with-timestamps"
            dados = None
            for tentativa in range(5):
                r = requests.post(url, params={"output_format": self.cfg.get("formato", "mp3_44100_128")},
                                  headers={"xi-api-key": self.chave, "Content-Type": "application/json"},
                                  json=corpo, timeout=120)
                if r.status_code == 200:
                    dados = r.json()
                    break
                if r.status_code == 422 and "language_code" in corpo:
                    corpo.pop("language_code")  # modelo não aceita language_code
                    continue
                if r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(3 * (tentativa + 1))
                    continue
                raise RuntimeError(f"ElevenLabs erro {r.status_code}: {r.text[:300]}")
            if dados is None:
                raise RuntimeError("ElevenLabs não respondeu após várias tentativas")
            arq.write_text(json.dumps(dados))
        audio = ffmpeg_decode(base64.b64decode(dados["audio_base64"]))
        al = dados.get("alignment") or dados.get("normalized_alignment") or {}
        letras = al.get("characters") or []
        if letras:
            return Fala(audio, letras, al["character_start_times_seconds"], al["character_end_times_seconds"])
        return Fala(audio, *_alinhamento_estimado(texto, len(audio) / SR))

    # ------------------------------------------------ espeak-ng (offline)
    ESPEAK = {
        "narrador": ("f3", 150, 62), "menino": ("m3", 160, 80), "menina": ("f4", 160, 85),
        "homem": ("m1", 145, 45), "mulher": ("f2", 145, 55), "idoso": ("m7", 135, 35),
        "idosa": ("f1", 135, 45), "gigante": ("m2", 130, 20), "deus": ("m6", 125, 30),
        "anjo": ("f5", 140, 70), "animal": ("m4", 160, 90),
    }

    def _espeak(self, texto: str, tipo: str) -> Fala:
        var, vel, tom = self.ESPEAK.get(tipo, ("m1", 145, 50))
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            caminho = f.name
        subprocess.run(["espeak-ng", "-v", f"pt-br+{var}", "-s", str(vel), "-p", str(tom), "-w", caminho, texto],
                       check=True, capture_output=True)
        audio = ffmpeg_decode(caminho=caminho)
        os.unlink(caminho)
        return Fala(audio, *_alinhamento_estimado(texto, len(audio) / SR))


def listar_vozes():
    chave = os.environ.get("ELEVENLABS_API_KEY")
    r = requests.get(f"{API}/voices", headers={"xi-api-key": chave}, timeout=60)
    r.raise_for_status()
    return [(v["voice_id"], v["name"], (v.get("labels") or {})) for v in r.json().get("voices", [])]
