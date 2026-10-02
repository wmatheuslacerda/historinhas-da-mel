import json, sys, numpy as np
from PIL import Image
from rembg import new_session, remove
sess = new_session("sam")
P = json.load(open("camadas/prompts.json"))
for nome, p in P.items():
    if nome != sys.argv[1]: continue
    im = Image.open(f"saida/cena{p['cena']}.png").convert("RGB")
    pr = [{"type": "point", "data": xy, "label": 1} for xy in p["pos"]] + \
         [{"type": "point", "data": xy, "label": 0} for xy in p["neg"]]
    m = remove(im, session=sess, only_mask=True, sam_prompt=pr)
    m.save(f"camadas/sam_{nome}.png"); print(nome, (np.array(m) > 127).mean().round(3), flush=True)
