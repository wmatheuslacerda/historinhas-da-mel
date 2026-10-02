"""Máscara final de cada personagem (572x1024): contorno automático + área demarcada."""
import numpy as np
from PIL import Image, ImageFilter

def L(p): return np.array(Image.open(p).convert("L")).astype(np.float32) / 255
H, W = 1024, 572
yy, xx = np.mgrid[0:H, 0:W]
def rect(x0, y0, x1, y1): return (xx >= x0) & (xx < x1) & (yy >= y0) & (yy < y1)

def dil(m, r):
    return np.array(Image.fromarray((m * 255).astype("uint8")).filter(ImageFilter.MaxFilter(r))) / 255

out = {}
iso = {c: L(f"camadas/mask_auto{c}.png") for c in range(1, 7)}
# 1 Bia: tudo à esquerda das mãos (braço da mãe fica no fundo)
out["1_bia"] = iso[1] * rect(100, 430, 362, 950)
# 2 Bia: sem a grade da cama
out["2_bia"] = iso[2] * rect(100, 415, 300, 838)
out["2_mae"] = L("camadas/sam_2_mae.png")
# 3 Davi + suporte de soro (SAM acertou), bordas suaves do contorno automático
s3 = L("camadas/sam_3_davi.png")
out["3_davi"] = np.maximum(s3, iso[3] * dil(s3, 9))
# 4 Bia: sem o travesseiro e sem o soro
r4b = rect(40, 360, 250, 785) * (1 - rect(0, 530, 98, 700))
out["4_bia"] = np.maximum(iso[4], L("camadas/sam_4_bia.png")) * r4b
# 4 Davi: sem o soro (exceto a faixa do braço) e sem a base
poste = rect(286, 0, 316, 1024) * (1 - rect(286, 462, 316, 520))
out["4_davi"] = iso[4] * rect(250, 335, 515, 828) * (1 - poste)
# 5 os dois juntos
out["5_dupla"] = iso[5] * rect(118, 345, 475, 822)
# 6 Davi + soro
out["6_davi"] = iso[6] * rect(212, 330, 565, 900)

for k, m in out.items():
    Image.fromarray((np.clip(m, 0, 1) * 255).astype("uint8")).save(f"camadas/alpha_{k}.png")
    print(k, round(float((m > .5).mean()), 3))
