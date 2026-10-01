"""Monta a linha do tempo, anima personagens e renderiza o MP4 vertical."""
from __future__ import annotations

import bisect
import math
import random
import subprocess
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

from . import audio as A
from .cenarios import W, H, PES, desenhar, nuvem_sprite
from .desenho import Pintor, rgba, estrela_pts
from .personagens import criar_personagem, PRESETS

FONTE = str(Path(__file__).resolve().parent.parent / "assets" / "fonts" / "Fredoka.ttf")
LEGENDA_Y = 1480
GAP_FALA = 0.28
BORDA_CENA = 0.30
NAO_DESENHADOS = {"narrador", "deus"}
TOC_BATIDAS = (0.18, 0.55)
TOC_DURACAO = 1.4


def fonte(tam, peso="Bold"):
    f = ImageFont.truetype(FONTE, tam)
    try:
        f.set_variation_by_name(peso)
    except Exception:
        pass
    return f


def forma_da_letra(c: str) -> str:
    c = unicodedata.normalize("NFD", c.lower())[:1]
    if c in "a":
        return "a"
    if c in "ei":
        return "e"
    if c in "ou":
        return "o"
    if c in "mbp":
        return "m"
    if c.isalpha():
        return "pequena"
    return "fechada"


def suave(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


@dataclass
class Evento:
    cena: int
    quem: str
    texto: str
    t0: float
    t1: float
    fala: object
    emocao: str | None
    acao: str | None
    alvo: str | None
    env: np.ndarray
    fl: dict | None = None


class Renderizador:
    def __init__(self, roteiro: dict, falas: list, cfg: dict, seed: int = 1, log=print):
        self.r = roteiro
        self.falas = falas          # lista paralela às falas do roteiro (ordem de leitura)
        self.cfg = cfg
        self.fps = cfg["video"]["fps"]
        self.seed = seed
        self.log = log
        self.rng = random.Random(seed)
        self._montar_elenco()
        self._linha_do_tempo()

    # ------------------------------------------------------------ elenco
    def _montar_elenco(self):
        elenco = dict(self.r.get("elenco", {}))
        elenco["mel"] = {"preset": "mel", "escala": 1.45}
        self.pers = {}
        for pid, spec in elenco.items():
            if pid in NAO_DESENHADOS:
                continue
            if isinstance(spec, str):
                spec = {"preset": spec}
            if "preset" not in spec and "tipo" not in spec and pid in PRESETS:
                spec = {"preset": pid, **spec}
            self.pers[pid] = criar_personagem(spec)
        mel_badge = criar_personagem({"preset": "mel", "escala": 0.9})
        self.mel_badge = mel_badge
        self._cache_rot = {}

    # ------------------------------------------------------------ tempo
    def _linha_do_tempo(self):
        self.eventos: list[Evento] = []
        self.cenas_t = []
        t, k = 0.15, 0
        for ci, cena in enumerate(self.r["cenas"]):
            ini = t if ci else 0.0
            t += 0.05 if ci == 0 else BORDA_CENA
            for fl in cena["falas"]:
                fala = self.falas[k]
                k += 1
                env = A.envelope(fala.audio, self.fps)
                self.eventos.append(Evento(ci, fl["quem"], fl["texto"], t, t + fala.duracao, fala,
                                           fl.get("emocao"), fl.get("acao"), fl.get("alvo"), env, fl))
                t += fala.duracao + GAP_FALA
            t += BORDA_CENA - GAP_FALA
            self.cenas_t.append([ini, t])
        self.total = t + 0.7
        self.cenas_t[-1][1] = self.total
        self.inicios = [e.t0 for e in self.eventos]

    # ------------------------------------------------------------ áudio
    def montar_audio(self, destino: str):
        n = int(self.total * A.SR) + A.SR
        voz = np.zeros(n, np.float32)
        efx = np.zeros(n, np.float32)
        for e in self.eventos:
            i0 = int(e.t0 * A.SR)
            voz[i0:i0 + len(e.fala.audio)] += e.fala.audio[: n - i0]
        plim = A.efeito_plim()
        for ci, (ini, _) in enumerate(self.cenas_t):
            if ci == 0:
                continue
            i0 = int((ini - 0.05) * A.SR)
            efx[i0:i0 + len(plim)] += plim[: n - i0]
        toc = A.efeito_toc()
        for e in self.eventos:
            if e.acao == "toctoc" and e.quem == "mel":
                for bat in TOC_BATIDAS:
                    i0 = int((e.t0 + bat) * A.SR)
                    efx[i0:i0 + len(toc)] += toc[: max(0, n - i0)]
        musica = A.gerar_musica(self.total + 0.5, self.seed)
        mix = A.mixar(voz[: int(self.total * A.SR)], musica[: int(self.total * A.SR)], efx[: int(self.total * A.SR)],
                      self.cfg["video"].get("musica_volume", 0.16))
        A.salvar_wav(mix, destino)

    # ------------------------------------------------------------ preparação
    def _preparar_cenas(self):
        self.fundos = []
        for ci, cena in enumerate(self.r["cenas"]):
            fundo, frente, info = desenhar(cena.get("cenario", "campo"), cena.get("periodo", "dia"), self.seed + ci)
            nuvens = []
            if info.get("nuvens"):
                for i in range(3):
                    spr = nuvem_sprite(self.rng, self.rng.uniform(0.6, 1.0),
                                       "#ffffff" if cena.get("periodo") != "tarde" else "#ffe7d6")
                    nuvens.append((spr, self.rng.uniform(0, W), self.rng.uniform(120, 700), self.rng.uniform(8, 22)))
            self.fundos.append((fundo, frente, nuvens))
            # posições
            ids = [p for p in cena.get("personagens", []) if p in self.pers][:3]
            cena["_ids"] = ids
            xs = {1: [540], 2: [300, 780], 3: [190, 540, 890]}.get(len(ids), [])
            cena["_x"] = dict(zip(ids, xs))
        self._luz = self._raios()
        self._arco = self._arco_iris()
        self._fx_rng = random.Random(self.seed + 99)
        self._chuva = [(self._fx_rng.uniform(0, W), self._fx_rng.uniform(0, H), self._fx_rng.uniform(900, 1400)) for _ in range(140)]
        self._brilhos = [(self._fx_rng.uniform(0, W), self._fx_rng.uniform(0, H), self._fx_rng.uniform(0, 6.28), self._fx_rng.uniform(8, 18)) for _ in range(28)]
        self._titulo = self._titulo_img()
        self._badge_mask = self._mascara_badge()

    def _raios(self):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        cx, cy = W / 2, -120
        for i in range(-6, 7):
            a = math.radians(90 + i * 9)
            a1, a2 = a - math.radians(2.6), a + math.radians(2.6)
            d.polygon([(cx, cy), (cx + 2600 * math.cos(a1), cy + 2600 * math.sin(a1)),
                       (cx + 2600 * math.cos(a2), cy + 2600 * math.sin(a2))], fill=(255, 246, 200, 70))
        img = img.filter(ImageFilter.GaussianBlur(18))
        g = Image.new("L", (W, H), 0)
        ImageDraw.Draw(g).ellipse((cx - 420, cy - 420, cx + 420, cy + 520), fill=160)
        g = g.filter(ImageFilter.GaussianBlur(90))
        img.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", (W, H), (255, 250, 220)).split(), g)))
        return img

    def _arco_iris(self):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        cores = ["#ff5252", "#ffa040", "#ffe14d", "#6fdc6f", "#4fc3f7", "#7c83ff", "#c77dff"]
        for i, c in enumerate(cores):
            r = 700 - i * 34
            d.arc((540 - r, 1150 - r, 540 + r, 1150 + r), 180, 360, fill=rgba(c, 190), width=34)
        return img.filter(ImageFilter.GaussianBlur(2))

    def _titulo_img(self):
        txt = self.r.get("titulo_curto") or self.r.get("titulo", "")
        f = fonte(56)
        w = int(f.getlength(txt)) + 90
        img = Image.new("RGBA", (w + 16, 120), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((8, 14, w + 8, 106), radius=46, fill=(255, 255, 255, 235), outline=(58, 42, 34, 255), width=6)
        d.text((w / 2 + 8, 60), txt, font=f, fill=(90, 50, 120), anchor="mm")
        return img

    def _mascara_badge(self):
        m = Image.new("L", (240, 240), 0)
        ImageDraw.Draw(m).ellipse((0, 0, 239, 239), fill=255)
        return m

    # ------------------------------------------------------------ estado
    def _evento_em(self, t):
        i = bisect.bisect_right(self.inicios, t) - 1
        if i >= 0 and self.eventos[i].t0 <= t <= self.eventos[i].t1:
            return self.eventos[i]
        return None

    def _cena_em(self, t):
        for ci, (a, b) in enumerate(self.cenas_t):
            if t < b:
                return ci
        return len(self.cenas_t) - 1

    def _boca(self, ev: Evento, t, emocao):
        lt = t - ev.t0
        fi = min(int(lt * self.fps), len(ev.env) - 1)
        if fi < 0 or ev.env[fi] < 0.12:
            return "fechada"
        f = ev.fala
        j = bisect.bisect_right(f.inicios, lt) - 1
        if 0 <= j < len(f.letras):
            forma = forma_da_letra(f.letras[j])
            if forma == "fechada":
                return "pequena" if ev.env[fi] > 0.3 else "fechada"
            if forma == "pequena" and ev.env[fi] > 0.65:
                return "e"
            return forma
        return "pequena"

    def _emocoes_ate(self, ci, t):
        """Emoção atual de cada personagem na cena ci."""
        emo = dict(self.r["cenas"][ci].get("emocoes", {}))
        for e in self.eventos:
            if e.cena != ci or e.t0 > t:
                continue
            quem = e.alvo if (e.alvo and e.quem in NAO_DESENHADOS) else e.quem
            if e.emocao:
                emo[quem] = e.emocao
        return emo

    def _acoes(self, ci, t):
        """{id: (acao, tempo desde o início)} de ações ativas."""
        out = {}
        for e in self.eventos:
            if e.cena != ci or not e.acao or e.t0 > t:
                continue
            alvo = e.alvo or e.quem
            if e.acao in ("cair", "tchau") or t <= e.t1 + 0.2:
                out[alvo] = (e.acao, t - e.t0, e.t1 - e.t0, e.fl or {})
        return out

    # ------------------------------------------------------------ sprites
    def _cabeca(self, pid, p, emocao, fechados, boca, tilt, espelho):
        k = (pid, emocao, fechados, boca, tilt, espelho)
        img = self._cache_rot.get(k)
        if img is None:
            img = p.sprite_cabeca(emocao, fechados, boca)
            if tilt:
                img = img.rotate(tilt, resample=Image.BICUBIC, center=p.pivo)
            if espelho:
                img = ImageOps.mirror(img)
            if len(self._cache_rot) > 1500:
                self._cache_rot.clear()
            self._cache_rot[k] = img
        return img

    def _corpo(self, pid, p, espelho):
        k = (pid, "corpo", espelho)
        img = self._cache_rot.get(k)
        if img is None:
            img = p.sprite_corpo()
            if espelho:
                img = ImageOps.mirror(img)
            self._cache_rot[k] = img
        return img

    # ------------------------------------------------------------ legenda
    def _legenda(self, ev: Evento, t):
        palavras = ev.fala.palavras()
        if not palavras:
            return None, None
        # divide em pedaços curtos
        pedacos, atual, chars = [], [], 0
        for i, (pw, a, b) in enumerate(palavras):
            if atual and (chars + len(pw) > 20 or len(atual) >= 4):
                pedacos.append(atual)
                atual, chars = [], 0
            atual.append(i)
            chars += len(pw) + 1
        if atual:
            pedacos.append(atual)
        lt = t - ev.t0
        ativo = 0
        for i, (pw, a, b) in enumerate(palavras):
            if lt >= a - 0.05:
                ativo = i
        for pi, ped in enumerate(pedacos):
            if ativo in ped:
                break
        chave = (id(ev), pi, ativo)
        if getattr(self, "_leg_k", None) == chave:
            return self._leg_img, self._leg_nome
        textos = [palavras[i][0] for i in ped]
        f = fonte(86)
        esp = f.getlength(" ") + 20
        larg = [f.getlength(x) for x in textos]
        total = sum(larg) + esp * (len(textos) - 1)
        linhas = [list(range(len(textos)))]
        if total > 960:
            meio = len(textos) // 2 or 1
            linhas = [list(range(meio)), list(range(meio, len(textos)))]
        img = Image.new("RGBA", (W, 250), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        y = 60 if len(linhas) == 1 else 10
        for ln in linhas:
            lw = sum(larg[i] for i in ln) + esp * (len(ln) - 1)
            x = (W - lw) / 2
            for i in ln:
                idx = ped[i]
                cor = (255, 214, 64) if idx == ativo else (255, 255, 255)
                d.text((x, y), textos[i], font=f, fill=cor, stroke_width=10, stroke_fill=(58, 34, 30))
                x += larg[i] + esp
            y += 104
        nome = None
        if ev.quem not in ("narrador", "mel") and ev.quem in self.pers:
            nome = self.pers[ev.quem].nome or ev.quem
        elif ev.quem == "deus":
            nome = "Deus"
        self._leg_k, self._leg_img, self._leg_nome = chave, img, nome
        return img, nome

    def _etiqueta(self, nome):
        k = ("etq", nome)
        if k not in self._cache_rot:
            f = fonte(46)
            w = int(f.getlength(nome)) + 60
            img = Image.new("RGBA", (w + 10, 84), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.rounded_rectangle((5, 8, w + 5, 76), radius=34, fill=(255, 111, 145, 255), outline=(58, 34, 30), width=5)
            d.text((w / 2 + 5, 42), nome, font=f, fill="white", anchor="mm")
            self._cache_rot[k] = img
        return self._cache_rot[k]

    # ------------------------------------------------------------ quadro
    def quadro(self, t: float) -> Image.Image:
        ci = self._cena_em(t)
        cena = self.r["cenas"][ci]
        fundo, frente, nuvens = self.fundos[ci]
        img = fundo.copy()
        ini_cena = self.cenas_t[ci][0]
        tc = t - ini_cena
        for spr, x0, y, vel in nuvens:
            x = (x0 + vel * t) % (W + spr.width) - spr.width
            img.paste(spr, (int(x), int(y)), spr)

        efeito = cena.get("efeito")
        ev = self._evento_em(t)
        voz_deus = bool(ev and ev.quem == "deus" and ev.cena == ci)
        if efeito == "luz" or voz_deus:
            a = 0.75 + 0.25 * math.sin(t * 2.2)
            luz = self._luz
            if a < 0.99:
                r, g, b, al = luz.split()
                luz = Image.merge("RGBA", (r, g, b, al.point(lambda v, a=a: int(v * a))))
            img.paste(luz, (0, 0), luz)
        if efeito == "arco_iris":
            a = suave(tc / 1.2)
            arco = self._arco
            if a < 0.99:
                r, g, b, al = arco.split()
                arco = Image.merge("RGBA", (r, g, b, al.point(lambda v, a=a: int(v * a))))
            img.paste(arco, (0, 0), arco)

        mel_fx = []
        mel_pos = None
        emo = self._emocoes_ate(ci, t)
        acoes = self._acoes(ci, t)
        ids = cena["_ids"]
        prev_ids = self.r["cenas"][ci - 1]["_ids"] if ci > 0 else []
        for idx, pid in enumerate(ids):
            p = self.pers[pid]
            x = cena["_x"][pid]
            larg = p.sprite_corpo().width
            x = min(max(x, larg / 2 - 40), W - larg / 2 + 40)
            espelho = x > 540 or (len(ids) == 1 and pid != "mel" and False)
            if pid not in prev_ids and ci > 0:
                u = suave((tc - 0.05) / 0.5)
                lado = -1 if x <= 540 else 1
                x = x + lado * (1 - u) * 800
            fase = idx * 1.7 + len(pid)
            falando = ev is not None and ev.quem == pid and ev.cena == ci
            dy = math.sin(t * 2 * math.pi * 0.45 + fase) * 4
            tilt = 0
            if falando:
                dy -= abs(math.sin((t - ev.t0) * 2 * math.pi * 2.0)) * 12
                tilt = int(round(3 * math.sin((t - ev.t0) * 2 * math.pi * 0.8) / 1.5)) * 1.5
            e = emo.get(pid, "feliz")
            boca = self._boca(ev, t, e) if falando else "fechada"
            piscar = ((t + fase * 1.3) % (3.1 + (idx % 3) * 0.7)) < 0.13
            dx, rot = 0, 0
            if pid in acoes:
                ac, at, dur, extra = acoes[pid]
                if ac == "pular" and at < 0.6:
                    dy -= math.sin(math.pi * at / 0.6) * 130
                elif ac == "comemorar" and at < dur:
                    dy -= abs(math.sin(math.pi * at / 0.45)) * 90
                elif ac == "tremer" and at < dur:
                    dx += math.sin(at * 70) * 7
                    e = "assustado" if "assustado" not in emo.get(pid, "") else emo[pid]
                elif pid == "mel" and ac in ("rir", "chorar", "tchau", "toctoc"):
                    rindo = ac == "rir" or (ac == "tchau" and extra.get("risadinha") and at < 1.1)
                    chorando = ac == "chorar" or (ac == "tchau" and extra.get("chorinho"))
                    if rindo and at < dur + 0.2:
                        dy -= abs(math.sin(at * 2 * math.pi * 3.2)) * 16
                        dx += math.sin(at * 2 * math.pi * 1.6) * 6
                        piscar = True
                        e = "feliz"
                        mel_fx.append(("rir", at))
                    if chorando and at < dur + 0.6:
                        e = "triste" if ac == "chorar" else "feliz"
                        mel_fx.append(("chorar", at))
                    if ac == "tchau" and (not extra.get("risadinha") or at >= 0.9):
                        mel_fx.append(("tchau", at))
                    if ac == "toctoc" and at < TOC_DURACAO:
                        mel_fx.append(("toctoc", at))
                elif ac == "cair":
                    rot = -85 * suave(at / 0.7)
                    piscar = at > 0.7
            corpo = self._corpo(pid, p, espelho)
            cab = self._cabeca(pid, p, e, piscar, boca, tilt * (-1 if espelho else 1), espelho)
            bx = int(x - corpo.width / 2 + dx)
            by = int(PES - corpo.height + dy + p.flutua)
            if rot:
                comp = Image.new("RGBA", corpo.size, (0, 0, 0, 0))
                comp.alpha_composite(corpo)
                comp.alpha_composite(cab)
                ang = rot if espelho else -rot   # cai para trás (longe de quem está no centro)
                comp = comp.rotate(ang, resample=Image.BICUBIC, expand=True)
                comp = comp.crop(comp.getbbox())
                if comp.width > 600:
                    f = 600 / comp.width
                    comp = comp.resize((600, max(1, int(comp.height * f))), Image.BILINEAR)
                cx_q = x + (40 if espelho else -40) * suave(abs(rot) / 85)
                cx_q = min(max(cx_q, comp.width / 2 - 10), W - comp.width / 2 + 10)
                img.paste(comp, (int(cx_q - comp.width / 2), int(PES + 25 - comp.height)), comp)
                continue
            # sombra no chão
            if p.flutua <= 0 and p.flutua > -100:
                sh = self._sombra(corpo.width)
                img.paste(sh, (int(x - sh.width / 2 + dx), PES - 20), sh)
            img.paste(corpo, (bx, by), corpo)
            img.paste(cab, (bx, by + int(min(dy, 0) * 0.15)), cab)
            if pid == "mel":
                mel_pos = (bx, by + int(min(dy, 0) * 0.15), p, espelho, corpo.width)
                for fx, at in mel_fx:
                    if fx == "tchau":
                        self._patinha_tchau(img, bx, by, p, espelho, corpo.width, at)
                    elif fx == "chorar":
                        self._lagrimas(img, mel_pos, at)

        if frente is not None:
            img.paste(frente, (0, 0), frente)

        if efeito == "chuva":
            d = ImageDraw.Draw(img, "RGBA")
            for x0, y0, v in self._chuva:
                y = (y0 + v * t) % (H + 100) - 50
                x = (x0 - 0.25 * v * t) % W
                d.line((x, y, x - 10, y + 44), fill=(210, 230, 255, 170), width=4)
        elif efeito in ("brilhos", "estrelas", "coracoes"):
            d = ImageDraw.Draw(img, "RGBA")
            for x0, y0, fase, r in self._brilhos:
                a = 0.5 + 0.5 * math.sin(t * 3 + fase)
                if efeito == "estrelas":
                    x, y = x0, y0 * 0.55
                else:
                    x = x0 + 18 * math.sin(t * 1.3 + fase)
                    y = (y0 - 60 * t) % H
                if efeito == "coracoes":
                    s = r * 1.3
                    cor = (255, 100, 140, int(200 * a + 40))
                    d.ellipse((x - s, y - s, x, y), fill=cor)
                    d.ellipse((x, y - s, x + s, y), fill=cor)
                    d.polygon([(x - s, y - s / 2), (x + s, y - s / 2), (x, y + s)], fill=cor)
                else:
                    cor = (255, 240, 150, int(230 * a + 20))
                    d.polygon(estrela_pts(x, y, r * (0.7 + 0.5 * a), r * 0.3, 4), fill=cor)

        # título
        if cena.get("cenario") != "abertura" or tc > 0:
            tt = self._titulo
            img.paste(tt, (int((W - tt.width) / 2), 150), tt)

        # selo da Mel quando ela narra fora de cena
        if ev and ev.quem in ("narrador", "mel") and "mel" not in cena["_ids"]:
            e = ev.emocao or "feliz"
            boca = self._boca(ev, t, e)
            cab = self.mel_badge.sprite_cabeca(e, ((t % 3.4) < 0.12), boca)
            s = self.mel_badge.escala
            recorte = cab.crop((int(50 * s), int(40 * s), int(50 * s) + 290, int(40 * s) + 290)).resize((230, 230))
            fundo_b = Image.new("RGBA", (240, 240), (255, 236, 179, 255))
            fundo_b.paste(recorte, (5, 18), recorte)
            bx, by = 800, 290
            ImageDraw.Draw(img).ellipse((bx - 8, by - 8, bx + 248, by + 248), fill=(255, 111, 145))
            img.paste(fundo_b, (bx, by), self._badge_mask)

        for fx, at in mel_fx:
            if fx == "rir" and mel_pos:
                self._risada(img, mel_pos, at)
        toc = next((at for fx, at in mel_fx if fx == "toctoc"), None)
        if toc is not None:
            img = self._toctoc(img, toc)

        # legenda
        if ev:
            leg, nome = self._legenda(ev, t)
            if leg is not None:
                img.paste(leg, (0, LEGENDA_Y - 60), leg)
                if nome:
                    et = self._etiqueta(nome)
                    img.paste(et, (int((W - et.width) / 2), LEGENDA_Y - 140), et)

        # transição (íris)
        r_iris = None
        for ci2, (a, b) in enumerate(self.cenas_t):
            if ci2 > 0 and abs(t - a) < 0.25:
                r_iris = 1250 * suave(abs(t - a) / 0.25)
        if t > self.total - 0.35:
            r_iris = 1250 * suave((self.total - t) / 0.35)
        if r_iris is not None and r_iris < 1240:
            m = Image.new("L", (W, H), 255)
            ImageDraw.Draw(m).ellipse((540 - r_iris, 950 - r_iris, 540 + r_iris, 950 + r_iris), fill=0)
            img.paste((58, 34, 72), (0, 0, W, H), m)
        return img

    # ------------------------------------------------------------ interações da Mel
    def _sprite_patinha(self, tam):
        k = ("patinha", tam)
        if k not in self._cache_rot:
            p = Pintor(260, 520)
            la = Pintor.soma(*[p.circ(p.m(), 130 + 18 * math.sin(i), 120 + i * 62, 64) for i in range(6)])
            p.pintar(la, "#fffaf2", contorno=5, sombra=0.35)
            casco = p.rect(p.m(), (78, 2, 182, 104), r=46)
            p.pintar(casco, "#4b3b3b", contorno=5)
            p.pintar(p.linha(p.m(), [(130, 14), (130, 70)], 7), "#2e2424", contorno=0)
            img = p.reduzir(1.0)
            img = img.resize((int(img.width * tam / img.height), tam), Image.LANCZOS)
            self._cache_rot[k] = img
        return self._cache_rot[k]

    def _sola(self, tam):
        k = ("sola", tam)
        if k not in self._cache_rot:
            p = Pintor(520, 520)
            la = Pintor.soma(*[p.circ(p.m(), 260 + 175 * math.cos(math.radians(a)), 260 + 175 * math.sin(math.radians(a)), 78)
                               for a in range(0, 360, 36)], p.circ(p.m(), 260, 260, 190))
            p.pintar(la, "#fffaf2", contorno=6, sombra=0.35)
            for lado in (-1, 1):
                casco = p.ell(p.m(), (260 + lado * 8 - (0 if lado > 0 else 110), 150, 260 + lado * 8 + (110 if lado > 0 else 0), 360))
                p.pintar(casco, "#4b3b3b", contorno=6)
                p.brilho(casco, forca=0.25)
            img = p.reduzir(1.0).resize((tam, tam), Image.LANCZOS)
            self._cache_rot[k] = img
        return self._cache_rot[k]

    def _patinha_tchau(self, img, bx, by, p, espelho, larg, at):
        s = p.escala
        lado = -1 if espelho else 1
        ombro_x = bx + larg / 2 + lado * 105 * s
        ombro_y = by + 300 * s
        sobe = suave(min(at, 0.35) / 0.35)
        ang = lado * (-(110 - 80 * sobe) - 22 * math.sin(at * 2 * math.pi * 1.8) * sobe)
        pat = self._sprite_patinha(int(200 * s))
        rot = pat.rotate(ang, resample=Image.BICUBIC, expand=True)
        # o "casco" fica na ponta: posiciona a base (lã) no ombro
        r = pat.height / 2 - 30 * s
        a = math.radians(ang)
        cx = ombro_x - math.sin(a) * r
        cy = ombro_y - math.cos(a) * r
        img.paste(rot, (int(cx - rot.width / 2), int(cy - rot.height / 2)), rot)

    def _lagrimas(self, img, pos, at):
        bx, by, p, espelho, larg = pos
        s = p.escala
        d = ImageDraw.Draw(img, "RGBA")
        for i, ex in enumerate((p.cx + p.off - 34, p.cx + p.off + 34)):
            x = bx + (larg - ex * s if espelho else ex * s) + (-14 if i == 0 else 14) * s
            for k in range(2):
                fase = (at * 0.9 + k * 0.5 + i * 0.25) % 1.0
                y = by + (200 + fase * 150) * s
                r = (12 + 5 * (1 - fase)) * s
                al = int(230 * (1 - fase ** 2))
                d.ellipse((x - r, y - r, x + r, y + r * 1.5), fill=(110, 190, 255, al), outline=(60, 130, 210, al), width=2)
                d.polygon([(x - r * 0.75, y - r * 0.4), (x + r * 0.75, y - r * 0.4), (x, y - r * 2.4)], fill=(110, 190, 255, al))
            # risquinho de lágrima no rosto
            d.line((x, by + 196 * s, x, by + 206 * s + 70 * s * min(at, 1)), fill=(150, 210, 255, 160), width=int(7 * s))

    def _risada(self, img, pos, at):
        bx, by, p, espelho, larg = pos
        f = fonte(84)
        d = ImageDraw.Draw(img, "RGBA")
        for i, txt in enumerate(("hi", "hi", "hi!")):
            ti = at - i * 0.22
            if ti < 0:
                continue
            u = min(ti / 1.1, 1)
            x = bx + larg / 2 + (150 + i * 70) * (-1 if espelho else 1)
            y = by + 40 - u * 120 - i * 40
            al = int(255 * (1 - u ** 3))
            d.text((x, y), txt, font=f, fill=(255, 111, 145, al), anchor="mm", stroke_width=6, stroke_fill=(255, 255, 255, al))

    def _toctoc(self, img, at):
        """A Mel bate na tela por dentro: patinha gigante, tela treme, ondinhas e TOC!"""
        out = img
        for j, bat in enumerate(TOC_BATIDAS):
            u = at - bat
            if -0.18 < u < 0.08:
                sh = int(14 * (1 - abs(u + 0.05) / 0.2))
                out = ImageOps.expand(img.crop((sh, sh, W, H)), border=(0, 0, sh, sh), fill=(58, 34, 72))
                break
        d = ImageDraw.Draw(out, "RGBA")
        tx, ty = 780, 640
        # patinha chegando perto da "tela"
        perto = 0.0
        for bat in TOC_BATIDAS:
            u = at - bat
            perto = max(perto, 1 - min(abs(u) / 0.18, 1))
        entra = suave(min(at, 0.25) / 0.25) * (1 - suave(max(0, at - (TOC_DURACAO - 0.3)) / 0.3))
        if entra > 0.01:
            tam = int(300 + 120 * perto)
            pat = self._sola(tam)
            if perto > 0.05:  # sombra de "vidro" quando encosta
                pat = pat.rotate(-8 * perto, resample=Image.BICUBIC)
            px = tx - pat.width / 2
            py = ty - pat.height / 2 + (1 - entra) * 900
            out.paste(pat, (int(px), int(py)), pat)
        for j, bat in enumerate(TOC_BATIDAS):
            u = at - bat
            if 0 <= u < 0.6:
                for k in range(3):
                    r = 60 + (u * 520) + k * 50
                    al = int(200 * (1 - u / 0.6))
                    d.ellipse((tx - r, ty - r * 0.7, tx + r, ty + r * 0.7), outline=(255, 255, 255, al), width=7)
                f = fonte(int(120 + 30 * (1 - min(u / 0.2, 1))))
                x = tx + (-260 if j == 0 else 40)
                y = ty - 300 + j * 40 - u * 60
                al = int(255 * (1 - (u / 0.6) ** 2))
                d.text((x, y), "TOC!", font=f, fill=(255, 213, 79, al), anchor="mm", stroke_width=10, stroke_fill=(61, 43, 86, al))
        return out

    def _sombra(self, largura):
        k = ("sombra", largura)
        if k not in self._cache_rot:
            w = int(largura * 0.7)
            s = Image.new("RGBA", (w, 44), (0, 0, 0, 0))
            ImageDraw.Draw(s).ellipse((0, 0, w - 1, 43), fill=(0, 0, 0, 60))
            self._cache_rot[k] = s.filter(ImageFilter.GaussianBlur(5))
        return self._cache_rot[k]

    # ------------------------------------------------------------ render
    def renderizar(self, destino: str, pasta_tmp: str):
        Path(pasta_tmp).mkdir(parents=True, exist_ok=True)
        wav = str(Path(pasta_tmp) / "audio.wav")
        self.log("🎵 Montando áudio (vozes + música)...")
        self.montar_audio(wav)
        self.log("🎨 Desenhando cenários e personagens...")
        self._preparar_cenas()
        n = int(self.total * self.fps)
        self.log(f"🎬 Renderizando {n} quadros ({self.total:.1f}s)...")
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
               "-r", str(self.fps), "-i", "pipe:0", "-i", wav, "-c:v", "libx264", "-preset", "veryfast",
               "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
               "-movflags", "+faststart", destino]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for i in range(n):
            proc.stdin.write(self.quadro(i / self.fps).tobytes())
            if i % (self.fps * 10) == 0 and i:
                self.log(f"   {i}/{n}")
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg falhou ao gerar o vídeo")
        return destino
