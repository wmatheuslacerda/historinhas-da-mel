"""Rode UMA VEZ no seu computador para autorizar o robô a postar no canal.

1. Baixe o "client_secret.json" do Google Cloud (veja o README) e coloque nesta pasta.
2. pip install google-auth-oauthlib
3. python scripts/autorizar_youtube.py
4. Vai abrir o navegador: entre na conta Google e ESCOLHA O CANAL das historinhas.
5. Copie os 3 valores que aparecerem para os Secrets do GitHub.
"""
import json
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]

arquivo = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).with_name("client_secret.json"))
if not arquivo.exists():
    sys.exit(f"Não achei {arquivo}. Baixe o JSON do cliente OAuth (tipo 'App para computador').")

flow = InstalledAppFlow.from_client_secrets_file(str(arquivo), SCOPES)
cred = flow.run_local_server(port=0, access_type="offline", prompt="consent")
dados = json.loads(arquivo.read_text())
cliente = dados.get("installed") or dados.get("web")

try:
    from googleapiclient.discovery import build
    canal = build("youtube", "v3", credentials=cred).channels().list(part="snippet", mine=True).execute()
    nome = canal["items"][0]["snippet"]["title"] if canal.get("items") else "(nenhum canal encontrado!)"
except Exception:
    nome = "(não consegui confirmar o nome)"

print("\n✅ Autorizado no canal:", nome)
print("\nCole estes valores nos Secrets do GitHub (Settings → Secrets and variables → Actions):\n")
print("YT_CLIENT_ID     =", cliente["client_id"])
print("YT_CLIENT_SECRET =", cliente["client_secret"])
print("YT_REFRESH_TOKEN =", cred.refresh_token)
