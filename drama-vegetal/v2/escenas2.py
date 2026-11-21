# -*- coding: utf-8 -*-
"""DRAMA VEGETAL Ep. 1 — VERSION 2 (45 s, aspecto realista).

Compone los recursos 3D de Blender (personajes, ojos, habitacion, telefono)
y anima encima: camara, mirada, parpados, cejas, boca sincronizada con la voz,
temblor, lagrimas. Acabado: desenfoque de profundidad, resplandor (bloom),
grano de pelicula, vineta y gradacion de color. 1080x1920, 30 fps.
"""
import json, math, os, random, subprocess, sys
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
AS = os.path.join(BUILD, "assets")
W, H, FPS, DUR = 1080, 1920, 30, 45.0
FD = "/usr/share/fonts/opentype/inter/"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
VOCES = json.load(open(os.path.join(BUILD, "voces.json"), encoding="utf-8"))
ANC = json.load(open(os.path.join(AS, "anchors.json")))


# ------------------------------------------------------------------ utilidades
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease(x):
    x = clamp(x); return x * x * (3 - 2 * x)


def eout(x):
    x = clamp(x); return 1 - (1 - x) ** 3


def back(x):
    x = clamp(x); c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def F(name, size):
    return ImageFont.truetype(FD + name, size)


def put(fr, spr, x, y, a=1.0, anchor="mm", scale=1.0):
    if a <= 0.004 or spr is None:
        return
    if scale != 1.0:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BILINEAR)
    if a < 0.999:
        arr = np.asarray(spr).copy(); arr[..., 3] = (arr[..., 3] * a).astype(np.uint8); spr = Image.fromarray(arr)
    w, h = spr.size
    x = int(round(x - {"l": 0, "m": w / 2, "r": w}[anchor[0]]))
    y = int(round(y - {"t": 0, "m": h / 2, "b": h}[anchor[1]]))
    sx, sy = max(0, -x), max(0, -y)
    if sx or sy:
        if sx >= w or sy >= h:
            return
        spr = spr.crop((sx, sy, w, h)); x += sx; y += sy
    if x < fr.width and y < fr.height:
        fr.alpha_composite(spr, (x, y))


_C = {}


def text(t, size, fill=(255, 255, 255), font="Inter-Black.otf", stroke=0, sfill=(0, 0, 0), shadow=True):
    k = (t, size, fill, font, stroke, sfill, shadow)
    if k in _C:
        return _C[k]
    f = F(font, size)
    l, tp, r, b = f.getbbox(t, stroke_width=stroke)
    pad = 26
    img = Image.new("RGBA", (r - l + pad * 2, b - tp + pad * 2), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - l + 4, pad - tp + 8), t, font=f, fill=(0, 0, 0, 170), stroke_width=stroke)
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(7)))
    ImageDraw.Draw(img).text((pad - l, pad - tp), t, font=f, fill=fill + (255,), stroke_width=stroke, stroke_fill=sfill + (255,))
    _C[k] = img
    return img


def emoji(ch, size):
    k = ("emoji", ch, size)
    if k not in _C:
        f = ImageFont.truetype(EMOJI, 109)
        img = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((80, 80), ch, font=f, embedded_color=True, anchor="mm")
        img = img.crop(img.getbbox())
        _C[k] = img.resize((max(1, int(img.width * size / 109)), max(1, int(img.height * size / 109))), Image.LANCZOS)
    return _C[k]


def rrect(w, h, r, fill):
    k = ("rr", w, h, r, fill)
    if k not in _C:
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(img).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=fill)
        _C[k] = img
    return _C[k]


def glow_spr(w, h, col, a):
    k = ("glow", w, h, col, a)
    if k not in _C:
        g = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse([w * 0.15, h * 0.15, w * 0.85, h * 0.85], fill=col + (a,))
        _C[k] = g.filter(ImageFilter.GaussianBlur(min(w, h) * 0.12))
    return _C[k]


@lru_cache(maxsize=32)
def load(name):
    img = Image.open(os.path.join(AS, name + ".png")).convert("RGBA")
    if name.startswith("ber_"):
        # atenua el reflejo calido de la luz de relleno (se veia como un parche junto a la boca)
        a = np.asarray(img).astype(np.float32)
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        warm = np.clip((r - b - 8) / 40, 0, 1) * (r > 90)
        warm = np.asarray(Image.fromarray((warm * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))).astype(np.float32) / 255
        tgt = np.stack([r * 0.32 + 10, g * 0.25, b * 0.45 + 25], -1)
        a[..., :3] = a[..., :3] * (1 - warm[..., None]) + tgt * warm[..., None]
        img = Image.fromarray(a.clip(0, 255).astype(np.uint8))
    return img


@lru_cache(maxsize=16)
def plate(name, blur=0):
    img = load(name)
    # limpieza de ruido del render (suavizado ligero que conserva bordes)
    img = img.filter(ImageFilter.MedianFilter(3))
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    return img


def camera(img, z, fx=0.5, fy=0.5, dx=0.0, dy=0.0):
    BW, BH = img.size
    s = z * max(W / BW, H / BH)
    a = 1 / s
    c = clamp(fx * BW + dx - (W / 2) * a, 0, BW - W * a)
    f = clamp(fy * BH + dy - (H / 2) * a, 0, BH - H * a)
    return img.transform((W, H), Image.AFFINE, (a, 0, c, 0, a, f), resample=Image.BICUBIC)


def plate_xy(name, pt, z, fx, fy, dx=0, dy=0):
    """Convierte coordenadas de la placa a coordenadas del cuadro con la camara dada."""
    BW, BH = load(name).size
    s = z * max(W / BW, H / BH)
    a = 1 / s
    c = clamp(fx * BW + dx - (W / 2) * a, 0, BW - W * a)
    f = clamp(fy * BH + dy - (H / 2) * a, 0, BH - H * a)
    return (pt[0] - c) / a, (pt[1] - f) / a, s


# ------------------------------------------------------------------ personajes
EYE_PREFIX = {"berenjena": "eye_ber", "tomate": "eye_tom", "pepino": "eye_pep"}
SKIN_DARK = {"berenjena": (14, 3, 22), "tomate": (70, 4, 4), "pepino": (6, 22, 8)}


def body_color(name, pt, r):
    """Color medio de la piel justo debajo del ojo (para los parpados)."""
    k = ("skin", name, int(pt[0]), int(pt[1]))
    if k not in _C:
        img = load(name)
        x, y = int(pt[0]), int(pt[1] + r * 1.6)
        box = img.crop((x - int(r * 0.6), y - int(r * 0.3), x + int(r * 0.6), y + int(r * 0.3))).convert("RGB")
        _C[k] = tuple(int(v) for v in np.asarray(box).reshape(-1, 3).mean(0))
    return _C[k]


def character(kind, name, h, e):
    """Sprite del personaje con cara animada. e: dict de expresion."""
    ex = dict(open=1.0, px=0.0, py=0.0, brow=0.0, brow_up=0.0, mouth="neutral", mo=0.0, tears=0.0, sweat=0.0, lid=0.0, big=1.0, glow_eyes=0.0)
    ex.update(e)
    key = (name, h, tuple(sorted((k, round(v, 2) if isinstance(v, float) else v) for k, v in ex.items())))
    if key in _C:
        return _C[key]
    base = load(name)
    A = ANC[name]
    s = h / base.height
    SS = 1.0
    img = base.resize((int(base.width * s), int(base.height * s)), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    er = A["eye_rad"] * s * 1.25 * ex["big"]
    gx = int(round(clamp(ex["px"], -1, 1) * 2))
    gy = int(round(clamp(ex["py"], -1, 1)))
    eye_img = load(f"{EYE_PREFIX[kind]}_{gx}_{gy}")
    skin = body_color(name, A["eye_l"], A["eye_rad"])
    for side in ("eye_l", "eye_r"):
        cx, cy = A[side][0] * s, A[side][1] * s
        if ex["open"] <= 0.06:   # ojo cerrado: linea curva con pestanas
            cl = Image.new("RGBA", img.size, (0, 0, 0, 0))
            cd = ImageDraw.Draw(cl)
            cd.arc([cx - er * 0.9, cy - er * 0.5, cx + er * 0.9, cy + er * 0.6], 15, 165, fill=SKIN_DARK[kind] + (255,), width=max(3, int(er * 0.16)))
            if kind == "tomate":
                for k2 in range(3):
                    a2 = math.radians(50 + k2 * 40)
                    x0, y0 = cx + math.cos(a2) * er * 0.9, cy + math.sin(a2) * er * 0.55
                    cd.line([(x0, y0), (x0 + math.cos(a2) * er * 0.35, y0 + math.sin(a2) * er * 0.35)], fill=SKIN_DARK[kind] + (255,), width=max(2, int(er * 0.1)))
            img.alpha_composite(cl.filter(ImageFilter.GaussianBlur(1.0)))
            continue
        # sombra de contacto (incrusta el ojo en la piel)
        sh = Image.new("RGBA", (int(er * 3), int(er * 3)), (0, 0, 0, 0))
        ImageDraw.Draw(sh).ellipse([er * 0.4, er * 0.5, er * 2.6, er * 2.7], fill=(0, 0, 0, 100))
        put(img, sh.filter(ImageFilter.GaussianBlur(er * 0.18)), cx, cy + er * 0.08)
        es = eye_img.resize((int(er * 2 * 1.12), int(er * 2 * 1.12)), Image.LANCZOS)
        op = ex["open"]
        if op < 0.999 or ex["lid"] > 0:
            # parpado superior: tapa una fraccion del ojo
            cover = max(1 - op, ex["lid"] * 0.55)
            m = Image.new("L", es.size, 0)
            md = ImageDraw.Draw(m)
            yb = es.height * (0.06 + 0.9 * cover)
            md.rectangle([0, yb, es.width, es.height], fill=255)
            if op <= 0.06:
                md.rectangle([0, 0, es.width, es.height], fill=0)
            es2 = Image.new("RGBA", es.size, (0, 0, 0, 0))
            es2.paste(es, (0, 0), ImageChops.multiply(m, es.getchannel("A")))
            lid = Image.new("RGBA", es.size, (0, 0, 0, 0))
            ld = ImageDraw.Draw(lid)
            ld.ellipse([0, 0, es.width - 1, es.height - 1], fill=skin + (255,))
            lm = Image.new("L", es.size, 0)
            ImageDraw.Draw(lm).rectangle([0, 0, es.width, yb], fill=255)
            lid.putalpha(ImageChops.multiply(lid.getchannel("A"), lm))
            # sombreado del parpado
            grad = Image.new("RGBA", es.size, (0, 0, 0, 0))
            gd = ImageDraw.Draw(grad)
            for i in range(10):
                gd.ellipse([es.width * (0.1 + i * 0.02), es.height * (0.02 + i * 0.01), es.width * (0.9 - i * 0.02), es.height * 0.6],
                           fill=(255, 255, 255, 6))
            lid.alpha_composite(Image.composite(grad, Image.new("RGBA", es.size, (0, 0, 0, 0)), lid.getchannel("A")))
            ImageDraw.Draw(lid).line([(es.width * 0.08, yb), (es.width * 0.92, yb)], fill=(10, 5, 10, 255), width=max(2, int(er * 0.1)))
            es2.alpha_composite(lid)
            es = es2
        put(img, es, cx, cy)
        if ex["glow_eyes"] > 0:
            put(img, glow_spr(int(er * 4), int(er * 4), (255, 220, 90), int(160 * ex["glow_eyes"])), cx, cy)
    # cejas
    bw = max(3, int(er * (0.18 if kind == "tomate" else 0.32)))
    for side, sgn in (("eye_l", -1), ("eye_r", 1)):
        cx, cy = A[side][0] * s, A[side][1] * s
        by = cy - er * 1.28 - ex["brow_up"] * er * 0.45
        inner = [cx - sgn * er * 0.85, by]
        outer = [cx + sgn * er * 1.05, by]
        if ex["brow"] < 0:      # enfado: interior abajo
            inner[1] += er * 0.6 * -ex["brow"]; outer[1] -= er * 0.2 * -ex["brow"]
        elif ex["brow"] > 0:    # tristeza: interior arriba
            inner[1] -= er * 0.45 * ex["brow"]; outer[1] += er * 0.3 * ex["brow"]
        br = Image.new("RGBA", img.size, (0, 0, 0, 0))
        bd = ImageDraw.Draw(br)
        mid = ((inner[0] + outer[0]) / 2, min(inner[1], outer[1]) - er * 0.12)
        pts = [tuple(inner), mid, tuple(outer)]
        bd.line(pts, fill=SKIN_DARK[kind] + (255,), width=bw, joint="curve")
        for p, r in ((inner, bw * 0.55), (outer, bw * 0.35)):
            bd.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=SKIN_DARK[kind] + (255,))
        img.alpha_composite(br.filter(ImageFilter.GaussianBlur(1.2)))
    # boca
    mx, my = A["mouth"][0] * s, A["mouth"][1] * s
    mw = er * 1.05
    mo = ex["mo"]
    mlayer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    md = ImageDraw.Draw(mlayer)
    if ex["mouth"] == "o" and mo < 0.3:
        mo = 0.45
    if mo > 0.06:
        ow = mw * (0.55 if ex["mouth"] == "o" else 0.95)
        oh = mw * (0.25 + 0.75 * mo)
        md.ellipse([mx - ow, my - oh * 0.35, mx + ow, my + oh * 0.65], fill=(30, 4, 10, 255))
        md.ellipse([mx - ow * 0.75, my - oh * 0.2, mx + ow * 0.75, my + oh * 0.3], fill=(12, 1, 4, 255))
        md.ellipse([mx - ow * 0.55, my + oh * 0.25, mx + ow * 0.55, my + oh * 0.62], fill=(150, 50, 60, 255))
        md.arc([mx - ow, my - oh * 0.35, mx + ow, my + oh * 0.65], 200, 340, fill=(255, 255, 255, 50), width=max(2, int(mw * 0.06)))
    else:
        wdt = max(3, int(mw * 0.13))
        col = SKIN_DARK[kind] + (255,)
        if ex["mouth"] == "smile":
            md.arc([mx - mw * 0.8, my - mw * 0.5, mx + mw * 0.8, my + mw * 0.35], 20, 160, fill=col, width=wdt)
        elif ex["mouth"] == "smirk":
            md.arc([mx - mw * 0.5, my - mw * 0.45, mx + mw * 0.95, my + mw * 0.3], 25, 125, fill=col, width=wdt)
        elif ex["mouth"] == "frown":
            md.arc([mx - mw * 0.75, my, mx + mw * 0.75, my + mw * 0.75], 205, 335, fill=col, width=wdt)
        elif ex["mouth"] == "wobbly":
            md.line([(mx - mw * 0.75 + i * mw * 0.125, my + math.sin(i * 1.9) * mw * 0.08) for i in range(13)], fill=col, width=wdt, joint="curve")
        else:
            md.line([(mx - mw * 0.55, my), (mx + mw * 0.55, my)], fill=col, width=wdt)
    img.alpha_composite(mlayer.filter(ImageFilter.GaussianBlur(1.0)))
    # lagrimas (gotas brillantes)
    if ex["tears"] > 0:
        tl = Image.new("RGBA", img.size, (0, 0, 0, 0))
        td = ImageDraw.Draw(tl)
        for side, sgn in (("eye_l", -1), ("eye_r", 1)):
            cx, cy = A[side][0] * s + sgn * er * 0.45, A[side][1] * s + er * 0.9
            L = er * 3.4 * ex["tears"]
            td.line([(cx, cy), (cx + sgn * er * 0.15, cy + L)], fill=(170, 210, 255, 120), width=int(er * 0.3))
            td.line([(cx - er * 0.05, cy), (cx + sgn * er * 0.15 - er * 0.05, cy + L)], fill=(255, 255, 255, 170), width=max(2, int(er * 0.08)))
            td.ellipse([cx - er * 0.2, cy + L - er * 0.1, cx + er * 0.3, cy + L + er * 0.4], fill=(190, 225, 255, 200))
            td.ellipse([cx - er * 0.05, cy + L, cx + er * 0.08, cy + L + er * 0.12], fill=(255, 255, 255, 255))
        img.alpha_composite(tl.filter(ImageFilter.GaussianBlur(0.8)))
    if ex["sweat"] > 0:
        cx, cy = A["eye_r"][0] * s + er * 2.0, A["eye_r"][1] * s - er * 1.6
        sd = Image.new("RGBA", img.size, (0, 0, 0, 0))
        dd = ImageDraw.Draw(sd)
        dd.polygon([(cx, cy - er * 0.8), (cx - er * 0.38, cy + er * 0.1), (cx + er * 0.38, cy + er * 0.1)], fill=(180, 220, 255, 200))
        dd.ellipse([cx - er * 0.38, cy - er * 0.2, cx + er * 0.38, cy + er * 0.5], fill=(180, 220, 255, 200))
        dd.ellipse([cx - er * 0.15, cy - er * 0.05, cx + er * 0.0, cy + er * 0.15], fill=(255, 255, 255, 255))
        img.alpha_composite(sd.filter(ImageFilter.GaussianBlur(0.8)))
    if len(_C) > 2500:
        _C.clear()
    _C[key] = img
    return img


def contact_shadow(w):
    k = ("csh", w)
    if k not in _C:
        h = int(w * 0.16)
        s = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(s).ellipse([0, 0, w - 1, h - 1], fill=(0, 0, 0, 170))
        _C[k] = s.filter(ImageFilter.GaussianBlur(h * 0.25))
    return _C[k]


def mouth_env(vid, t):
    v = VOCES.get(vid)
    if not v or not (v["start"] <= t <= v["end"]):
        return 0.0
    i = int((t - v["start"]) * 30)
    env = v.get("env", [])
    return round((env[i] if i < len(env) else 0.0) * 4) / 4


def blink(t, period=3.7, phase=0.0):
    x = (t + phase) % period
    return 0.0 if x < 0.12 else 1.0


# ------------------------------------------------------------------ telefono
def bubble(txt, maxw=640, incoming=True, size=50, hl=None):
    k = ("bub", txt, incoming, size, hl)
    if k in _C:
        return _C[k]
    f = F("Inter-SemiBold.otf", size)
    words, lines, cur = txt.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if f.getlength(test) > maxw - 60 and cur:
            lines.append(cur); cur = w
        else:
            cur = test
    lines.append(cur)
    lh = int(size * 1.3)
    bw = int(max(f.getlength(l) for l in lines)) + 60
    bh = lh * len(lines) + 40
    img = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, bw - 1, bh - 1], 34, fill=(44, 44, 54, 255) if incoming else (40, 110, 255, 255))
    y = 20
    for l in lines:
        x = 30
        for w in l.split():
            col = (255, 214, 60, 255) if hl and any(h in w.lower() for h in hl) else (255, 255, 255, 255)
            d.text((x, y), w, font=f, fill=col)
            x += f.getlength(w + " ")
        y += lh
    _C[k] = img
    return img


def photo_card():
    k = "photo"
    if k in _C:
        return _C[k]
    pw, ph = 560, 640
    y = np.linspace(0, 1, ph)[:, None, None]
    top, mid, sea = np.array([255, 150, 90]), np.array([255, 95, 120]), np.array([30, 90, 150])
    arr = np.where(y < 0.58, top + (mid - top) * (y / 0.58), mid * 0 + sea * (1 - (y - 0.58)))
    pic = Image.fromarray(np.broadcast_to(arr, (ph, pw, 3)).clip(0, 255).astype(np.uint8)).convert("RGBA")
    ImageDraw.Draw(pic).ellipse([pw / 2 - 80, 250, pw / 2 + 80, 410], fill=(255, 225, 150, 255))
    pep = character("pepino", "pep_sunset", 600, dict(mouth="smirk", lid=0.4, px=-0.5))
    tom = character("tomate", "tom_sunset", 300, dict(mouth="smile", px=0.6))
    pic.alpha_composite(pep, (int(pw * 0.42), ph - pep.height + 40))
    pic.alpha_composite(tom, (int(pw * -0.02), ph - tom.height + 20))
    put(pic, emoji("❤️", 90), pw // 2, 110)
    card = Image.new("RGBA", (pw + 30, ph + 30), (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle([0, 0, pw + 29, ph + 29], 30, fill=(44, 44, 54, 255))
    m = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, pw - 1, ph - 1], 24, fill=255)
    card.paste(pic, (15, 15), m)
    _C[k] = card
    return card


SCR_W, SCR_H = 720, 1480


def screen_ui(t, mode):
    scr = Image.new("RGBA", (SCR_W, SCR_H), (10, 10, 14, 255))
    d = ImageDraw.Draw(scr)
    if mode == "unlock" and t < 0.9:
        y = np.linspace(0, 1, SCR_H)[:, None, None]
        arr = np.array([60, 30, 110]) * (1 - y) + np.array([10, 20, 50]) * y
        scr = Image.fromarray(np.broadcast_to(arr, (SCR_H, SCR_W, 3)).astype(np.uint8)).convert("RGBA")
        put(scr, text("03:14", 170, font="InterDisplay-Bold.otf"), SCR_W / 2, 330)
        put(scr, text("martes, 21 de noviembre", 36, font="Inter-Medium.otf"), SCR_W / 2, 440)
        put(scr, emoji("🔒" if t < 0.5 else "🔓", 90), SCR_W / 2, 140, 1 - clamp((t - 0.55) / 0.3))
        return scr
    msg1 = bubble("No puedo seguir ocultándote lo de la berenjena…", hl=("berenjena",))
    if mode == "unlock":
        tt = t - 0.9
        put(scr, msg1, 30, 260, clamp(tt / 0.15), "lt", scale=0.6 + 0.4 * back(tt / 0.35))
    elif mode == "photo":
        scroll = eout((t - 0.2) / 0.6) * 160
        put(scr, msg1, 30, 260 - scroll, 1, "lt")
        y = 260 - scroll + msg1.height + 30
        if t > 0.5:
            m2 = bubble("¿Ya se lo dijiste?", size=48)
            put(scr, m2, 30, y, clamp((t - 0.5) / 0.15), "lt", scale=0.7 + 0.3 * back((t - 0.5) / 0.3))
            y += m2.height + 26
        if t > 1.2:
            m3 = bubble("Todavía no… tengo miedo 😔", size=48, incoming=False)
            put(scr, m3, SCR_W - 30, y, clamp((t - 1.2) / 0.15), "rt", scale=0.7 + 0.3 * back((t - 1.2) / 0.3))
            y += m3.height + 26
        if t > 2.0:
            sc2 = eout((t - 2.0) / 0.4) * 380
            put(scr, photo_card(), 30, y - sc2 * 0.0 + 0, clamp((t - 2.0) / 0.15), "lt", scale=(0.7 + 0.3 * back((t - 2.0) / 0.4)) * 0.92)
    elif mode == "reveal":
        put(scr, photo_card(), 30, -200, 0.5, "lt", scale=0.8)
        if 0.3 < t < 1.2:
            put(scr, rrect(170, 80, 40, (44, 44, 54, 255)), 30, 740, 1, "lt")
            for i in range(3):
                put(scr, rrect(20, 20, 10, (200, 200, 210, 255)), 75 + i * 40, 780 + math.sin(t * 14 + i) * 8)
        if t >= 1.2:
            m = bubble("Él todavía no sabe que el pepino es su verdadero hermano…", size=60, maxw=680, hl=("verdadero", "hermano"))
            put(scr, m, 30, 680, clamp((t - 1.2) / 0.15), "lt", scale=0.6 + 0.4 * back((t - 1.2) / 0.35))
    elif mode == "last":
        put(scr, bubble("Él todavía no sabe que el pepino es su verdadero hermano…", size=60, maxw=680, hl=("verdadero", "hermano")), 30, 200, 0.6, "lt")
        if t > 0.4:
            m = bubble("Sé que estás leyendo esto… hermano.", size=64, maxw=680, hl=("hermano.",))
            put(scr, m, 30, 760, clamp((t - 0.4) / 0.15), "lt", scale=0.6 + 0.4 * back((t - 0.4) / 0.35))
    # cabecera
    d = ImageDraw.Draw(scr)
    d.rectangle([0, 0, SCR_W, 190], fill=(22, 22, 28, 255))
    d.ellipse([34, 70, 134, 170], fill=(80, 80, 95, 255))
    put(scr, text("?", 60, font="InterDisplay-Black.otf", shadow=False), 84, 120)
    put(scr, text("Número oculto", 42, font="Inter-Bold.otf", shadow=False), 160, 100, anchor="lm")
    put(scr, text("en línea", 30, (120, 220, 140), font="Inter-Medium.otf", shadow=False), 160, 148, anchor="lm")
    return scr


def persp_coeffs(src, dst):
    """Coeficientes para Image.transform PERSPECTIVE: mapean dst (salida) -> src (entrada)."""
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()


def shot_phone(t, mode, shake=0.0, z0=1.0, z1=1.06, dur=3.0):
    z = z0 + (z1 - z0) * ease(t / dur)
    sx = random.Random(int(t * 40)).uniform(-shake, shake) if shake else 0
    sy = random.Random(int(t * 40) + 3).uniform(-shake, shake) if shake else 0
    fr = camera(plate("phone_plate"), z, 0.5, 0.5, sx, sy)
    corners = [plate_xy("phone_plate", c, z, 0.5, 0.5, sx, sy)[:2] for c in ANC["phone"]]
    ui = screen_ui(t, mode)
    src = [(0, 0), (SCR_W, 0), (SCR_W, SCR_H), (0, SCR_H)]
    co = persp_coeffs(src, corners)
    warped = ui.transform((W, H), Image.PERSPECTIVE, co, resample=Image.BICUBIC)
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon([tuple(c) for c in corners], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(1.2))
    fr.paste(warped, (0, 0), m)
    # reflejo del cristal y luz que derrama la pantalla
    refl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(refl).polygon([corners[0], ((corners[0][0] + corners[1][0]) / 2, corners[0][1]), corners[3]], fill=(255, 255, 255, 14))
    fr.alpha_composite(refl)
    return fr


# ------------------------------------------------------------------ subtitulos y marca
def sub_y(t):
    if t < 9.6 or 18.6 <= t < 24.2:
        return 720
    if 24.2 <= t < 29.0:
        return 1100
    if 34.2 <= t < 39.6:
        return 1130
    if 41.2 <= t < 42.6:
        return 1450
    return 1560


SUB_COL = {"narrador": (255, 226, 50), "berenjena": (205, 150, 255), "pepino": (140, 240, 120)}


def subtitle(fr, t):
    for vid, v in VOCES.items():
        if v["start"] - 0.05 <= t <= v["end"] + 0.35:
            words = v["text"].split()
            total = sum(len(w) for w in words)
            dur = v["end"] - v["start"]
            acc, times = 0, []
            for w in words:
                times.append(v["start"] + dur * acc / total); acc += len(w)
            cur = max(0, sum(1 for x in times if x <= t) - 1)
            blk = cur // 3
            chunk = words[blk * 3: blk * 3 + 3]
            size = 90 if v["who"] != "narrador" else 80
            sprs = [text(w.upper(), size, SUB_COL[v["who"]] if blk * 3 + i == cur else (255, 255, 255), stroke=9)
                    for i, w in enumerate(chunk)]
            tw = sum(s.width for s in sprs) - 30 * (len(sprs) - 1)
            fit = min(1.0, (W - 90) / tw)
            x = W / 2 - tw * fit / 2
            y = sub_y(t)
            pop = back((t - times[cur]) / 0.18) if t >= times[cur] else 1
            if v["who"] != "narrador":
                put(fr, emoji("🍆" if v["who"] == "berenjena" else "🥒", 68), W / 2, y - 105)
            for i, s in enumerate(sprs):
                sc = (0.85 + 0.15 * pop if blk * 3 + i == cur else 1.0) * fit
                put(fr, s, x + s.width * fit / 2, y, 1, "mm", scale=sc)
                x += (s.width - 30) * fit
            return


def watermark(fr):
    put(fr, text("DRAMA VEGETAL", 38, stroke=4), W / 2 + 26, 210, 0.85)
    put(fr, emoji("🍆", 44), W / 2 - 205, 210, 0.85)
    put(fr, text("EP. 1", 28, (255, 226, 50), stroke=3), W / 2, 262, 0.8)


# ------------------------------------------------------------------ planos
def room_shot(name, z, fx, fy, blur=0):
    return camera(plate(f"room_{name}", blur), z, fx, fy)


def shot_hook(t):
    z, fx, fy = 1.05 + 0.03 * t, 0.55, 0.6
    fr = room_shot("wide", z, fx, fy)
    px, py, s = plate_xy("room_wide", ANC["rooms"]["wide"]["pillow"], z, fx, fy)
    tom = character("tomate", "tom_moon", int(170 * s), dict(open=0.0, mouth="smile"))
    put(fr, tom, px - 30 * s, py + 10 * s, anchor="mb", scale=1 + 0.012 * math.sin(t * 3))
    jit = math.sin(t * 90) * 5 if (0.3 < t < 0.7 or 1.4 < t < 1.8) else 0
    put(fr, glow_spr(520, 300, (90, 200, 255), 200), px + 70 * s + jit, py + 25 * s, 0.6 + 0.4 * math.sin(t * 8) ** 2)
    look = ease((t - 0.6) / 0.6)
    ber = character("berenjena", "ber_moon", 980, dict(px=0.9 * look, py=-0.4 * look, brow_up=0.8 * look, open=blink(t, 2.4, 1.2)))
    put(fr, contact_shadow(560), 300, 1885)
    put(fr, ber, 300, 1915, anchor="mb")
    k = back(t / 0.35)
    put(fr, text("¿QUÉ ESCONDE", 96, (255, 226, 50), stroke=10), W / 2, 430, clamp(t / 0.1), scale=0.6 + 0.4 * k)
    put(fr, text("ELLA?", 130, stroke=12), W / 2, 550, clamp((t - 0.15) / 0.1), scale=0.6 + 0.4 * back((t - 0.15) / 0.35))
    return fr


def shot_approach(t):
    z, fx, fy = 1.0 + 0.04 * t / 4.2, 0.5, 0.55
    fr = room_shot("bed", z, fx, fy, blur=3)
    put(fr, glow_spr(900, 900, (90, 200, 255), 150), 960, 1250, 0.9)
    x = 380 + 120 * ease(t / 4.2)
    ber = character("berenjena", "ber_phone", 1350, dict(px=0.8, py=0.3, brow_up=1.0 if t < 2.5 else 0.4, brow=0.0 if t < 2.5 else 0.3,
                                                          open=blink(t, 3.0, 0.5), mouth="neutral"))
    put(fr, contact_shadow(760), x, 1885)
    put(fr, ber, x, 1940 + math.sin(t * 5) * 5, anchor="mb")
    return fr


def shot_whisper(t):
    fr = room_shot("bed", 1.25, 0.45, 0.5, blur=8)
    put(fr, glow_spr(1100, 1100, (90, 200, 255), 160), 1000, 1000, 1)
    mo = mouth_env("b0", t + 7.2)
    ber = character("berenjena", "ber_phone", 2300, dict(px=1.0, py=0.4, brow=0.6, brow_up=0.4, mo=mo, open=blink(t, 3.1, 0.2), mouth="neutral"))
    put(fr, ber, W / 2 - 60, 2650 + math.sin(t * 2) * 6, anchor="mb")
    return fr


def shot_eyes(t):
    fr = Image.new("RGBA", (W, H), (22, 6, 40, 255))
    d = ImageDraw.Draw(fr)
    rr = random.Random(int(t * 12))
    for k in range(52):
        a = k / 52 * 2 * math.pi + rr.uniform(-0.03, 0.03)
        r0 = 600 + rr.uniform(0, 140)
        d.line([(W / 2 + math.cos(a) * r0, H * 0.42 + math.sin(a) * r0), (W / 2 + math.cos(a) * 1600, H * 0.42 + math.sin(a) * 1600)],
               fill=(90, 40, 160, 255), width=rr.randint(4, 14))
    z = 1.0 + 0.3 * eout(t / 0.35) + 0.05 * t
    ber = character("berenjena", "ber_phone", 3000, dict(open=1.0, big=1.25, brow_up=1.6, mouth="o", sweat=1.0 if t > 1.0 else 0.0))
    A = ANC["ber_phone"]
    s = 3000 / A["size"][1]
    ey = (A["eye_l"][1] + A["eye_r"][1]) / 2 * s
    put(fr, ber, W / 2, H * 0.42 + (ber.height / 2 - ey) * z * 0.62, scale=z * 0.62)
    return fr


def shot_angry(t):
    fr = room_shot("corner", 1.15, 0.5, 0.5, blur=7)
    fr = Image.blend(fr, Image.new("RGBA", (W, H), (120, 0, 25, 255)), 0.22 + 0.08 * math.sin(t * 8))
    tr = 6 + 4 * math.sin(t * 3)
    jx = random.Random(int(t * 30)).uniform(-tr, tr)
    jy = random.Random(int(t * 30) + 7).uniform(-tr, tr)
    tt = t + 18.6
    mo = max(mouth_env("b1", tt), mouth_env("b2", tt))
    sad = tt > 21.5
    ber = character("berenjena", "ber_moon", 1650, dict(brow=0.8 if sad else -1.0, tears=min(1.0, t / 1.5), mouth="wobbly" if sad else "frown",
                                                         mo=mo, py=0.3 if sad else 0.0, open=blink(t, 2.6)))
    put(fr, ber, W / 2 + jx, 2060 + jy, anchor="mb")
    return fr


def shot_sad(t):
    z, fx, fy = 1.08 + 0.05 * t / 4.8, 0.55, 0.6
    fr = room_shot("wide", z, fx, fy)
    px, py, s = plate_xy("room_wide", ANC["rooms"]["wide"]["pillow"], z, fx, fy)
    tom = character("tomate", "tom_moon", int(170 * s), dict(open=0.0, mouth="smile"))
    put(fr, tom, px - 30 * s, py + 10 * s, anchor="mb", scale=1 + 0.012 * math.sin(t * 3))
    if t > 1.8:
        a = clamp((t - 1.8) / 0.4) * (1 - clamp((t - 4.2) / 0.4))
        put(fr, text("Zzz… Pepi… ❤", 46, font="Inter-BoldItalic.otf", stroke=4) if False else text("Zzz… Pepi…", 48, font="Inter-BoldItalic.otf", stroke=5),
            px + 40, py - 190 * s, a)
    # lluvia sobre la ventana
    wx, wy, _ = plate_xy("room_wide", ANC["rooms"]["wide"]["window"], z, fx, fy)
    d = ImageDraw.Draw(fr)
    rr = random.Random(5)
    for _ in range(50):
        x = wx + rr.uniform(-150, 150) * s
        y = wy + ((rr.uniform(0, 400) + t * 600) % 400 - 200) * s
        d.line([(x, y), (x - 3, y + 26 * s)], fill=(170, 200, 255, 90), width=2)
    ber = character("berenjena", "ber_moon", 820, dict(brow=1.0, mouth="wobbly", tears=0.9, py=0.8, px=-0.3, open=blink(t, 3.3, 0.8)))
    put(fr, contact_shadow(480), 300, 1855)
    put(fr, ber, 300, 1880, anchor="mb", scale=1 + 0.01 * math.sin(t * 2.2))
    return fr


def shot_frozen(t):
    z = 1.0 + 0.06 * ease(t / 5.4)
    fr = room_shot("window", z, 0.5, 0.45)
    wx, wy, s = plate_xy("room_window", ANC["rooms"]["window"]["window"], z, 0.5, 0.45)
    if t > 2.3:
        a = clamp((t - 2.3) / 1.0)
        pep = character("pepino", "pep_back", 560, dict(lid=0.6, mouth="smirk", px=0.6, glow_eyes=0.8 + 0.2 * math.sin(t * 5)))
        put(fr, pep, wx - 250, wy - 40, a * 0.92, "mm")
    zz = 1.0 + 0.22 * ease(t / 5.4)
    ber = character("berenjena", "ber_moon", 1900, dict(open=1.0, big=1.1, brow_up=1.2, mouth="o", sweat=1.0))
    put(fr, ber, W / 2 - 40, 2520 + 260 * (zz - 1), anchor="mb", scale=zz)
    return fr


def shot_pepino(t):
    fr = room_shot("window", 1.6, 0.42, 0.42, blur=2)
    fr = Image.blend(fr, Image.new("RGBA", (W, H), (0, 10, 25, 255)), 0.3)
    mo = mouth_env("p1", t + 41.2)
    pep = character("pepino", "pep_moon", 2600, dict(lid=0.55, mouth="smirk", mo=mo, px=0.0, glow_eyes=0.6))
    put(fr, pep, W / 2 + 40, 1500 + 40 * ease(t / 1.4), anchor="mm", scale=1.0 + 0.05 * t)
    return fr


def shot_end(t):
    fr = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    k = back(t / 0.5)
    put(fr, text("CONTINUARÁ…", 130, font="InterDisplay-Black.otf"), W / 2, 820, clamp(t / 0.3), scale=0.7 + 0.3 * k)
    if t > 0.6:
        a = clamp((t - 0.6) / 0.3)
        put(fr, text("¿QUIERES LA PARTE 2?", 64, (255, 226, 50), stroke=6), W / 2, 1010, a)
        put(fr, text("COMENTA", 64, stroke=6), W / 2 - 60, 1110, a)
        put(fr, emoji("🍆", 80), W / 2 + 190, 1110, a, scale=1 + 0.1 * math.sin(t * 8))
    if t > 1.1:
        put(fr, text("DRAMA VEGETAL · EPISODIO 1", 34, (180, 170, 220), "Inter-Bold.otf"), W / 2, 1260, clamp((t - 1.1) / 0.3))
    return fr


SHOTS = [
    (0.0, 3.0, shot_hook),
    (3.0, 7.2, shot_approach),
    (7.2, 9.6, shot_whisper),
    (9.6, 13.0, lambda t: shot_phone(t, "unlock", dur=3.4)),
    (13.0, 15.4, shot_eyes),
    (15.4, 18.6, lambda t: shot_phone(t, "photo", shake=10 if 2.6 < t < 3.0 else 0, z0=1.02, z1=1.1, dur=3.2)),
    (18.6, 24.2, shot_angry),
    (24.2, 29.0, shot_sad),
    (29.0, 29.7, None),
    (29.7, 34.2, lambda t: shot_phone(t, "reveal", shake=8 if 2.1 < t < 2.4 else 0, z0=1.0, z1=1.15, dur=4.5)),
    (34.2, 39.6, shot_frozen),
    (39.6, 41.2, lambda t: shot_phone(t, "last", shake=6 if t < 0.3 else 0, z0=1.15, z1=1.2, dur=1.6)),
    (41.2, 42.6, shot_pepino),
    (42.6, 45.0, shot_end),
]
NO_MARK = {3, 5, 9, 11, 13}


# ------------------------------------------------------------------ acabado
@lru_cache(maxsize=1)
def vignette():
    y, x = np.ogrid[:H, :W]
    r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    v = np.clip((r - 0.5) / 0.85, 0, 1) ** 1.6
    return v[..., None].astype(np.float32)


def grade(fr, tt, mood=None):
    a = np.asarray(fr.convert("RGB")).astype(np.float32)
    # resplandor (bloom) de las zonas brillantes
    lum = a.mean(2, keepdims=True)
    bright = np.clip((a - 170) * 1.6, 0, 255) * (lum > 150)
    bl = Image.fromarray(bright.astype(np.uint8)).resize((W // 8, H // 8), Image.BILINEAR).filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BILINEAR)
    a = a + np.asarray(bl).astype(np.float32) * 0.55
    # gradacion: sombras frias, luces calidas, contraste suave
    a = a / 255.0
    a = a * a * (3 - 2 * a) * 0.35 + a * 0.65
    a[..., 2] = a[..., 2] * 1.04 + 0.012
    a[..., 0] = a[..., 0] * 1.02
    a = a * (1 - vignette() * 0.75)
    # grano de pelicula
    rng = np.random.default_rng(int(tt * FPS))
    a = a + rng.normal(0, 0.018, (H // 2, W // 2, 1)).repeat(2, 0).repeat(2, 1)
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def frame(tt):
    idx = 0
    for i, (a, b, fn) in enumerate(SHOTS):
        if a <= tt < b or (i == len(SHOTS) - 1 and tt >= a):
            idx = i; break
    a, b, fn = SHOTS[idx]
    t = tt - a
    if fn is None:
        fr = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        put(fr, glow_spr(600, 600, (80, 160, 255), 80), W / 2, H / 2, clamp(t / 0.5))
    else:
        fr = fn(t)
    out = grade(fr, tt)
    out = out.convert("RGBA")
    if 18.0 <= tt < 18.4:
        out = Image.blend(out, Image.new("RGBA", (W, H), (255, 255, 255, 255)), 1 - (tt - 18.0) / 0.4)
    for (a2, _, _) in SHOTS[1:]:
        if abs(tt - a2) < 0.05:
            out = Image.blend(out, Image.new("RGBA", (W, H), (0, 0, 0, 255)), 0.55)
    if idx not in NO_MARK and tt < 42.6 and fn is not None:
        watermark(out)
    subtitle(out, tt)
    if tt < 0.25:
        out = Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 255)), out, tt / 0.25)
    return out.convert("RGB")


def render_chunk(args):
    ci, f0, f1 = args
    path = os.path.join(BUILD, "chunks", f"c{ci:02d}.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", path],
                         stdin=subprocess.PIPE)
    for i in range(f0, f1):
        p.stdin.write(frame(i / FPS).tobytes())
    p.stdin.close(); p.wait()
    print(f"tramo {ci} listo", flush=True)
    return path


def main():
    if "--preview" in sys.argv:
        os.makedirs(os.path.join(BUILD, "preview"), exist_ok=True)
        for a in sys.argv[sys.argv.index("--preview") + 1:]:
            frame(float(a)).save(os.path.join(BUILD, "preview", f"f_{float(a):05.2f}.jpg"), quality=90)
        return
    os.makedirs(os.path.join(BUILD, "chunks"), exist_ok=True)
    total = int(DUR * FPS)
    step = 75
    jobs = [(i, f0, min(total, f0 + step)) for i, f0 in enumerate(range(0, total, step))]
    with Pool(os.cpu_count() or 4) as pool:
        paths = pool.map(render_chunk, jobs, chunksize=1)
    lst = os.path.join(BUILD, "chunks", "list.txt")
    open(lst, "w").write("".join(f"file '{os.path.basename(p)}'\n" for p in paths))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    os.path.join(BUILD, "mudo.mp4")], check=True)
    print("mudo.mp4 listo")


if __name__ == "__main__":
    main()
