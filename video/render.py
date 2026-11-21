# -*- coding: utf-8 -*-
"""Montaje: genera todos los cuadros del video a partir de timeline.json.

Camara con paralaje sobre las capas de arte.py, graficos animados por escena,
rotulos, etiqueta de capitulo, subtitulos, transiciones y vineta.
Se renderiza en paralelo por tramos y cada tramo se codifica con ffmpeg.

Uso: python3 render.py [--preview SEG]   (SEG = segundo a previsualizar)
"""
import json, math, os, random, subprocess, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import arte
from arte import W, H, LW, LH, font, hexc, glow, vgrad

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
FPS = 30
XFADE = 0.6

PINK, ORANGE, TEAL, PURPLE, GREEN, RED = "#ff3d8b", "#ffb15c", "#22d3c5", "#8b5cf6", "#3ddc84", "#ff4d4d"

TL = json.load(open(os.path.join(BUILD, "timeline.json"), encoding="utf-8"))
SCENES = TL["scenes"]
SUBS = TL["subs"]
DURATION = TL["duration"]

# capitulo vigente para la etiqueta superior
_chap = None
for sc in SCENES:
    if sc["visual"] == "chapter":
        _chap = f"CAP. {sc['num']} · {sc['title'].upper()}"
        sc["_tag"] = None
    elif sc["visual"] in ("outro", "sunset_city", "title"):
        sc["_tag"] = None
        if sc["visual"] == "outro":
            _chap = None
    else:
        sc["_tag"] = _chap


# ------------------------------------------------------------------ helpers
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def appear(t, t0, d=0.5):
    return ease_out((t - t0) / d)


_SPR = {}


def text_sprite(text, fname="InterDisplay-Black.otf", size=80, fill="#ffffff", stroke=0, stroke_fill="#000000",
                glow_r=0, glow_col=None, shadow=False):
    key = (text, fname, size, fill, stroke, stroke_fill, glow_r, glow_col, shadow)
    if key in _SPR:
        return _SPR[key]
    f = font(fname, size)
    l, t, r, b = f.getbbox(text, stroke_width=stroke)
    pad = max(glow_r * 3, 12)
    w, h = r - l + 2 * pad, b - t + 2 * pad
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if shadow:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - l + 4, pad - t + 6), text, font=f, fill=(0, 0, 0, 170), stroke_width=stroke)
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    if glow_r:
        g = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((pad - l, pad - t), text, font=f, fill=hexc(glow_col or fill), stroke_width=stroke + 2)
        g = g.filter(ImageFilter.GaussianBlur(glow_r))
        img.alpha_composite(g)
        img.alpha_composite(g)
    d.text((pad - l, pad - t), text, font=f, fill=hexc(fill) if isinstance(fill, str) else fill,
           stroke_width=stroke, stroke_fill=hexc(stroke_fill) if stroke else None)
    _SPR[key] = img
    return img


def grad_text_sprite(text, size, c1, c2, fname="InterDisplay-Black.otf", glow_r=24, glow_col=PINK):
    key = ("grad", text, size, c1, c2, fname, glow_r, glow_col)
    if key in _SPR:
        return _SPR[key]
    f = font(fname, size)
    l, t, r, b = f.getbbox(text)
    pad = glow_r * 3 + 10
    w, h = r - l + 2 * pad, b - t + 2 * pad
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).text((pad - l, pad - t), text, font=f, fill=255)
    g = vgrad(w, h, [(0, c1), (0.5, c1), (1, c2)])
    txt = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    txt.paste(g, (0, 0), mask)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gl = Image.new("RGBA", (w, h), hexc(glow_col))
    gl.putalpha(mask.filter(ImageFilter.GaussianBlur(glow_r)))
    out.alpha_composite(gl)
    out.alpha_composite(gl)
    out.alpha_composite(txt)
    _SPR[key] = out
    return out


def put(frame, spr, x, y, alpha=1.0, anchor="mm", scale=1.0):
    if alpha <= 0.003:
        return
    if scale != 1.0:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BILINEAR)
    if alpha < 0.999:
        a = np.asarray(spr).copy()
        a[..., 3] = (a[..., 3].astype(np.float32) * alpha).astype(np.uint8)
        spr = Image.fromarray(a)
    w, h = spr.size
    ox = {"l": 0, "m": w // 2, "r": w}[anchor[0]]
    oy = {"t": 0, "m": h // 2, "b": h}[anchor[1]]
    x, y = int(x - ox), int(y - oy)
    # recorte para alpha_composite (no admite coordenadas negativas)
    sx, sy = max(0, -x), max(0, -y)
    if sx or sy:
        spr = spr.crop((sx, sy, w, h))
        x, y = x + sx, y + sy
    if x >= W or y >= H:
        return
    frame.alpha_composite(spr, (x, y))


def panel(w, h, fill=(10, 8, 24, 200), outline=None, radius=28, width=3):
    key = ("panel", w, h, fill, outline, radius, width)
    if key in _SPR:
        return _SPR[key]
    img = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([20, 26, w + 20, h + 26], radius, fill=(0, 0, 0, 140))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)))
    ImageDraw.Draw(img).rounded_rectangle([20, 20, w + 20, h + 20], radius, fill=fill,
                                           outline=hexc(outline) if outline else None, width=width)
    _SPR[key] = img
    return img


def wrap(text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        test = (cur + " " + wd).strip()
        if f.getlength(test) > maxw and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def sub_sprite(text):
    key = ("sub", text)
    if key in _SPR:
        return _SPR[key]
    f = font("Inter-SemiBold.otf", 44)
    lines = wrap(text, f, 1480)
    lh = 58
    w = int(max(f.getlength(l) for l in lines)) + 80
    h = lh * len(lines) + 34
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 18, fill=(0, 0, 0, 150))
    for i, l in enumerate(lines):
        d.text((w // 2, 17 + i * lh + lh // 2), l, font=f, fill=(255, 255, 255, 255), anchor="mm",
               stroke_width=2, stroke_fill=(0, 0, 0, 255))
    _SPR[key] = img
    return img


def fmt_int(n):
    return f"{int(n):,}".replace(",", ".")


# ------------------------------------------------------------------ arte y camara
_ART = {}


def art_layers(visual):
    if visual not in _ART:
        _ART[visual] = arte.SCENE_ART[visual]()
    return _ART[visual]


def camera(idx, u):
    rng = random.Random(idx * 7919 + 3)
    zin = rng.random() < 0.6
    z0, z1 = (1.0, 1.09) if zin else (1.09, 1.0)
    ang = rng.uniform(0, 2 * math.pi)
    mag = rng.uniform(40, 90)
    px0, py0 = math.cos(ang) * mag, math.sin(ang) * mag * 0.5
    e = ease(u) * 0.85 + u * 0.15
    z = z0 + (z1 - z0) * e
    return z, px0 * (1 - 2 * e), py0 * (1 - 2 * e)


def render_bg(idx, sc, u):
    z, px, py = camera(idx, u)
    frame = None
    for img, d in art_layers(sc["visual"]):
        s = 1 + (z - 1) * (0.4 + 0.6 * d)
        ox, oy = px * (0.3 + 0.7 * d), py * (0.3 + 0.7 * d)
        a = 1 / s
        c = LW / 2 - ox - (W / 2) * a
        f = LH / 2 - oy - (H / 2) * a
        t = img.transform((W, H), Image.AFFINE, (a, 0, c, 0, a, f), resample=Image.BILINEAR)
        if frame is None:
            frame = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        frame.alpha_composite(t)
    return frame


# ------------------------------------------------------------------ overlays por escena
def lt(sc):
    """inicios de frase relativos al inicio de escena"""
    return [l["start"] - sc["start"] for l in sc["lines"]]


def ov_label(fr, sc, t, dur):
    if not sc.get("label"):
        return
    a = appear(t, 0.5, 0.6) * (1 - appear(t, dur - 0.9, 0.5))
    slide = (1 - appear(t, 0.5, 0.6)) * -60
    spr = text_sprite(sc["label"].upper(), "InterDisplay-Black.otf", 64, "#ffffff", shadow=True)
    bar = panel(14, spr.height - 30, fill=hexc(PINK), radius=6)
    put(fr, bar, 110 + slide, 150, a, "lm")
    put(fr, spr, 150 + slide, 150, a, "lm")


def ov_tag(fr, sc, t, dur):
    if not sc.get("_tag"):
        return
    spr = text_sprite(sc["_tag"], "Inter-Bold.otf", 26, "#ffffff", shadow=True)
    put(fr, spr, W - 70, 66, 0.8 * appear(t, 0.2), "rm")


def ov_sunset_city(fr, sc, t, dur):
    txt = "19 · 11 · 2026"
    n = int(clamp((t - 1.0) / 1.6) * len(txt))
    a = 1 - appear(t, 7.0, 0.8)
    if n:
        put(fr, text_sprite(txt[:n], "InterDisplay-Black.otf", 130, "#ffffff", glow_r=18, glow_col=PINK), 140, 380, a, "lm")
    if t > 2.8:
        put(fr, text_sprite("00:00", "InterDisplay-Light.otf", 90, "#ffffff", glow_r=12, glow_col=TEAL), 150, 520, a * appear(t, 2.8), "lm")
    ls = lt(sc)
    if len(ls) >= 4 and t > ls[3]:
        k = appear(t, ls[3], 0.5)
        put(fr, grad_text_sprite("GTA VI", 300, "#ffe86b", PINK), W / 2, H / 2 - 40, k, scale=0.85 + 0.15 * k)


def ov_title(fr, sc, t, dur):
    k = ease_out(t / 0.8)
    put(fr, grad_text_sprite("GTA VI", 300, "#ffe86b", PINK), W / 2, H / 2 - 120, 1.0, scale=1.0 + 0.03 * t / dur)
    put(fr, text_sprite("LA HISTORIA COMPLETA", "InterDisplay-Bold.otf", 64, "#ffffff", glow_r=10, glow_col=TEAL),
        W / 2, H / 2 + 110, appear(t, 0.6, 0.8))
    items = ["LA ESPERA", "LEONIDA", "PROTAGONISTAS", "LANZAMIENTO", "CRÍTICAS", "RÉCORDS"]
    for i, it in enumerate(items):
        a = appear(t, 1.6 + i * 0.25, 0.4)
        x = W / 2 + (i - 2.5) * 270
        put(fr, text_sprite(it, "Inter-Bold.otf", 28, "#ffffff"), x, H / 2 + 220, a * 0.85)


def ov_chapter(fr, sc, t, dur):
    a = appear(t, 0.05, 0.5) * (1 - appear(t, dur - 0.5, 0.45))
    num = text_sprite(str(sc["num"]), "InterDisplay-Black.otf", 620, "#ffffff")
    put(fr, num, W / 2 + 40 * t, H / 2, 0.07 * a)
    put(fr, text_sprite(f"CAPÍTULO {sc['num']}", "Inter-Bold.otf", 42, PINK), W / 2, H / 2 - 110, a)
    k = appear(t, 0.25, 0.6)
    put(fr, grad_text_sprite(sc["title"].upper(), 130, "#ffffff", ORANGE, glow_r=18), W / 2, H / 2 + 10, a * k, scale=0.92 + 0.08 * k)
    wl = int(700 * appear(t, 0.4, 0.8))
    if wl > 2:
        put(fr, panel(wl, 6, fill=hexc(PINK), radius=3), W / 2, H / 2 + 120, a)


def ov_retro_city(fr, sc, t, dur):
    pass


def ov_leak(fr, sc, t, dur):
    ls = lt(sc)
    if len(ls) > 1 and t > ls[1]:
        k = appear(t, ls[1], 0.25)
        spr = text_sprite("FILTRADO", "InterDisplay-Black.otf", 190, RED, glow_r=8)
        spr = spr.rotate(-12, expand=True, resample=Image.BICUBIC)
        put(fr, spr, W / 2 + 120, H / 2 - 20, 0.9 * k, scale=1.6 - 0.6 * k)
        put(fr, text_sprite("90+ VIDEOS", "InterDisplay-Black.otf", 70, "#ffffff", shadow=True), W / 2 + 140, H / 2 + 150, appear(t, ls[1] + 0.5))
    if len(ls) > 0:
        put(fr, text_sprite("FEB 2022 · CONFIRMADO OFICIALMENTE", "Inter-Bold.otf", 36, TEAL, shadow=True), 150, 240,
            appear(t, ls[0] + 0.5) * (1 - appear(t, ls[1] if len(ls) > 1 else dur, 0.4)), "lm")


def ov_views(fr, sc, t, dur):
    ls = lt(sc)
    pulse = 1 + 0.03 * math.sin(t * 4)
    k = appear(t, 0.2, 0.6)
    btn = _SPR.get("play")
    if btn is None:
        btn = Image.new("RGBA", (420, 300), (0, 0, 0, 0))
        d = ImageDraw.Draw(btn)
        d.rounded_rectangle([10, 10, 410, 290], 70, fill=hexc(RED))
        d.polygon([(165, 85), (165, 215), (285, 150)], fill=(255, 255, 255, 255))
        btn = glow(btn, 30, 0.8)
        _SPR["play"] = btn
    put(fr, btn, W / 2, H / 2 - 150, k, scale=pulse * (0.8 + 0.2 * k))
    t0 = ls[1] + 1.0 if len(ls) > 1 else 2
    if t > t0 - 0.3:
        val = 90_000_000 * ease_out((t - t0) / 3.5)
        put(fr, text_sprite(fmt_int(val), "InterDisplay-Black.otf", 150, "#ffffff", glow_r=14, glow_col=RED), W / 2, H / 2 + 110, appear(t, t0 - 0.3))
        put(fr, text_sprite("VISTAS EN 24 HORAS", "Inter-Bold.otf", 44, "#ffffff"), W / 2, H / 2 + 220, appear(t, t0))
    if len(ls) > 2 and t > ls[2]:
        put(fr, text_sprite("RÉCORD · VIDEO NO MUSICAL", "Inter-Black.otf", 36, "#111111"), W / 2, 150, 0)
        b = panel(560, 70, fill=hexc(ORANGE), radius=35)
        a2 = appear(t, ls[2], 0.4) * (1 - appear(t, ls[3] if len(ls) > 3 else dur, 0.4))
        put(fr, b, W / 2, 230, a2)
        put(fr, text_sprite("RÉCORD · VIDEO NO MUSICAL", "Inter-Black.otf", 34, "#1a0b1f"), W / 2, 230, a2)


def ov_timeline(fr, sc, t, dur):
    ls = lt(sc) + [dur] * 5
    y = 560
    x0, x1 = 220, 1700
    wl = int((x1 - x0) * appear(t, 0.2, 1.2))
    if wl > 2:
        put(fr, panel(wl, 8, fill=(255, 255, 255, 120), radius=4), x0 - 20, y, 1, "lm")
    nodes = [
        (x0 + 40, "OTOÑO 2025", "fecha original", ls[0], ls[1]),
        (x0 + 520, "26 MAY 2026", "1.er retraso", ls[1], ls[3]),
        (x0 + 900, "TRÁILER 2", "~475 M vistas / 24 h", ls[2], None),
        (x1 - 60, "19 NOV 2026", "fecha definitiva", ls[3], None),
    ]
    for i, (x, title, sub, tin, tx) in enumerate(nodes):
        a = appear(t, tin, 0.5)
        if a <= 0:
            continue
        col = GREEN if i == 3 else (TEAL if i == 2 else ORANGE)
        dot = panel(36, 36, fill=hexc(col), radius=18)
        put(fr, dot, x, y, a, scale=0.6 + 0.4 * a)
        up = i % 2 == 0
        ty = y - 120 if up else y + 120
        put(fr, text_sprite(title, "InterDisplay-Black.otf", 54, "#ffffff", shadow=True), x, ty, a)
        put(fr, text_sprite(sub, "Inter-Medium.otf", 30, "#d8d0ff"), x, ty + (48 if up else 48), a)
        if tx is not None and t > tx:
            k = appear(t, tx, 0.4)
            ln = panel(int(300 * k) + 1, 8, fill=hexc(RED), radius=4)
            put(fr, ln.rotate(-8, expand=True), x, ty, 1)
            put(fr, text_sprite("RETRASADO", "Inter-Black.otf", 30, RED), x, ty - 60 if up else ty + 100, k)
        if i == 3:
            put(fr, panel(330, 120, fill=(0, 0, 0, 0), outline=GREEN, radius=20, width=4), x, ty + 20, a * (0.6 + 0.4 * math.sin(t * 3)))


MAP_PTS = [(40, 130), (400, 120), (430, 160), (600, 160), (640, 140), (700, 150), (720, 200), (760, 330), (820, 460),
           (870, 560), (900, 650), (910, 760), (880, 840), (830, 880), (780, 870), (740, 820), (700, 760), (660, 700),
           (620, 640), (600, 560), (560, 480), (540, 420), (560, 360), (520, 300), (470, 260), (400, 250), (330, 230),
           (250, 220), (150, 240), (60, 230)]
MAP_REG = [("VICE CITY", (875, 720), PINK), ("GRASSRIVERS", (760, 790), GREEN), ("LEONIDA KEYS", (700, 950), TEAL),
           ("AMBROSIA", (680, 470), ORANGE), ("PORT GELLHORN", (250, 235), "#9fb4ff"), ("MOUNT KALAGA", (560, 200), "#7ee08a")]


def map_xy(p):
    s = 0.86
    return 640 + p[0] * s, 40 + p[1] * s


def map_sprite():
    if "map" in _SPR:
        return _SPR["map"]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = [map_xy(p) for p in MAP_PTS]
    d.polygon(pts, fill=(20, 60, 90, 230))
    d.line(pts + [pts[0]], fill=hexc(TEAL), width=5, joint="curve")
    for i in range(9):  # cayos
        tt = i / 8
        x = 800 - 190 * tt
        y = 890 + 70 * math.sin(tt * 2.2)
        cx, cy = map_xy((x, y))
        d.ellipse([cx - 9 + i, cy - 6, cx + 9 - i // 2, cy + 6], fill=hexc(TEAL))
    img = glow(img, 14, 0.9)
    _SPR["map"] = img
    return img


def ov_map(fr, sc, t, dur):
    a = appear(t, 0.1, 1.0)
    put(fr, map_sprite(), 0, 0, a, "lt")
    put(fr, grad_text_sprite("LEONIDA", 140, "#ffffff", TEAL, glow_r=16, glow_col=TEAL), 330, 380, appear(t, 0.5, 0.8))
    put(fr, text_sprite("ESTADO FICTICIO · INSPIRADO EN FLORIDA", "Inter-Bold.otf", 28, "#cfe9ff"), 330, 480, appear(t, 1.0))
    for i, (name, p, col) in enumerate(MAP_REG):
        t0 = 2.5 + i * (max(dur - 5, 6) / len(MAP_REG))
        k = appear(t, t0, 0.5)
        if k <= 0:
            continue
        x, y = map_xy(p)
        put(fr, panel(26, 26, fill=hexc(col), radius=13), x, y, k, scale=0.5 + 0.5 * k + 0.08 * math.sin(t * 5 + i))
        right = x < 1300 or name == "VICE CITY"
        put(fr, text_sprite(name, "Inter-Black.otf", 32, "#ffffff", shadow=True), x + (30 if right else -30), y - 2, k, "lm" if right else "rm")


_THUMBS = None


def thumbs():
    global _THUMBS
    if _THUMBS is None:
        _THUMBS = []
        for v in ("neon_city", "keys", "highway", "swamp", "duo", "sunset_city", "port", "factory"):
            img = Image.new("RGBA", (LW, LH), (0, 0, 0, 255))
            for l, _ in art_layers(v):
                img.alpha_composite(l)
            cx = LW // 2
            crop = img.crop((cx - 360, 60, cx + 360, 60 + 1280 if 60 + 1280 <= LH else LH))
            _THUMBS.append(crop.resize((300, 520)))
    return _THUMBS


def ov_phones(fr, sc, t, dur):
    th = thumbs()
    for i in range(4):
        x = 330 + i * 420
        y0 = H / 2 - 40 + (30 if i % 2 else -30)
        a = appear(t, 0.2 + i * 0.2, 0.5)
        ph = Image.new("RGBA", (340, 600), (0, 0, 0, 0))
        ImageDraw.Draw(ph).rounded_rectangle([0, 0, 339, 599], 44, fill=(10, 10, 14, 255), outline=(80, 80, 100, 255), width=4)
        speed = 60 + i * 15
        off = (t * speed + i * 180) % 520
        k = int((t * speed + i * 180) // 520)
        scr = Image.new("RGBA", (300, 520), (0, 0, 0, 255))
        scr.paste(th[(k + i * 2) % len(th)], (0, int(-off)))
        scr.paste(th[(k + 1 + i * 2) % len(th)], (0, int(520 - off)))
        d = ImageDraw.Draw(scr)
        if i % 2 == 0:
            d.rounded_rectangle([14, 14, 96, 48], 8, fill=hexc(RED))
            d.text((55, 31), "LIVE", font=font("Inter-Black.otf", 22), fill="white", anchor="mm")
        likes = fmt_int(1000 + (t * 3457 * (i + 1)) % 900000)
        d.text((286, 470), "♥", font=font("Inter-Black.otf", 34), fill=hexc(PINK), anchor="rm") if False else None
        d.ellipse([250, 400, 286, 436], fill=hexc(PINK))
        d.text((268, 452), likes, font=font("Inter-Bold.otf", 16), fill="white", anchor="mm")
        m = Image.new("L", (300, 520), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, 299, 519], 30, fill=255)
        ph.paste(scr, (20, 40), m)
        put(fr, ph, x, y0, a)
    # corazones flotando
    rng = random.Random(5)
    for k in range(18):
        st = rng.uniform(0, 6)
        sp = rng.uniform(60, 140)
        x = rng.uniform(150, W - 150)
        ph_ = ((t + st) % 6) / 6
        y = H - 160 - ph_ * 700
        put(fr, panel(22, 22, fill=hexc(rng.choice([PINK, RED, ORANGE])), radius=11), x + math.sin(t * 2 + k) * 20, y,
            0.8 * math.sin(ph_ * math.pi))


def ov_prison(fr, sc, t, dur):
    put(fr, text_sprite("PENITENCIARÍA DE LEONIDA", "Inter-Bold.otf", 30, "#bcd8ff", shadow=True), 150, 225, appear(t, 1.0) * (1 - appear(t, dur - 0.9)), "lm")


def ov_highway(fr, sc, t, dur):
    pass


def ov_duo(fr, sc, t, dur):
    ls = lt(sc)
    if len(ls) > 3 and t > ls[3]:
        for i, wd in enumerate(["LEALTAD", "CONFIANZA", "SUPERVIVENCIA"]):
            a = appear(t, ls[3] + 2.0 + i * 0.8, 0.5)
            put(fr, text_sprite(wd, "InterDisplay-Black.otf", 72, "#ffffff", glow_r=14, glow_col=PINK), W / 2 + (i - 1) * 520, 220, a)


def card(fr, x, y, w, h, title, value, col, a, sub=None, scale=1.0):
    put(fr, panel(w, h, fill=(12, 10, 28, 215), outline=col, radius=30, width=4), x, y, a, scale=scale)
    put(fr, text_sprite(title, "Inter-Bold.otf", 34, col), x, y - h * 0.28 * scale, a, scale=scale)
    put(fr, text_sprite(value, "InterDisplay-Black.otf", 110, "#ffffff"), x, y + h * 0.05 * scale, a, scale=scale)
    if sub:
        put(fr, text_sprite(sub, "Inter-Medium.otf", 28, "#cfc8ee"), x, y + h * 0.32 * scale, a, scale=scale)


def ov_price(fr, sc, t, dur):
    ls = lt(sc) + [dur] * 3
    for i, (ti, val, col, sub) in enumerate([("EDICIÓN ESTÁNDAR", "$79.99", TEAL, "USD"), ("EDICIÓN ULTIMATE", "$99.99", ORANGE, "USD")]):
        k = appear(t, 0.6 + i * 1.4, 0.6)
        card(fr, W / 2 + (i - 0.5) * 620, 430 - (1 - k) * 40, 540, 360, ti, val, col, k, sub)
    if t > ls[1]:
        for i, (txt, col) in enumerate([("$69.99 · PRECIO HABITUAL", "#9a98b8"), ("$100 · EL RUMOR", RED)]):
            a = appear(t, ls[1] + 0.8 + i * 1.6, 0.4)
            put(fr, panel(520, 70, fill=(0, 0, 0, 160), outline=col, radius=35), W / 2 + (i - 0.5) * 620, 720, a)
            put(fr, text_sprite(txt, "Inter-Black.otf", 30, col), W / 2 + (i - 0.5) * 620, 720, a)


def ov_platforms(fr, sc, t, dur):
    ls = lt(sc) + [dur] * 4
    a0 = 1 - appear(t, ls[1] - 0.4, 0.4)
    for i, (name, col) in enumerate([("PlayStation 5", "#4f7cff"), ("Xbox Series X|S", GREEN)]):
        k = appear(t, 0.4 + i * 0.6, 0.5) * a0
        put(fr, panel(620, 220, fill=(12, 10, 28, 220), outline=col, radius=30, width=4), W / 2 + (i - 0.5) * 700, 440, k)
        put(fr, text_sprite(name, "InterDisplay-Black.otf", 72, "#ffffff"), W / 2 + (i - 0.5) * 700, 440, k)
    if ls[1] - 0.4 < t < ls[2]:
        k = appear(t, ls[1], 0.5) * (1 - appear(t, ls[2] - 0.4, 0.4))
        put(fr, panel(980, 300, fill=(12, 10, 28, 220), outline=ORANGE, radius=30, width=4), W / 2, 440, k)
        put(fr, text_sprite("CAJA FÍSICA", "Inter-Bold.otf", 36, ORANGE), W / 2, 350, k)
        put(fr, text_sprite("= CÓDIGO DE DESCARGA", "InterDisplay-Black.otf", 80, "#ffffff"), W / 2, 440, k)
        put(fr, text_sprite("el juego no viene en el disco", "Inter-Medium.otf", 32, "#cfc8ee"), W / 2, 530, k)
    if t > ls[2] - 0.2:
        k = appear(t, ls[2], 0.5)
        card(fr, W / 2 - 360, 440, 600, 330, "PRECARGA", "12 NOV", TEAL, k, "2026")
        k2 = appear(t, ls[2] + 2.5, 0.5)
        card(fr, W / 2 + 360, 440, 600, 330, "LANZAMIENTO", "19 NOV", PINK, k2, "00:00 hora local")
    if t > ls[3]:
        k = appear(t, ls[3], 0.5)
        put(fr, text_sprite("NUEVA ZELANDA  ▸▸▸  EUROPA  ▸▸▸  AMÉRICA", "Inter-Black.otf", 40, "#ffffff", shadow=True), W / 2, 720, k) if False else \
            put(fr, text_sprite("NUEVA ZELANDA  >>>  EUROPA  >>>  AMÉRICA", "Inter-Black.otf", 40, "#ffffff", shadow=True), W / 2, 720, k)


def ring_sprite(frac, col):
    size = 520
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([20, 20, size - 20, size - 20], outline=(255, 255, 255, 40), width=34)
    if frac > 0:
        d.arc([20, 20, size - 20, size - 20], -90, -90 + 360 * frac, fill=hexc(col), width=34)
    return img


def ov_score(fr, sc, t, dur):
    ls = lt(sc) + [dur] * 3
    t0 = ls[1] + 0.8
    frac = 0.99 * ease_out((t - t0) / 2.5) if t > t0 else 0
    a = appear(t, 0.3, 0.6)
    ring = ring_sprite(frac, GREEN)
    put(fr, glow(ring, 16, 0.8) if frac > 0 else ring, 640, 470, a)
    put(fr, text_sprite(str(int(round(frac * 100))), "InterDisplay-Black.otf", 210, "#ffffff"), 640, 460, a)
    put(fr, text_sprite("METASCORE · PS5", "Inter-Bold.otf", 34, GREEN), 640, 780, a)
    k = appear(t, t0 + 0.5, 0.5)
    put(fr, text_sprite("~150", "InterDisplay-Black.otf", 120, "#ffffff"), 1300, 330, k, "lm")
    put(fr, text_sprite("reseñas de prensa", "Inter-Medium.otf", 38, "#cfe9d8"), 1305, 410, k, "lm")
    put(fr, text_sprite("100 % positivas", "Inter-Bold.otf", 38, GREEN), 1305, 460, k, "lm")
    if t > ls[2]:
        k = appear(t, ls[2] + 0.5, 0.5)
        put(fr, panel(560, 190, fill=(12, 10, 28, 220), outline=ORANGE, radius=26, width=4), 1520, 640, k)
        put(fr, text_sprite("EMPATE HISTÓRICO", "Inter-Black.otf", 30, ORANGE), 1520, 585, k)
        put(fr, text_sprite("Ocarina of Time · 99", "InterDisplay-Bold.otf", 46, "#ffffff"), 1520, 645, k)
        put(fr, text_sprite("(1998, con 22 reseñas)", "Inter-Medium.otf", 28, "#cfc8ee"), 1520, 695, k)


def ov_quotes(fr, sc, t, dur):
    ls = lt(sc) + [dur] * 2
    qs = [("«Una obra maestra»", 0.5, (560, 300)), ("«Una asombrosa épica americana»", 2.4, (1260, 430)),
          ("El mundo abierto más vivo", ls[1] + 1.0, (620, 600)), ("Química: Lucía + Jason", ls[1] + 5.0, (1330, 720))]
    for i, (q, t0, (x, y)) in enumerate(qs):
        k = appear(t, t0, 0.6)
        if k <= 0:
            continue
        spr = text_sprite(q, "InterDisplay-BoldItalic.otf" if i < 2 else "InterDisplay-Black.otf", 64 if i < 2 else 54,
                          "#ffffff", glow_r=0)
        w = spr.width + 40
        put(fr, panel(w, 130, fill=(16, 8, 26, 220), outline=PINK if i < 2 else TEAL, radius=26, width=3), x, y + (1 - k) * 30, k)
        put(fr, spr, x, y + (1 - k) * 30, k)


def ov_proscons(fr, sc, t, dur):
    ls = lt(sc) + [dur] * 2
    put(fr, text_sprite("A FAVOR", "InterDisplay-Black.otf", 60, GREEN), 520, 200, appear(t, 0.2))
    put(fr, text_sprite("EN CONTRA", "InterDisplay-Black.otf", 60, RED), 1400, 200, appear(t, 0.2))
    pros = ["Mundo increíblemente detallado", "Historia íntima y humana", "Química de los protagonistas"]
    cons = [("Misiones muy guiadas", 1.5), ("Problemas de ritmo", 4.0), ("Controles pesados", 6.0), ("30 FPS en consola", ls[1] + 3.0)]
    for i, p in enumerate(pros):
        a = appear(t, 0.6 + i * 0.4, 0.4)
        put(fr, text_sprite("+  " + p, "Inter-Bold.otf", 40, "#e6ffef"), 260, 320 + i * 95, a, "lm")
    for i, (c, t0) in enumerate(cons):
        a = appear(t, t0, 0.4)
        big = i == 3
        spr = text_sprite("–  " + c, "Inter-Black.otf" if big else "Inter-Bold.otf", 52 if big else 40, "#ffffff" if big else "#ffe6e6")
        if big and a > 0:
            put(fr, panel(spr.width + 20, 90, fill=(120, 10, 20, 200), outline=RED, radius=20), 1110, 320 + i * 95, a, "lm")
        put(fr, spr, 1130, 320 + i * 95, a, "lm")


def ov_money(fr, sc, t, dur):
    ls = lt(sc) + [dur] * 2
    t0 = ls[1] + 2.0
    v = 3_790_000_000 * ease_out((t - t0) / 4.0) if t > t0 else 0
    a = appear(t, 0.3, 0.6)
    put(fr, text_sprite("$" + fmt_int(v), "InterDisplay-Black.otf", 170, "#ffffff", glow_r=20, glow_col=GREEN), W / 2, H / 2 - 40, a)
    put(fr, text_sprite("PRIMERAS 24 HORAS", "Inter-Black.otf", 48, GREEN), W / 2, H / 2 + 100, a)
    put(fr, text_sprite("estimación de Take-Two · ventas mundiales", "Inter-Medium.otf", 32, "#cfe9d8"), W / 2, H / 2 + 160, appear(t, t0 + 3))


def ov_bars(fr, sc, t, dur):
    ls = lt(sc) + [dur] * 4
    base = 730
    maxh = 470
    items = [("GTA V · 2013", 0.8159, "#7a7f9a", 0.6, "$816 M"), ("GTA VI · 2026", 3.79, PINK, ls[1], "$3.790 M")]
    for i, (name, val, col, t0, lab) in enumerate(items):
        x = 600 + i * 440
        k = ease_out((t - t0) / 1.4) if t > t0 else 0
        h = max(2, int(maxh * val / 3.79 * k))
        put(fr, panel(220, h, fill=hexc(col), radius=14), x, base, appear(t, t0 - 0.3) if t0 > 0.6 else appear(t, 0.3), "mb")
        put(fr, text_sprite(name, "Inter-Black.otf", 36, "#ffffff"), x, base + 50, appear(t, 0.3))
        if k > 0.05:
            put(fr, text_sprite(lab, "InterDisplay-Black.otf", 54, "#ffffff", shadow=True), x, base - h - 50, k)
    put(fr, text_sprite("VENTAS EL DÍA DEL ESTRENO (USD)", "Inter-Bold.otf", 34, "#d8d0ff"), 820, 170, appear(t, 0.3))
    if t > ls[1] + 1.5:
        k = appear(t, ls[1] + 1.5, 0.4)
        put(fr, text_sprite("×4,7", "InterDisplay-Black.otf", 120, ORANGE, glow_r=14, glow_col=ORANGE), 1500, 400, k, scale=1.4 - 0.4 * k)
    if t > ls[2]:
        k = appear(t, ls[2], 0.5)
        put(fr, panel(560, 120, fill=(0, 0, 0, 170), outline=ORANGE, radius=20), 1500, 640, k)
        put(fr, text_sprite("Cifras de la propia empresa", "Inter-Bold.otf", 30, "#ffffff"), 1500, 618, k)
        put(fr, text_sprite("Sensor Tower estima menos", "Inter-Medium.otf", 28, ORANGE), 1500, 662, k)


def ov_pc(fr, sc, t, dur):
    ls = lt(sc) + [dur] * 2
    if t > ls[1]:
        k = appear(t, ls[1] + 2.0, 0.5)
        put(fr, panel(520, 90, fill=(0, 0, 0, 180), outline=TEAL, radius=45), W / 2, 960 - 140, k)
        put(fr, text_sprite("REPORTES: 1.er TRIMESTRE 2027", "Inter-Black.otf", 30, TEAL), W / 2, 960 - 140, k)


def ov_online(fr, sc, t, dur):
    ls = lt(sc) + [dur] * 3
    if t > ls[1]:
        k = appear(t, ls[1] + 0.5, 0.5)
        put(fr, panel(600, 100, fill=(0, 0, 0, 180), outline=PINK, radius=50), W / 2, 820, k)
        put(fr, text_sprite("¿FINALES DE 2027? · BLOOMBERG", "Inter-Black.otf", 32, "#ffffff"), W / 2, 820, k)


def ov_outro(fr, sc, t, dur):
    ls = lt(sc) + [dur] * 4
    if t > ls[2]:
        k = appear(t, ls[2], 0.8)
        put(fr, grad_text_sprite("GTA VI", 260, "#ffe86b", PINK), W / 2, H / 2 - 130, k, scale=0.9 + 0.1 * k)
    if t > dur - 6.5:
        k = appear(t, dur - 6.5, 0.8)
        put(fr, text_sprite("GRACIAS POR VER", "InterDisplay-Black.otf", 70, "#ffffff", glow_r=12, glow_col=TEAL), W / 2, H / 2 + 60, k)
        put(fr, text_sprite("Video informativo hecho por fans · sin afiliación con Rockstar Games ni Take-Two Interactive.",
                            "Inter-Medium.otf", 26, "#e8e0ff", shadow=True), W / 2, H - 120, k)
        put(fr, text_sprite("Ilustraciones originales generadas por computadora · Voz sintética · Fuentes: CBS News, Al Jazeera, Variety, Rolling Stone, CBC, TechRadar, Vice.",
                            "Inter-Medium.otf", 22, "#cfc8ee", shadow=True), W / 2, H - 80, k)


OVERLAYS = {k[3:]: v for k, v in globals().items() if k.startswith("ov_") and k not in ("ov_label", "ov_tag")}
_VIG = None


def scene_frame(idx, tt):
    sc = SCENES[idx]
    dur = sc["end"] - sc["start"]
    tl = tt - sc["start"]
    fr = render_bg(idx, sc, clamp(tl / max(dur, 0.1)))
    if sc["visual"] in ("chapter",):
        pass
    ov = OVERLAYS.get(sc["visual"])
    if ov:
        ov(fr, sc, tl, dur)
    ov_label(fr, sc, tl, dur)
    ov_tag(fr, sc, tl, dur)
    return fr


def frame_at(tt):
    global _VIG
    if _VIG is None:
        _VIG = arte.vignette_mask()
    # escena actual y transicion
    idx = 0
    for i, sc in enumerate(SCENES):
        if sc["start"] <= tt:
            idx = i
    fr = scene_frame(idx, tt)
    sc = SCENES[idx]
    if idx > 0 and tt - sc["start"] < XFADE / 2:
        # mezcla con la escena anterior (cruce centrado en el corte)
        a = 0.5 + (tt - sc["start"]) / XFADE
        prev = scene_frame(idx - 1, tt)
        fr = Image.blend(prev, fr, a)
    elif idx < len(SCENES) - 1 and SCENES[idx + 1]["start"] - tt < XFADE / 2:
        a = 0.5 - (SCENES[idx + 1]["start"] - tt) / XFADE
        nxt = scene_frame(idx + 1, tt)
        fr = Image.blend(fr, nxt, a)
    fr.alpha_composite(_VIG)
    # subtitulos
    for s in SUBS:
        if s["start"] - 0.05 <= tt <= s["end"] + 0.25:
            spr = sub_sprite(s["text"])
            a = min(appear(tt, s["start"] - 0.05, 0.15), 1 - appear(tt, s["end"] + 0.1, 0.15))
            put(fr, spr, W / 2, H - 70, a, "mb")
            break
    # fundido de entrada y salida
    fade = min(clamp(tt / 1.0), clamp((DURATION - tt) / 2.0))
    out = fr.convert("RGB")
    if fade < 1:
        out = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), out, fade)
    return out


def render_chunk(args):
    ci, f0, f1 = args
    path = os.path.join(BUILD, "chunks", f"c{ci:03d}.mp4")
    if os.path.exists(path + ".done"):
        return path
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-tune", "animation", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        p.stdin.write(frame_at(fi / FPS).tobytes())
    p.stdin.close()
    p.wait()
    open(path + ".done", "w").close()
    print(f"tramo {ci} listo ({f0}-{f1})", flush=True)
    return path


def main():
    if "--preview" in sys.argv:
        os.makedirs(os.path.join(BUILD, "preview"), exist_ok=True)
        for a in sys.argv[sys.argv.index("--preview") + 1:]:
            frame_at(float(a)).save(os.path.join(BUILD, "preview", f"f_{float(a):07.2f}.jpg"), quality=88)
        return
    os.makedirs(os.path.join(BUILD, "chunks"), exist_ok=True)
    total = int(math.ceil(DURATION * FPS))
    step = 600
    jobs = [(i, f0, min(total, f0 + step)) for i, f0 in enumerate(range(0, total, step))]
    procs = int(os.environ.get("PROCS", os.cpu_count() or 4))
    with Pool(procs) as pool:
        paths = pool.map(render_chunk, jobs, chunksize=1)
    with open(os.path.join(BUILD, "chunks", "list.txt"), "w") as f:
        for p in paths:
            f.write(f"file '{os.path.basename(p)}'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i",
                    os.path.join(BUILD, "chunks", "list.txt"), "-c", "copy", os.path.join(BUILD, "video_mudo.mp4")], check=True)
    print("video_mudo.mp4 listo")


if __name__ == "__main__":
    main()
