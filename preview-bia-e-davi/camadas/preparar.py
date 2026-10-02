"""Roda no GitHub Actions: amplia as cenas (Real-ESRGAN), recorta os personagens
e preenche o fundo onde eles estavam (LaMa), para o Remotion animar."""
import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageFilter
from spandrel import ModelLoader

AQUI = Path(__file__).parent
SAIDA = AQUI.parent / "saida"
OUT = AQUI / "out"
OUT.mkdir(exist_ok=True)
torch.set_num_threads(4)

PERSONAGENS = {1: ["1_bia"], 2: ["2_bia", "2_mae"], 3: ["3_davi"], 4: ["4_bia", "4_davi"],
               5: ["5_dupla"], 6: ["6_davi"]}
W2, H2 = 1144, 2048

sr = ModelLoader().load_from_file(str(AQUI / "realesr-general-x4v3.pth")).eval()
lama = torch.jit.load(str(AQUI / "big-lama.pt"), map_location="cpu").eval()


def ampliar(img: Image.Image) -> Image.Image:
    t = torch.from_numpy(np.array(img.convert("RGB"))).permute(2, 0, 1).float().div(255).unsqueeze(0)
    with torch.no_grad():
        o = sr.model(t) if hasattr(sr, "model") else sr(t)
    o = o.squeeze(0).clamp(0, 1).permute(1, 2, 0).numpy()
    return Image.fromarray((o * 255).round().astype("uint8")).resize((W2, H2), Image.LANCZOS)


def preencher(img: Image.Image, mask: Image.Image) -> Image.Image:
    a = torch.from_numpy(np.array(img.convert("RGB"))).permute(2, 0, 1).float().div(255).unsqueeze(0)
    m = torch.from_numpy((np.array(mask) > 127).astype("float32"))[None, None]
    h, w = a.shape[2:]
    ph, pw = (8 - h % 8) % 8, (8 - w % 8) % 8
    a = torch.nn.functional.pad(a, (0, pw, 0, ph), mode="reflect")
    m = torch.nn.functional.pad(m, (0, pw, 0, ph), mode="reflect")
    with torch.inference_mode():
        o = lama(a, m)
    o = o[0, :, :h, :w].permute(1, 2, 0).numpy()
    return Image.fromarray(np.clip(o * 255, 0, 255).astype("uint8"))


camadas = {}
for c, nomes in PERSONAGENS.items():
    print("cena", c, flush=True)
    orig = Image.open(SAIDA / f"cena{c}.png").convert("RGB")
    alfas = {n: np.array(Image.open(AQUI / f"alpha_{n}.png").convert("L")) for n in nomes}
    uniao = np.max(np.stack([(a > 25) for a in alfas.values()]), axis=0).astype("uint8") * 255
    buraco = Image.fromarray(uniao).filter(ImageFilter.MaxFilter(27))
    fundo = preencher(orig, buraco)
    ampliar(fundo).save(OUT / f"fundo{c}.jpg", quality=92)
    grande = ampliar(orig)
    for n, a in alfas.items():
        A = Image.fromarray(a).resize((W2, H2), Image.BILINEAR)
        A = np.clip((np.array(A).astype(float) - 30) / 200, 0, 1)
        ys, xs = np.where(A > 0.02)
        x0, y0 = max(xs.min() - 6, 0), max(ys.min() - 6, 0)
        x1, y1 = min(xs.max() + 7, W2), min(ys.max() + 7, H2)
        rgba = np.dstack([np.array(grande), (A * 255).astype("uint8")])[y0:y1, x0:x1]
        Image.fromarray(rgba, "RGBA").save(OUT / f"{n}.png", optimize=True)
        camadas[n] = {"cena": c, "x": int(x0), "y": int(y0), "w": int(x1 - x0), "h": int(y1 - y0)}
        print("  ", n, camadas[n], flush=True)

(OUT / "camadas.json").write_text(json.dumps(camadas, indent=1))
print("ok")
