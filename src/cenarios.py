"""Cenários desenhados em Python (1080x1920, vertical)."""
from __future__ import annotations

import math
import random

import numpy as np
from PIL import Image, ImageFilter

from .desenho import Pintor, rgba, escurecer, clarear, mistura, estrela_pts

W, H = 1080, 1920
CHAO = 1180      # onde começa o chão
PES = 1330       # linha dos pés dos personagens
SS = 2

CENARIOS = ["abertura", "campo", "deserto", "egito", "mar", "oceano", "barco", "cidade", "palacio",
            "cova", "montanha", "rio", "arca", "dentro_peixe", "estabulo", "templo", "jardim", "casa",
            "fornalha", "muralha"]
PERIODOS = ["dia", "tarde", "noite", "nublado"]

CEUS = {
    "dia": ("#5ec2f7", "#dff4ff"),
    "tarde": ("#ff8a65", "#ffe3a3"),
    "noite": ("#16224f", "#4b3c86"),
    "nublado": ("#8fa6bd", "#dfe7ef"),
}


# ----------------------------------------------------------- utilidades
def gradiente(p: Pintor, y0, y1, c0, c1, mask=None):
    a, b = np.array(rgba(c0), float), np.array(rgba(c1), float)
    h = int((y1 - y0) * p.ss)
    t = np.linspace(0, 1, max(h, 1))[:, None, None]
    arr = (a + (b - a) * t).astype(np.uint8)
    arr = np.repeat(arr, p.size[0], axis=1)
    img = Image.fromarray(arr, "RGBA")
    if mask is None:
        p.img.paste(img, (0, int(y0 * p.ss)))
    else:
        full = Image.new("RGBA", p.size, (0, 0, 0, 0))
        full.paste(img, (0, int(y0 * p.ss)))
        p.img.paste(full, (0, 0), mask)


def ceu(p, periodo, rng):
    c0, c1 = CEUS.get(periodo, CEUS["dia"])
    gradiente(p, 0, H, c0, c1)
    if periodo == "dia":
        brilho = p.circ(p.m(), 830, 430, 190).filter(ImageFilter.GaussianBlur(60))
        p.img.paste(rgba("#fff6c9"), (0, 0) + p.size, brilho.point(lambda v: v * 0.55))
        p.pintar(p.circ(p.m(), 830, 430, 84), "#ffe066", contorno=0)
    elif periodo == "tarde":
        brilho = p.circ(p.m(), 300, 900, 260).filter(ImageFilter.GaussianBlur(80))
        p.img.paste(rgba("#fff0b3"), (0, 0) + p.size, brilho.point(lambda v: v * 0.6))
        p.pintar(p.circ(p.m(), 300, 900, 120), "#ffc857", contorno=0)
    elif periodo == "noite":
        for _ in range(70):
            x, y, r = rng.uniform(0, W), rng.uniform(0, CHAO - 150), rng.uniform(1.5, 4)
            p.pintar(p.circ(p.m(), x, y, r), "#fffbe0", contorno=0)
        lua = Pintor.menos(p.circ(p.m(), 820, 380, 80), p.circ(p.m(), 855, 355, 70))
        brilho = p.circ(p.m(), 810, 390, 150).filter(ImageFilter.GaussianBlur(50))
        p.img.paste(rgba("#fff9d6"), (0, 0) + p.size, brilho.point(lambda v: v * 0.35))
        p.pintar(lua, "#fff4c2", contorno=0)


def colina(p, y_base, amp, cor, seed, freq=1.0, ate=H):
    rnd = random.Random(seed)
    fases = [rnd.uniform(0, 6.28) for _ in range(3)]
    pts = []
    for x in range(-20, W + 40, 20):
        y = y_base - amp * (0.55 * math.sin(x / 260 * freq + fases[0]) + 0.3 * math.sin(x / 130 * freq + fases[1])
                            + 0.15 * math.sin(x / 60 * freq + fases[2]))
        pts.append((x, y))
    pts += [(W + 40, ate), (-20, ate)]
    m = p.poly(p.m(), pts)
    p.pintar(m, cor, contorno=0)
    return m


def chao(p, cor0, cor1, y=CHAO):
    gradiente(p, y, H, cor0, cor1)


def ajustar_periodo(cor, periodo):
    if periodo == "noite":
        return mistura(cor, "#1b2350", 0.55)
    if periodo == "tarde":
        return mistura(cor, "#ff9e6b", 0.18)
    if periodo == "nublado":
        return mistura(cor, "#9aa8b5", 0.25)
    return rgba(cor)


def arvore(p, x, y, s, cor, fruta=None, rng=None):
    p.pintar(p.rect(p.m(), (x - 16 * s, y - 150 * s, x + 16 * s, y), r=8 * s), "#8d5a32", contorno=3)
    copa = Pintor.soma(p.circ(p.m(), x, y - 190 * s, 80 * s), p.circ(p.m(), x - 62 * s, y - 150 * s, 58 * s),
                       p.circ(p.m(), x + 62 * s, y - 150 * s, 58 * s))
    p.pintar(copa, cor, contorno=3, sombra=0.5, sombra_dx=-10, sombra_dy=-10)
    if fruta and rng:
        for _ in range(6):
            fx, fy = x + rng.uniform(-80, 80) * s, y - 150 * s + rng.uniform(-80, 30) * s
            p.pintar(p.circ(p.m(), fx, fy, 11 * s), fruta, contorno=2.5)


def palmeira(p, x, y, s, periodo="dia"):
    tronco = p.linha(p.m(), [(x, y), (x + 14 * s, y - 120 * s), (x + 30 * s, y - 250 * s)], 26 * s)
    p.pintar(tronco, ajustar_periodo("#a0703c", periodo), contorno=3)
    tx, ty = x + 30 * s, y - 250 * s
    for ang in (200, 240, 290, 330, 20):
        a = math.radians(ang)
        pts = [(tx, ty), (tx + 70 * s * math.cos(a), ty + 30 * s * math.sin(a) - 30 * s),
               (tx + 140 * s * math.cos(a), ty + 80 * s * max(math.sin(a), 0.2))]
        p.pintar(p.linha(p.m(), pts, 24 * s), ajustar_periodo("#43a047", periodo), contorno=3)


def casa(p, x, y, w, h, cor, periodo, janela=True):
    c = ajustar_periodo(cor, periodo)
    p.pintar(p.rect(p.m(), (x, y - h, x + w, y), r=10), c, contorno=3.5, sombra=0.4)
    p.pintar(p.rect(p.m(), (x - 8, y - h - 14, x + w + 8, y - h + 8), r=6), escurecer(c, 0.85), contorno=3)
    dx = x + w * 0.5
    porta = Pintor.soma(p.rect(p.m(), (dx - 24, y - 70, dx + 24, y)), p.circ(p.m(), dx, y - 70, 24))
    p.pintar(porta, ajustar_periodo("#6d4c41", periodo), contorno=3)
    if janela and w > 110:
        for jx in (x + w * 0.2, x + w * 0.8):
            j = Pintor.soma(p.rect(p.m(), (jx - 14, y - h + 40, jx + 14, y - h + 76)), p.circ(p.m(), jx, y - h + 40, 14))
            p.pintar(j, "#ffe8a3" if periodo == "noite" else ajustar_periodo("#5d4037", periodo), contorno=2.5)


def flores(p, rng, y0, y1, n=40):
    for _ in range(n):
        x, y = rng.uniform(0, W), rng.uniform(y0, y1)
        cor = rng.choice(["#ff7eb6", "#ffd23f", "#ffffff", "#b388ff", "#ff8a65"])
        for a in range(0, 360, 72):
            p.pintar(p.circ(p.m(), x + 9 * math.cos(math.radians(a)), y + 9 * math.sin(math.radians(a)), 7), cor, contorno=0)
        p.pintar(p.circ(p.m(), x, y, 6), "#ffb300", contorno=0)


def capim(p, rng, y0, y1, cor, n=70):
    for _ in range(n):
        x, y = rng.uniform(0, W), rng.uniform(y0, y1)
        for d in (-10, 0, 10):
            p.pintar(p.linha(p.m(), [(x, y), (x + d * 1.4, y - 26)], 5), cor, contorno=0)


def pedras(p, rng, y0, y1, cor, n=14):
    for _ in range(n):
        x, y, r = rng.uniform(0, W), rng.uniform(y0, y1), rng.uniform(14, 34)
        p.pintar(p.ell(p.m(), (x - r, y - r * 0.6, x + r, y + r * 0.6)), cor, contorno=2.5, sombra=0.4)


def colunas(p, xs, y_top, y_bot, cor, periodo):
    c = ajustar_periodo(cor, periodo)
    for x in xs:
        p.pintar(p.rect(p.m(), (x - 42, y_top, x + 42, y_bot)), c, contorno=3, sombra=0.5)
        for i in range(-2, 3):
            p.pintar(p.linha(p.m(), [(x + i * 14, y_top + 40), (x + i * 14, y_bot - 40)], 3), escurecer(c, 0.88), contorno=0)
        p.pintar(p.rect(p.m(), (x - 62, y_top - 30, x + 62, y_top + 6), r=6), c, contorno=3)
        p.pintar(p.rect(p.m(), (x - 62, y_bot - 6, x + 62, y_bot + 26), r=6), c, contorno=3)


def ondas(p, y0, y1, cor, rng, esp=46):
    for y in range(int(y0), int(y1), esp):
        fase = rng.uniform(0, 6)
        pts = [(x, y + 8 * math.sin(x / 55 + fase)) for x in range(-20, W + 40, 20)]
        p.pintar(p.linha(p.m(), pts, 6), cor, contorno=0)


# ----------------------------------------------------------- cenários
def desenhar(nome: str, periodo: str = "dia", seed: int = 1):
    """Retorna (fundo RGB, frente RGBA|None, info)."""
    rng = random.Random(seed)
    p = Pintor(W, H, SS)
    frente = None
    info = {"nuvens": periodo in ("dia", "tarde", "nublado")}
    A = lambda c: ajustar_periodo(c, periodo)

    if nome not in CENARIOS:
        nome = "campo"

    if nome == "abertura":
        info["nuvens"] = False
        gradiente(p, 0, H, "#ffd86b", "#ff9f7a")
        cx, cy = W / 2, 860
        for i in range(24):
            a0, a1 = math.radians(i * 15), math.radians(i * 15 + 7.5)
            pts = [(cx, cy), (cx + 2400 * math.cos(a0), cy + 2400 * math.sin(a0)), (cx + 2400 * math.cos(a1), cy + 2400 * math.sin(a1))]
            p.pintar(p.poly(p.m(), pts), "#ffe79a", contorno=0, alpha=150)
        for _ in range(60):
            x, y = rng.uniform(0, W), rng.uniform(250, 1800)
            cor = rng.choice(["#ff6f91", "#6ec6ff", "#8bd17c", "#ffffff", "#b388ff"])
            p.pintar(p.circ(p.m(), x, y, rng.uniform(6, 14)), cor, contorno=0)
        colina(p, CHAO + 60, 40, "#8bd17c", seed, 0.8)
        gradiente(p, CHAO + 160, H, "#7cc86b", "#5aa84e", mask=None)

    elif nome in ("campo", "jardim", "arca", "rio", "muralha"):
        ceu(p, periodo, rng)
        colina(p, 1010, 70, A("#a5d6a7" if nome != "muralha" else "#d7c49e"), seed, 0.9)
        if nome == "arca":
            m = p.poly(p.m(), [(120, 900), (960, 900), (880, 1080), (200, 1080)])
            p.pintar(m, A("#8d5a32"), contorno=4, sombra=0.5)
            for y in range(930, 1080, 36):
                p.pintar(p.inter(p.linha(p.m(), [(100, y), (980, y)], 4), m), A("#6d4424"), contorno=0)
            p.pintar(p.rect(p.m(), (330, 760, 750, 905), r=10), A("#a1683a"), contorno=4, sombra=0.4)
            p.pintar(p.poly(p.m(), [(300, 770), (540, 650), (780, 770)]), A("#6d4424"), contorno=4)
            for x in (420, 540, 660):
                p.pintar(p.rect(p.m(), (x - 26, 800, x + 26, 850), r=6), A("#4e342e"), contorno=3)
        if nome == "muralha":
            m = p.rect(p.m(), (0, 820, W, 1120))
            p.pintar(m, A("#d9b779"), contorno=4, sombra=0.4)
            for x in range(0, W, 90):
                p.pintar(p.rect(p.m(), (x, 780, x + 55, 830)), A("#d9b779"), contorno=4)
            for y in range(860, 1120, 52):
                for x in range((y // 52 % 2) * 60, W, 120):
                    p.pintar(p.linha(p.m(), [(x, y), (x + 100, y)], 3), A("#b8955a"), contorno=0)
            porta = Pintor.soma(p.rect(p.m(), (450, 960, 630, 1120)), p.circ(p.m(), 540, 960, 90))
            p.pintar(porta, A("#6d4c41"), contorno=4)
        colina(p, 1120, 45, A("#81c784"), seed + 1, 1.3)
        if nome in ("campo", "jardim"):
            for x, s in ((110, 0.9), (960, 1.05)) if nome == "campo" else ((90, 1.1), (330, 0.8), (780, 0.85), (1000, 1.15)):
                arvore(p, x, 1150, s, A("#66bb6a" if nome == "campo" else "#4caf50"),
                       fruta="#e53935" if nome == "jardim" else None, rng=rng)
        chao(p, A("#8bd17c"), A("#5fae52"))
        if nome == "rio":
            m = p.poly(p.m(), [(0, 1190), (W, 1150), (W, 1270), (0, 1300)])
            p.pintar(m, A("#4fb3e8"), contorno=0)
            ondas(p, 1180, 1290, A("#9fdcff"), rng, 34)
            for x in list(range(20, 260, 34)) + list(range(820, 1080, 34)):
                p.pintar(p.linha(p.m(), [(x, 1300), (x + rng.uniform(-8, 8), 1200)], 7), A("#6d9f3a"), contorno=0)
                p.pintar(p.ell(p.m(), (x - 7, 1190, x + 11, 1240)), A("#8d6e3a"), contorno=0)
        capim(p, rng, CHAO + 40, H - 40, A("#4f9d44"))
        if nome in ("campo", "jardim") and periodo != "noite":
            flores(p, rng, CHAO + 60, H - 60, 45 if nome == "jardim" else 25)

    elif nome in ("deserto", "egito"):
        ceu(p, periodo, rng)
        if nome == "egito":
            for x, s in ((240, 1.0), (560, 0.7), (820, 0.85)):
                m = p.poly(p.m(), [(x - 230 * s, 1050), (x, 1050 - 300 * s), (x + 230 * s, 1050)])
                p.pintar(m, A("#e3b566"), contorno=3.5)
                p.pintar(p.poly(p.m(), [(x, 1050 - 300 * s), (x + 230 * s, 1050), (x + 40 * s, 1050)]), A("#c99543"), contorno=0)
        colina(p, 1060, 60, A("#f3cf87"), seed, 0.7)
        colina(p, 1140, 40, A("#ebbd6c"), seed + 3, 1.1)
        chao(p, A("#f0c878"), A("#dca85a"))
        if nome == "egito":
            m = p.poly(p.m(), [(0, 1180), (W, 1160), (W, 1230), (0, 1250)])
            p.pintar(m, A("#4fb3e8"), contorno=0)
        for x, s in ((90, 1.1), (1000, 0.9)):
            palmeira(p, x, 1260, s, periodo)
        pedras(p, rng, CHAO + 150, H - 40, A("#c4914c"), 8)

    elif nome in ("mar", "oceano", "barco"):
        ceu(p, periodo if periodo != "nublado" else "nublado", rng)
        hz = 980
        gradiente(p, hz, H, A("#3ba3e0"), A("#1f6fb5"))
        ondas(p, hz + 30, H, A("#7fcfff"), rng, 52)
        if nome == "mar":
            m = p.poly(p.m(), [(0, 1200), (W, 1150), (W, H), (0, H)])
            gradiente(p, 1150, H, A("#f3d69a"), A("#e2b872"), mask=m)
            p.pintar(p.linha(p.m(), [(x, 1200 - 50 * x / W + 6 * math.sin(x / 40)) for x in range(0, W + 20, 20)], 12),
                     "#ffffff", contorno=0, alpha=200)
            palmeira(p, 980, 1300, 1.0, periodo)
            pedras(p, rng, 1260, H - 40, A("#c9a36a"), 6)
        if nome == "barco":
            m = p.poly(p.m(), [(-40, 1250), (W + 40, 1250), (W + 40, H), (-40, H)])
            p.pintar(m, A("#b07a45"), contorno=4)
            for y in range(1290, H, 70):
                p.pintar(p.linha(p.m(), [(-20, y), (W + 20, y)], 4), A("#8d5a32"), contorno=0)
            p.pintar(p.rect(p.m(), (-20, 1230, W + 20, 1262), r=10), A("#8d5a32"), contorno=4)
            p.pintar(p.rect(p.m(), (930, 300, 962, 1240)), A("#8d5a32"), contorno=4)
            vela = p.poly(p.m(), [(930, 330), (930, 900), (620, 880)])
            p.pintar(vela, A("#fff8e7"), contorno=4, sombra=0.4)
        if nome == "oceano":
            fr = Pintor(W, H, 1)
            pts = [(x, 1250 + 14 * math.sin(x / 60)) for x in range(-20, W + 40, 20)] + [(W + 40, H), (-20, H)]
            m = fr.poly(fr.m(), pts)
            full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            g = Pintor(W, H, 1)
            gradiente(g, 1230, H, A("#3ba3e0"), A("#1a5f9e"))
            frente = Image.composite(g.img, full, m)
            fp = Pintor(W, H, 1)
            fp.img = frente
            ondas(fp, 1270, H, A("#86d3ff"), rng, 58)
            fp.pintar(fp.linha(fp.m(), pts[:-2], 8), "#e8f7ff", contorno=0)
            frente = fp.img

    elif nome == "cidade":
        ceu(p, periodo, rng)
        colina(p, 1000, 40, A("#cbb58c"), seed, 0.8)
        for i, (x, w, h, cor) in enumerate([(-30, 220, 260, "#e8cf9f"), (170, 180, 330, "#f1dcb1"), (330, 240, 220, "#e0c08b"),
                                            (560, 200, 300, "#efd6a6"), (740, 180, 240, "#e6c893"), (900, 220, 320, "#f0d9ad")]):
            casa(p, x, 1190, w, h, cor, periodo)
        chao(p, A("#e8c992"), A("#d4ae70"))
        for y in range(1230, H, 90):
            for x in range(((y // 90) % 2) * 70, W, 140):
                p.pintar(p.rect(p.m(), (x + 6, y + 6, x + 130, y + 80), r=12), A("#dcb97f"), contorno=0)

    elif nome in ("palacio", "templo"):
        info["nuvens"] = False
        parede = "#8e5a9e" if nome == "palacio" else "#d9c7a0"
        gradiente(p, 0, CHAO, A(clarear(parede, 0.1)), A(escurecer(parede, 0.8)))
        colunas(p, (120, 400, 680, 960), 200, CHAO - 20, "#f3e6c8" if nome == "palacio" else "#fff3d6", periodo)
        if nome == "palacio":
            for lado in (-1, 1):
                x0 = 0 if lado < 0 else W
                m = p.poly(p.m(), [(x0, 0), (x0 - lado * 300, 0), (x0 - lado * 120, 520), (x0, 700)])
                p.pintar(m, A("#c62828"), contorno=3, sombra=0.4)
            p.pintar(p.rect(p.m(), (0, 0, W, 60)), A("#ffc629"), contorno=3)
            trono = Pintor.soma(p.rect(p.m(), (430, 760, 650, 1100), r=30), p.rect(p.m(), (400, 960, 680, 1040), r=16))
            p.pintar(trono, A("#ffc629"), contorno=4, sombra=0.5)
            p.pintar(p.rect(p.m(), (460, 800, 620, 1000), r=20), A("#c62828"), contorno=3)
        else:
            for x in (260, 820):
                p.pintar(p.rect(p.m(), (x - 18, 700, x + 18, 900), r=6), A("#ffc629"), contorno=3)
                p.pintar(p.ell(p.m(), (x - 50, 660, x + 50, 710)), A("#ffc629"), contorno=3)
                p.pintar(p.ell(p.m(), (x - 16, 610, x + 16, 668)), "#ffb300", contorno=0)
        chao(p, A("#e8dcc4"), A("#cbb994"))
        for y in range(CHAO + 20, H, 110):
            for x in range(((y // 110) % 2) * 110, W, 220):
                p.pintar(p.rect(p.m(), (x, y, x + 110, y + 110)), A("#d9caa8"), contorno=0)

    elif nome in ("cova", "dentro_peixe", "fornalha"):
        info["nuvens"] = False
        if nome == "cova":
            gradiente(p, 0, H, "#5a4636", "#2e231b")
            luz = p.poly(p.m(), [(420, 0), (660, 0), (820, CHAO + 200), (260, CHAO + 200)]).filter(ImageFilter.GaussianBlur(40))
            p.img.paste(rgba("#fff3c4"), (0, 0) + p.size, luz.point(lambda v: v * 0.35))
            for _ in range(22):
                x, y, r = rng.uniform(0, W), rng.uniform(0, CHAO), rng.uniform(40, 110)
                p.pintar(p.ell(p.m(), (x - r, y - r * 0.7, x + r, y + r * 0.7)), rng.choice(["#6d5645", "#5d4a3b", "#7a624f"]), contorno=0)
            chao(p, "#8a6d55", "#5a4636")
            pedras(p, rng, CHAO + 100, H - 40, "#6d5645", 10)
        elif nome == "dentro_peixe":
            gradiente(p, 0, H, "#b8455a", "#6e1f33")
            for i, x in enumerate(range(-100, W + 200, 220)):
                p.pintar(p.arco(p.m(), (x - 200, 150, x + 200, CHAO + 300), 180, 360, 26), "#e98aa0", contorno=0)
            chao(p, "#c85a6e", "#7e2a3f", y=CHAO + 40)
            gradiente(p, CHAO + 150, H, "#4fb3e8", "#1f6fb5")
        else:  # fornalha
            gradiente(p, 0, H, "#3b2a3a", "#1c1420")
            m = Pintor.soma(p.rect(p.m(), (140, 380, 940, CHAO), r=40), p.circ(p.m(), 540, 420, 400))
            p.pintar(m, "#7a4a3a", contorno=4)
            boca = Pintor.soma(p.rect(p.m(), (260, 620, 820, CHAO), r=30), p.circ(p.m(), 540, 640, 280))
            gradiente(p, 350, CHAO, "#ffd54f", "#ff6f00", mask=boca)
            chao(p, "#5d4037", "#2e1f1a")

    elif nome == "montanha":
        ceu(p, periodo, rng)
        m = p.poly(p.m(), [(-100, CHAO), (540, 380), (1180, CHAO)])
        p.pintar(m, A("#a1887f"), contorno=0)
        p.pintar(p.poly(p.m(), [(540, 380), (1180, CHAO), (700, CHAO)]), A("#8d6e63"), contorno=0)
        p.pintar(p.poly(p.m(), [(540, 380), (440, 540), (500, 520), (560, 560), (640, 530)]), "#ffffff", contorno=0)
        colina(p, 1140, 40, A("#bcaaa4"), seed, 1.2)
        chao(p, A("#c7b299"), A("#a38a6c"))
        pedras(p, rng, CHAO + 80, H - 40, A("#8d7b68"), 14)

    elif nome == "estabulo":
        ceu(p, "noite" if periodo == "dia" else periodo, rng)
        for r, a in ((140, 0.25), (70, 0.5)):
            b = p.circ(p.m(), 540, 260, r).filter(ImageFilter.GaussianBlur(40))
            p.img.paste(rgba("#fff8d0"), (0, 0) + p.size, b.point(lambda v: int(v * a)))
        p.pintar(p.poly(p.m(), estrela_pts(540, 260, 70, 26, 5)), "#ffe36e", contorno=0)
        colina(p, 1050, 50, "#3d4f6b", seed)
        est = p.rect(p.m(), (110, 640, 970, CHAO + 30))
        p.pintar(est, "#8d5a32", contorno=4, sombra=0.4)
        p.pintar(p.rect(p.m(), (160, 700, 920, CHAO + 30)), "#5d3a1f", contorno=0)
        p.pintar(p.poly(p.m(), [(60, 690), (540, 470), (1020, 690)]), "#a1683a", contorno=4)
        for x in (110, 950):
            p.pintar(p.rect(p.m(), (x, 640, x + 30, CHAO + 30)), "#6d4424", contorno=3)
        chao(p, "#d9b25c", "#b58b3a")
        capim(p, rng, CHAO, H - 30, "#e6c46b", 90)
        mj = Pintor.soma(p.poly(p.m(), [(400, 1110), (680, 1110), (640, 1200), (440, 1200)]))
        p.pintar(mj, "#a1683a", contorno=4)
        p.pintar(p.ell(p.m(), (400, 1080, 680, 1130)), "#f0cf6b", contorno=3)

    elif nome == "casa":
        info["nuvens"] = False
        gradiente(p, 0, CHAO, A("#f2d7b0"), A("#d9b88c"))
        jan = p.rect(p.m(), (650, 380, 930, 700), r=20)
        g = Pintor(W, H, SS)
        ceu(g, periodo, rng)
        p.img.paste(g.img, (0, 0), jan)
        p.pintar(Pintor.menos(p.dilatar(jan, 14), jan), A("#8d5a32"), contorno=3)
        p.pintar(p.rect(p.m(), (120, 480, 460, 510), r=6), A("#8d5a32"), contorno=3)
        for i, x in enumerate((150, 230, 320, 400)):
            p.pintar(p.ell(p.m(), (x - 30, 400, x + 30, 482)), A(["#c77d3a", "#b0bec5", "#e0a458", "#8d6e63"][i]), contorno=3)
        p.pintar(p.rect(p.m(), (100, 940, 520, 980), r=10), A("#a1683a"), contorno=3.5)
        for x in (140, 480):
            p.pintar(p.rect(p.m(), (x - 12, 970, x + 12, 1160)), A("#8d5a32"), contorno=3)
        p.pintar(p.ell(p.m(), (230, 890, 330, 945)), A("#c77d3a"), contorno=3)
        chao(p, A("#c99f6c"), A("#a57c4c"))

    fundo = p.reduzir(1).convert("RGB")
    return fundo, frente, info


def nuvem_sprite(rng, escala=1.0, cor="#ffffff"):
    p = Pintor(420, 200, 2)
    m = Pintor.soma(p.ell(p.m(), (20, 90, 400, 180)), p.circ(p.m(), 140, 95, 70), p.circ(p.m(), 250, 80, 85), p.circ(p.m(), 330, 110, 55))
    p.pintar(m, cor, contorno=0)
    p.pintar(p.inter(m, p.abaixo_de(150)), mistura(cor, "#b8d8f0", 0.35), contorno=0)
    img = p.reduzir(escala)
    return img
