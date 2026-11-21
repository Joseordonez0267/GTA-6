# -*- coding: utf-8 -*-
"""Render de un episodio: registra el arte y los graficos de la serie sobre el
motor de ../render.py y lanza el render. Se llama desde hacer_serie.py con las
variables de entorno TIMELINE, CHUNKS, OUT y STEP."""
import json, math, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import personajes                      # registra escenarios y fichas en arte.SCENE_ART
import arte
from PIL import Image, ImageDraw
import render
from render import (put, text_sprite, grad_text_sprite, panel, appear, ease_out, clamp, lt, W, H,
                    PINK, ORANGE, TEAL, GREEN, RED, glow, art_layers)
from episodios import PERSONAJES, EPISODIOS

META = render.TL.get("meta", {})
EP = META.get("num", 1)
TITLE = META.get("title", "")

arte.SCENE_ART["ep_title"] = arte.SCENE_ART["chapter"]
arte.SCENE_ART["ep_end"] = arte.SCENE_ART["chapter"]

for sc in render.SCENES:
    sc["_tag"] = None if sc["visual"] in ("ep_title", "ep_end") else f"EP. {EP} · {TITLE.upper()}"

_orig_tag = render.ov_tag


def ov_tag(fr, sc, t, dur):
    _orig_tag(fr, sc, t, dur)
    if sc.get("_tag"):
        put(fr, text_sprite("FICCIÓN DE FANS", "Inter-Black.otf", 20, "#1a0b1f"), W - 70, 108, 0, "rm")
        b = text_sprite("FICCIÓN DE FANS", "Inter-Black.otf", 20, PINK, shadow=True)
        put(fr, b, W - 70, 106, 0.85 * appear(t, 0.2), "rm")


render.ov_tag = ov_tag


def ov_ep_title(fr, sc, t, dur):
    a = appear(t, 0.05, 0.4) * (1 - appear(t, dur - 0.35, 0.3))
    put(fr, text_sprite("L E O N I D A", "Inter-Black.otf", 40, PINK), W / 2, H / 2 - 170, a)
    put(fr, text_sprite(f"EPISODIO {EP}", "Inter-Bold.otf", 46, "#ffffff"), W / 2, H / 2 - 95, a)
    k = appear(t, 0.2, 0.5)
    put(fr, grad_text_sprite(TITLE.upper(), 128, "#ffffff", ORANGE, glow_r=18), W / 2, H / 2 + 20, a * k, scale=0.9 + 0.1 * k)
    put(fr, panel(330, 54, fill=(0, 0, 0, 0), outline=PINK, radius=27, width=3), W / 2, H / 2 + 150, a * appear(t, 0.6))
    put(fr, text_sprite("FICCIÓN DE FANS", "Inter-Black.otf", 26, PINK), W / 2, H / 2 + 150, a * appear(t, 0.6))


def ov_ep_end(fr, sc, t, dur):
    a = appear(t, 0.1, 0.5)
    if META.get("final"):
        put(fr, grad_text_sprite("FIN DE LA TEMPORADA 1", 110, "#ffffff", RED, glow_r=18, glow_col=RED), W / 2, H / 2 - 60, a)
        put(fr, text_sprite("¿Quién los traicionó? Cuéntalo en los comentarios.", "Inter-Bold.otf", 40, "#ffffff"), W / 2, H / 2 + 60, appear(t, 0.6))
    else:
        put(fr, grad_text_sprite("CONTINUARÁ…", 140, "#ffffff", PINK, glow_r=18), W / 2, H / 2 - 50, a, scale=0.95 + 0.05 * a)
        nxt = META.get("next")
        if nxt:
            put(fr, text_sprite(f"PRÓXIMO · EP. {EP + 1}: {nxt.upper()}", "Inter-Bold.otf", 40, TEAL), W / 2, H / 2 + 80, appear(t, 0.5))
    put(fr, text_sprite("Historia inventada por fans · sin relación con la trama oficial ni con Rockstar Games",
                        "Inter-Medium.otf", 24, "#cfc8ee"), W / 2, H - 70, appear(t, 0.8))


def ov_card(fr, sc, t, dur):
    p = PERSONAJES[sc["char"]]
    col = p["color"]
    k = appear(t, 0.25, 0.5)
    x = 1100 + (1 - k) * 160
    put(fr, panel(250, 46, fill=(0, 0, 0, 0), outline=col, radius=23, width=3), x, 330, appear(t, 0.15), "lm")
    put(fr, text_sprite("NUEVO PERSONAJE", "Inter-Black.otf", 22, col), x + 145, 330, appear(t, 0.15), "mm")
    nm = text_sprite(p["name"], "InterDisplay-Black.otf", 110, "#ffffff", shadow=True)
    put(fr, nm, x - 12, 450, k, "lm", scale=min(1.0, (W - 80 - x) / nm.width))
    wl = int(560 * appear(t, 0.5, 0.6))
    if wl > 2:
        put(fr, panel(wl, 8, fill=tuple(int(col[i:i + 2], 16) for i in (1, 3, 5)) + (255,), radius=4), x, 530, 1, "lm")
    put(fr, text_sprite(p["role"], "Inter-SemiBold.otf", 38, "#e8e0ff"), x, 590, appear(t, 0.7, 0.5), "lm")


def ov_keys_night(fr, sc, t, dur):
    if not sc.get("radio"):
        return
    a = appear(t, 0.3, 0.5)
    put(fr, panel(560, 170, fill=(0, 10, 20, 210), outline=TEAL, radius=22), 120, 330, a, "lm")
    put(fr, text_sprite("CANAL 16 · GUARDIA COSTERA", "Inter-Black.otf", 26, TEAL), 160, 290, a, "lm")
    rng = random.Random(int(t * 12))
    for i in range(26):
        hgt = 6 + rng.random() * 60 * (0.6 + 0.4 * math.sin(t * 6 + i))
        put(fr, panel(10, int(hgt), fill=(34, 211, 197, 255), radius=4), 165 + i * 19, 365, a, "lm")
    if int(t * 2) % 2 == 0:
        put(fr, panel(16, 16, fill=(255, 77, 77, 255), radius=8), 640, 290, a)


def ov_disco(fr, sc, t, dur):
    if sc.get("target"):
        a = appear(t, 0.6, 0.5)
        put(fr, panel(760, 230, fill=(10, 4, 8, 220), outline=RED, radius=22, width=4), W / 2, 270, a)
        put(fr, text_sprite("OBJETIVO LOCALIZADO", "Inter-Black.otf", 32, RED), W / 2, 205, a * (0.6 + 0.4 * (int(t * 3) % 2)))
        put(fr, text_sprite("BÓVEDA PRIVADA", "InterDisplay-Black.otf", 80, "#ffffff"), W / 2, 275, a)
        put(fr, text_sprite("PORT GELLHORN · MUELLE 9", "Inter-Bold.otf", 30, "#ffd6d6"), W / 2, 340, a)
        return
    a = appear(t, 1.2, 0.6)
    put(fr, panel(700, 330, fill=(4, 10, 14, 225), outline=TEAL, radius=22, width=3), 1350, 330, a)
    for i, lab in enumerate(["NOMBRES", "CUENTAS", "FECHAS"]):
        k = appear(t, 1.6 + i * 0.6, 0.4)
        y = 230 + i * 95
        put(fr, text_sprite(lab, "Inter-Black.otf", 30, TEAL), 1040, y, k, "lm")
        for j in range(3):
            w = 120 + (i * 37 + j * 53) % 140
            put(fr, panel(w, 22, fill=(230, 240, 245, 210), radius=4), 1260 + j * 150, y, k, "lm")


def ov_club(fr, sc, t, dur):
    if not sc.get("rec"):
        return
    a = appear(t, 0.1, 0.3)
    c = (255, 255, 255, 220)
    for (x, y, sx, sy) in ((90, 90, 1, 1), (W - 90, 90, -1, 1), (90, H - 200, 1, -1), (W - 90, H - 200, -1, -1)):
        put(fr, panel(80, 8, fill=c, radius=3), x if sx > 0 else x - 80, y, a, "lm")
        put(fr, panel(8, 80, fill=c, radius=3), x, y if sy > 0 else y - 80, a, "mt")
    if int(t * 2) % 2 == 0:
        put(fr, panel(26, 26, fill=(255, 40, 60, 255), radius=13), 150, 150, a)
    put(fr, text_sprite("REC", "Inter-Black.otf", 38, "#ffffff"), 180, 150, a, "lm")
    put(fr, text_sprite(f"00:{int(8 + t):02d}", "Inter-Bold.otf", 34, "#ffffff"), W - 150, 150, a, "rm")
    # circulo que revela a Lucia al fondo
    t0 = max(0.5, dur * 0.45)
    if t > t0:
        k = appear(t, t0, 0.5)
        ring = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([8, 8, 192, 192], outline=(255, 209, 102, 255), width=8)
        put(fr, glow(ring, 8, 1.0), 1480, 640, k, scale=1.8 - 0.8 * k)
        put(fr, text_sprite("¿LUCÍA?", "Inter-Black.otf", 40, "#ffd166", shadow=True), 1480, 520, k)


_ov_phones = render.OVERLAYS["phones"]


def ov_phones(fr, sc, t, dur):
    _ov_phones(fr, sc, t, dur)
    if not sc.get("viral"):
        return
    a = appear(t, 0.4, 0.5)
    v = 2_000_000 * ease_out((t - 0.4) / 3.0)
    put(fr, panel(760, 150, fill=(10, 4, 16, 225), outline=PINK, radius=30, width=4), W / 2, 150, a)
    put(fr, text_sprite(f"{int(v):,}".replace(",", ".") + " VISTAS", "InterDisplay-Black.otf", 80, "#ffffff"), W / 2, 150, a)
    ls = lt(sc)
    if len(ls) and t > ls[0] + 3.2:
        k = appear(t, ls[0] + 3.2, 0.3)
        put(fr, panel(330, 110, fill=(0, 0, 0, 220), outline=ORANGE, radius=24, width=4), W / 2, 330, k)
        put(fr, panel(14, 50, fill=(255, 177, 92, 255), radius=4), W / 2 - 110, 330, k)
        put(fr, panel(14, 50, fill=(255, 177, 92, 255), radius=4), W / 2 - 80, 330, k)
        put(fr, text_sprite("0:14", "InterDisplay-Black.otf", 64, ORANGE), W / 2 + 40, 330, k)


TEAM = [("raul", "Raul", "DIRIGE"), ("cal", "Cal", "LA RADIO"), ("brian", "Brian", "EL BARCO"),
        ("boobie", "Boobie", "EL DINERO"), ("dimez", "Real Dimez", "LA DISTRACCIÓN")]


def ov_team(fr, sc, t, dur):
    put(fr, text_sprite("EL PLAN", "InterDisplay-Black.otf", 90, "#ffffff", glow_r=14, glow_col=PINK), W / 2, 150, appear(t, 0.1))
    lines = sc["lines"]
    for i, (key, word, job) in enumerate(TEAM):
        # se ilumina cuando el narrador nombra al personaje
        ln = 0 if key != "dimez" else 1
        line = lines[ln]
        off = line["text"].find(word)
        tt = line["start"] - sc["start"] + (line["end"] - line["start"]) * max(0, off) / len(line["text"])
        k = appear(t, tt - 0.1, 0.4)
        p = PERSONAJES[key]
        x = 260 + i * 350
        col = p["color"]
        fill = (20, 14, 34, 230)
        put(fr, panel(300, 420, fill=fill, outline=col if k > 0 else "#3a3450", radius=26, width=4), x, 520, 0.5 + 0.5 * k)
        thumb = _thumb(key)
        put(fr, thumb, x, 470, 0.35 + 0.65 * k)
        put(fr, text_sprite(p["name"].split()[0] if key != "dimez" else "REAL DIMEZ", "Inter-Black.otf", 30, "#ffffff"), x, 640, 0.4 + 0.6 * k)
        put(fr, text_sprite(job, "Inter-Black.otf", 26, col), x, 690, k)


_TH = {}


def _thumb(key):
    if key not in _TH:
        img = Image.new("RGBA", (arte.LW, arte.LH), (0, 0, 0, 0))
        for l, _ in art_layers("card_" + key)[1:]:
            img.alpha_composite(l)
        cx = 640 if key != "dimez" else 650
        crop = img.crop((cx - 420, 180, cx + 420, 180 + 840)).resize((250, 250))
        _TH[key] = crop
    return _TH[key]


def ov_vault(fr, sc, t, dur):
    if not sc.get("photo"):
        return
    k = appear(t, 0.3, 0.8)
    ph = _TH.get("photo")
    if ph is None:
        img = Image.new("RGBA", (arte.LW, arte.LH), (0, 0, 0, 255))
        for l, _ in art_layers("duo"):
            img.alpha_composite(l)
        pic = img.crop((700, 300, 1700, 1100)).resize((420, 336))
        ph = Image.new("RGBA", (470, 450), (245, 242, 235, 255))
        ph.paste(pic, (25, 25))
        ImageDraw.Draw(ph).text((235, 405), "hoy, 9:14 a. m.", font=arte.font("Inter-Medium.otf", 26), fill=(60, 60, 70, 255), anchor="mm")
        ph = ph.rotate(-6, expand=True, resample=Image.BICUBIC)
        _TH["photo"] = ph
    put(fr, ph, W / 2 + 20, H / 2 - 40 + (1 - k) * 200, k, scale=0.7 + 0.3 * k + 0.02 * t)


def ov_black(fr, sc, t, dur):
    # parpadeo de luces antes del apagon
    if t < 1.0 and int(t * 10) % 3 == 0:
        put(fr, panel(W, H, fill=(200, 190, 160, 40), radius=1), 0, 0, 1, "lt")
    if t > 1.5:
        k = appear(t, 1.5, 0.6)
        if int(t * 1.5) % 2 == 0:
            put(fr, panel(18, 18, fill=(255, 40, 60, 255), radius=9), W / 2, H / 2 - 80, k)


render.OVERLAYS.update(ep_title=ov_ep_title, ep_end=ov_ep_end, keys_night=ov_keys_night, disco=ov_disco,
                       club=ov_club, phones=ov_phones, team=ov_team, vault=ov_vault, black=ov_black)
for _key in PERSONAJES:
    render.OVERLAYS["card_" + _key] = ov_card

if __name__ == "__main__":
    if "--preview" in sys.argv:
        out = os.path.join(os.path.dirname(os.environ["OUT"]), "preview")
        os.makedirs(out, exist_ok=True)
        for a in sys.argv[sys.argv.index("--preview") + 1:]:
            render.frame_at(float(a)).save(os.path.join(out, f"f_{float(a):05.2f}.jpg"), quality=88)
    else:
        render.main()
