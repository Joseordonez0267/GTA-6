# -*- coding: utf-8 -*-
"""Escenas de DRAMA VEGETAL Ep. 1 — render vertical 1080x1920 a 30 fps.

Planos (segundos):
  0.0- 2.0  gancho: el telefono vibra bajo la almohada
  2.0- 4.6  la berenjena se acerca, intrigada
  4.6- 7.6  telefono: desbloqueo y primer mensaje
  7.6-10.0  primerisimo plano: ojos abiertos de golpe
 10.0-12.4  telefono: aparece la foto (golpe dramatico)
 12.4-16.0  berenjena temblando: "¡¿Con él?! ¡No puedo creerlo!"
 16.0-20.0  plano general triste; la tomate duerme sonriendo
 20.0-20.6  silencio y oscuridad
 20.6-23.8  telefono: el mensaje de la revelacion
 23.8-27.4  zoom lento al rostro paralizado; el pepino aparece en la ventana
 27.4-30.0  pantalla negra: CONTINUARA...
"""
import json, math, os, random, subprocess, sys
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from vegetales import draw, shadow

BUILD = os.path.join(HERE, "build")
W, H, FPS, DUR = 1080, 1920, 30, 30.0
FD = "/usr/share/fonts/opentype/inter/"
EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
VOCES = json.load(open(os.path.join(BUILD, "voces.json"), encoding="utf-8"))


def F(name, size):
    return ImageFont.truetype(FD + name, size)


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def eout(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def back(x):  # rebote al aparecer
    x = clamp(x)
    c = 1.9
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def vgrad(w, h, stops):
    y = np.linspace(0, 1, h)[:, None]
    out = np.zeros((h, w, 3), np.float32)
    for c in range(3):
        out[..., c] = np.interp(y, [s[0] for s in stops], [s[1][c] for s in stops])
    return Image.fromarray(np.repeat(out, 1, 1).clip(0, 255).astype(np.uint8).repeat(1, 0) if False else
                           np.broadcast_to(out, (h, w, 3)).clip(0, 255).astype(np.uint8)).convert("RGBA")


def put(fr, spr, x, y, a=1.0, anchor="mm", scale=1.0):
    if a <= 0.004 or spr is None:
        return
    if scale != 1.0:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.BILINEAR)
    if a < 0.999:
        arr = np.asarray(spr).copy()
        arr[..., 3] = (arr[..., 3] * a).astype(np.uint8)
        spr = Image.fromarray(arr)
    w, h = spr.size
    x = int(x - {"l": 0, "m": w // 2, "r": w}[anchor[0]])
    y = int(y - {"t": 0, "m": h // 2, "b": h}[anchor[1]])
    sx, sy = max(0, -x), max(0, -y)
    if sx or sy:
        spr = spr.crop((sx, sy, w, h)); x += sx; y += sy
    if x < W and y < H:
        fr.alpha_composite(spr, (x, y))


_C = {}


def text(t, size, fill=(255, 255, 255), font="Inter-Black.otf", stroke=0, sfill=(0, 0, 0), shadow_=True):
    k = (t, size, fill, font, stroke, sfill, shadow_)
    if k in _C:
        return _C[k]
    f = F(font, size)
    l, tp, r, b = f.getbbox(t, stroke_width=stroke)
    pad = 24
    img = Image.new("RGBA", (r - l + pad * 2, b - tp + pad * 2), (0, 0, 0, 0))
    if shadow_:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - l + 4, pad - tp + 8), t, font=f, fill=(0, 0, 0, 160), stroke_width=stroke)
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    ImageDraw.Draw(img).text((pad - l, pad - tp), t, font=f, fill=fill + (255,) if len(fill) == 3 else fill,
                             stroke_width=stroke, stroke_fill=sfill + (255,))
    _C[k] = img
    return img


def emoji(ch, size):
    k = ("emoji", ch, size)
    if k not in _C:
        f = ImageFont.truetype(EMOJI, 109)
        img = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((80, 80), ch, font=f, embedded_color=True, anchor="mm")
        img = img.crop(img.getbbox())
        _C[k] = img.resize((int(img.width * size / 109), int(img.height * size / 109)), Image.LANCZOS)
    return _C[k]


def rrect(w, h, r, fill, outline=None, width=0):
    k = ("rr", w, h, r, fill, outline, width)
    if k not in _C:
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(img).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=fill, outline=outline, width=width)
        _C[k] = img
    return _C[k]


@lru_cache(maxsize=64)
def veg(kind, h, key):
    return draw(kind, h, dict(key))


def V(kind, h, **e):
    # cuantiza la expresion para reutilizar sprites
    key = tuple(sorted((k, round(v, 2) if isinstance(v, float) else v) for k, v in e.items()))
    return veg(kind, int(h), key)


# ------------------------------------------------------------------ fondos
@lru_cache(maxsize=4)
def bedroom(rain=False):
    BW, BH = int(W * 1.15), int(H * 1.15)
    img = vgrad(BW, BH, [(0, (16, 20, 52)), (0.62, (10, 12, 34)), (0.63, (40, 26, 30)), (1, (18, 12, 14))])
    d = ImageDraw.Draw(img)
    # tablas del suelo
    for y in range(int(BH * 0.63), BH, 60):
        d.line([(0, y), (BW, y)], fill=(28, 18, 22, 255), width=3)
    # ventana con luna
    wx0, wy0, wx1, wy1 = 120, 300, 620, 900
    win = vgrad(wx1 - wx0, wy1 - wy0, [(0, (20, 40, 90)), (1, (40, 70, 130))])
    wd = ImageDraw.Draw(win)
    rr = random.Random(2)
    for _ in range(60):
        x, y = rr.randrange(win.width), rr.randrange(win.height)
        wd.ellipse([x, y, x + 2, y + 2], fill=(255, 255, 255, rr.randint(80, 220)))
    wd.ellipse([300, 70, 430, 200], fill=(245, 240, 220, 255))
    img.paste(win, (wx0, wy0))
    d.rectangle([wx0, wy0, wx1, wy1], outline=(70, 50, 40, 255), width=18)
    d.line([((wx0 + wx1) // 2, wy0), ((wx0 + wx1) // 2, wy1)], fill=(70, 50, 40, 255), width=12)
    d.line([(wx0, (wy0 + wy1) // 2), (wx1, (wy0 + wy1) // 2)], fill=(70, 50, 40, 255), width=12)
    # cortinas
    for x0, x1 in ((40, 200), (540, 700)):
        d.rectangle([x0, 240, x1, 1000], fill=(90, 30, 80, 255))
        for k in range(5):
            xx = x0 + k * (x1 - x0) / 5
            d.line([(xx, 240), (xx, 1000)], fill=(60, 18, 55, 255), width=6)
    # haz de luz de luna
    beam = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(beam).polygon([(wx0, wy0), (wx1, wy0), (1100, BH), (300, BH)], fill=(140, 170, 255, 34))
    img.alpha_composite(beam.filter(ImageFilter.GaussianBlur(40)))
    # cama
    d.rounded_rectangle([600, 820, 1220, 1150], 40, fill=(70, 40, 30, 255))          # cabecero
    d.rounded_rectangle([560, 1080, 1250, 1500], 30, fill=(46, 30, 70, 255))         # colchon/manta
    d.rounded_rectangle([560, 1180, 1250, 1500], 30, fill=(60, 40, 110, 255))
    for k in range(6):
        d.arc([560 + k * 115, 1150, 700 + k * 115, 1260], 0, 180, fill=(80, 56, 140, 255), width=6)
    d.rounded_rectangle([640, 1010, 1010, 1150], 60, fill=(200, 205, 230, 255))     # almohada
    d.rectangle([560, 1500, 600, 1560], fill=(50, 30, 24, 255))
    d.rectangle([1210, 1500, 1250, 1560], fill=(50, 30, 24, 255))
    # mesita y lampara apagada
    d.rectangle([60, 1150, 360, 1500], fill=(60, 36, 28, 255))
    d.rectangle([80, 1250, 340, 1270], fill=(40, 24, 20, 255))
    d.polygon([(150, 980), (270, 980), (300, 1080), (120, 1080)], fill=(200, 170, 120, 255))
    d.rectangle([200, 1080, 220, 1150], fill=(90, 80, 70, 255))
    return img


@lru_cache(maxsize=4)
def bokeh_bg(tint=(20, 18, 50), seed=1):
    img = vgrad(W, H, [(0, tint), (1, (4, 4, 10))])
    b = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(b)
    rr = random.Random(seed)
    for _ in range(30):
        x, y, r = rr.randrange(W), rr.randrange(H), rr.randint(30, 110)
        c = rr.choice([(120, 90, 255), (60, 200, 255), (255, 80, 160)])
        d.ellipse([x - r, y - r, x + r, y + r], fill=c + (rr.randint(25, 60),))
    img.alpha_composite(b.filter(ImageFilter.GaussianBlur(18)))
    return img


@lru_cache(maxsize=2)
def vignette(strength=210, color=(0, 0, 0)):
    y, x = np.ogrid[:H, :W]
    r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    v = np.clip((r - 0.55) / 0.8, 0, 1) ** 1.5 * strength
    arr = np.zeros((H, W, 4), np.uint8)
    arr[..., :3] = color
    arr[..., 3] = v.astype(np.uint8)
    return Image.fromarray(arr)


def camera(img, z, fx=0.5, fy=0.5, dx=0, dy=0):
    """Recorta el fondo (mas grande que el cuadro) con zoom z hacia el punto (fx, fy)."""
    BW, BH = img.size
    s = z * max(W / BW, H / BH) * 1.0
    s = max(s, W / BW, H / BH)
    a = 1 / s
    cx = fx * BW + dx
    cy = fy * BH + dy
    c = cx - (W / 2) * a
    f = cy - (H / 2) * a
    c = clamp(c, 0, BW - W * a)
    f = clamp(f, 0, BH - H * a)
    return img.transform((W, H), Image.AFFINE, (a, 0, c, 0, a, f), resample=Image.BILINEAR)


# ------------------------------------------------------------------ telefono
PHW, PHH = 820, 1480
PX, PY = W // 2, 860


def phone_frame():
    k = "phone"
    if k not in _C:
        img = Image.new("RGBA", (PHW + 80, PHH + 80), (0, 0, 0, 0))
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([40, 50, PHW + 40, PHH + 50], 90, fill=(0, 0, 0, 200))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(25)))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([40, 40, PHW + 40, PHH + 40], 90, fill=(18, 18, 22, 255), outline=(90, 90, 110, 255), width=6)
        _C[k] = img
    return _C[k]


def bubble(txt, maxw=600, incoming=True, size=40, hl=None):
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
    d.rounded_rectangle([0, 0, bw - 1, bh - 1], 34, fill=(48, 48, 58, 255) if incoming else (46, 120, 255, 255))
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
    pw, ph = 560, 620
    pic = vgrad(pw, ph, [(0, (255, 150, 90)), (0.55, (255, 90, 120)), (0.56, (40, 120, 170)), (1, (20, 60, 110))])
    d = ImageDraw.Draw(pic)
    d.ellipse([pw / 2 - 90, 200, pw / 2 + 90, 380], fill=(255, 230, 140, 255))
    tom = V("tomate", 300, blush=0.9, mouth="smile", px=0.5, open=0.9)
    pep = V("pepino", 520, mouth="smirk", lid=0.35, px=-0.6)
    pic.alpha_composite(pep, (int(pw * 0.48), ph - pep.height + 30))
    pic.alpha_composite(tom, (int(pw * 0.06), ph - tom.height + 10))
    hrt = emoji("❤️", 90)
    pic.alpha_composite(hrt, (pw // 2 - 50, 60))
    card = Image.new("RGBA", (pw + 30, ph + 30), (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle([0, 0, pw + 29, ph + 29], 30, fill=(48, 48, 58, 255))
    m = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, pw - 1, ph - 1], 24, fill=255)
    card.paste(pic, (15, 15), m)
    _C[k] = card
    return card


def phone_screen(fr, t, mode, shake=0.0):
    """mode: unlock | photo | reveal. t local."""
    ox = PX + (random.Random(int(t * 40)).uniform(-shake, shake) if shake else 0)
    oy = PY + (random.Random(int(t * 40) + 9).uniform(-shake, shake) if shake else 0)
    put(fr, phone_frame(), ox, oy)
    sx0, sy0 = int(ox - PHW / 2 + 22), int(oy - PHH / 2 + 22)
    sw, sh = PHW - 44, PHH - 44
    scr = Image.new("RGBA", (sw, sh), (10, 10, 14, 255))
    d = ImageDraw.Draw(scr)
    if mode == "unlock" and t < 0.9:
        g = vgrad(sw, sh, [(0, (60, 30, 110)), (1, (10, 20, 50))])
        scr.alpha_composite(g)
        put(scr, text("03:14", 150, font="InterDisplay-Bold.otf"), sw / 2, 300)
        put(scr, text("martes, 21 de noviembre", 34, font="Inter-Medium.otf"), sw / 2, 400)
        a = 1 - clamp((t - 0.55) / 0.3)
        lk = emoji("🔒" if t < 0.5 else "🔓", 90)
        put(scr, lk, sw / 2, 120, a)
    else:
        msg1 = bubble("No puedo seguir ocultándote lo de la berenjena…", size=50, maxw=680, hl=("berenjena",))
        if mode == "unlock":
            tt = t - 0.9
            if tt < 0.0:
                pass
            elif tt < 0.0001:
                pass
            k = back(tt / 0.35)
            put(scr, msg1, 40, 300, clamp(tt / 0.15), "lt", scale=0.6 + 0.4 * k)
        elif mode == "photo":
            scroll = eout((t - 0.2) / 0.6) * 260
            put(scr, msg1, 40, 300 - scroll, 1, "lt")
            if t > 0.8:
                k = back((t - 0.8) / 0.4)
                put(scr, photo_card(), 40, 460 - scroll + 140, clamp((t - 0.8) / 0.15), "lt", scale=0.7 + 0.3 * k)
        elif mode == "reveal":
            put(scr, msg1, 40, 40 - 200, 0.6, "lt")
            put(scr, photo_card(), 40, 320 - 300, 0.6, "lt", scale=0.7)
            if 0.15 < t < 0.85:  # escribiendo...
                b = rrect(170, 80, 40, (48, 48, 58, 255))
                put(scr, b, 40, 720, 1, "lt")
                for i in range(3):
                    yy = 760 + math.sin(t * 14 + i) * 8
                    put(scr, rrect(20, 20, 10, (200, 200, 210, 255)), 80 + i * 40, yy)
            if t >= 0.85:
                k = back((t - 0.85) / 0.35)
                m2 = bubble("Él todavía no sabe que el pepino es su verdadero hermano…", size=58, maxw=700, hl=("verdadero", "hermano"))
                put(scr, m2, 40, 720, clamp((t - 0.85) / 0.15), "lt", scale=0.6 + 0.4 * k)
    if not (mode == "unlock" and t < 0.9):
        # cabecera del chat
        d.rectangle([0, 0, sw, 190], fill=(24, 24, 30, 255))
        d.ellipse([40, 70, 140, 170], fill=(80, 80, 95, 255))
        put(scr, text("?", 60, font="InterDisplay-Black.otf", shadow_=False), 90, 120)
        put(scr, text("Número oculto", 40, font="Inter-Bold.otf", shadow_=False), 170, 100, anchor="lm")
        put(scr, text("en línea", 28, (120, 220, 140), font="Inter-Medium.otf", shadow_=False), 170, 146, anchor="lm")
    mask = rrect(sw, sh, 70, (255, 255, 255, 255)).getchannel("A")
    fr.paste(scr, (sx0, sy0), mask)
    # resplandor de la pantalla
    put(fr, rrect(160, 14, 7, (40, 40, 48, 255)), ox, sy0 + 26)


# ------------------------------------------------------------------ subtitulos
def subtitle(fr, t):
    for vid, v in VOCES.items():
        if v["start"] - 0.05 <= t <= v["end"] + 0.35:
            words = v["text"].split()
            total = sum(len(w) for w in words)
            dur = v["end"] - v["start"]
            # tiempos por palabra proporcionales a su longitud
            acc, times = 0, []
            for w in words:
                times.append(v["start"] + dur * acc / total)
                acc += len(w)
            cur = max(0, sum(1 for x in times if x <= t) - 1)
            # bloques de 3 palabras
            blk = cur // 3
            chunk = words[blk * 3: blk * 3 + 3]
            size = 92 if v["who"] == "berenjena" else 80
            sprs = []
            for i, w in enumerate(chunk):
                idx = blk * 3 + i
                col = (255, 226, 50) if idx == cur else (255, 255, 255)
                if v["who"] == "berenjena" and idx == cur:
                    col = (200, 140, 255)
                sprs.append(text(w.upper(), size, col, "Inter-Black.otf", stroke=9, sfill=(0, 0, 0)))
            tw = sum(s.width for s in sprs) - 30 * (len(sprs) - 1)
            fit = min(1.0, (W - 90) / tw)
            tw *= fit
            x = W / 2 - tw / 2
            pop = back((t - times[cur]) / 0.18) if t >= times[cur] else 1
            y = sub_y(t)
            if v["who"] == "berenjena":
                put(fr, emoji("🍆", 70), W / 2, y - 105)
            for i, s in enumerate(sprs):
                sc = (0.85 + 0.15 * pop if blk * 3 + i == cur else 1.0) * fit
                put(fr, s, x + s.width * fit / 2, y, 1, "mm", scale=sc)
                x += (s.width - 30) * fit
            return


def sub_y(t):
    if t < 4.6 or 12.4 <= t < 16.0:
        return 760
    if 16.0 <= t < 20.0 or 23.8 <= t < 27.4:
        return 1180
    return 1330


def watermark(fr, t, a=1.0):
    put(fr, text("DRAMA VEGETAL", 38, (255, 255, 255), "Inter-Black.otf", stroke=4), W / 2 + 26, 210, 0.85 * a)
    put(fr, emoji("🍆", 44), W / 2 - 205, 210, 0.85 * a)
    put(fr, text("EP. 1", 28, (255, 226, 50), "Inter-Black.otf", stroke=3), W / 2, 262, 0.8 * a)


def mouth_env(t):
    v = VOCES.get("b1")
    if not v or not (v["start"] <= t <= v["end"]):
        return 0.0
    i = int((t - v["start"]) * 30)
    env = v.get("env", [])
    return env[i] if i < len(env) else 0.0


# ------------------------------------------------------------------ planos
def shot_hook(t):
    fr = camera(bedroom(), 1.0 + 0.04 * t, 0.62, 0.62)
    # tomate durmiendo sobre la almohada
    breath = 1 + 0.015 * math.sin(t * 3)
    tom = V("tomate", 230, open=0.0, mouth="smile", blush=0.4)
    put(fr, tom, 790, 1015, scale=breath)
    # telefono vibrando bajo la almohada (resplandor)
    jit = math.sin(t * 90) * 6 if (0.2 < t < 0.6 or 1.0 < t < 1.4) else 0
    gl = Image.new("RGBA", (420, 220), (0, 0, 0, 0))
    ImageDraw.Draw(gl).ellipse([0, 0, 419, 219], fill=(90, 200, 255, 150))
    put(fr, gl.filter(ImageFilter.GaussianBlur(30)), 900 + jit, 1110, 0.6 + 0.4 * math.sin(t * 8) ** 2)
    put(fr, rrect(150, 40, 12, (180, 240, 255, 255)), 930 + jit, 1125)
    # berenjena en primer plano, mira hacia la almohada
    look = ease((t - 0.4) / 0.6)
    ber = V("berenjena", 900, px=0.8 * look, py=-0.2 * look, brow_up=0.8 * look, mouth="neutral" if look > 0.5 else "smile")
    put(fr, shadow(520), 330, 1880)
    put(fr, ber, 330, 1900, anchor="mb")
    # gancho
    k = back(t / 0.35)
    put(fr, text("¿QUÉ ESCONDE", 96, (255, 226, 50), stroke=10), W / 2, 450, clamp(t / 0.1), scale=0.6 + 0.4 * k)
    put(fr, text("ELLA?", 130, (255, 255, 255), stroke=12), W / 2, 570, clamp((t - 0.15) / 0.1), scale=0.6 + 0.4 * back((t - 0.15) / 0.35))
    return fr


def shot_approach(t):
    fr = camera(bedroom(), 1.25 + 0.05 * t, 0.7, 0.7)
    gl = Image.new("RGBA", (700, 700), (0, 0, 0, 0))
    ImageDraw.Draw(gl).ellipse([0, 0, 699, 699], fill=(90, 200, 255, 120))
    put(fr, gl.filter(ImageFilter.GaussianBlur(80)), 1000, 1150, 0.8)
    x = 420 + 90 * ease(t / 2.6)
    ber = V("berenjena", 1250, px=0.7, py=0.1, brow_up=1.0, brow=0.2 if t > 1.6 else 0.0, mouth="o" if t > 1.6 else "neutral")
    put(fr, shadow(700), x, 1900)
    put(fr, ber, x, 1950 + math.sin(t * 6) * 6, anchor="mb")
    return fr


def shot_phone(t, mode, tint=(20, 18, 50), shake=0.0):
    fr = bokeh_bg(tint).copy()
    phone_screen(fr, t, mode, shake)
    return fr


def shot_eyes(t):
    fr = Image.new("RGBA", (W, H), (30, 10, 50, 255))
    # lineas de impacto
    d = ImageDraw.Draw(fr)
    rr = random.Random(int(t * 12))
    for k in range(48):
        a = k / 48 * 2 * math.pi + rr.uniform(-0.03, 0.03)
        r0 = 560 + rr.uniform(0, 120)
        d.line([(W / 2 + math.cos(a) * r0, H * 0.45 + math.sin(a) * r0), (W / 2 + math.cos(a) * 1500, H * 0.45 + math.sin(a) * 1500)],
               fill=(120, 60, 200, 255), width=rr.randint(4, 14))
    z = 1.0 + 0.35 * eout(t / 0.35) + 0.05 * t
    ber = V("berenjena", 2300, open=1.3, brow_up=1.6, mouth="o", px=0.0, py=0.0, sweat=1.0 if t > 1.0 else 0.0)
    put(fr, ber, W / 2, H * 0.45 + 2300 * 0.06, scale=z * 0.75)
    put(fr, vignette(230), 0, 0, anchor="lt")
    return fr


def shot_angry(t):
    fr = camera(bedroom(), 1.5, 0.3, 0.55)
    fr = Image.blend(fr, Image.new("RGBA", (W, H), (120, 0, 30, 255)), 0.25 + 0.1 * math.sin(t * 8))
    tr = 7 + 4 * math.sin(t * 3)
    jx = random.Random(int(t * 30)).uniform(-tr, tr)
    jy = random.Random(int(t * 30) + 7).uniform(-tr, tr)
    mo = mouth_env(t + 12.4)
    ber = V("berenjena", 1500, brow=-1.0, tears=min(1.0, t / 1.5), mouth="frown", mouth_open=round(mo * 4) / 4, px=0.0, py=0.15)
    put(fr, ber, W / 2 + jx, 1980 + jy, anchor="mb")
    put(fr, vignette(240, (60, 0, 10)), 0, 0, anchor="lt")
    return fr


def shot_sad(t):
    fr = camera(bedroom(), 1.0 + 0.05 * t / 4, 0.55, 0.6)
    tom = V("tomate", 230, open=0.0, mouth="smile", blush=0.5)
    put(fr, tom, 790, 1015, scale=1 + 0.015 * math.sin(t * 3))
    # lluvia en la ventana
    d = ImageDraw.Draw(fr)
    rr = random.Random(5)
    for _ in range(60):
        x = rr.uniform(110, 600)
        y = (rr.uniform(0, 600) + t * 900) % 620 + 290
        d.line([(x, y), (x - 6, y + 40)], fill=(170, 200, 255, 120), width=2)
    ber = V("berenjena", 760, brow=1.0, mouth="wobbly", tears=0.9, py=0.5, px=-0.3)
    put(fr, shadow(440), 330, 1840)
    put(fr, ber, 330, 1860, anchor="mb", scale=1.0)
    put(fr, vignette(200), 0, 0, anchor="lt")
    return fr


def shot_frozen(t):
    # zoom lento al rostro; el pepino aparece en la ventana al fondo
    z = 1.0 + 0.25 * ease(t / 3.6)
    fr = camera(bedroom(), 1.35, 0.25, 0.32)
    if t > 1.2:
        a = clamp((t - 1.2) / 0.8)
        pep = V("pepino", 520, lid=0.45, mouth="smirk", px=0.4)
        # silueta oscura con ojos que brillan
        dark = Image.new("RGBA", pep.size, (5, 15, 10, 255))
        dark.putalpha(pep.getchannel("A"))
        sil = Image.blend(pep, dark, 0.65)
        put(fr, sil, 330, 640, a * 0.95)
        gl = Image.new("RGBA", (200, 80), (0, 0, 0, 0))
        ImageDraw.Draw(gl).ellipse([20, 20, 70, 60], fill=(255, 230, 80, 255))
        ImageDraw.Draw(gl).ellipse([130, 20, 180, 60], fill=(255, 230, 80, 255))
        put(fr, gl.filter(ImageFilter.GaussianBlur(10)), 330, 640 - 520 * 0.26 + 20, a * (0.6 + 0.4 * math.sin(t * 5) ** 2))
    fr = Image.blend(fr, Image.new("RGBA", (W, H), (0, 0, 10, 255)), 0.35)
    ber = V("berenjena", 1700, open=1.15, brow_up=1.2, mouth="o", sweat=1.0, px=0.0, py=0.0)
    put(fr, ber, W / 2 + 120, 2380 + 300 * (z - 1), anchor="mb", scale=z)
    put(fr, vignette(245), 0, 0, anchor="lt")
    return fr


def shot_end(t):
    fr = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    k = back(t / 0.5)
    put(fr, text("CONTINUARÁ…", 130, (255, 255, 255), "InterDisplay-Black.otf", stroke=0), W / 2, 820, clamp(t / 0.3), scale=0.7 + 0.3 * k)
    if t > 0.6:
        a = clamp((t - 0.6) / 0.3)
        put(fr, text("¿QUIERES LA PARTE 2?", 64, (255, 226, 50), stroke=6), W / 2, 1010, a)
        put(fr, text("COMENTA", 64, (255, 255, 255), stroke=6), W / 2 - 60, 1110, a)
        put(fr, emoji("🍆", 80), W / 2 + 190, 1110, a, scale=1 + 0.1 * math.sin(t * 8))
    if t > 1.1:
        put(fr, text("DRAMA VEGETAL · EPISODIO 1", 34, (180, 170, 220), "Inter-Bold.otf"), W / 2, 1260, clamp((t - 1.1) / 0.3))
    return fr


SHOTS = [
    (0.0, 2.0, lambda t: shot_hook(t)),
    (2.0, 4.6, lambda t: shot_approach(t)),
    (4.6, 7.6, lambda t: shot_phone(t, "unlock")),
    (7.6, 10.0, lambda t: shot_eyes(t)),
    (10.0, 12.4, lambda t: shot_phone(t, "photo", (40, 12, 40), shake=10 if 1.6 < t < 2.0 else 0)),
    (12.4, 16.0, lambda t: shot_angry(t)),
    (16.0, 20.0, lambda t: shot_sad(t)),
    (20.0, 20.6, None),
    (20.6, 23.8, lambda t: shot_phone(t, "reveal", (10, 10, 24), shake=8 if 1.7 < t < 2.0 else 0)),
    (23.8, 27.4, lambda t: shot_frozen(t)),
    (27.4, 30.0, lambda t: shot_end(t)),
]


def frame(tt):
    for (a, b, fn) in SHOTS:
        if a <= tt < b or (b == DUR and tt >= a):
            break
    t = tt - a
    if fn is None:  # silencio: solo el brillo del telefono en la oscuridad
        fr = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        gl = Image.new("RGBA", (500, 500), (0, 0, 0, 0))
        ImageDraw.Draw(gl).ellipse([0, 0, 499, 499], fill=(80, 160, 255, 70))
        put(fr, gl.filter(ImageFilter.GaussianBlur(60)), W / 2, H / 2, clamp(t / 0.5))
    else:
        fr = fn(t)
    # destello blanco al ver la foto
    if 11.6 <= tt < 12.0:
        fr = Image.blend(fr, Image.new("RGBA", (W, H), (255, 255, 255, 255)), 1 - (tt - 11.6) / 0.4)
    # corte rapido: breve fundido a negro en los cambios de plano
    for (a2, _, _) in SHOTS[1:]:
        if abs(tt - a2) < 0.07:
            fr = Image.blend(fr, Image.new("RGBA", (W, H), (0, 0, 0, 255)), 0.5)
    if tt < 27.4 and not (20.0 <= tt < 20.6) and not (4.6 <= tt < 7.6 or 10.0 <= tt < 12.4 or 20.6 <= tt < 23.8):
        watermark(fr, tt)
    subtitle(fr, tt)
    return fr.convert("RGB")


def render_chunk(args):
    ci, f0, f1 = args
    path = os.path.join(BUILD, "chunks", f"c{ci:02d}.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", path],
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
            frame(float(a)).save(os.path.join(BUILD, "preview", f"f_{float(a):05.2f}.jpg"), quality=88)
        return
    os.makedirs(os.path.join(BUILD, "chunks"), exist_ok=True)
    total = int(DUR * FPS)
    step = 113
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
