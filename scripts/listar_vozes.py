"""Mostra as vozes da sua conta ElevenLabs (para colar os IDs no config.yaml).

Uso:  ELEVENLABS_API_KEY=sua_chave python scripts/listar_vozes.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.main import carregar_env  # noqa
from src.vozes import listar_vozes  # noqa

carregar_env()
for vid, nome, rotulos in listar_vozes():
    extra = ", ".join(f"{k}: {v}" for k, v in rotulos.items())
    print(f"{vid}  {nome:25s} {extra}")
