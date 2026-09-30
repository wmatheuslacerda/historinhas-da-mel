"""Ferramentas de desenho vetorial simples sobre Pillow.

Tudo é desenhado em alta resolução (supersampling) e reduzido no final,
o que deixa as bordas lisas. Cada forma é uma "máscara" (imagem L) que
pode ser somada/subtraída e depois pintada com contorno e sombra.
"""
from __future__ import annotations

import math
from PIL import Image, ImageChops, ImageDraw, ImageFilter

CONTORNO = "#3a2a22"


def rgba(cor, a: int = 255):
    if isinstance(cor, tuple):
        return cor if len(cor) == 4 else (*cor, a)
    cor = cor.lstrip("#")
    return (int(cor[0:2], 16), int(cor[2:4], 16), int(cor[4:6], 16), a)


def mistura(c1, c2, t: float):
    a, b = rgba(c1), rgba(c2)
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,)


def escurecer(cor, f: float = 0.78):
    r, g, b, a = rgba(cor)
    return (int(r * f), int(g * f), int(b * f), a)


def clarear(cor, f: float = 0.35):
    return mistura(cor, "#ffffff", f)


class Pintor:
    """Tela RGBA em alta resolução com operações de máscara."""

    def __init__(self, w: int, h: int, ss: int = 3):
        self.w, self.h, self.ss = w, h, ss
        self.size = (w * ss, h * ss)
        self.img = Image.new("RGBA", self.size, (0, 0, 0, 0))

    # ---------- máscaras ----------
    def m(self):
        return Image.new("L", self.size, 0)

    def _s(self, v):
        return [x * self.ss for x in v]

    def ell(self, m, box, fill=255):
        ImageDraw.Draw(m).ellipse(self._s(box), fill=fill)
        return m

    def circ(self, m, cx, cy, r, fill=255):
        return self.ell(m, (cx - r, cy - r, cx + r, cy + r), fill)

    def rect(self, m, box, r=0, fill=255):
        box = self._s(box)
        if r:
            ImageDraw.Draw(m).rounded_rectangle(box, radius=r * self.ss, fill=fill)
        else:
            ImageDraw.Draw(m).rectangle(box, fill=fill)
        return m

    def poly(self, m, pts, fill=255):
        ImageDraw.Draw(m).polygon([(x * self.ss, y * self.ss) for x, y in pts], fill=fill)
        return m

    def linha(self, m, pts, w, fill=255):
        d = ImageDraw.Draw(m)
        sp = [(x * self.ss, y * self.ss) for x, y in pts]
        d.line(sp, fill=fill, width=int(w * self.ss), joint="curve")
        r = w * self.ss / 2
        for x, y in (sp[0], sp[-1]):
            d.ellipse((x - r, y - r, x + r, y + r), fill=fill)
        return m

    def arco(self, m, box, ini, fim, w, fill=255):
        ImageDraw.Draw(m).arc(self._s(box), ini, fim, fill=fill, width=int(w * self.ss))
        return m

    @staticmethod
    def soma(*ms):
        out = ms[0].copy()
        for x in ms[1:]:
            out = ImageChops.lighter(out, x)
        return out

    @staticmethod
    def menos(a, b):
        return ImageChops.subtract(a, b)

    @staticmethod
    def inter(a, b):
        return ImageChops.multiply(a, b)

    def acima_de(self, y):
        """Máscara de tudo acima da linha y."""
        return self.rect(self.m(), (0, 0, self.w, y))

    def abaixo_de(self, y):
        return self.rect(self.m(), (0, y, self.w, self.h))

    # ---------- pintura ----------
    def dilatar(self, m, px):
        if px <= 0:
            return m
        sig = px * self.ss / 1.7
        return m.filter(ImageFilter.GaussianBlur(sig)).point(lambda v: 255 if v > 12 else 0)

    def deslocar(self, m, dx, dy):
        out = Image.new("L", m.size, 0)
        out.paste(m, (int(dx * self.ss), int(dy * self.ss)))
        return out

    def pintar(self, m, cor, contorno: float = 5, sombra: float = 0.0,
               cor_contorno=CONTORNO, sombra_dx=-14, sombra_dy=-10, alpha: int = 255):
        full = (0, 0) + self.size
        if contorno:
            self.img.paste(rgba(cor_contorno), full, self.dilatar(m, contorno))
        if alpha < 255:
            m2 = m.point(lambda v: v * alpha // 255)
            self.img.alpha_composite(Image.composite(
                Image.new("RGBA", self.size, rgba(cor)), Image.new("RGBA", self.size, (0, 0, 0, 0)), m2))
        else:
            self.img.paste(rgba(cor), full, m)
        if sombra:
            desl = self.deslocar(m, sombra_dx, sombra_dy)
            cres = ImageChops.subtract(m, desl).filter(ImageFilter.GaussianBlur(self.ss * 2))
            cres = self.inter(cres, m).point(lambda v: int(v * sombra))
            self.img.paste(escurecer(cor, 0.72), full, cres)
        return self

    def brilho(self, m, cor="#ffffff", forca=0.35, dx=10, dy=12):
        """Luz suave no lado de cima/esquerda."""
        desl = self.deslocar(m, dx, dy)
        cres = ImageChops.subtract(m, desl).filter(ImageFilter.GaussianBlur(self.ss * 3))
        cres = self.inter(cres, m).point(lambda v: int(v * forca))
        self.img.paste(rgba(cor), (0, 0) + self.size, cres)

    def reduzir(self, escala: float = 1.0):
        w = max(1, round(self.w * escala))
        h = max(1, round(self.h * escala))
        return self.img.resize((w, h), Image.LANCZOS)


def estrela_pts(cx, cy, r_ext, r_int, n=5, rot=-90):
    pts = []
    for i in range(n * 2):
        r = r_ext if i % 2 == 0 else r_int
        a = math.radians(rot + i * 180 / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts
