"""Personagens desenhados 100% em Python (estilo desenho infantil "chibi").

Cada personagem é gerado a partir de atributos (pele, cabelo, roupa,
barba, cobertura da cabeça, acessório...). Existe um catálogo de
personagens bíblicos prontos (PRESETS) para manter a aparência igual
em todos os vídeos, e o roteirista pode criar novos por atributos.
"""
from __future__ import annotations

import math
from functools import lru_cache

from PIL import Image

from .desenho import Pintor, rgba, escurecer, clarear, estrela_pts

# ------------------------------------------------------------------ cores
PELES = {"clara": "#f6d2b8", "media": "#e8b48f", "morena": "#c98e62", "escura": "#8d5a3b"}
CABELOS = {"preto": "#2e2420", "castanho": "#6b4226", "ruivo": "#b5562b", "loiro": "#e0b04e",
           "grisalho": "#b8b0a8", "branco": "#f1ede6"}
EMOCOES = ["neutro", "feliz", "triste", "assustado", "surpreso", "bravo"]
FORMAS_BOCA = ["fechada", "a", "e", "o", "m", "pequena"]


def _cor(v, tabela, padrao):
    if not v:
        return tabela[padrao]
    if isinstance(v, str) and v.startswith("#"):
        return v
    return tabela.get(v, tabela[padrao])


# ------------------------------------------------------- rostos (comum)
def desenhar_olhos(p: Pintor, emocao: str, fechados: bool, centros, k: float = 1.0,
                   cor_sobrancelha="#3a2a22", sobrancelha=True, bochecha=True, pupila_dx=4):
    susto = emocao in ("assustado", "surpreso")
    ow, oh = 20 * k, 26 * k
    if susto:
        ow, oh = ow * 1.12, oh * 1.12
    for i, (ex, ey) in enumerate(centros):
        if fechados:
            m = p.arco(p.m(), (ex - ow, ey - oh * 0.55, ex + ow, ey + oh * 0.55), 15, 165, 6 * k)
            p.pintar(m, "#3a2a22", contorno=0)
        else:
            m = p.ell(p.m(), (ex - ow, ey - oh, ex + ow, ey + oh))
            p.pintar(m, "#ffffff", contorno=3.2 * k)
            pr = (0.62 if not susto else 0.46)
            px, py = ex + pupila_dx * k, ey + 3 * k
            m = p.ell(p.m(), (px - ow * pr, py - oh * pr, px + ow * pr, py + oh * pr))
            p.pintar(m, "#2b1d14", contorno=0)
            m = p.circ(p.m(), px - ow * pr * 0.35, py - oh * pr * 0.45, 5.5 * k)
            p.pintar(m, "#ffffff", contorno=0)
            m = p.circ(p.m(), px + ow * pr * 0.3, py + oh * pr * 0.35, 2.5 * k)
            p.pintar(m, "#ffffff", contorno=0)
        if sobrancelha:
            by = ey - oh - 12 * k - (8 * k if susto else 0) - (3 * k if emocao == "feliz" else 0)
            lado = -1 if i == 0 else 1  # -1 = olho esquerdo (interno fica à direita)
            a, b = ex - 17 * k, ex + 17 * k
            if emocao == "triste":
                ya, yb = (by + 5 * k, by - 7 * k) if lado < 0 else (by - 7 * k, by + 5 * k)
                pts = [(a, ya), (b, yb)]
            elif emocao == "bravo":
                ya, yb = (by - 7 * k, by + 6 * k) if lado < 0 else (by + 6 * k, by - 7 * k)
                pts = [(a, ya), (b, yb)]
            else:
                pts = [(a, by + 3 * k), (ex, by - 3 * k), (b, by + 3 * k)]
            p.pintar(p.linha(p.m(), pts, 7 * k), cor_sobrancelha, contorno=0)
    if bochecha and emocao not in ("bravo",):
        for (ex, ey) in centros[:2]:
            dx = -1 if ex == centros[0][0] and len(centros) > 1 else 1
            cx = ex + dx * 16 * k
            m = p.ell(p.m(), (cx - 17 * k, ey + oh + 4 * k, cx + 17 * k, ey + oh + 20 * k))
            p.pintar(m, "#ff8f9c", contorno=0, alpha=120)


def desenhar_boca(p: Pintor, forma: str, emocao: str, mx: float, my: float, k: float = 1.0):
    escuro, lingua = "#7a2430", "#ff7b8a"
    if forma == "fechada":
        if emocao in ("assustado", "surpreso"):
            forma = "o" if emocao == "surpreso" else "pequena"
        elif emocao == "triste":
            m = p.arco(p.m(), (mx - 20 * k, my + 2 * k, mx + 20 * k, my + 26 * k), 200, 340, 6 * k)
            p.pintar(m, "#3a2a22", contorno=0)
            return
        elif emocao == "bravo":
            p.pintar(p.linha(p.m(), [(mx - 17 * k, my + 6 * k), (mx + 17 * k, my + 3 * k)], 6 * k),
                     "#3a2a22", contorno=0)
            return
        elif emocao == "neutro":
            m = p.arco(p.m(), (mx - 18 * k, my - 8 * k, mx + 18 * k, my + 8 * k), 20, 160, 6 * k)
            p.pintar(m, "#3a2a22", contorno=0)
            return
        else:  # feliz
            m = p.ell(p.m(), (mx - 26 * k, my - 16 * k, mx + 26 * k, my + 22 * k))
            m = p.inter(m, p.abaixo_de(my + 2 * k))
            p.pintar(m, escuro, contorno=3.5 * k)
            t = p.inter(m, p.ell(p.m(), (mx - 15 * k, my + 8 * k, mx + 15 * k, my + 30 * k)))
            p.pintar(t, lingua, contorno=0)
            return
    if forma == "m":
        p.pintar(p.linha(p.m(), [(mx - 16 * k, my + 4 * k), (mx + 16 * k, my + 4 * k)], 6.5 * k),
                 "#3a2a22", contorno=0)
        return
    if forma == "a":
        m = p.inter(p.ell(p.m(), (mx - 30 * k, my - 22 * k, mx + 30 * k, my + 36 * k)), p.abaixo_de(my - 6 * k))
        dentes = (mx - 22 * k, my - 7 * k, mx + 22 * k, my + 1 * k)
    elif forma == "e":
        m = p.inter(p.ell(p.m(), (mx - 34 * k, my - 14 * k, mx + 34 * k, my + 22 * k)), p.abaixo_de(my - 4 * k))
        dentes = (mx - 26 * k, my - 5 * k, mx + 26 * k, my + 2 * k)
    elif forma == "o":
        m = p.ell(p.m(), (mx - 17 * k, my - 14 * k, mx + 17 * k, my + 24 * k))
        dentes = None
    else:  # pequena
        m = p.ell(p.m(), (mx - 19 * k, my - 3 * k, mx + 19 * k, my + 17 * k))
        dentes = None
    p.pintar(m, escuro, contorno=3.5 * k)
    t = p.inter(m, p.ell(p.m(), (mx - 17 * k, my + 10 * k, mx + 17 * k, my + 40 * k)))
    p.pintar(t, lingua, contorno=0)
    if dentes:
        p.pintar(p.inter(m, p.rect(p.m(), dentes)), "#ffffff", contorno=0)


# ------------------------------------------------------------ base
class Personagem:
    W = 460
    H = 700
    altura_px = 560
    flutua = 0          # deslocamento vertical (ex.: pomba voando)
    tem_boca = True

    def __init__(self, spec: dict):
        self.spec = spec
        self.voz = spec.get("voz", "homem")
        self.nome = spec.get("nome", "")
        self.geometria()
        esc = spec.get("escala")
        if esc:
            self.altura_px = self.altura_px * float(esc)
        self.escala = self.altura_px / self.H
        self._cache = {}

    # subclasses definem
    def geometria(self): ...
    def desenhar_corpo(self, p: Pintor): ...
    def desenhar_cabeca(self, p: Pintor, emocao: str, fechados: bool): ...
    def desenhar_boca(self, p: Pintor, forma: str, emocao: str): ...

    @property
    def pivo(self):
        return (self.pivo_1x[0] * self.escala, self.pivo_1x[1] * self.escala)

    def sprite_corpo(self):
        if "corpo" not in self._cache:
            p = Pintor(self.W, self.H)
            self.desenhar_corpo(p)
            self._cache["corpo"] = p.reduzir(self.escala)
        return self._cache["corpo"]

    def sprite_cabeca(self, emocao="feliz", fechados=False, boca="fechada"):
        chave = ("cab", emocao, fechados, boca)
        if chave not in self._cache:
            base_k = ("base", emocao, fechados)
            if base_k not in self._cache:
                p = Pintor(self.W, self.H)
                self.desenhar_cabeca(p, emocao, fechados)
                self._cache[base_k] = p.reduzir(self.escala)
            img = self._cache[base_k].copy()
            if self.tem_boca:
                bk = ("boca", boca, emocao)
                if bk not in self._cache:
                    p = Pintor(self.W, self.H)
                    self.desenhar_boca(p, boca, emocao)
                    self._cache[bk] = p.reduzir(self.escala)
                img.alpha_composite(self._cache[bk])
            self._cache[chave] = img
        return self._cache[chave]

    def retrato(self, emocao="feliz"):
        img = self.sprite_corpo().copy()
        img.alpha_composite(self.sprite_cabeca(emocao))
        return img


# ------------------------------------------------------------ humano
class Humano(Personagem):
    def geometria(self):
        s = self.spec
        self.idade = s.get("idade", "adulto")
        self.fem = s.get("genero", "m") == "f"
        corpo = {"adulto": 330, "crianca": 215, "idoso": 315, "bebe": 120}.get(self.idade, 330)
        self.cx, self.hy, self.r = 230, 190, 118
        self.y0 = self.hy + 95
        self.y1 = self.y0 + corpo
        self.H = self.y1 + 46
        self.W = 460
        self.off = 12
        self.altura_px = {"adulto": 560, "crianca": 420, "idoso": 545, "bebe": 250}.get(self.idade, 560)
        if s.get("gigante"):
            self.altura_px = 960
        self.pivo_1x = (self.cx, self.hy + 100)
        self.pele = _cor(s.get("pele"), PELES, "morena")
        self.cab = _cor(s.get("cabelo"), CABELOS, "castanho")
        if self.idade == "idoso" and not s.get("cabelo"):
            self.cab = CABELOS["branco"]
        self.roupa = s.get("roupa", "#8d6e63")
        self.roupa2 = s.get("roupa2", "#f2c14e")

    # ---------------- corpo
    def desenhar_corpo(self, p: Pintor):
        s, cx, y0, y1 = self.spec, self.cx, self.y0, self.y1
        if s.get("asas"):
            for lado in (-1, 1):
                ms = []
                for i, (dx, dy, rw, rh) in enumerate([(120, -10, 95, 60), (140, 40, 90, 50), (125, 85, 70, 40)]):
                    x = cx + lado * dx
                    ms.append(p.ell(p.m(), (x - rw, y0 + dy - rh, x + rw, y0 + dy + rh)))
                p.pintar(Pintor.soma(*ms), "#ffffff", contorno=4.5, sombra=0.5)
        if self.idade == "bebe":
            m = p.ell(p.m(), (cx - 105, y0 - 30, cx + 105, y1 + 30))
            p.pintar(m, s.get("roupa", "#fff8e1"), contorno=5, sombra=0.6)
            for yy in (y0 + 20, y0 + 70):
                p.pintar(p.arco(p.m(), (cx - 100, yy - 30, cx + 100, yy + 30), 20, 160, 5), "#d7ccc8", contorno=0)
            return
        # pés
        for dx in (-34, 34):
            m = p.ell(p.m(), (cx + dx - 30, y1 - 12, cx + dx + 30, y1 + 30))
            p.pintar(m, "#6d4c41", contorno=4.5)
        # manto de rei
        if s.get("manto"):
            m = p.poly(p.m(), [(cx - 70, y0), (cx + 70, y0), (cx + 150, y1 + 8), (cx - 150, y1 + 8)])
            m = Pintor.soma(m, p.ell(p.m(), (cx - 95, y0 - 20, cx + 95, y0 + 60)))
            p.pintar(m, self.roupa2 if s.get("cobertura") != "coroa" else s.get("cor_manto", "#8e24aa"),
                     contorno=5, sombra=0.5)
        largura = 128 if self.fem else 116
        tronco = p.rect(p.m(), (cx - 78, y0 - 12, cx + 78, y0 + 130), r=56)
        saia = p.poly(p.m(), [(cx - 80, y0 + 60), (cx + 80, y0 + 60), (cx + largura, y1), (cx - largura, y1)])
        barra = p.rect(p.m(), (cx - largura, y1 - 30, cx + largura, y1 + 6), r=16)
        roupa = Pintor.soma(tronco, saia, barra)
        # braço de trás (esquerdo)
        bra_t = p.linha(p.m(), [(cx - 70, y0 + 28), (cx - 108, y0 + 132)], 44)
        p.pintar(bra_t, self.roupa, contorno=5, sombra=0.4)
        p.pintar(p.circ(p.m(), cx - 110, y0 + 150, 23), self.pele, contorno=4.5)
        # roupa
        padrao = s.get("padrao")
        if padrao == "colorida":
            p.pintar(roupa, self.roupa, contorno=5)
            cores = ["#e53935", "#fb8c00", "#fdd835", "#43a047", "#1e88e5", "#8e24aa"]
            for i, yy in enumerate(range(int(y0 - 12), int(y1 + 8), 34)):
                faixa = p.inter(roupa, p.rect(p.m(), (0, yy, self.W, yy + 34)))
                p.pintar(faixa, cores[i % len(cores)], contorno=0)
        else:
            p.pintar(roupa, self.roupa, contorno=5, sombra=0.55)
            p.brilho(roupa, forca=0.18)
        if s.get("armadura"):
            placa = p.rect(p.m(), (cx - 72, y0 + 2, cx + 72, y0 + 122), r=42)
            p.pintar(placa, "#c8923c", contorno=4.5, sombra=0.6)
            p.brilho(placa, forca=0.35)
            for i in range(-3, 4):
                tira = p.rect(p.m(), (cx + i * 26 - 11, y0 + 126, cx + i * 26 + 11, y0 + 196), r=6)
                p.pintar(tira, "#a86f2a", contorno=3.5)
        else:
            # cinto e gola
            cinto = p.inter(roupa, p.rect(p.m(), (0, y0 + 112, self.W, y0 + 134)))
            p.pintar(cinto, self.roupa2, contorno=0)
            gola = p.poly(p.m(), [(cx - 34, y0 - 8), (cx + 34, y0 - 8), (cx, y0 + 42)])
            p.pintar(gola, self.roupa2, contorno=3)
        # braço da frente (direito) + acessório
        bra_f = p.linha(p.m(), [(cx + 70, y0 + 28), (cx + 104, y0 + 122)], 44)
        hx, hy = cx + 108, y0 + 140
        self._acessorio(p, s.get("acessorio"), hx, hy, atras=True)
        p.pintar(bra_f, self.roupa, contorno=5, sombra=0.4)
        p.pintar(p.circ(p.m(), hx, hy, 23), self.pele, contorno=4.5)
        self._acessorio(p, s.get("acessorio"), hx, hy, atras=False)

    def _acessorio(self, p, ac, hx, hy, atras):
        if not ac or ac == "nenhum":
            return
        if ac == "cajado" and atras:
            m = p.linha(p.m(), [(hx + 4, hy - 230), (hx + 4, self.y1 + 20)], 15)
            gancho = p.arco(p.m(), (hx - 44, hy - 290, hx + 6, hy - 200), 180, 360, 15)
            p.pintar(Pintor.soma(m, gancho), "#8d5a32", contorno=4)
        elif ac == "lanca" and atras:
            m = p.linha(p.m(), [(hx + 4, hy - 300), (hx + 4, self.y1 + 10)], 13)
            p.pintar(m, "#8d5a32", contorno=4)
            ponta = p.poly(p.m(), [(hx - 16, hy - 296), (hx + 24, hy - 296), (hx + 4, hy - 360)])
            p.pintar(ponta, "#cfd8dc", contorno=4)
        elif ac == "espada" and atras:
            lamina = p.poly(p.m(), [(hx - 9, hy - 20), (hx + 17, hy - 20), (hx + 17, hy - 170), (hx + 4, hy - 196), (hx - 9, hy - 170)])
            p.pintar(lamina, "#e0e6ea", contorno=4)
            p.pintar(p.rect(p.m(), (hx - 30, hy - 26, hx + 38, hy - 12), r=6), "#f2c14e", contorno=4)
        elif ac == "funda" and not atras:
            p.pintar(p.linha(p.m(), [(hx, hy + 10), (hx + 8, hy + 60), (hx + 26, hy + 88)], 6), "#8d5a32", contorno=2)
            p.pintar(p.circ(p.m(), hx + 30, hy + 96, 13), "#9e9e9e", contorno=3.5)
        elif ac == "harpa" and not atras:
            m = p.poly(p.m(), [(hx - 60, hy - 110), (hx + 10, hy - 40), (hx - 60, hy + 30)])
            fora = p.dilatar(m, 0)
            aro = Pintor.menos(p.dilatar(m, 12), m)
            p.pintar(aro, "#f2c14e", contorno=3.5)
            for i in range(4):
                x = hx - 50 + i * 14
                p.pintar(p.linha(p.m(), [(x, hy - 90 + i * 12), (x, hy + 10 - i * 12)], 2.5), "#fff3c4", contorno=0)
        elif ac == "pergaminho" and not atras:
            p.pintar(p.rect(p.m(), (hx - 30, hy - 50, hx + 18, hy + 30), r=4), "#fff3d6", contorno=4)
            for yy in (hy - 54, hy + 26):
                p.pintar(p.rect(p.m(), (hx - 38, yy, hx + 26, yy + 12), r=6), "#b08050", contorno=3.5)
        elif ac == "cesta" and not atras:
            for i, dx in enumerate((-22, 6, 30)):
                p.pintar(p.ell(p.m(), (hx + dx - 26, hy - 36, hx + dx + 22, hy - 4)),
                         "#e0a458" if i != 1 else "#90a4ae", contorno=3.5)
            m = p.inter(p.ell(p.m(), (hx - 56, hy - 40, hx + 66, hy + 50)), p.abaixo_de(hy - 14))
            p.pintar(m, "#b07a3c", contorno=4.5, sombra=0.5)
        elif ac == "lampiao" and not atras:
            p.pintar(p.ell(p.m(), (hx - 34, hy - 20, hx + 40, hy + 14)), "#c77d3a", contorno=4)
            p.pintar(p.ell(p.m(), (hx + 26, hy - 46, hx + 46, hy - 12)), "#ffca28", contorno=0)
        elif ac == "pao" and not atras:
            p.pintar(p.ell(p.m(), (hx - 34, hy - 26, hx + 34, hy + 16)), "#e0a458", contorno=4)
        elif ac == "ramo" and not atras:
            p.pintar(p.linha(p.m(), [(hx, hy), (hx + 30, hy - 80)], 6), "#6d8b3a", contorno=2)
            for i in range(3):
                yy = hy - 22 - i * 22
                p.pintar(p.ell(p.m(), (hx + 12 + i * 8, yy - 10, hx + 40 + i * 8, yy + 4)), "#7cb342", contorno=2.5)

    # ---------------- cabeça
    def desenhar_cabeca(self, p: Pintor, emocao: str, fechados: bool):
        s, cx, hy, r, off = self.spec, self.cx, self.hy, self.r, self.off
        cob = s.get("cobertura", "nenhuma")
        estilo = s.get("estilo_cabelo", "longo" if self.fem else "curto")
        if self.idade == "bebe":
            estilo = "bebe"
        rosto = p.ell(p.m(), (cx - 97 + off * 0.5, hy - 64, cx + 97 + off * 0.5, hy + 150))
        # halo do anjo
        if s.get("asas"):
            m = Pintor.menos(p.ell(p.m(), (cx - 80, hy - 178, cx + 80, hy - 128)),
                             p.ell(p.m(), (cx - 60, hy - 168, cx + 60, hy - 138)))
            p.pintar(m, "#ffd54f", contorno=3.5)
        # cabelo/véu de trás
        if cob in ("veu", "lenco", "nemes"):
            larg = 150 if cob == "veu" else 140
            desce = 215 if cob == "veu" else 175
            m = p.rect(p.m(), (cx - larg, hy - 70, cx + larg, hy + desce), r=70)
            cor = s.get("cor_cobertura", "#f1e9da" if cob == "veu" else "#e8dcc4")
            if cob == "nemes":
                cor = "#1e5aa8"
            p.pintar(m, escurecer(cor, 0.9), contorno=5)
        elif estilo in ("longo", "tranca") and cob != "capacete":
            baixo = hy + (200 if estilo == "longo" else 120)
            m = Pintor.soma(p.rect(p.m(), (cx - 130, hy - 60, cx + 130, hy + 70), r=62),
                            p.rect(p.m(), (cx - 132, hy - 20, cx - 58, baixo), r=34),
                            p.rect(p.m(), (cx + 58, hy - 20, cx + 132, baixo), r=34))
            p.pintar(m, escurecer(self.cab, 0.85), contorno=5)
            if estilo == "tranca":
                for lado in (-1, 1):
                    ms = [p.ell(p.m(), (cx + lado * 112 - 22, hy + 70 + i * 36, cx + lado * 112 + 22, hy + 112 + i * 36))
                          for i in range(4)]
                    p.pintar(Pintor.soma(*ms), self.cab, contorno=4)
        elif estilo == "coque" and cob == "nenhuma":
            p.pintar(p.circ(p.m(), cx - 4, hy - 128, 42), self.cab, contorno=5)
        # orelhas
        for lado in (-1, 1):
            m = p.ell(p.m(), (cx + lado * 116 - 22, hy - 4, cx + lado * 116 + 22, hy + 46))
            p.pintar(m, self.pele, contorno=4.5)
        # cabeça
        cabeca = p.circ(p.m(), cx, hy, r)
        p.pintar(cabeca, self.pele, contorno=5.5, sombra=0.55)
        p.brilho(cabeca, forca=0.16)
        # nariz
        p.pintar(p.ell(p.m(), (cx + off - 1, hy + 30, cx + off + 19, hy + 46)), escurecer(self.pele, 0.86), contorno=0)
        # barba
        barba = s.get("barba", "nenhuma")
        cor_barba = s.get("cor_barba") or self.cab
        if barba in ("curta", "longa"):
            mand = p.inter(p.ell(p.m(), (cx - 114 + off * 0.3, hy - 60, cx + 114 + off * 0.3, hy + 158)), p.abaixo_de(hy + 44))
            if barba == "longa":
                mand = Pintor.soma(mand, p.poly(p.m(), [(cx - 84, hy + 110), (cx + 96 + off, hy + 110), (cx + off + 6, hy + 238)]))
            bigode = Pintor.soma(p.ell(p.m(), (cx + off - 48, hy + 40, cx + off + 2, hy + 66)),
                                 p.ell(p.m(), (cx + off - 2, hy + 40, cx + off + 48, hy + 66)))
            buraco = p.ell(p.m(), (cx + off - 34, hy + 56, cx + off + 34, hy + 96))
            m = Pintor.soma(Pintor.menos(mand, buraco), bigode)
            p.pintar(m, cor_barba, contorno=4.5, sombra=0.35)
        # olhos
        olhos = [(cx - 40 + off, hy + 6), (cx + 40 + off, hy + 6)]
        desenhar_olhos(p, emocao, fechados, olhos, 1.0,
                       cor_sobrancelha=escurecer(self.cab, 0.7) if self.cab != CABELOS["branco"] else "#9e948a",
                       bochecha=barba == "nenhuma")
        # cabelo da frente
        if cob in ("nenhuma", "faixa", "coroa") and estilo != "careca":
            if estilo == "bebe":
                m = p.arco(p.m(), (cx - 10, hy - 150, cx + 40, hy - 100), 90, 330, 9)
                p.pintar(m, self.cab, contorno=3)
            else:
                topo = p.inter(p.ell(p.m(), (cx - 126, hy - 134, cx + 126, hy + 74)), p.acima_de(hy + 34))
                if estilo == "cacheado":
                    bol = [p.circ(p.m(), cx + 122 * math.cos(math.radians(a)), hy - 8 + 122 * math.sin(math.radians(a)), 36)
                           for a in range(160, 390, 22)]
                    topo = Pintor.soma(topo, *[p.inter(b, p.acima_de(hy + 40)) for b in bol])
                if estilo in ("longo", "tranca"):
                    topo = Pintor.soma(topo, p.rect(p.m(), (cx - 128, hy - 30, cx - 96, hy + 110), r=16),
                                       p.rect(p.m(), (cx + 96, hy - 30, cx + 128, hy + 110), r=16))
                franja = p.ell(p.m(), (cx - 92 + off * 0.5, hy - 58, cx + 92 + off * 0.5, hy + 160))
                m = Pintor.menos(topo, franja)
                if estilo == "curto":  # mecha
                    m = Pintor.soma(m, p.poly(p.m(), [(cx - 30 + off, hy - 70), (cx + 50 + off, hy - 72), (cx + 10 + off, hy - 36)]))
                p.pintar(m, self.cab, contorno=5, sombra=0.4)
                p.brilho(m, forca=0.25)
        elif estilo == "careca" and cob == "nenhuma":
            for lado in (-1, 1):
                p.pintar(p.ell(p.m(), (cx + lado * 110 - 26, hy - 30, cx + lado * 110 + 26, hy + 30)), self.cab, contorno=4)
        if cob in ("lenco", "veu", "nemes"):
            cor = s.get("cor_cobertura", "#f1e9da" if cob == "veu" else "#e8dcc4")
            if cob == "nemes":
                cor = "#f2c14e"
            pano = p.inter(p.ell(p.m(), (cx - 136, hy - 146, cx + 136, hy + 76)), p.acima_de(hy + 30))
            abertura = p.ell(p.m(), (cx - 90 + off * 0.5, hy - 52, cx + 90 + off * 0.5, hy + 160))
            lados = Pintor.soma(p.rect(p.m(), (cx - 140, hy - 20, cx - 90, hy + 150), r=24),
                                p.rect(p.m(), (cx + 90, hy - 20, cx + 140, hy + 150), r=24))
            m = Pintor.menos(Pintor.soma(pano, lados), abertura)
            p.pintar(m, cor, contorno=5, sombra=0.5)
            if cob == "nemes":
                for yy in range(int(hy - 140), int(hy + 150), 26):
                    p.pintar(p.inter(m, p.rect(p.m(), (0, yy, self.W, yy + 12))), "#1e5aa8", contorno=0)
            elif cob == "lenco":
                faixa = p.inter(p.rect(p.m(), (cx - 132, hy - 70, cx + 132, hy - 46)), p.dilatar(m, 2))
                p.pintar(faixa, s.get("cor_faixa", self.roupa2), contorno=3.5)
        if cob == "faixa":
            faixa = p.inter(p.rect(p.m(), (cx - 124, hy - 64, cx + 124, hy - 42)), p.circ(p.m(), cx, hy, r + 6))
            p.pintar(faixa, self.roupa2, contorno=3.5)
        if cob == "coroa":
            pts = [(cx - 78, hy - 96), (cx - 78, hy - 160), (cx - 40, hy - 124), (cx, hy - 172),
                   (cx + 40, hy - 124), (cx + 78, hy - 160), (cx + 78, hy - 96)]
            m = p.poly(p.m(), pts)
            p.pintar(m, "#ffc629", contorno=4.5, sombra=0.4)
            p.brilho(m, forca=0.4)
            for dx, c in ((-40, "#e53935"), (0, "#1e88e5"), (40, "#43a047")):
                p.pintar(p.circ(p.m(), cx + dx, hy - 110, 9), c, contorno=2.5)
        if cob == "capacete":
            dome = p.inter(p.ell(p.m(), (cx - 132, hy - 150, cx + 132, hy + 70)), p.acima_de(hy - 40))
            guard = Pintor.soma(p.rect(p.m(), (cx - 136, hy - 60, cx - 104, hy + 50), r=14),
                                p.rect(p.m(), (cx + 104, hy - 60, cx + 136, hy + 50), r=14))
            m = Pintor.soma(dome, guard)
            p.pintar(m, "#c8923c", contorno=5, sombra=0.5)
            p.brilho(m, forca=0.35)
            crista = p.ell(p.m(), (cx - 70, hy - 196, cx + 70, hy - 128))
            crista = p.inter(crista, p.acima_de(hy - 140))
            p.pintar(crista, "#d84315", contorno=4.5)

    def desenhar_boca(self, p, forma, emocao):
        desenhar_boca(p, forma, emocao, self.cx + self.off, self.hy + 72)


# ------------------------------------------------------------ animais
class Ovelha(Personagem):
    def geometria(self):
        self.W, self.H, self.cx = 440, 520, 220
        self.altura_px = 360 if not self.spec.get("pequena") else 250
        self.pivo_1x = (self.cx, 270)
        self.off = 10

    def desenhar_corpo(self, p):
        cx = self.cx
        for dx in (-92, -40, 36, 88):
            p.pintar(p.rect(p.m(), (cx + dx - 17, 400, cx + dx + 17, 505), r=14), "#4b3b3b", contorno=4)
        bol = [p.ell(p.m(), (cx - 150, 250, cx + 150, 450))]
        for a in range(0, 360, 30):
            x = cx + 142 * math.cos(math.radians(a))
            y = 350 + 92 * math.sin(math.radians(a))
            bol.append(p.circ(p.m(), x, y, 46))
        m = Pintor.soma(*bol)
        p.pintar(m, "#fffaf2", contorno=5, sombra=0.45)

    def desenhar_cabeca(self, p, emocao, fechados):
        cx, off = self.cx, self.off
        for lado in (-1, 1):
            m = p.ell(p.m(), (cx + lado * 112 - 50 + off, 150, cx + lado * 112 + 50 + off, 196))
            p.pintar(m, "#e9d2c0", contorno=4.5)
        rosto = p.ell(p.m(), (cx - 84 + off, 96, cx + 84 + off, 282))
        p.pintar(rosto, "#f7e4d4", contorno=5, sombra=0.45)
        tufo = Pintor.soma(*[p.circ(p.m(), cx + off + dx, 96 + dy, 34)
                              for dx, dy in ((-52, 12), (-22, -10), (14, -14), (48, 6), (0, 16))])
        p.pintar(tufo, "#fffaf2", contorno=5, sombra=0.3)
        if self.spec.get("laco"):
            bx, by = cx + off + 62, 78
            m = Pintor.soma(p.poly(p.m(), [(bx, by), (bx - 44, by - 30), (bx - 44, by + 30)]),
                            p.poly(p.m(), [(bx, by), (bx + 44, by - 30), (bx + 44, by + 30)]))
            p.pintar(m, "#ff6f91", contorno=4)
            p.pintar(p.circ(p.m(), bx, by, 13), "#ff4f7b", contorno=3.5)
        desenhar_olhos(p, emocao, fechados, [(cx + off - 34, 180), (cx + off + 34, 180)], 0.92,
                       cor_sobrancelha="#8a6f60")
        p.pintar(p.ell(p.m(), (cx + off - 12, 214, cx + off + 12, 226)), "#e38a9a", contorno=0)

    def desenhar_boca(self, p, forma, emocao):
        desenhar_boca(p, forma, emocao, self.cx + self.off, 244, 0.8)


class Leao(Personagem):
    def geometria(self):
        self.W, self.H, self.cx = 520, 560, 260
        self.altura_px = 440
        self.pivo_1x = (self.cx, 300)
        self.off = 10

    def desenhar_corpo(self, p):
        cx = self.cx
        p.pintar(p.linha(p.m(), [(cx + 100, 480), (cx + 170, 440), (cx + 196, 360)], 18), "#e2ac5a", contorno=4.5)
        p.pintar(p.circ(p.m(), cx + 198, 350, 24), "#a0522d", contorno=4.5)
        m = p.ell(p.m(), (cx - 125, 260, cx + 125, 530))
        p.pintar(m, "#e9b563", contorno=5, sombra=0.5)
        p.pintar(p.ell(p.m(), (cx - 70, 330, cx + 70, 520)), "#f6d69a", contorno=0)
        for dx in (-60, 60):
            p.pintar(p.ell(p.m(), (cx + dx - 38, 488, cx + dx + 38, 548)), "#e9b563", contorno=4.5)

    def desenhar_cabeca(self, p, emocao, fechados):
        cx, off, cy = self.cx, self.off, 190
        juba = Pintor.soma(*[p.circ(p.m(), cx + off * 0.5 + 132 * math.cos(math.radians(a)),
                                    cy + 128 * math.sin(math.radians(a)), 56) for a in range(0, 360, 26)])
        p.pintar(juba, "#b8642b", contorno=5, sombra=0.4)
        for lado in (-1, 1):
            p.pintar(p.circ(p.m(), cx + lado * 88 + off, 92, 30), "#e9b563", contorno=4.5)
        rosto = p.ell(p.m(), (cx - 104 + off, 84, cx + 104 + off, 296))
        p.pintar(rosto, "#f0c274", contorno=5, sombra=0.4)
        p.pintar(p.ell(p.m(), (cx - 56 + off, 204, cx + 56 + off, 280)), "#fbe3b6", contorno=0)
        desenhar_olhos(p, emocao, fechados, [(cx - 42 + off, 160), (cx + 42 + off, 160)], 0.95,
                       cor_sobrancelha="#8a4b22")
        p.pintar(p.ell(p.m(), (cx + off - 18, 196, cx + off + 18, 218)), "#5a3326", contorno=0)

    def desenhar_boca(self, p, forma, emocao):
        desenhar_boca(p, forma, emocao, self.cx + self.off, 244, 0.85)


class Pomba(Personagem):
    flutua = -420

    def geometria(self):
        self.W, self.H = 320, 260
        self.altura_px = 170
        self.pivo_1x = (210, 150)
        self.tem_boca = False

    def desenhar_corpo(self, p):
        p.pintar(p.poly(p.m(), [(90, 150), (20, 120), (30, 190)]), "#eceff1", contorno=4)
        m = p.ell(p.m(), (60, 110, 240, 210))
        p.pintar(m, "#ffffff", contorno=4.5, sombra=0.4)
        p.pintar(p.ell(p.m(), (90, 70, 200, 160)), "#eef2f5", contorno=4)
        if self.spec.get("acessorio") == "ramo":
            p.pintar(p.linha(p.m(), [(270, 110), (300, 150)], 5), "#6d8b3a", contorno=2)
            p.pintar(p.ell(p.m(), (282, 130, 312, 146)), "#7cb342", contorno=2)

    def desenhar_cabeca(self, p, emocao, fechados):
        p.pintar(p.circ(p.m(), 215, 100, 48), "#ffffff", contorno=4.5, sombra=0.3)
        p.pintar(p.poly(p.m(), [(252, 96), (292, 108), (252, 120)]), "#ff9f43", contorno=3.5)
        desenhar_olhos(p, emocao, fechados, [(226, 90)], 0.6, sobrancelha=False, bochecha=False)


class Baleia(Personagem):
    def geometria(self):
        self.W, self.H = 900, 520
        self.altura_px = 400
        self.pivo_1x = (650, 330)
        self.flutua = -40

    def desenhar_corpo(self, p):
        cauda = p.poly(p.m(), [(230, 300), (40, 150), (80, 262), (26, 380), (220, 360)])
        corpo = p.ell(p.m(), (170, 120, 830, 470))
        m = Pintor.soma(cauda, corpo)
        p.pintar(m, "#5b8fd6", contorno=5.5, sombra=0.5)
        barriga = p.inter(p.ell(p.m(), (260, 330, 820, 520)), corpo)
        p.pintar(barriga, "#d3e6fb", contorno=0)
        for x in range(360, 760, 60):
            p.pintar(p.inter(p.linha(p.m(), [(x, 340), (x + 10, 470)], 5), barriga), "#a9c9ee", contorno=0)
        for i, (dx, dy, r) in enumerate([(0, 0, 16), (-26, -36, 12), (26, -40, 12), (0, -70, 10)]):
            p.pintar(p.circ(p.m(), 560 + dx, 96 + dy, r), "#9fd3ff", contorno=3)

    def desenhar_cabeca(self, p, emocao, fechados):
        desenhar_olhos(p, emocao, fechados, [(640, 250), (720, 244)], 1.1, cor_sobrancelha="#2f5b99")

    def desenhar_boca(self, p, forma, emocao):
        desenhar_boca(p, forma, emocao, 700, 318, 1.1)


class Quadrupede(Personagem):
    """Jumento ou camelo (vista de lado)."""

    def geometria(self):
        self.W, self.H = 520, 520
        self.camelo = self.spec.get("tipo") == "camelo"
        self.altura_px = 470 if self.camelo else 380
        self.cor = self.spec.get("roupa") or ("#d8a86a" if self.camelo else "#9e9e9e")
        self.pivo_1x = (360, 200)

    def desenhar_corpo(self, p):
        c = self.cor
        for x in (130, 180, 320, 370):
            p.pintar(p.rect(p.m(), (x - 16, 330, x + 16, 500), r=12), escurecer(c, 0.9), contorno=4.5)
        p.pintar(p.linha(p.m(), [(80, 270), (50, 350)], 12), c, contorno=4)
        corpo = p.ell(p.m(), (70, 210, 420, 390))
        if self.camelo:
            corpo = Pintor.soma(corpo, p.ell(p.m(), (160, 130, 300, 290)))
        pesc = p.poly(p.m(), [(330, 250), (400, 250), (430, 140 if not self.camelo else 110), (370, 130 if not self.camelo else 100)])
        m = Pintor.soma(corpo, pesc)
        p.pintar(m, c, contorno=5, sombra=0.5)
        if not self.camelo and self.spec.get("sela", True):
            p.pintar(p.rect(p.m(), (170, 200, 300, 250), r=20), "#c0392b", contorno=4)

    def desenhar_cabeca(self, p, emocao, fechados):
        c = self.cor
        if not self.camelo:
            for dx in (-20, 16):
                p.pintar(p.ell(p.m(), (380 + dx, 20, 412 + dx, 120)), c, contorno=4.5)
        cab = p.ell(p.m(), (340, 70, 490, 190))
        p.pintar(cab, c, contorno=5, sombra=0.4)
        p.pintar(p.ell(p.m(), (430, 120, 500, 190)), clarear(c, 0.4), contorno=3.5)
        desenhar_olhos(p, emocao, fechados, [(420, 112)], 0.75, cor_sobrancelha=escurecer(c, 0.6), bochecha=False)

    def desenhar_boca(self, p, forma, emocao):
        desenhar_boca(p, forma, emocao, 468, 168, 0.55)


class Cobra(Personagem):
    def geometria(self):
        self.W, self.H = 360, 420
        self.altura_px = 300
        self.pivo_1x = (190, 180)

    def desenhar_corpo(self, p):
        for box in [(40, 300, 320, 410), (70, 230, 290, 330), (110, 170, 250, 260)]:
            p.pintar(p.ell(p.m(), box), "#7cb342", contorno=5, sombra=0.45)

    def desenhar_cabeca(self, p, emocao, fechados):
        p.pintar(p.ell(p.m(), (110, 40, 270, 170)), "#8bc34a", contorno=5, sombra=0.4)
        desenhar_olhos(p, emocao, fechados, [(165, 96), (220, 96)], 0.8, cor_sobrancelha="#33691e")

    def desenhar_boca(self, p, forma, emocao):
        desenhar_boca(p, forma, emocao, 194, 140, 0.7)


# ------------------------------------------------------------ catálogo
H_ = dict  # atalho

PRESETS: dict[str, dict] = {
    # mascote / narradora
    "mel": H_(tipo="ovelha", laco=True, voz="narrador", nome="Mel"),
    # Antigo Testamento
    "adao": H_(nome="Adão", pele="media", cabelo="castanho", estilo_cabelo="cacheado", roupa="#66bb6a", roupa2="#33691e", voz="homem"),
    "eva": H_(nome="Eva", genero="f", pele="media", cabelo="castanho", estilo_cabelo="longo", roupa="#81c784", roupa2="#388e3c", voz="mulher"),
    "noe": H_(nome="Noé", idade="idoso", barba="longa", roupa="#8d6e63", roupa2="#ffca28", acessorio="cajado", voz="idoso"),
    "esposa_noe": H_(nome="Esposa de Noé", genero="f", idade="idoso", cobertura="veu", roupa="#e57373", voz="idosa"),
    "abraao": H_(nome="Abraão", idade="idoso", barba="longa", cabelo="grisalho", cobertura="lenco", cor_cobertura="#efe6d2", cor_faixa="#8d6e63", roupa="#5c6bc0", acessorio="cajado", voz="idoso"),
    "sara": H_(nome="Sara", genero="f", idade="idoso", cobertura="veu", cor_cobertura="#f8e9d6", roupa="#e57373", voz="idosa"),
    "isaque": H_(nome="Isaque", idade="crianca", estilo_cabelo="cacheado", cabelo="preto", roupa="#4fc3f7", voz="menino"),
    "jaco": H_(nome="Jacó", barba="curta", estilo_cabelo="cacheado", roupa="#26a69a", roupa2="#ffe082", voz="homem"),
    "esau": H_(nome="Esaú", barba="curta", cabelo="ruivo", estilo_cabelo="cacheado", roupa="#a1887f", roupa2="#5d4037", voz="homem"),
    "jose": H_(nome="José", cabelo="preto", roupa="#ffffff", padrao="colorida", voz="homem"),
    "jose_menino": H_(nome="José", idade="crianca", cabelo="preto", roupa="#ffffff", padrao="colorida", voz="menino"),
    "farao": H_(nome="Faraó", pele="morena", cobertura="nemes", roupa="#f5f0e1", roupa2="#f2c14e", manto=True, cor_manto="#1e5aa8", voz="homem"),
    "moises": H_(nome="Moisés", barba="longa", cabelo="castanho", cobertura="lenco", cor_cobertura="#e7dccb", cor_faixa="#b71c1c", roupa="#c62828", roupa2="#ffe082", acessorio="cajado", voz="homem"),
    "moises_bebe": H_(nome="Moisés bebê", idade="bebe", cabelo="preto", roupa="#fff8e1", voz="menino"),
    "arao": H_(nome="Arão", barba="longa", cabelo="preto", cobertura="lenco", cor_cobertura="#ffffff", cor_faixa="#1e88e5", roupa="#1e88e5", voz="homem"),
    "miria": H_(nome="Miriã", genero="f", idade="crianca", cabelo="preto", estilo_cabelo="tranca", roupa="#ab47bc", roupa2="#ffd54f", voz="menina"),
    "josue": H_(nome="Josué", barba="curta", cobertura="capacete", armadura=True, acessorio="espada", roupa="#5d4037", voz="homem"),
    "gideao": H_(nome="Gideão", barba="curta", cabelo="castanho", roupa="#7cb342", roupa2="#5d4037", acessorio="lampiao", voz="homem"),
    "sansao": H_(nome="Sansão", barba="curta", estilo_cabelo="longo", cabelo="preto", roupa="#ff7043", roupa2="#5d4037", voz="homem"),
    "rute": H_(nome="Rute", genero="f", cobertura="veu", cor_cobertura="#ffe0b2", roupa="#8bc34a", voz="mulher"),
    "noemi": H_(nome="Noemi", genero="f", idade="idoso", cobertura="veu", roupa="#8d6e63", voz="idosa"),
    "ana": H_(nome="Ana", genero="f", cobertura="veu", cor_cobertura="#e1f5fe", roupa="#4fc3f7", voz="mulher"),
    "samuel_menino": H_(nome="Samuel", idade="crianca", cabelo="castanho", roupa="#ffffff", roupa2="#1e88e5", voz="menino"),
    "samuel": H_(nome="Samuel", idade="idoso", barba="longa", cobertura="lenco", cor_cobertura="#ffffff", cor_faixa="#1e88e5", roupa="#3949ab", acessorio="cajado", voz="idoso"),
    "eli": H_(nome="Eli", idade="idoso", barba="longa", cobertura="lenco", cor_cobertura="#f5f5f5", roupa="#6d4c41", voz="idoso"),
    "davi": H_(nome="Davi", idade="crianca", cabelo="ruivo", estilo_cabelo="cacheado", roupa="#f2c14e", roupa2="#8d6e63", acessorio="funda", voz="menino"),
    "davi_rei": H_(nome="Rei Davi", barba="curta", cabelo="ruivo", estilo_cabelo="cacheado", cobertura="coroa", manto=True, cor_manto="#1e88e5", roupa="#fff3e0", roupa2="#f2c14e", acessorio="harpa", voz="homem"),
    "golias": H_(nome="Golias", gigante=True, pele="media", cabelo="preto", barba="longa", cobertura="capacete", armadura=True, roupa="#6d4c41", acessorio="lanca", voz="gigante"),
    "saul": H_(nome="Rei Saul", barba="curta", cabelo="preto", cobertura="coroa", manto=True, cor_manto="#7e57c2", roupa="#b39ddb", voz="homem"),
    "jonatas": H_(nome="Jônatas", cabelo="castanho", roupa="#29b6f6", roupa2="#f2c14e", voz="homem"),
    "salomao": H_(nome="Rei Salomão", barba="curta", cabelo="preto", cobertura="coroa", manto=True, cor_manto="#1565c0", roupa="#fff8e1", voz="homem"),
    "elias": H_(nome="Elias", idade="idoso", barba="longa", cabelo="grisalho", estilo_cabelo="cacheado", roupa="#795548", roupa2="#3e2723", acessorio="cajado", voz="idoso"),
    "eliseu": H_(nome="Eliseu", barba="curta", estilo_cabelo="careca", cabelo="castanho", roupa="#8d6e63", roupa2="#ffcc80", voz="homem"),
    "naama": H_(nome="Naamã", barba="curta", cobertura="capacete", armadura=True, roupa="#455a64", voz="homem"),
    "daniel": H_(nome="Daniel", cabelo="preto", roupa="#3949ab", roupa2="#ffd54f", voz="homem"),
    "dario": H_(nome="Rei Dario", barba="longa", cabelo="preto", cobertura="coroa", manto=True, cor_manto="#6a1b9a", roupa="#ffe082", voz="homem"),
    "nabucodonosor": H_(nome="Rei Nabucodonosor", barba="longa", cabelo="preto", cobertura="coroa", manto=True, cor_manto="#c62828", roupa="#ffcc80", voz="homem"),
    "sadraque": H_(nome="Sadraque", cabelo="preto", roupa="#ef5350", voz="homem"),
    "mesaque": H_(nome="Mesaque", cabelo="castanho", estilo_cabelo="cacheado", roupa="#66bb6a", voz="homem"),
    "abednego": H_(nome="Abede-Nego", cabelo="preto", roupa="#42a5f5", voz="homem"),
    "ester": H_(nome="Rainha Ester", genero="f", cabelo="preto", estilo_cabelo="longo", cobertura="coroa", roupa="#e91e63", roupa2="#ffd54f", voz="mulher"),
    "mardoqueu": H_(nome="Mardoqueu", idade="idoso", barba="longa", cobertura="lenco", roupa="#5d4037", voz="idoso"),
    "jonas": H_(nome="Jonas", barba="curta", cabelo="castanho", estilo_cabelo="cacheado", roupa="#00897b", roupa2="#ffcc80", voz="homem"),
    # Novo Testamento
    "maria": H_(nome="Maria", genero="f", cobertura="veu", cor_cobertura="#64b5f6", roupa="#f5f5f5", roupa2="#64b5f6", voz="mulher"),
    "jose_carpinteiro": H_(nome="José", barba="curta", cabelo="castanho", roupa="#8d6e63", roupa2="#ffcc80", acessorio="cajado", voz="homem"),
    "jesus_bebe": H_(nome="Jesus bebê", idade="bebe", cabelo="castanho", roupa="#fffde7", voz="menino"),
    "jesus_menino": H_(nome="Jesus", idade="crianca", cabelo="castanho", roupa="#fafafa", roupa2="#e53935", voz="menino"),
    "jesus": H_(nome="Jesus", cabelo="castanho", estilo_cabelo="longo", barba="curta", roupa="#fafafa", roupa2="#e53935", manto=True, cor_manto="#e53935", voz="homem"),
    "joao_batista": H_(nome="João Batista", barba="longa", estilo_cabelo="longo", cabelo="castanho", roupa="#8d6e63", roupa2="#4e342e", voz="homem"),
    "pedro": H_(nome="Pedro", barba="curta", cabelo="grisalho", estilo_cabelo="cacheado", roupa="#1565c0", roupa2="#ffcc80", voz="homem"),
    "andre": H_(nome="André", barba="curta", cabelo="castanho", roupa="#43a047", voz="homem"),
    "tiago": H_(nome="Tiago", barba="curta", cabelo="preto", roupa="#fb8c00", voz="homem"),
    "joao": H_(nome="João", cabelo="castanho", roupa="#26c6da", roupa2="#ffffff", voz="homem"),
    "mateus": H_(nome="Mateus", barba="curta", cabelo="preto", roupa="#7e57c2", roupa2="#f2c14e", acessorio="pergaminho", voz="homem"),
    "zaqueu": H_(nome="Zaqueu", escala=0.74, barba="curta", cabelo="preto", roupa="#fb8c00", roupa2="#6d4c41", voz="homem"),
    "bartimeu": H_(nome="Bartimeu", barba="curta", cabelo="grisalho", roupa="#a1887f", acessorio="cajado", voz="homem"),
    "lazaro": H_(nome="Lázaro", barba="curta", cabelo="castanho", roupa="#eeeeee", voz="homem"),
    "marta": H_(nome="Marta", genero="f", cobertura="veu", cor_cobertura="#ffcc80", roupa="#ef6c00", voz="mulher"),
    "maria_betania": H_(nome="Maria", genero="f", cabelo="castanho", estilo_cabelo="longo", roupa="#9575cd", voz="mulher"),
    "paulo": H_(nome="Paulo", barba="longa", estilo_cabelo="careca", cabelo="grisalho", roupa="#6d4c41", roupa2="#ffcc80", acessorio="pergaminho", voz="homem"),
    "menino_lanche": H_(nome="Menino", idade="crianca", cabelo="preto", estilo_cabelo="cacheado", roupa="#29b6f6", acessorio="cesta", voz="menino"),
    "samaritano": H_(nome="Bom Samaritano", barba="curta", cobertura="lenco", cor_cobertura="#ffffff", cor_faixa="#00897b", roupa="#00897b", voz="homem"),
    "pastor": H_(nome="Pastor", barba="curta", cobertura="lenco", cor_cobertura="#d7ccc8", roupa="#795548", acessorio="cajado", voz="homem"),
    "pastorzinho": H_(nome="Pastorzinho", idade="crianca", cobertura="faixa", roupa="#a1887f", roupa2="#e53935", acessorio="cajado", voz="menino"),
    "mago_1": H_(nome="Mago", barba="longa", cabelo="branco", cobertura="coroa", manto=True, cor_manto="#8e24aa", roupa="#ffd54f", voz="idoso"),
    "mago_2": H_(nome="Mago", pele="escura", barba="curta", cabelo="preto", cobertura="coroa", manto=True, cor_manto="#00897b", roupa="#ffcc80", voz="homem"),
    "mago_3": H_(nome="Mago", barba="curta", cabelo="castanho", cobertura="coroa", manto=True, cor_manto="#c62828", roupa="#90caf9", voz="homem"),
    "anjo": H_(nome="Anjo", asas=True, cabelo="loiro", estilo_cabelo="cacheado", roupa="#ffffff", roupa2="#ffd54f", voz="anjo"),
    "soldado": H_(nome="Soldado", barba="curta", cobertura="capacete", armadura=True, acessorio="lanca", roupa="#8d6e63", voz="homem"),
    "rei": H_(nome="Rei", barba="curta", cobertura="coroa", manto=True, roupa="#ffe082", voz="homem"),
    "rainha": H_(nome="Rainha", genero="f", estilo_cabelo="longo", cobertura="coroa", roupa="#ba68c8", voz="mulher"),
    # genéricos
    "menino": H_(nome="Menino", idade="crianca", cabelo="preto", roupa="#42a5f5", voz="menino"),
    "menina": H_(nome="Menina", genero="f", idade="crianca", cabelo="castanho", estilo_cabelo="tranca", roupa="#f06292", voz="menina"),
    "homem": H_(nome="Homem", barba="curta", roupa="#8d6e63", voz="homem"),
    "mulher": H_(nome="Mulher", genero="f", cobertura="veu", roupa="#4db6ac", voz="mulher"),
    "idoso": H_(nome="Vovô", idade="idoso", barba="longa", roupa="#a1887f", acessorio="cajado", voz="idoso"),
    "idosa": H_(nome="Vovó", genero="f", idade="idoso", cobertura="veu", roupa="#9575cd", voz="idosa"),
    # animais
    "ovelhinha": H_(tipo="ovelha", pequena=True, voz="animal", nome="Ovelhinha"),
    "ovelha": H_(tipo="ovelha", voz="animal", nome="Ovelha"),
    "leao": H_(tipo="leao", voz="animal", nome="Leão"),
    "pomba": H_(tipo="pomba", voz="animal", nome="Pomba", acessorio="ramo"),
    "baleia": H_(tipo="baleia", voz="gigante", nome="Grande Peixe"),
    "jumento": H_(tipo="jumento", voz="animal", nome="Jumentinho"),
    "camelo": H_(tipo="camelo", voz="animal", nome="Camelo"),
    "cobra": H_(tipo="cobra", voz="animal", nome="Serpente"),
}

TIPOS = {"humano": Humano, "ovelha": Ovelha, "leao": Leao, "pomba": Pomba, "baleia": Baleia,
         "jumento": Quadrupede, "camelo": Quadrupede, "cobra": Cobra}


def criar_personagem(spec: dict) -> Personagem:
    spec = dict(spec or {})
    if "preset" in spec:
        base = dict(PRESETS.get(spec.pop("preset"), PRESETS["homem"]))
        base.update({k: v for k, v in spec.items() if v not in (None, "")})
        spec = base
    cls = TIPOS.get(spec.get("tipo", "humano"), Humano)
    return cls(spec)


def descricao_catalogo() -> str:
    """Texto curto com o catálogo, usado no prompt do roteirista."""
    linhas = []
    for k, v in PRESETS.items():
        linhas.append(f"{k} ({v.get('nome', k)}, voz {v.get('voz')})")
    return "; ".join(linhas)
