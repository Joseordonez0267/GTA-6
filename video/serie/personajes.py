# -*- coding: utf-8 -*-
"""Personajes (siluetas estilizadas originales) y escenarios nuevos para la serie.

Las figuras son siluetas genericas con contraluz de color y accesorios que las
distinguen; no reproducen el aspecto de ningun personaje oficial.
Al importar este modulo se registran los escenarios en arte.SCENE_ART.
"""
import math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import arte
from arte import LW, LH, layer, vgrad, hexc, glow, font, tech_bg, stars, skyline, water, reflect, palms_layer

from episodios import PERSONAJES

DARK = (10, 8, 16, 255)


# ------------------------------------------------------------------ figura
def figure(cx, base, h, spec, rim, dark=DARK):
    """Devuelve una capa con un busto en silueta. cx = centro, base = borde inferior, h = altura."""
    b = spec.get("build", 1.0)
    shape = Image.new("L", (LW, LH), 0)
    d = ImageDraw.Draw(shape)
    hr = h * 0.12                      # radio de la cabeza
    hy = base - h + hr * 1.7           # centro de la cabeza
    hx = cx
    # torso y hombros
    sw = h * 0.33 * b
    top_t = hy + hr * 1.75
    d.ellipse([cx - sw, top_t, cx + sw, top_t + h * 0.45], fill=255)
    d.rounded_rectangle([cx - sw, top_t + h * 0.16, cx + sw, base + 40], int(h * 0.05), fill=255)
    d.polygon([(cx - hr * 0.5, hy + hr * 0.6), (cx + hr * 0.5, hy + hr * 0.6), (cx + hr * 0.62, top_t + hr * 0.4), (cx - hr * 0.62, top_t + hr * 0.4)], fill=255)
    d.ellipse([hx - hr * 0.92, hy - hr * 1.1, hx + hr * 0.92, hy + hr * 1.1], fill=255)
    hair = spec.get("hair", "short")
    if hair == "long":
        d.ellipse([hx - hr * 1.15, hy - hr * 1.25, hx + hr * 1.15, hy + hr * 0.6], fill=255)
        d.rounded_rectangle([hx - hr * 1.2, hy - hr * 0.2, hx + hr * 1.2, hy + hr * 2.6], int(hr * 0.6), fill=255)
    elif hair == "bun":
        d.ellipse([hx - hr * 1.0, hy - hr * 1.25, hx + hr * 1.0, hy + hr * 0.3], fill=255)
        d.ellipse([hx - hr * 0.55, hy - hr * 2.05, hx + hr * 0.55, hy - hr * 0.95], fill=255)
    elif hair == "curly":
        for k in range(9):
            a = math.pi * (0.9 + k / 8 * 1.2)
            d.ellipse([hx + math.cos(a) * hr - hr * 0.4, hy + math.sin(a) * hr - hr * 0.4,
                       hx + math.cos(a) * hr + hr * 0.4, hy + math.sin(a) * hr + hr * 0.4], fill=255)
    elif hair == "slick":
        d.ellipse([hx - hr * 1.0, hy - hr * 1.2, hx + hr * 1.05, hy + hr * 0.1], fill=255)
        d.polygon([(hx - hr, hy - hr * 0.3), (hx + hr * 1.1, hy - hr * 0.6), (hx + hr * 1.0, hy + hr * 0.2)], fill=255)
    elif hair == "short":
        d.ellipse([hx - hr * 0.98, hy - hr * 1.18, hx + hr * 0.98, hy + hr * 0.2], fill=255)
    if spec.get("beard"):
        d.ellipse([hx - hr * 0.85, hy + hr * 0.1, hx + hr * 0.85, hy + hr * 1.35], fill=255)
    hat = spec.get("hat")
    if hat == "cap":
        d.chord([hx - hr * 1.05, hy - hr * 1.45, hx + hr * 1.05, hy + hr * 0.4], 180, 360, fill=255)
        d.rounded_rectangle([hx - hr * 0.2, hy - hr * 0.62, hx + hr * 1.9, hy - hr * 0.42], int(hr * 0.1), fill=255)
    elif hat == "cap_back":
        d.chord([hx - hr * 1.05, hy - hr * 1.45, hx + hr * 1.05, hy + hr * 0.4], 180, 360, fill=255)
        d.rounded_rectangle([hx - hr * 1.8, hy - hr * 0.62, hx + hr * 0.2, hy - hr * 0.42], int(hr * 0.1), fill=255)
    elif hat == "bucket":
        d.chord([hx - hr * 1.0, hy - hr * 1.6, hx + hr * 1.0, hy + hr * 0.2], 180, 360, fill=255)
        d.polygon([(hx - hr * 1.7, hy - hr * 0.35), (hx + hr * 1.7, hy - hr * 0.35), (hx + hr * 1.1, hy - hr * 0.75), (hx - hr * 1.1, hy - hr * 0.75)], fill=255)
    elif hat == "fedora":
        d.rounded_rectangle([hx - hr * 0.85, hy - hr * 1.9, hx + hr * 0.85, hy - hr * 0.6], int(hr * 0.3), fill=255)
        d.ellipse([hx - hr * 1.8, hy - hr * 0.9, hx + hr * 1.8, hy - hr * 0.45], fill=255)
    if spec.get("headphones"):        # cascos al cuello
        d.ellipse([hx - hr * 1.25, hy + hr * 1.15, hx - hr * 0.55, hy + hr * 1.85], fill=255)
        d.ellipse([hx + hr * 0.6, hy + hr * 1.1, hx + hr * 1.3, hy + hr * 1.9], fill=255)
    if spec.get("headset"):
        d.ellipse([hx - hr * 1.15, hy - hr * 0.2, hx - hr * 0.7, hy + hr * 0.5], fill=255)
    if spec.get("mic"):
        d.line([(hx + hr * 1.6, base - h * 0.3), (hx + hr * 0.9, hy + hr * 0.9)], fill=255, width=int(hr * 0.22))
        d.ellipse([hx + hr * 0.6, hy + hr * 0.5, hx + hr * 1.15, hy + hr * 1.1], fill=255)
    # contraluz: la silueta desplazada en el color del personaje
    rimimg = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    off = max(3, int(h * 0.008))
    rim_mask = Image.new("L", (LW, LH), 0)
    rim_mask.paste(shape, (off * 2, -off))
    rimc = Image.new("RGBA", (LW, LH), hexc(rim))
    rimimg.paste(rimc, (0, 0), rim_mask)
    rimimg = glow(rimimg, 14, 1.0)
    out = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    out.alpha_composite(rimimg)
    body = Image.new("RGBA", (LW, LH), dark)
    out.paste(body, (0, 0), shape)
    # detalles de ropa y accesorios (visibles sobre la silueta)
    dd = ImageDraw.Draw(out)
    top = top_t + hr * 0.15
    shirt = spec.get("shirt", "tee")
    if shirt == "hawaii":
        rng = random.Random(4)
        for _ in range(60):
            x = rng.uniform(cx - sw * 0.95, cx + sw * 0.95)
            y = rng.uniform(top + 30, base)
            r = rng.uniform(8, 18) * h / 900
            dd.ellipse([x - r, y - r, x + r, y + r], fill=hexc(rim, 70))
        dd.line([(cx, top + 20), (cx, base)], fill=(0, 0, 0, 255), width=4)
    elif shirt == "suit":
        dd.polygon([(cx - hr * 0.7, top), (cx, top + h * 0.28), (cx - sw * 0.55, top + h * 0.05)], fill=(30, 28, 40, 255))
        dd.polygon([(cx + hr * 0.7, top), (cx, top + h * 0.28), (cx + sw * 0.55, top + h * 0.05)], fill=(30, 28, 40, 255))
        dd.polygon([(cx - hr * 0.55, top), (cx + hr * 0.55, top), (cx, top + h * 0.26)], fill=(225, 225, 230, 255))
        if spec.get("tie"):
            dd.polygon([(cx - hr * 0.15, top + 6), (cx + hr * 0.15, top + 6), (cx + hr * 0.22, top + h * 0.22), (cx, top + h * 0.26), (cx - hr * 0.22, top + h * 0.22)], fill=hexc(rim))
    elif shirt == "hoodie":
        dd.line([(cx - hr * 0.4, top + 10), (cx - hr * 0.5, top + h * 0.2)], fill=(200, 200, 210, 200), width=4)
        dd.line([(cx + hr * 0.4, top + 10), (cx + hr * 0.5, top + h * 0.2)], fill=(200, 200, 210, 200), width=4)
    elif shirt == "top":
        dd.line([(cx - sw * 0.6, top + 6), (cx + sw * 0.6, top + 6)], fill=hexc(rim, 160), width=5)
    if spec.get("chain"):
        dd.arc([cx - hr * 1.1, top - hr * 0.6, cx + hr * 1.1, top + h * 0.2], 20, 160, fill=hexc("#ffd166"), width=max(4, int(h * 0.008)))
    if spec.get("sunglasses"):
        for sx in (-1, 1):
            dd.rounded_rectangle([hx + sx * hr * 0.4 - hr * 0.32, hy - hr * 0.28, hx + sx * hr * 0.4 + hr * 0.32, hy + hr * 0.08], int(hr * 0.12), fill=hexc(rim, 230))
        dd.line([(hx - hr * 0.1, hy - hr * 0.18), (hx + hr * 0.1, hy - hr * 0.18)], fill=hexc(rim, 230), width=4)
    if spec.get("glasses"):
        for sx in (-1, 1):
            dd.ellipse([hx + sx * hr * 0.42 - hr * 0.3, hy - hr * 0.25, hx + sx * hr * 0.42 + hr * 0.3, hy + hr * 0.15], outline=hexc(rim, 220), width=3)
    return out


def card_scene(key):
    p = PERSONAJES[key]
    col = p["color"]
    bg = vgrad(LW, LH, [(0, "#0b0814"), (1, "#020104")])
    # franja diagonal de color con trama de puntos
    band = Image.new("L", (LW, LH), 0)
    ImageDraw.Draw(band).polygon([(0, 0), (1150, 0), (800, LH), (0, LH)], fill=255)
    colimg = vgrad(LW, LH, [(0, col), (1, "#1a0b2a")])
    dots = Image.new("L", (LW, LH), 0)
    dd = ImageDraw.Draw(dots)
    for y in range(0, LH, 26):
        for x in range(0, 1200, 26):
            r = 2 + 6 * (1 - x / 1200)
            dd.ellipse([x - r, y - r, x + r, y + r], fill=60)
    m = np.minimum(np.asarray(band, np.float32), 255) * 0.85 / 255
    m = Image.fromarray((m * 255).astype(np.uint8))
    bg.paste(colimg, (0, 0), m)
    dark = Image.new("RGBA", (LW, LH), (0, 0, 0, 255))
    bg.paste(dark, (0, 0), Image.fromarray((np.asarray(dots) * (np.asarray(band) > 0)).astype(np.uint8)))
    # nombre gigante de fondo
    txt = layer()
    ImageDraw.Draw(txt).text((LW - 60, LH // 2 + 40), p["name"].split()[0], font=font("InterDisplay-Black.otf", 420),
                             fill=(255, 255, 255, 14), anchor="rm")
    bg.alpha_composite(txt)
    figs = layer()
    if "duo" in p:
        figs.alpha_composite(figure(420, LH + 20, 860, p["duo"][0], col))
        figs.alpha_composite(figure(880, LH + 20, 900, p["duo"][1], "#ffd166"))
    else:
        figs.alpha_composite(figure(640, LH + 20, 950, p["fig"], col))
    return [(bg, 0.15), (figs, 0.7)]


# ------------------------------------------------------------------ escenarios
def sc_keys_night():
    hz = 760
    sky = vgrad(LW, LH, [(0, "#030616"), (0.6, "#0d1f3f"), (1, "#163a5c")])
    stars(sky, 380, 700, 21)
    moon = layer(); ImageDraw.Draw(moon).ellipse([880, 150, 1000, 270], fill=(240, 240, 255, 255))
    sky.alpha_composite(glow(moon, 30))
    sea = water(hz, "#10304f", "#02060e")
    sea.alpha_composite(reflect(sky, hz, tint=(5, 15, 30), seed=5))
    back = sky; back.alpha_composite(sea)
    # casa sobre pilotes con muelle
    h = layer(); d = ImageDraw.Draw(h)
    c = (6, 8, 14, 255)
    d.rectangle([1200, 470, 1900, 720], fill=c)
    d.polygon([(1150, 480), (1550, 330), (1950, 480)], fill=c)
    for x in range(1210, 1900, 90):
        d.rectangle([x, 720, x + 16, 900], fill=c)
    d.rectangle([700, 760, 1900, 785], fill=c)
    for x in range(720, 1200, 120):
        d.rectangle([x, 785, x + 12, 900], fill=c)
    win = layer(); wd = ImageDraw.Draw(win)
    for (x, y) in ((1280, 540), (1460, 540), (1700, 540)):
        wd.rectangle([x, y, x + 110, y + 90], fill=hexc("#ffcf7a", 230))
    h.alpha_composite(glow(win, 18, 1.0))
    # barco
    d.polygon([(760, 840), (1120, 840), (1080, 890), (800, 890)], fill=c)
    d.rectangle([880, 790, 1000, 840], fill=c)
    palms = palms_layer(31, [(150, LH + 40), (2050, LH + 40)], (3, 4, 8, 255), (750, 950))
    return [(back, 0.2), (h, 0.55), (palms, 1.0)]


def sc_disco():
    bg = tech_bg(41, "#0b1220", "#020408", "#22d3c5")
    lamp = layer(); ld = ImageDraw.Draw(lamp)
    ld.polygon([(LW // 2 - 120, 0), (LW // 2 + 120, 0), (LW // 2 + 700, LH), (LW // 2 - 700, LH)], fill=(255, 230, 180, 50))
    bg.alpha_composite(lamp.filter(ImageFilter.GaussianBlur(50)))
    obj = layer(); d = ImageDraw.Draw(obj)
    d.rectangle([0, 820, LW, LH], fill=(22, 16, 14, 255))          # mesa
    cx, cy = LW // 2, 760
    d.rounded_rectangle([cx - 300, cy - 190, cx + 300, cy + 60], 26, fill=(40, 42, 50, 255), outline=(120, 125, 140, 255), width=4)
    d.rounded_rectangle([cx - 260, cy - 150, cx + 260, cy + 20], 16, fill=(28, 30, 36, 255))
    d.ellipse([cx + 190, cy - 40, cx + 220, cy - 10], fill=hexc("#3ddc84"))
    d.line([(cx + 300, cy - 30), (cx + 700, cy + 120)], fill=(20, 20, 20, 255), width=10)
    # bolsa abierta
    d.polygon([(260, 840), (720, 820), (760, 1100), (220, 1120)], fill=(30, 24, 20, 255))
    d.polygon([(260, 840), (720, 820), (640, 700), (330, 720)], fill=(44, 34, 28, 255))
    obj = glow(obj, 6, 0.3)
    return [(bg, 0.2), (obj, 0.8)]


def sc_club():
    bg = vgrad(LW, LH, [(0, "#0a0214"), (1, "#14041e")])
    beams = layer(); bd = ImageDraw.Draw(beams)
    rng = random.Random(8)
    for k in range(9):
        x = 150 + k * 250
        c = rng.choice(["#ff3d8b", "#22f3ff", "#a26bff", "#ffd166"])
        bd.polygon([(x, 0), (x + 30, 0), (x + rng.randint(-500, 500) + 200, LH), (x + rng.randint(-500, 500) - 200, LH)], fill=hexc(c, 55))
    bg.alpha_composite(beams.filter(ImageFilter.GaussianBlur(14)))
    stage = layer(); sd = ImageDraw.Draw(stage)
    sd.rectangle([0, 0, LW, 70], fill=(5, 2, 8, 255))
    sd.text((LW // 2, 260), "THE CLUB", font=font("InterDisplay-Black.otf", 150), fill=hexc("#ff3d8b"), anchor="mm")
    sd.rectangle([LW // 2 - 520, 360, LW // 2 + 520, 372], fill=hexc("#22f3ff"))
    stage = glow(stage, 20, 1.0)
    crowd = layer(); cd = ImageDraw.Draw(crowd)
    for i in range(60):
        x = rng.randint(-50, LW + 50)
        y = rng.randint(820, 1000)
        s = rng.uniform(0.7, 1.2)
        cd.ellipse([x - 40 * s, y - 150 * s, x + 40 * s, y - 60 * s], fill=(4, 2, 8, 255))
        cd.rounded_rectangle([x - 85 * s, y - 70 * s, x + 85 * s, y + 300], int(40 * s), fill=(4, 2, 8, 255))
        if rng.random() < 0.3:  # brazos arriba
            cd.line([(x + 60 * s, y - 40 * s), (x + 110 * s, y - 220 * s)], fill=(4, 2, 8, 255), width=int(24 * s))
    return [(bg, 0.15), (stage, 0.4), (crowd, 1.0)]


def sc_studio():
    bg = vgrad(LW, LH, [(0, "#120a1e"), (1, "#05030a")])
    wall = layer(); wd = ImageDraw.Draw(wall)
    for x in range(0, LW, 120):        # paneles acusticos
        for y in range(0, 760, 120):
            wd.rectangle([x + 6, y + 6, x + 114, y + 114], fill=(26, 18, 38, 255))
    sign = layer(); sd = ImageDraw.Draw(sign)
    sd.text((LW // 2, 300), "ONLY RAW", font=font("InterDisplay-Black.otf", 170), fill=hexc("#a26bff"), anchor="mm")
    sd.text((LW // 2, 430), "RECORDS", font=font("Inter-Bold.otf", 64), fill=hexc("#ffffff", 220), anchor="mm")
    wall.alpha_composite(glow(sign, 22, 1.2))
    desk = layer(); d = ImageDraw.Draw(desk)
    d.polygon([(200, 820), (2000, 820), (2208, LH), (0, LH)], fill=(14, 12, 20, 255))
    for i in range(40):
        x = 320 + i * 40
        d.rectangle([x, 860, x + 18, 1000], fill=(40, 36, 52, 255))
        y = 880 + (i * 37) % 100
        d.rectangle([x - 4, y, x + 22, y + 14], fill=hexc(random.Random(i).choice(["#ff3d8b", "#22d3c5", "#ffd166"])))
    for x in (120, 1880):                 # monitores de estudio
        d.rounded_rectangle([x, 560, x + 210, 840], 18, fill=(10, 9, 14, 255))
        d.ellipse([x + 45, 650, x + 165, 770], fill=(30, 28, 40, 255))
    return [(bg, 0.1), (wall, 0.35), (desk, 0.9)]


def sc_street():
    hz = 700
    sky = vgrad(LW, LH, [(0, "#3b8fd6"), (1, "#bfe3f5")])
    b, w = skyline(hz, 77, (205, 190, 175, 255), hmin=200, hmax=420, win_p=0.5, win_cols=("#7aa5c9",), spire=0.0)
    back = sky; back.alpha_composite(b); back.alpha_composite(w)
    st = layer(); d = ImageDraw.Draw(st)
    d.rectangle([0, hz, LW, LH], fill=(70, 70, 76, 255))
    d.rectangle([0, hz, LW, hz + 40], fill=(150, 145, 140, 255))
    for x in range(0, LW, 200):
        d.rectangle([x, 960, x + 110, 975], fill=(235, 235, 235, 255))
    # estudio
    d.rectangle([700, 330, 1500, hz], fill=(40, 30, 50, 255))
    d.text((1100, 400), "ONLY RAW", font=font("InterDisplay-Black.otf", 90), fill=hexc("#a26bff"), anchor="mm")
    d.rectangle([1020, 520, 1180, hz], fill=(15, 12, 20, 255))
    suv = layer(); sd = ImageDraw.Draw(suv)
    for x0 in (250, 1250):
        y0 = 940
        c = (8, 8, 10, 255)
        sd.rounded_rectangle([x0, y0 - 230, x0 + 700, y0 - 20], 30, fill=c)
        sd.polygon([(x0 + 60, y0 - 230), (x0 + 560, y0 - 230), (x0 + 520, y0 - 340), (x0 + 110, y0 - 340)], fill=c)
        sd.rectangle([x0 + 140, y0 - 320, x0 + 300, y0 - 240], fill=(40, 46, 60, 255))
        sd.rectangle([x0 + 330, y0 - 320, x0 + 500, y0 - 240], fill=(40, 46, 60, 255))
        for wx in (x0 + 140, x0 + 560):
            sd.ellipse([wx - 70, y0 - 90, wx + 70, y0 + 50], fill=(20, 20, 22, 255))
            sd.ellipse([wx - 30, y0 - 50, wx + 30, y0 + 10], fill=(120, 120, 130, 255))
    return [(back, 0.15), (st, 0.45), (suv, 1.0)]


def sc_team():
    return [(tech_bg(51, "#120a26", "#030208", "#ff3d8b"), 0.25)]


def sc_vault():
    bg = vgrad(LW, LH, [(0, "#0c1014"), (1, "#020304")])
    v = layer(); d = ImageDraw.Draw(v)
    cx, cy = LW // 2, LH // 2 - 20
    d.rectangle([0, 0, LW, LH], fill=(18, 20, 24, 255))
    d.ellipse([cx - 470, cy - 470, cx + 470, cy + 470], fill=(6, 7, 9, 255), outline=(90, 96, 104, 255), width=30)
    # puerta abierta a un lado
    d.ellipse([cx + 420, cy - 450, cx + 760, cy + 450], fill=(70, 74, 82, 255), outline=(120, 126, 134, 255), width=12)
    for k in range(6):
        a = k / 6 * 2 * math.pi
        d.line([(cx + 590, cy), (cx + 590 + math.cos(a) * 110, cy + math.sin(a) * 280)], fill=(150, 156, 164, 255), width=14)
    # mesa vacia dentro
    d.polygon([(cx - 250, cy + 170), (cx + 250, cy + 170), (cx + 320, cy + 260), (cx - 320, cy + 260)], fill=(40, 34, 30, 255))
    d.rectangle([cx - 300, cy + 260, cx - 280, cy + 420], fill=(30, 26, 22, 255))
    d.rectangle([cx + 280, cy + 260, cx + 300, cy + 420], fill=(30, 26, 22, 255))
    light = layer(); ld = ImageDraw.Draw(light)
    ld.polygon([(cx - 40, cy - 470), (cx + 40, cy - 470), (cx + 330, cy + 260), (cx - 330, cy + 260)], fill=(255, 240, 200, 50))
    v.alpha_composite(light.filter(ImageFilter.GaussianBlur(30)))
    return [(bg, 0.1), (v, 0.6)]


def sc_port_night():
    hz = 780
    sky = vgrad(LW, LH, [(0, "#04040e"), (0.7, "#1a1030"), (1, "#2a1440")])
    stars(sky, 200, 600, 61)
    sea = water(hz, "#1a1030", "#03020a")
    cr = layer(); cd = ImageDraw.Draw(cr)
    c = (5, 5, 10, 255)
    for cx in (300, 1700):
        cd.rectangle([cx - 90, hz - 420, cx - 70, hz], fill=c)
        cd.rectangle([cx + 70, hz - 420, cx + 90, hz], fill=c)
        cd.rectangle([cx - 260, hz - 440, cx + 380, hz - 410], fill=c)
        cd.ellipse([cx + 360, hz - 450, cx + 380, hz - 430], fill=hexc("#ff4d4d"))
    # escenario del concierto con focos
    stg = layer(); sd = ImageDraw.Draw(stg)
    sd.rectangle([800, hz - 260, 1400, hz], fill=(12, 8, 20, 255))
    sd.rectangle([780, hz - 280, 1420, hz - 250], fill=(30, 20, 40, 255))
    beams = layer(); bd = ImageDraw.Draw(beams)
    for i, col in enumerate(["#ff3d8b", "#22f3ff", "#ffd166", "#a26bff", "#ff3d8b"]):
        x = 850 + i * 125
        bd.polygon([(x, hz - 270), (x + 20, hz - 270), (x - 400 + i * 200 + 300, 0), (x - 400 + i * 200 + 100, 0)], fill=hexc(col, 70))
    stg.alpha_composite(beams.filter(ImageFilter.GaussianBlur(10)))
    sd2 = ImageDraw.Draw(stg)
    sd2.text((1100, hz - 180), "REAL DIMEZ · LIVE", font=font("InterDisplay-Black.otf", 54), fill=hexc("#ff3d8b"), anchor="mm")
    stg = glow(stg, 8, 0.8)
    full = sky.copy(); full.alpha_composite(cr); full.alpha_composite(stg)
    sea.alpha_composite(reflect(full, hz, tint=(20, 5, 40), seed=9))
    mid = layer(); mid.alpha_composite(cr); mid.alpha_composite(stg); mid.alpha_composite(sea)
    cont = layer(); kd = ImageDraw.Draw(cont)
    rng = random.Random(3)
    for x in range(-40, LW, 260):
        for lvl in range(rng.randint(1, 3)):
            kd.rectangle([x, LH - 120 - 110 * (lvl + 1), x + 250, LH - 120 - 110 * lvl - 4], fill=(10 + lvl * 4, 10, 18, 255))
    kd.rectangle([0, LH - 120, LW, LH], fill=(6, 6, 10, 255))
    return [(sky, 0.15), (mid, 0.45), (cont, 1.0)]


def sc_black():
    bg = Image.new("RGBA", (LW, LH), (2, 2, 4, 255))
    return [(bg, 0.1)]


for _k, _f in list(globals().items()):
    if _k.startswith("sc_"):
        arte.SCENE_ART[_k[3:]] = _f
for _key in PERSONAJES:
    arte.SCENE_ART["card_" + _key] = (lambda k=_key: card_scene(k))
