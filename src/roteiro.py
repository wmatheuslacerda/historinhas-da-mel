"""Roteirista: escolhe a história do dia e pede o roteiro à API do Claude."""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

from .cenarios import CENARIOS, PERIODOS
from .personagens import PRESETS, EMOCOES, criar_personagem

RAIZ = Path(__file__).resolve().parent.parent
EFEITOS = ["nenhum", "brilhos", "luz", "chuva", "estrelas", "arco_iris", "coracoes"]
ACOES = ["nenhuma", "pular", "comemorar", "tremer", "cair", "toctoc", "rir", "chorar", "tchau"]
VOZES = ["narrador", "menino", "menina", "homem", "mulher", "idoso", "idosa", "gigante", "deus", "anjo", "animal"]

ABORDAGENS = [
    "Conte do jeito clássico, com a Mel narrando e os personagens falando.",
    "Conte pelo olhar de um personagem secundário ou de um animal que estava lá (ex.: a ovelhinha, o jumentinho, um passarinho), sempre fiel ao relato bíblico.",
    "Inclua uma frase curtinha que se repete 2 ou 3 vezes, como um refrão que a criança consegue repetir junto.",
    "Comece com uma pergunta do dia a dia da criança (medo do escuro, dividir brinquedo, ficar com raiva...) e mostre como a história responde.",
    "Faça a Mel convidar a criança a participar: imitar um som, contar até três, bater palmas — sem pedir para curtir ou se inscrever.",
    "Destaque um detalhe curioso e verdadeiro do texto bíblico que as crianças costumam não conhecer.",
]


# ------------------------------------------------------------ escolha
def pascoa(ano: int) -> dt.date:
    a, b, c = ano % 19, ano // 100, ano % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return dt.date(ano, mes, dia)


def escolher_historia(catalogo: list, postados: list, hoje: dt.date):
    """Escolhe a próxima história sem repetir no ciclo; alterna Antigo/Novo Testamento."""
    n = len(catalogo)
    ciclo = len(postados) // len([h for h in catalogo if not h.get('tag')])
    n = len([h for h in catalogo if not h.get('tag')])
    abordagem = ABORDAGENS[ciclo % len(ABORDAGENS)]
    usados_ciclo = {p["historia_id"] for p in postados[ciclo * n:]}
    recentes = {p["historia_id"] for p in postados[-40:]}
    normais = [h for h in catalogo if not h.get("tag")]  # Natal/Páscoa só na época certa
    livres = [h for h in normais if h["id"] not in usados_ciclo] or normais

    # datas especiais
    tag = None
    if dt.date(hoje.year, 12, 15) <= hoje <= dt.date(hoje.year, 12, 25):
        tag = "natal"
    pa = pascoa(hoje.year)
    if pa - dt.timedelta(days=7) <= hoje <= pa + dt.timedelta(days=1):
        tag = "pascoa"
    if tag:
        especiais = [h for h in catalogo if h.get("tag") == tag and h["id"] not in recentes]
        if especiais:
            return especiais[0], abordagem

    ultimo_t = None
    if postados:
        ult = next((h for h in catalogo if h["id"] == postados[-1]["historia_id"]), None)
        ultimo_t = ult and ult["t"]
    preferidos = [h for h in livres if h["t"] != ultimo_t] or livres
    return preferidos[0], abordagem


# ------------------------------------------------------------ prompt
def _catalogo_personagens():
    return "\n".join(f"- {k}: {v.get('nome', k)} (voz {v.get('voz')})" for k, v in PRESETS.items())


SISTEMA = """Você é roteirista de um canal infantil cristão no YouTube Shorts chamado "{canal}".
A apresentadora é a Mel, uma ovelhinha fofa com laço cor-de-rosa. Público: {publico}.

REGRAS DE CONTEÚDO
- Seja FIEL ao relato bíblico. A criatividade fica na linguagem, no humor leve e nos detalhes de cena — nunca invente fatos, milagres, falas de Deus que mudem o sentido, nem doutrina.
- Linguagem de hoje, brasileira, carinhosa e simples: frases curtas (até 10 palavras), palavras que uma criança de 4 anos entende, onomatopeias divertidas (tum!, splash!, zuuum!).
- Nada assustador: sem sangue, morte explícita, violência ou tristeza pesada. Suavize (ex.: "o gigante caiu no chão, tum!").
- Deus nunca aparece desenhado: quando Deus fala, use quem="deus" (vira uma luz do céu). Jesus pode aparecer normalmente.
- Nunca peça para curtir, comentar, se inscrever ou comprar nada (conteúdo infantil).
- Nada de nomes de marcas, pessoas reais ou referências à atualidade.

ESTRUTURA (vídeo de até ~55 segundos)
- Total de {pmin} a {pmax} palavras somando todas as falas.
- 5 a 7 cenas. Cada cena tem 1 a 4 falas.
- Cena 1: cenário "abertura", só a Mel, 1 fala-gancho animada (até 12 palavras) que desperta curiosidade.
- Cenas do meio: a história. Use quem="narrador" para a Mel narrar (ela aparece num selinho) e deixe os personagens falarem bastante.
- Última cena: cenário "abertura", só a Mel: a lição em 1 frase + despedida carinhosa (ex.: "Tchau, amiguinho! Deus te ama!").
- No máximo 3 personagens por cena.

PERSONAGENS
Use preferencialmente o catálogo abaixo (mantém a aparência igual em todos os vídeos). No "elenco", cada id aponta para {{"preset": "<id do catálogo>"}}.
Se precisar de alguém que não existe, crie com atributos: tipo (humano|ovelha|leao|pomba|baleia|jumento|camelo|cobra), nome, voz, idade (crianca|adulto|idoso|bebe), genero (m|f), pele (clara|media|morena|escura), cabelo (preto|castanho|ruivo|loiro|grisalho|branco), estilo_cabelo (curto|cacheado|longo|careca|coque|tranca), barba (nenhuma|curta|longa), roupa (#hex), roupa2 (#hex), cobertura (nenhuma|lenco|veu|coroa|capacete|faixa|nemes), acessorio (nenhum|cajado|espada|lanca|harpa|pergaminho|cesta|funda|lampiao|pao|ramo), manto (bool), armadura (bool), asas (bool), gigante (bool).
Vozes possíveis: {vozes}.

CATÁLOGO:
{catalogo}

Valores permitidos:
- cenario: {cenarios}
- periodo: {periodos}
- efeito: {efeitos}
- emocao: {emocoes}
- acao: {acoes} ("cair" pode usar "alvo" para indicar quem cai quando o narrador fala)
  Ações só da Mel: "toctoc" (bate na tela e fala com a criança), "rir" (risadinha, escreva "hihihi" na fala),
  "chorar" (só em momento emocionante), "tchau" (acena com a patinha na despedida).
"""

FERRAMENTA = {
    "name": "entregar_roteiro",
    "description": "Entrega o roteiro final do vídeo.",
    "input_schema": {
        "type": "object",
        "properties": {
            "titulo": {"type": "string", "description": "Título do YouTube, até 90 caracteres, com 1 emoji e terminando em #shorts"},
            "titulo_curto": {"type": "string", "description": "Nome da história em até 24 caracteres (aparece no vídeo)"},
            "descricao": {"type": "string", "description": "2 a 4 frases para os pais + referência bíblica + lição"},
            "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 15},
            "licao": {"type": "string"},
            "elenco": {"type": "object", "additionalProperties": {"type": "object"}},
            "cenas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "cenario": {"type": "string", "enum": CENARIOS},
                        "periodo": {"type": "string", "enum": PERIODOS},
                        "efeito": {"type": "string", "enum": EFEITOS},
                        "personagens": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
                        "falas": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "quem": {"type": "string"},
                                    "texto": {"type": "string"},
                                    "emocao": {"type": "string", "enum": EMOCOES},
                                    "acao": {"type": "string", "enum": ACOES},
                                    "alvo": {"type": "string"},
                                },
                                "required": ["quem", "texto"],
                            },
                        },
                    },
                    "required": ["cenario", "personagens", "falas"],
                },
            },
        },
        "required": ["titulo", "titulo_curto", "descricao", "tags", "licao", "elenco", "cenas"],
    },
}


# ------------------------------------------------------------ validação
def validar(r: dict, cfg: dict) -> dict:
    elenco = {}
    for pid, spec in (r.get("elenco") or {}).items():
        if pid in ("narrador", "deus"):
            continue
        if isinstance(spec, str):
            spec = {"preset": spec}
        if "preset" in spec and spec["preset"] not in PRESETS:
            spec = {k: v for k, v in spec.items() if k != "preset"} or {"preset": "homem"}
        if "preset" not in spec and "tipo" not in spec and pid in PRESETS:
            spec = {"preset": pid, **spec}
        try:
            criar_personagem(spec)
        except Exception:
            spec = {"preset": "homem", "nome": spec.get("nome", pid)}
        elenco[pid] = spec
    elenco["mel"] = {"preset": "mel"}
    r["elenco"] = elenco

    cenas = []
    for c in r.get("cenas", []):
        c["cenario"] = c.get("cenario") if c.get("cenario") in CENARIOS else "campo"
        c["periodo"] = c.get("periodo") if c.get("periodo") in PERIODOS else "dia"
        if c.get("efeito") in (None, "nenhum") or c.get("efeito") not in EFEITOS:
            c.pop("efeito", None)
        c["personagens"] = [p for p in c.get("personagens", []) if p in elenco][:3]
        falas = []
        for f in c.get("falas", []):
            texto = " ".join(str(f.get("texto", "")).split())
            if not texto:
                continue
            f["texto"] = texto
            if f.get("quem") == "mel" and "mel" not in c["personagens"]:
                f["quem"] = "narrador"
            if f.get("quem") not in elenco and f.get("quem") not in ("narrador", "deus"):
                f["quem"] = "narrador"
            if f["quem"] in elenco and f["quem"] not in c["personagens"] and f["quem"] != "mel":
                if len(c["personagens"]) < 3:
                    c["personagens"].append(f["quem"])
                else:
                    f["quem"] = "narrador"
            if f.get("emocao") not in EMOCOES:
                f.pop("emocao", None)
            if f.get("acao") in (None, "nenhuma") or f.get("acao") not in ACOES:
                f.pop("acao", None)
            if f.get("alvo") and f["alvo"] not in elenco:
                f.pop("alvo")
            falas.append(f)
        if falas:
            c["falas"] = falas
            cenas.append(c)
    if len(cenas) < 3:
        raise ValueError("roteiro com poucas cenas")
    r["cenas"] = cenas
    palavras = sum(len(f["texto"].split()) for c in cenas for f in c["falas"])
    if palavras > cfg["roteiro"]["palavras_max"] + 30:
        raise ValueError(f"roteiro longo demais ({palavras} palavras)")
    r["titulo"] = r.get("titulo", "")[:95]
    if "#shorts" not in r["titulo"].lower() and len(r["titulo"]) < 88:
        r["titulo"] += " #shorts"
    r["titulo_curto"] = (r.get("titulo_curto") or r["titulo"])[:28]
    return r


def voz_de(roteiro: dict, quem: str) -> str:
    if quem in ("narrador", "mel"):
        return "narrador"
    if quem == "deus":
        return "deus"
    spec = roteiro["elenco"].get(quem, {})
    if "voz" in spec:
        return spec["voz"]
    return PRESETS.get(spec.get("preset", ""), {}).get("voz", "homem")


# ------------------------------------------------------------ Claude
class Roteirista:
    def __init__(self, cfg: dict):
        import anthropic
        self.cfg = cfg
        self.cliente = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def criar(self, historia: dict, abordagem: str, recentes: list[str]) -> dict:
        c = self.cfg
        sistema = SISTEMA.format(
            canal=c["canal"]["nome"], publico=c["canal"]["publico"],
            pmin=c["roteiro"]["palavras_min"], pmax=c["roteiro"]["palavras_max"],
            vozes=", ".join(VOZES), catalogo=_catalogo_personagens(), cenarios=", ".join(CENARIOS),
            periodos=", ".join(PERIODOS), efeitos=", ".join(EFEITOS), emocoes=", ".join(EMOCOES),
            acoes=", ".join(ACOES))
        pedido = (f"História de hoje: {historia['titulo']} ({historia['ref']}).\n"
                  f"Resumo: {historia['ideia']}.\n"
                  f"Abordagem deste vídeo: {abordagem}\n"
                  f"Títulos recentes do canal (não repita o mesmo jeito de contar): {'; '.join(recentes[-12:]) or 'nenhum'}.\n"
                  "Escreva o roteiro e entregue com a ferramenta entregar_roteiro.")
        erro = None
        for tentativa in range(c["roteiro"].get("tentativas", 3)):
            msgs = [{"role": "user", "content": pedido + (f"\n\nA tentativa anterior falhou: {erro}. Corrija." if erro else "")}]
            resp = self.cliente.messages.create(
                model=c["roteiro"]["modelo"], max_tokens=4000, system=sistema, messages=msgs,
                tools=[FERRAMENTA], tool_choice={"type": "tool", "name": "entregar_roteiro"})
            bloco = next((b for b in resp.content if b.type == "tool_use"), None)
            if bloco is None:
                erro = "não usou a ferramenta"
                continue
            try:
                r = validar(dict(bloco.input), c)
                r["historia_id"] = historia["id"]
                r["referencia"] = historia["ref"]
                r["abordagem"] = abordagem
                return r
            except Exception as e:  # noqa
                erro = str(e)
        raise RuntimeError(f"Não consegui um roteiro válido: {erro}")
