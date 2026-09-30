"""Vídeo longo de domingo: junta os Shorts da semana num vídeo horizontal (16:9).

Uso:
  python -m src.longo                 # baixa os Shorts da semana (GitHub Releases), monta e publica
  python -m src.longo --pasta X --nao-postar --offline   # teste local com vídeos de uma pasta
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import subprocess
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFilter

from . import audio as A
from .main import RAIZ, FUSO, carregar_env, log
from .personagens import criar_personagem
from .video import fonte
from .vozes import Vozes

W, H, FPS = 1920, 1080, 30
MAX_HISTORIAS = 15


def sh(*cmd):
    subprocess.run(cmd, check=True)


def duracao(arquivo) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(arquivo)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


# ------------------------------------------------------------ Shorts da semana
def baixar_semana(pasta: Path) -> list[Path]:
    pasta.mkdir(parents=True, exist_ok=True)
    hoje = dt.datetime.now(FUSO).date()
    for semanas in (0, 1):
        d = hoje - dt.timedelta(weeks=semanas)
        tag = f"semana-{d.isocalendar()[0]}-{d.isocalendar()[1]:02d}"
        r = subprocess.run(["gh", "release", "download", tag, "-D", str(pasta), "--skip-existing"], capture_output=True, text=True)
        log(f"📥 {tag}: {'ok' if r.returncode == 0 else r.stderr.strip()[:120]}")
        if len(list(pasta.glob("*.mp4"))) >= 7:
            break
    return sorted(pasta.glob("*.mp4"))


# ------------------------------------------------------------ artes
def fundo_festa(seed=1) -> Image.Image:
    img = Image.new("RGB", (W, H), "#ffcf6b")
    d = ImageDraw.Draw(img)
    cx, cy = W * 0.3, H * 0.55
    for i in range(36):
        a0, a1 = math.radians(i * 10), math.radians(i * 10 + 5)
        d.polygon([(cx, cy), (cx + 3000 * math.cos(a0), cy + 3000 * math.sin(a0)),
                   (cx + 3000 * math.cos(a1), cy + 3000 * math.sin(a1))], fill="#ffe29a")
    rng = np.random.default_rng(seed)
    for _ in range(90):
        x, y, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(5, 13)
        d.ellipse((x - r, y - r, x + r, y + r), fill=["#ff6f91", "#6ec6ff", "#8bd17c", "#ffffff", "#b388ff"][int(rng.integers(5))])
    d.rectangle((0, H - 170, W, H), fill="#8bd17c")
    return img


def texto_contorno(d, xy, txt, f, cor="white", contorno=(90, 40, 110), larg=10, anchor="la"):
    d.text(xy, txt, font=f, fill=cor, stroke_width=larg, stroke_fill=contorno, anchor=anchor)


def cartao(titulo: str, linhas: list[str], destino: Path, tamanho=(W, H)):
    img = fundo_festa()
    mel = criar_personagem({"preset": "mel", "escala": 2.2}).retrato("feliz")
    mel = mel.crop(mel.getbbox())
    f = 820 / mel.height
    mel = mel.resize((int(mel.width * f), 820), Image.LANCZOS)
    sombra = Image.new("RGBA", (mel.width, 60), (0, 0, 0, 0))
    ImageDraw.Draw(sombra).ellipse((40, 0, mel.width - 40, 50), fill=(0, 0, 0, 60))
    img.paste(sombra, (120, H - 150), sombra.filter(ImageFilter.GaussianBlur(8)))
    img.paste(mel, (120, H - 110 - mel.height), mel)
    d = ImageDraw.Draw(img)
    x = 960
    livre = W - x - 110  # margem extra por causa do zoom suave

    def caber(txt, tam):
        while tam > 30 and fonte(tam).getlength(txt) > livre:
            tam -= 4
        return fonte(tam)

    texto_contorno(d, (x, 170), titulo, caber(titulo, 104), larg=12)
    y = 340
    for ln in linhas[:6]:
        texto_contorno(d, (x, y), "• " + ln, caber("• " + ln, 64), cor="#fff7c2", larg=8)
        y += 90
    img = img.resize(tamanho, Image.LANCZOS)
    img.save(destino)
    return destino


def clipe_cartao(img: Path, fala_audio: np.ndarray, musica_seed: int, destino: Path, dur_min=5.0):
    dur = max(dur_min, len(fala_audio) / A.SR + 1.2)
    voz = np.pad(fala_audio, (int(0.4 * A.SR), 0))
    mus = A.gerar_musica(dur + 0.5, musica_seed)
    mix = A.mixar(voz, mus[: int(dur * A.SR)], np.zeros(1, np.float32), 0.22)
    wav = destino.with_suffix(".wav")
    A.salvar_wav(mix[: int(dur * A.SR)], str(wav))
    sh("ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-i", str(img), "-i", str(wav),
       "-vf", f"zoompan=z='min(zoom+0.0006,1.06)':d={int(dur * FPS)}:s={W}x{H}:fps={FPS}",
       "-t", f"{dur:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2", str(destino))
    return destino


def horizontal(entrada: Path, destino: Path):
    """Short vertical -> 16:9 com fundo desfocado do próprio vídeo."""
    filtro = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:4,eq=brightness=-0.06[bg];"
              f"[0:v]scale=-2:{H}[fg];[bg][fg]overlay=(W-w)/2:0,fps={FPS},format=yuv420p[v]")
    sh("ffmpeg", "-v", "error", "-y", "-i", str(entrada), "-filter_complex", filtro, "-map", "[v]", "-map", "0:a",
       "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
       str(destino))
    return destino


def ts(seg: float) -> str:
    seg = int(seg)
    return f"{seg // 60}:{seg % 60:02d}" if seg < 3600 else f"{seg // 3600}:{seg % 3600 // 60:02d}:{seg % 60:02d}"


# ------------------------------------------------------------ principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pasta", help="usar Shorts desta pasta em vez de baixar do GitHub")
    ap.add_argument("--nao-postar", action="store_true")
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()
    carregar_env()
    cfg = yaml.safe_load((RAIZ / "config.yaml").read_text())
    tmp = RAIZ / ".cache" / "longo"
    tmp.mkdir(parents=True, exist_ok=True)

    videos = sorted(Path(args.pasta).glob("*.mp4")) if args.pasta else baixar_semana(tmp / "shorts")
    videos = videos[-MAX_HISTORIAS:]
    if len(videos) < 3:
        raise SystemExit("Poucos Shorts nesta semana para montar o vídeo longo.")
    historias = []
    for v in videos:
        meta = v.with_suffix(".json")
        r = json.loads(meta.read_text()) if meta.exists() else {}
        historias.append({"arq": v, "nome": r.get("titulo_curto") or v.stem, "ref": r.get("referencia", "")})
    nomes = [h["nome"] for h in historias]
    log(f"📚 {len(historias)} histórias: {', '.join(nomes)}")

    vozes = Vozes(cfg, offline=args.offline, cache=RAIZ / ".cache" / "vozes")
    seed = int(dt.datetime.now(FUSO).strftime("%Y%m%d"))
    abertura = cartao("Histórias da Bíblia com a Mel!", nomes, tmp / "abertura.png")
    fala_ab = vozes.falar(f"Oi, amiguinho! Hoje tem {len(historias)} historinhas da Bíblia pra gente ver juntinho. Vamos lá?", "narrador")
    partes = [clipe_cartao(abertura, fala_ab.audio, seed, tmp / "p00_abertura.mp4")]
    for i, h in enumerate(historias, 1):
        log(f"🎞️  {i}/{len(historias)} {h['nome']}")
        partes.append(horizontal(h["arq"], tmp / f"p{i:02d}.mp4"))
    fim = cartao("Até domingo que vem!", ["Deus te ama!", "Tem historinha nova todo dia"], tmp / "fim.png")
    fala_fim = vozes.falar("Que alegria ver essas histórias com você! Até a próxima. Deus te ama!", "narrador")
    partes.append(clipe_cartao(fim, fala_fim.audio, seed + 1, tmp / "p99_fim.mp4"))

    lista = tmp / "lista.txt"
    lista.write_text("".join(f"file '{p.resolve()}'\n" for p in partes))
    data = dt.datetime.now(FUSO).strftime("%Y-%m-%d")
    saida = RAIZ / "saida"
    saida.mkdir(exist_ok=True)
    mp4 = saida / f"{data}_longo.mp4"
    sh("ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", "-movflags", "+faststart", str(mp4))

    # capítulos
    t, caps = 0.0, []
    for nome, p in zip(["Abertura"] + nomes + ["Tchau!"], partes):
        caps.append(f"{ts(t)} {nome}")
        t += duracao(p)
    minutos = round(t / 60)
    destaque = ", ".join(nomes[:3])
    titulo = f"{len(historias)} Historinhas Bíblicas com a Mel 🐑 {destaque} e mais! | {minutos} min"
    if len(titulo) > 100:
        titulo = f"{len(historias)} Historinhas Bíblicas com a Mel 🐑 | Desenho Bíblico Infantil | {minutos} min"
    descricao = (f"{minutos} minutos de historinhas da Bíblia para crianças de 3 a 6 anos, contadas pela ovelhinha Mel! "
                 "Perfeito para assistir em família, na hora de dormir ou no culto infantil.\n\n"
                 "📚 Histórias deste vídeo:\n" + "\n".join(caps) +
                 "\n\n#historinhabiblica #bibliaparacriancas #desenhobiblico #historiasbiblicas")
    tags = ["historinha bíblica", "histórias bíblicas para crianças", "desenho bíblico", "bíblia para crianças",
            "historinhas da mel", "desenho infantil cristão"] + [n.lower() for n in nomes[:6]]
    capa = cartao(f"{len(historias)} Histórias da Bíblia", nomes[:4], saida / f"{data}_capa.png", tamanho=(1280, 720))
    (saida / f"{data}_longo.json").write_text(json.dumps({"titulo": titulo, "descricao": descricao, "tags": tags},
                                                         ensure_ascii=False, indent=1))
    log(f"✅ Vídeo longo pronto: {mp4} ({ts(t)})")

    if not (args.nao_postar or args.offline):
        from .youtube import enviar
        vid = enviar(str(mp4), titulo, descricao, tags, cfg, capa=str(capa), log=log)
        log(f"🎉 Publicado: https://youtu.be/{vid}")
        resumo = os.environ.get("GITHUB_STEP_SUMMARY")
        if resumo:
            with open(resumo, "a") as f:
                f.write(f"### 🐑 {titulo}\n\nhttps://youtu.be/{vid}\n")


if __name__ == "__main__":
    main()
