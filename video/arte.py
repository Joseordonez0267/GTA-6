# -*- coding: utf-8 -*-
"""Ilustraciones originales generadas por codigo (PIL + numpy).

Cada funcion devuelve una lista de capas [(imagen RGBA, profundidad)], de la
mas lejana a la mas cercana. La profundidad (0..1) controla el paralaje en el
montaje. Ninguna imagen proviene de material oficial del juego.
"""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

W, H = 1920, 1080
LW, LH = 2208, 1242          # capas 15 % mas grandes que el cuadro, para mover la camara
FONT_DIR = "/usr/share/fonts/opentype/inter/"


def font(name, size):
    return ImageFont.truetype(FONT_DIR + name, size)


# ------------------------------------------------------------------ utilidades
def hexc(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def vgrad(w, h, stops):
    """Degradado vertical. stops = [(pos 0..1, '#rrggbb'), ...]"""
    y = np.linspace(0, 1, h)[:, None]
    out = np.zeros((h, w, 3), np.float32)
    pos = [s[0] for s in stops]
    cols = [np.array(hexc(s[1])[:3], np.float32) for s in stops]
    for c in range(3):
        out[..., c] = np.interp(y, pos, [col[c] for col in cols])
    img = Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGB").convert("RGBA")
    return img


def layer():
    return Image.new("RGBA", (LW, LH), (0, 0, 0, 0))


def glow(img, radius=18, strength=1.0):
    """Anade resplandor a una capa RGBA."""
    g = img.filter(ImageFilter.GaussianBlur(radius))
    if strength != 1.0:
        a = np.asarray(g).astype(np.float32)
        a[..., 3] = np.clip(a[..., 3] * strength, 0, 255)
        g = Image.fromarray(a.astype(np.uint8))
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.alpha_composite(g)
    out.alpha_composite(img)
    return out


def noise_tex(w, h, scale, seed, octaves=4):
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        sw, sh = max(2, int(w / scale * 2 ** o)), max(2, int(h / scale * 2 ** o))
        n = rng.random((sh, sw)).astype(np.float32)
        n = np.asarray(Image.fromarray((n * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)).astype(np.float32) / 255
        acc += n * amp
        tot += amp
        amp *= 0.5
    return acc / tot


def sun(lay, cx, cy, r, top="#ffe86b", bot="#ff3d8b", stripes=True):
    s = Image.new("RGBA", (2 * r, 2 * r), (0, 0, 0, 0))
    g = vgrad(2 * r, 2 * r, [(0, top), (1, bot)])
    m = Image.new("L", (2 * r, 2 * r), 0)
    d = ImageDraw.Draw(m)
    d.ellipse([0, 0, 2 * r - 1, 2 * r - 1], fill=255)
    if stripes:
        y = int(r * 1.0)
        gap, th = int(r * 0.07), int(r * 0.025)
        while y < 2 * r:
            d.rectangle([0, y, 2 * r, y + th], fill=0)
            y += gap
            th = int(th * 1.25) + 1
    s.paste(g, (0, 0), m)
    halo = Image.new("RGBA", lay.size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    hd.ellipse([cx - r * 1.5, cy - r * 1.5, cx + r * 1.5, cy + r * 1.5], fill=hexc(bot, 110))
    halo = halo.filter(ImageFilter.GaussianBlur(r * 0.5))
    lay.alpha_composite(halo)
    lay.alpha_composite(s, (cx - r, cy - r))


def stars(lay, n, ymax, seed, color=(255, 255, 255)):
    rng = random.Random(seed)
    d = ImageDraw.Draw(lay)
    for _ in range(n):
        x, y = rng.randrange(LW), rng.randrange(int(ymax))
        a = rng.randint(60, 220)
        s = rng.choice([1, 1, 1, 2])
        d.ellipse([x, y, x + s, y + s], fill=color + (a,))


def skyline(base_y, seed, color, hmin=120, hmax=520, wmin=50, wmax=150, win_p=0.35,
            win_cols=("#ffd27a", "#ffefc2", "#7ef9ff", "#ff7ad9"), x0=-20, x1=None, spire=0.25):
    """Devuelve (capa edificios, capa ventanas)."""
    rng = random.Random(seed)
    b, w = layer(), layer()
    db, dw = ImageDraw.Draw(b), ImageDraw.Draw(w)
    x = x0
    x1 = LW + 20 if x1 is None else x1
    while x < x1:
        bw = rng.randint(wmin, wmax)
        # mas altos en el centro
        center = 1 - abs((x - LW * 0.55) / (LW * 0.6))
        bh = int(rng.uniform(hmin, hmax) * (0.55 + 0.6 * max(0, center)))
        top = base_y - bh
        db.rectangle([x, top, x + bw, base_y + 400], fill=color)
        r = rng.random()
        if r < spire:
            db.rectangle([x + bw // 2 - 3, top - rng.randint(40, 120), x + bw // 2 + 3, top], fill=color)
        elif r < spire + 0.2:
            db.rectangle([x + bw * 0.15, top - 30, x + bw * 0.85, top], fill=color)
            db.rectangle([x + bw * 0.3, top - 55, x + bw * 0.7, top - 30], fill=color)
        elif r < spire + 0.3:
            db.polygon([(x, top), (x + bw, top), (x + bw // 2, top - bw * 0.6)], fill=color)
        # ventanas
        cols = rng.choice(win_cols)
        for wy in range(top + 14, base_y - 6, 18):
            for wx in range(x + 8, x + bw - 8, 14):
                if rng.random() < win_p:
                    c = hexc(cols, rng.randint(150, 255))
                    dw.rectangle([wx, wy, wx + 6, wy + 9], fill=c)
        x += bw + rng.randint(-10, 12)
    return b, w


def palm(d, x, y, h, lean, color, rng, fronds=9, scale=1.0):
    """Palmera silueta. (x,y)=base"""
    pts = []
    n = 40
    tx, ty = x + lean, y - h
    cx, cy = x + lean * 0.2, y - h * 0.5
    for i in range(n + 1):
        t = i / n
        px = (1 - t) ** 2 * x + 2 * (1 - t) * t * cx + t * t * tx
        py = (1 - t) ** 2 * y + 2 * (1 - t) * t * cy + t * t * ty
        pts.append((px, py))
    for i, (px, py) in enumerate(pts):
        r = (14 - 7 * i / n) * scale
        d.ellipse([px - r, py - r, px + r, py + r], fill=color)
    # hojas
    for k in range(fronds):
        ang = -math.pi / 2 + (k / (fronds - 1) - 0.5) * math.pi * 1.9 + rng.uniform(-0.15, 0.15)
        L = rng.uniform(0.75, 1.05) * h * 0.42
        droop = rng.uniform(0.6, 1.1)
        prev = (tx, ty)
        segs = 18
        for s in range(1, segs + 1):
            t = s / segs
            px = tx + math.cos(ang) * L * t
            py = ty + math.sin(ang) * L * t + droop * L * 0.9 * t * t
            wdt = max(1, (10 * (1 - t) + 2) * scale)
            d.line([prev, (px, py)], fill=color, width=int(wdt))
            # foliolos
            if s % 2 == 0 and t < 0.95:
                ll = L * 0.16 * (1 - t * 0.6)
                for sg in (-1, 1):
                    a2 = ang + sg * 1.1 + 0.5
                    d.line([(px, py), (px + math.cos(a2) * ll, py + math.sin(a2) * ll + ll * 0.6)], fill=color, width=max(1, int(3 * scale)))
            prev = (px, py)
    d.ellipse([tx - 12 * scale, ty - 8 * scale, tx + 12 * scale, ty + 14 * scale], fill=color)


def palms_layer(seed, positions, color, hrange=(380, 620)):
    lay = layer()
    d = ImageDraw.Draw(lay)
    rng = random.Random(seed)
    for (x, y) in positions:
        h = rng.uniform(*hrange)
        palm(d, x, y, h, rng.uniform(-120, 120), color, rng, scale=h / 500)
    return lay


def reflect(src, horizon, tint=(20, 10, 40), fade=0.85, wobble=6, seed=0):
    """Reflejo en el agua de todo lo que hay sobre el horizonte."""
    a = np.asarray(src).astype(np.float32)
    top = a[:horizon][::-1]
    hh = min(top.shape[0], LH - horizon)
    ref = top[:hh].copy()
    rng = np.random.default_rng(seed)
    for yy in range(hh):
        sh = int(math.sin(yy * 0.35 + rng.random()) * wobble * (0.3 + yy / hh))
        ref[yy] = np.roll(ref[yy], sh, axis=0)
    k = np.linspace(fade, 0.15, hh)[:, None]
    ref[..., :3] = ref[..., :3] * 0.55 + np.array(tint) * 0.45
    ref[..., 3] *= k
    out = np.zeros_like(a)
    out[horizon:horizon + hh] = ref
    # lineas de brillo horizontales
    img = Image.fromarray(out.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    r2 = random.Random(seed)
    for _ in range(260):
        y = r2.randint(horizon + 4, LH - 1)
        x = r2.randint(0, LW)
        L = r2.randint(20, 160)
        d.line([(x, y), (x + L, y)], fill=(255, 220, 255, r2.randint(15, 60)), width=1)
    return img


def water(horizon, top="#2a1655", bot="#07051a"):
    lay = layer()
    g = vgrad(LW, LH - horizon, [(0, top), (1, bot)])
    lay.paste(g, (0, horizon))
    return lay


def hills(seed, base_y, amp, color, freq=0.004, rough=0.3):
    rng = np.random.default_rng(seed)
    xs = np.arange(LW + 1)
    ph = rng.random(4) * 10
    y = (np.sin(xs * freq + ph[0]) * 0.6 + np.sin(xs * freq * 2.3 + ph[1]) * 0.3 * rough * 2 +
         np.sin(xs * freq * 5.1 + ph[2]) * 0.1 * rough * 3)
    y = base_y - (y + 1) * amp / 2
    lay = layer()
    d = ImageDraw.Draw(lay)
    d.polygon([(0, LH)] + [(int(x), float(yy)) for x, yy in zip(xs, y)] + [(LW, LH)], fill=color)
    return lay, y


def fog(y0, y1, color=(255, 230, 255), alpha=120):
    lay = layer()
    a = np.zeros((LH, LW), np.float32)
    yy = np.arange(LH)[:, None]
    mid, half = (y0 + y1) / 2, (y1 - y0) / 2
    a[:] = np.clip(1 - np.abs(yy - mid) / half, 0, 1) ** 1.5 * alpha
    n = noise_tex(LW, LH, 400, 7)
    a *= 0.5 + n
    arr = np.zeros((LH, LW, 4), np.uint8)
    arr[..., :3] = color
    arr[..., 3] = a.clip(0, 255)
    return Image.fromarray(arr)


def grid_floor(lay, horizon, color="#ff3d8b", alpha=160, spacing=90):
    d = ImageDraw.Draw(lay)
    c = hexc(color, alpha)
    vx = LW / 2
    for i in range(-30, 31):
        x = vx + i * spacing * 3
        d.line([(vx + i * 6, horizon), (x, LH)], fill=c, width=2)
    y, k = horizon + 4, 4
    while y < LH:
        d.line([(0, y), (LW, y)], fill=c, width=2)
        k *= 1.35
        y += k


def vignette_mask():
    y, x = np.ogrid[:H, :W]
    r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    v = np.clip((r - 0.65) / 0.75, 0, 1) ** 1.6 * 200
    arr = np.zeros((H, W, 4), np.uint8)
    arr[..., 3] = v.astype(np.uint8)
    return Image.fromarray(arr)


def tech_bg(seed=0, c1="#160b33", c2="#05030f", accent="#ff3d8b"):
    """Fondo oscuro con rejilla y brillos, para los graficos."""
    bg = vgrad(LW, LH, [(0, c1), (1, c2)])
    lay = layer()
    d = ImageDraw.Draw(lay)
    for x in range(0, LW, 69):
        d.line([(x, 0), (x, LH)], fill=(255, 255, 255, 12))
    for y in range(0, LH, 69):
        d.line([(0, y), (LW, y)], fill=(255, 255, 255, 12))
    bg.alpha_composite(lay)
    blobs = layer()
    bd = ImageDraw.Draw(blobs)
    rng = random.Random(seed)
    for col in (accent, "#22d3c5", "#6b2fbf"):
        x, y, r = rng.randint(0, LW), rng.randint(0, LH), rng.randint(300, 600)
        bd.ellipse([x - r, y - r, x + r, y + r], fill=hexc(col, 70))
    blobs = blobs.filter(ImageFilter.GaussianBlur(160))
    bg.alpha_composite(blobs)
    return bg


# ------------------------------------------------------------------ escenas
def sc_sunset_city():
    hz = 840
    sky = vgrad(LW, LH, [(0, "#1b0b3a"), (0.35, "#5a1e6e"), (0.62, "#e8457c"), (0.78, "#ffb15c"), (1, "#ffb15c")])
    stars(sky, 220, 380, 1)
    sun(sky, LW // 2, 640, 300)
    far_b, far_w = skyline(hz, 11, (110, 40, 100, 255), hmin=80, hmax=300, wmin=40, wmax=90, win_p=0.05)
    near_b, near_w = skyline(hz, 12, (35, 10, 45, 255), hmin=120, hmax=560, win_p=0.14, spire=0.35)
    city = layer()
    city.alpha_composite(far_b); city.alpha_composite(far_w)
    city.alpha_composite(near_b); city.alpha_composite(glow(near_w, 6))
    sea = water(hz, "#7a2c74", "#120624")
    full = sky.copy(); full.alpha_composite(city)
    sea.alpha_composite(reflect(full, hz, seed=3))
    back = sky
    mid = layer(); mid.alpha_composite(city); mid.alpha_composite(sea)
    palms = palms_layer(5, [(120, LH + 40), (330, LH + 80), (1900, LH + 60), (2120, LH + 30)], (15, 4, 20, 255), (700, 1000))
    return [(back, 0.15), (mid, 0.45), (palms, 1.0)]


def sc_title():
    layers = sc_sunset_city()
    return layers


def sc_retro_city():
    hz = 860
    sky = vgrad(LW, LH, [(0, "#0d2a4a"), (0.5, "#3f7fb5"), (0.8, "#f2c38b"), (1, "#f7d9a8")])
    sun(sky, 1500, 560, 170, top="#fff7d6", bot="#ffb15c", stripes=False)
    hl, _ = hills(4, hz - 10, 260, (58, 78, 110, 255), freq=0.003)
    b, w = skyline(hz, 21, (40, 50, 72, 255), hmin=120, hmax=480, win_p=0.06, win_cols=("#ffe6a8",))
    mid = layer(); mid.alpha_composite(hl); mid.alpha_composite(b); mid.alpha_composite(w)
    ground = layer()
    d = ImageDraw.Draw(ground)
    d.rectangle([0, hz, LW, LH], fill=(46, 52, 64, 255))
    # autopista elevada
    d.rectangle([0, hz + 60, LW, hz + 95], fill=(28, 30, 38, 255))
    for x in range(40, LW, 260):
        d.rectangle([x, hz + 95, x + 30, LH], fill=(28, 30, 38, 255))
    palms = palms_layer(8, [(250, LH + 30), (1980, LH + 60)], (20, 26, 34, 255), (650, 900))
    # tono "sepia 2013"
    return [(sky, 0.15), (mid, 0.45), (ground, 0.7), (palms, 1.0)]


def sc_leak():
    bg = vgrad(LW, LH, [(0, "#05060a"), (1, "#0b0f18")])
    rng = random.Random(3)
    d = ImageDraw.Draw(bg)
    f = font("Inter-Medium.otf", 22)
    chars = "0123456789ABCDEF"
    for row in range(0, LH, 30):
        line = " ".join("".join(rng.choice(chars) for _ in range(4)) for _ in range(40))
        d.text((10, row), line, font=f, fill=(40, 255, 140, rng.randint(25, 70)))
    mid = layer()
    md = ImageDraw.Draw(mid)
    # ventanas de "video" difuminadas
    for i in range(14):
        x, y = rng.randint(80, LW - 520), rng.randint(60, LH - 360)
        w_, h_ = rng.randint(320, 460), rng.randint(180, 260)
        md.rectangle([x, y, x + w_, y + h_], fill=(18, 22, 34, 235), outline=(60, 255, 160, 120), width=2)
        md.rectangle([x, y, x + w_, y + 26], fill=(30, 40, 56, 255))
        md.text((x + 10, y + 3), f"clip_{rng.randint(10,99)}.mp4", font=font("Inter-Medium.otf", 18), fill=(150, 255, 200, 200))
        for k in range(5):
            yy = y + 40 + k * (h_ - 50) // 5
            md.rectangle([x + 12, yy, x + 12 + rng.randint(60, w_ - 30), yy + 10], fill=(60, 255, 160, rng.randint(20, 60)))
    mid = glow(mid, 10, 0.6)
    front = layer()
    fd = ImageDraw.Draw(front)
    for _ in range(40):  # bloques de glitch
        x, y = rng.randint(0, LW), rng.randint(0, LH)
        fd.rectangle([x, y, x + rng.randint(80, 500), y + rng.randint(3, 16)],
                     fill=rng.choice([(255, 0, 90, 90), (0, 255, 255, 80), (255, 255, 255, 50)]))
    return [(bg, 0.1), (mid, 0.5), (front, 1.0)]


def sc_views():
    bg = tech_bg(5, "#2a0a12", "#07030a", "#ff2a2a")
    return [(bg, 0.3)]


def sc_timeline():
    return [(tech_bg(8), 0.3)]


def sc_map():
    bg = vgrad(LW, LH, [(0, "#06233f"), (1, "#031426")])
    d = ImageDraw.Draw(bg)
    for x in range(0, LW, 80):
        d.line([(x, 0), (x, LH)], fill=(80, 200, 255, 18))
    for y in range(0, LH, 80):
        d.line([(0, y), (LW, y)], fill=(80, 200, 255, 18))
    return [(bg, 0.3)]


def sc_neon_city():
    hz = 860
    sky = vgrad(LW, LH, [(0, "#05021a"), (0.55, "#2a0b4f"), (0.85, "#7a1a6e"), (1, "#7a1a6e")])
    stars(sky, 300, 600, 9)
    moon = layer(); md = ImageDraw.Draw(moon)
    md.ellipse([1650, 140, 1790, 280], fill=(255, 235, 250, 255))
    sky.alpha_composite(glow(moon, 30))
    far_b, far_w = skyline(hz, 31, (40, 14, 70, 255), hmin=100, hmax=360, win_p=0.25)
    near_b, near_w = skyline(hz, 32, (14, 6, 28, 255), hmin=180, hmax=650, win_p=0.45, spire=0.4,
                             win_cols=("#ff4fd8", "#3ff3ff", "#ffd27a", "#b47cff"))
    # letreros neon
    signs = layer(); sd = ImageDraw.Draw(signs)
    rng = random.Random(4)
    for _ in range(18):
        x, y = rng.randint(50, LW - 200), rng.randint(hz - 520, hz - 120)
        c = hexc(rng.choice(["#ff3d8b", "#22f3ff", "#ffe066", "#a26bff"]))
        if rng.random() < 0.5:
            sd.rectangle([x, y, x + rng.randint(60, 160), y + rng.randint(10, 18)], fill=c)
        else:
            sd.rectangle([x, y, x + 10, y + rng.randint(80, 160)], fill=c)
    city = layer()
    city.alpha_composite(far_b); city.alpha_composite(glow(far_w, 5))
    city.alpha_composite(near_b); city.alpha_composite(glow(near_w, 6)); city.alpha_composite(glow(signs, 16))
    sea = water(hz, "#2c0b52", "#05020f")
    full = sky.copy(); full.alpha_composite(city)
    sea.alpha_composite(reflect(full, hz, tint=(30, 0, 60), seed=6))
    mid = layer(); mid.alpha_composite(city); mid.alpha_composite(sea)
    palms = palms_layer(7, [(90, LH + 40), (2050, LH + 70)], (5, 2, 10, 255), (800, 1050))
    return [(sky, 0.15), (mid, 0.5), (palms, 1.0)]


def sc_keys():
    hz = 640
    sky = vgrad(LW, LH, [(0, "#2a8fd6"), (0.5, "#8fd3f5"), (0.55, "#bfe8f7"), (1, "#bfe8f7")])
    # nubes
    cl = layer(); cd = ImageDraw.Draw(cl)
    rng = random.Random(2)
    for _ in range(26):
        x, y = rng.randint(-100, LW), rng.randint(60, 420)
        for k in range(6):
            r = rng.randint(40, 90)
            cd.ellipse([x + k * 50 - r, y - r * 0.6, x + k * 50 + r, y + r * 0.6], fill=(255, 255, 255, 170))
    sky.alpha_composite(cl.filter(ImageFilter.GaussianBlur(12)))
    sea = water(hz, "#22d3c5", "#0a6b8f")
    sd = ImageDraw.Draw(sea)
    for _ in range(500):
        y = rng.randint(hz, LH); x = rng.randint(0, LW)
        sd.line([(x, y), (x + rng.randint(10, 80) * (y - hz) / 300, y)], fill=(255, 255, 255, rng.randint(30, 90)), width=2)
    # islas
    isl = layer(); idr = ImageDraw.Draw(isl)
    for (x, w_) in [(150, 360), (980, 260), (1700, 420)]:
        idr.ellipse([x, hz - 26, x + w_, hz + 22], fill=(242, 226, 180, 255))
        idr.ellipse([x + 20, hz - 48, x + w_ - 30, hz + 4], fill=(40, 120, 70, 255))
    # puente largo
    br = layer(); bd = ImageDraw.Draw(br)
    y0 = hz + 140
    bd.rectangle([0, y0, LW, y0 + 26], fill=(225, 225, 220, 255))
    bd.rectangle([0, y0 + 26, LW, y0 + 34], fill=(150, 160, 165, 255))
    for x in range(30, LW, 150):
        bd.rectangle([x, y0 + 34, x + 22, LH], fill=(190, 195, 195, 255))
    for x in range(0, LW, 70):
        bd.line([(x, y0 - 8), (x, y0)], fill=(140, 140, 140, 255), width=3)
    bd.line([(0, y0 - 8), (LW, y0 - 8)], fill=(140, 140, 140, 255), width=3)
    palms = palms_layer(3, [(1960, LH + 50), (2140, LH + 120)], (20, 60, 40, 255), (650, 850))
    back = sky; back.alpha_composite(sea); back.alpha_composite(isl)
    return [(back, 0.2), (br, 0.6), (palms, 1.0)]


def sc_swamp():
    hz = 700
    sky = vgrad(LW, LH, [(0, "#3b4a3a"), (0.6, "#c9b98a"), (1, "#c9b98a")])
    sun(sky, 700, 520, 130, top="#fff4c8", bot="#ffcf7a", stripes=False)
    wt = water(hz, "#6b6a4a", "#1f2a1c")
    far = layer(); fd = ImageDraw.Draw(far)
    rng = random.Random(5)
    for x in range(-50, LW + 50, 22):  # linea de arboles lejana
        h_ = rng.randint(60, 180)
        fd.ellipse([x - 40, hz - h_, x + 40, hz - h_ + 120], fill=(70, 88, 66, 255))
    fd.rectangle([0, hz - 40, LW, hz], fill=(70, 88, 66, 255))
    full = sky.copy(); full.alpha_composite(far)
    wt.alpha_composite(reflect(full, hz, tint=(40, 50, 30), seed=2, wobble=3))
    back = sky; back.alpha_composite(far); back.alpha_composite(wt)
    back.alpha_composite(fog(hz - 160, hz + 120, (240, 235, 210), 150))
    # manglares cercanos
    mg = layer(); md = ImageDraw.Draw(mg)
    col = (22, 30, 20, 255)
    for cx in (180, 520, 1850, 2100):
        base = LH - 120
        md.ellipse([cx - 260, 40, cx + 260, 520], fill=col)
        md.ellipse([cx - 360, 180, cx + 120, 600], fill=col)
        for k in range(14):
            x = cx + rng.randint(-220, 220)
            md.line([(cx + rng.randint(-60, 60), 450), (x, base + rng.randint(0, 120))], fill=col, width=rng.randint(5, 14))
    # lancha de aire
    boat = layer(); bd = ImageDraw.Draw(boat)
    bx, by = 1200, hz + 230
    bd.polygon([(bx - 140, by), (bx + 160, by), (bx + 120, by + 30), (bx - 120, by + 30)], fill=(30, 30, 28, 255))
    bd.ellipse([bx - 120, by - 120, bx - 30, by - 10], outline=(30, 30, 28, 255), width=8)
    bd.rectangle([bx - 20, by - 50, bx + 30, by], fill=(30, 30, 28, 255))
    bd.line([(bx + 160, by + 26), (bx + 600, by + 32)], fill=(255, 255, 255, 120), width=3)
    return [(back, 0.2), (boat, 0.5), (mg, 1.0)]


def sc_port():
    hz = 780
    sky = vgrad(LW, LH, [(0, "#2b3550"), (0.6, "#c7735a"), (1, "#e39b6a")])
    sea = water(hz, "#3b3a50", "#121420")
    cr = layer(); cd = ImageDraw.Draw(cr)
    col = (28, 26, 34, 255)
    for cx in (500, 1100, 1650):  # gruas portuarias
        cd.rectangle([cx - 90, hz - 420, cx - 70, hz], fill=col)
        cd.rectangle([cx + 70, hz - 420, cx + 90, hz], fill=col)
        cd.rectangle([cx - 260, hz - 440, cx + 380, hz - 410], fill=col)
        cd.line([(cx - 80, hz - 420), (cx + 80, hz - 200)], fill=col, width=8)
        cd.line([(cx + 80, hz - 420), (cx - 80, hz - 200)], fill=col, width=8)
        cd.rectangle([cx + 200, hz - 410, cx + 230, hz - 300], fill=col)
    rng = random.Random(9)
    for x in range(0, LW, 120):  # contenedores
        for lvl in range(rng.randint(1, 4)):
            c = rng.choice([(140, 50, 40), (40, 80, 120), (150, 120, 40), (60, 100, 70)])
            cd.rectangle([x, hz - 50 * (lvl + 1), x + 112, hz - 50 * lvl - 2], fill=c + (255,))
    full = sky.copy(); full.alpha_composite(cr)
    sea.alpha_composite(reflect(full, hz, seed=4))
    # motel con letrero
    fr = layer(); fd = ImageDraw.Draw(fr)
    fd.rectangle([1500, 520, 2208, LH], fill=(22, 20, 26, 255))
    fd.rectangle([1600, 330, 1980, 470], fill=(22, 20, 26, 255))
    fd.rectangle([1770, 470, 1800, 520], fill=(22, 20, 26, 255))
    f = font("InterDisplay-Black.otf", 92)
    fd.text((1625, 340), "MOTEL", font=f, fill=hexc("#ff4f6d"))
    for x in range(1540, 2200, 110):
        fd.rectangle([x, 640, x + 60, 720], fill=hexc("#ffcf7a", 200))
    fr = glow(fr, 14, 0.8)
    return [(sky, 0.15), (merge(cr, sea), 0.4), (fr, 1.0)]


def merge(*ls):
    out = layer()
    for l in ls:
        out.alpha_composite(l)
    return out


def sc_factory():
    hz = 760
    sky = vgrad(LW, LH, [(0, "#4d6fa3"), (0.65, "#f1b780"), (1, "#f6d29b")])
    fac = layer(); d = ImageDraw.Draw(fac)
    col = (48, 40, 46, 255)
    d.rectangle([700, hz - 260, 1500, hz], fill=col)
    for i, x in enumerate([780, 900, 1020, 1340]):
        hh = 520 + (i % 2) * 120
        d.rectangle([x, hz - hh, x + 50, hz], fill=col)
    for x in range(720, 1480, 70):
        d.polygon([(x, hz - 260), (x + 70, hz - 260), (x + 70, hz - 310)], fill=col)
    # humo
    smoke = layer(); sd = ImageDraw.Draw(smoke)
    rng = random.Random(1)
    for i, x in enumerate([805, 925, 1045, 1365]):
        hh = 520 + (i % 2) * 120
        for k in range(18):
            r = 30 + k * 9
            sd.ellipse([x + 25 + k * 22 - r, hz - hh - k * 30 - r, x + 25 + k * 22 + r, hz - hh - k * 30 + r],
                       fill=(235, 225, 220, max(0, 120 - k * 6)))
    smoke = smoke.filter(ImageFilter.GaussianBlur(14))
    # campos de cana
    fields = layer(); fd = ImageDraw.Draw(fields)
    fd.rectangle([0, hz, LW, LH], fill=(122, 140, 64, 255))
    for y in range(hz + 6, LH, 14):
        fd.line([(0, y), (LW, y)], fill=(96, 118, 46, 255), width=4)
    # carretera con moto
    road = layer(); rd = ImageDraw.Draw(road)
    rd.polygon([(0, LH - 220), (LW, LH - 300), (LW, LH - 200), (0, LH - 90)], fill=(50, 50, 54, 255))
    rd.line([(0, LH - 155), (LW, LH - 250)], fill=(240, 210, 90, 255), width=5)
    mx, my = 1250, LH - 250
    c = (15, 12, 14, 255)
    rd.ellipse([mx - 70, my - 10, mx - 10, my + 50], outline=c, width=10)
    rd.ellipse([mx + 70, my - 20, mx + 130, my + 40], outline=c, width=10)
    rd.polygon([(mx - 40, my + 10), (mx + 100, my - 5), (mx + 70, my - 45), (mx - 10, my - 35)], fill=c)
    rd.ellipse([mx + 10, my - 120, mx + 50, my - 80], fill=c)
    rd.polygon([(mx + 10, my - 85), (mx + 55, my - 85), (mx + 60, my - 30), (mx, my - 30)], fill=c)
    back = sky; back.alpha_composite(fac); back.alpha_composite(smoke)
    return [(back, 0.2), (fields, 0.5), (road, 1.0)]


def sc_forest():
    hz = 760
    sky = vgrad(LW, LH, [(0, "#5f8fc4"), (0.6, "#cfe3ee"), (1, "#e8efe6")])
    l1, _ = hills(1, hz - 160, 300, (110, 140, 150, 255), freq=0.0025)
    l2, _ = hills(2, hz - 40, 260, (70, 105, 95, 255), freq=0.003)
    back = sky; back.alpha_composite(l1); back.alpha_composite(fog(hz - 300, hz - 60, (235, 245, 245), 140)); back.alpha_composite(l2)
    trees = layer(); td = ImageDraw.Draw(trees)
    rng = random.Random(4)
    td.rectangle([0, hz, LW, LH], fill=(38, 70, 48, 255))
    # rio
    pts = [(LW * 0.45 + math.sin(y * 0.01) * 120 + (y - hz) * 0.6, y) for y in range(hz, LH + 1, 8)]
    for (x, y) in pts:
        w_ = 20 + (y - hz) * 1.1
        td.line([(x - w_, y), (x + w_, y)], fill=(120, 170, 200, 255), width=9)
    for _ in range(170):
        x = rng.randint(-40, LW + 40); y = rng.randint(hz - 30, hz + 120)
        h_ = rng.randint(80, 200)
        td.polygon([(x, y - h_), (x - h_ * 0.28, y), (x + h_ * 0.28, y)], fill=(25 + rng.randint(0, 20), 60 + rng.randint(0, 25), 40, 255))
    near = layer(); nd = ImageDraw.Draw(near)
    for x in (60, 260, 1950, 2150):
        for k in range(8):
            hh = 900 - k * 100
            nd.polygon([(x, LH - hh - 200), (x - 60 - k * 22, LH - hh + 60), (x + 60 + k * 22, LH - hh + 60)], fill=(12, 30, 20, 255))
        nd.rectangle([x - 14, LH - 200, x + 14, LH], fill=(30, 20, 14, 255))
    return [(back, 0.2), (trees, 0.5), (near, 1.0)]


def sc_phones():
    return [(tech_bg(12, "#1d0a33", "#070312", "#ff3d8b"), 0.3)]


def sc_prison():
    bg = vgrad(LW, LH, [(0, "#0b1a2a"), (1, "#02060c")])
    lightc = layer(); ld = ImageDraw.Draw(lightc)
    ld.polygon([(900, 0), (1300, 0), (1700, LH), (500, LH)], fill=(150, 200, 255, 60))
    bg.alpha_composite(lightc.filter(ImageFilter.GaussianBlur(40)))
    # silueta (anonima) de perfil, solo forma
    fig = layer(); fd = ImageDraw.Draw(fig)
    c = (5, 10, 16, 255)
    cx = LW // 2 + 60
    fd.ellipse([cx - 95, 330, cx + 95, 560], fill=c)  # cabeza
    fd.ellipse([cx - 150, 280, cx + 90, 520], fill=c)  # pelo
    fd.polygon([(cx - 140, 470), (cx + 40, 470), (cx + 30, 600), (cx - 130, 600)], fill=c)
    fd.rectangle([cx - 50, 540, cx + 40, 640], fill=c)  # cuello
    fd.ellipse([cx - 360, 610, cx + 360, 1300], fill=c)  # hombros
    rim = layer(); rd = ImageDraw.Draw(rim)
    rd.arc([cx - 95, 330, cx + 95, 560], 200, 350, fill=(180, 220, 255, 200), width=5)
    rd.arc([cx - 360, 610, cx + 360, 1300], 200, 260, fill=(180, 220, 255, 120), width=6)
    fig.alpha_composite(glow(rim, 8))
    bars = layer(); bd = ImageDraw.Draw(bars)
    for x in range(60, LW, 170):
        bd.rectangle([x, 0, x + 30, LH], fill=(25, 30, 38, 255))
        bd.rectangle([x + 4, 0, x + 10, LH], fill=(90, 110, 130, 255))
    bd.rectangle([0, 150, LW, 185], fill=(25, 30, 38, 255))
    bd.rectangle([0, 1000, LW, 1035], fill=(25, 30, 38, 255))
    return [(bg, 0.1), (fig, 0.4), (bars, 1.0)]


def sc_highway():
    hz = 560
    sky = vgrad(LW, LH, [(0, "#0a0620"), (0.45, "#3a1250"), (0.5, "#ff6a6a"), (1, "#ff6a6a")])
    stars(sky, 200, 400, 2)
    sun(sky, LW // 2, hz + 30, 200, top="#ffd36b", bot="#ff3d8b")
    hl, _ = hills(6, hz + 10, 140, (30, 10, 40, 255), freq=0.004)
    sky.alpha_composite(hl)
    road = layer(); rd = ImageDraw.Draw(road)
    vx = LW / 2
    rd.polygon([(vx - 20, hz), (vx + 20, hz), (LW + 600, LH), (-600, LH)], fill=(18, 12, 26, 255))
    rd.rectangle([0, hz, LW, hz + 4], fill=(18, 12, 26, 255))
    grid = layer(); grid_floor(grid, hz + 2, "#ff3d8b", 70, 80)
    road2 = layer(); road2.alpha_composite(grid); road2.alpha_composite(road)
    r2 = ImageDraw.Draw(road2)
    for side in (-1, 1):
        r2.line([(vx + side * 20, hz), (vx + side * (LW / 2 + 600), LH)], fill=hexc("#22f3ff"), width=6)
    road2 = glow(road2, 8, 0.7)
    car = layer(); cd = ImageDraw.Draw(car)
    cx, cy = LW // 2, 1030
    c = (6, 4, 10, 255)
    cd.rounded_rectangle([cx - 330, cy - 150, cx + 330, cy + 40], 40, fill=c)
    cd.polygon([(cx - 230, cy - 150), (cx + 230, cy - 150), (cx + 170, cy - 270), (cx - 170, cy - 270)], fill=c)
    cd.rectangle([cx - 360, cy + 20, cx - 250, cy + 110], fill=c)
    cd.rectangle([cx + 250, cy + 20, cx + 360, cy + 110], fill=c)
    tl = layer(); td = ImageDraw.Draw(tl)
    td.rounded_rectangle([cx - 310, cy - 100, cx - 140, cy - 70], 10, fill=hexc("#ff2a4a"))
    td.rounded_rectangle([cx + 140, cy - 100, cx + 310, cy - 70], 10, fill=hexc("#ff2a4a"))
    car.alpha_composite(glow(tl, 20, 1.3))
    return [(sky, 0.15), (road2, 0.5), (car, 1.0)]


def sc_duo():
    hz = 860
    sky = vgrad(LW, LH, [(0, "#1a0838"), (0.4, "#7a2266"), (0.7, "#ff7a59"), (1, "#ffc46b")])
    sun(sky, 1300, 760, 260)
    sea = water(hz, "#a8406a", "#2a0a2a")
    sea.alpha_composite(reflect(sky, hz, seed=8))
    back = sky; back.alpha_composite(sea)
    fg = layer(); d = ImageDraw.Draw(fg)
    c = (12, 4, 14, 255)
    d.rectangle([0, LH - 190, LW, LH], fill=c)  # muelle
    # auto clasico
    x0, y0 = 1180, LH - 190
    d.rounded_rectangle([x0, y0 - 150, x0 + 760, y0 - 30], 50, fill=c)
    d.polygon([(x0 + 160, y0 - 150), (x0 + 520, y0 - 150), (x0 + 450, y0 - 240), (x0 + 240, y0 - 240)], fill=c)
    for wx in (x0 + 150, x0 + 600):
        d.ellipse([wx - 60, y0 - 90, wx + 60, y0 + 30], fill=c)

    def person(px, h, hair_long):
        hr = h * 0.075
        d.ellipse([px - hr, y0 - h, px + hr, y0 - h + 2 * hr], fill=c)
        if hair_long:
            d.polygon([(px - hr * 1.1, y0 - h + hr), (px + hr * 1.1, y0 - h + hr), (px + hr * 1.3, y0 - h + hr * 3.6), (px - hr * 1.3, y0 - h + hr * 3.6)], fill=c)
        d.polygon([(px - hr * 2.2, y0 - h + hr * 2.6), (px + hr * 2.2, y0 - h + hr * 2.6), (px + hr * 1.6, y0 - h * 0.48), (px - hr * 1.6, y0 - h * 0.48)], fill=c)
        d.polygon([(px - hr * 1.6, y0 - h * 0.5), (px + hr * 1.6, y0 - h * 0.5), (px + hr * 1.2, y0), (px + hr * 0.2, y0), (px, y0 - h * 0.3), (px - hr * 0.2, y0), (px - hr * 1.2, y0)], fill=c)
    person(900, 560, True)
    person(1040, 610, False)
    palms = palms_layer(12, [(140, LH + 20), (360, LH + 60)], c, (800, 1000))
    return [(back, 0.2), (fg, 0.7), (palms, 1.0)]


def sc_price():
    return [(tech_bg(21, "#0e1d33", "#03070f", "#22d3c5"), 0.3)]


def sc_platforms():
    return [(tech_bg(22, "#101433", "#04050f", "#4f7cff"), 0.3)]


def sc_score():
    return [(tech_bg(23, "#0f2a1c", "#030a06", "#3ddc84"), 0.3)]


def sc_quotes():
    return [(tech_bg(24, "#2a0f2a", "#0a030a", "#ff3d8b"), 0.3)]


def sc_proscons():
    return [(tech_bg(25, "#1a1430", "#05040c", "#ffb15c"), 0.3)]


def sc_money():
    return [(tech_bg(26, "#0f2a16", "#020a04", "#3ddc84"), 0.3)]


def sc_bars():
    return [(tech_bg(27, "#14122e", "#04030c", "#ff3d8b"), 0.3)]


def sc_pc():
    bg = tech_bg(28, "#0b1430", "#02040c", "#22d3c5")
    fg = layer(); d = ImageDraw.Draw(fg)
    c = (8, 10, 20, 255)
    d.rectangle([0, 900, LW, LH], fill=(14, 16, 30, 255))
    d.rounded_rectangle([560, 220, 1650, 840], 24, fill=c, outline=hexc("#22d3c5"), width=6)
    d.rectangle([1050, 840, 1160, 930], fill=c)
    d.rounded_rectangle([880, 920, 1330, 950], 10, fill=c)
    d.rounded_rectangle([600, 990, 1500, 1080], 14, fill=c, outline=hexc("#ff3d8b", 200), width=3)
    for i in range(14):
        for j in range(3):
            d.rounded_rectangle([630 + i * 60, 1005 + j * 24, 680 + i * 60, 1022 + j * 24], 4, fill=hexc("#ff3d8b", 120))
    fg = glow(fg, 12, 0.8)
    scr = layer(); sd = ImageDraw.Draw(scr)
    scr_img = vgrad(1060, 590, [(0, "#2a0b4f"), (0.6, "#e8457c"), (1, "#ffb15c")])
    m = Image.new("L", (1060, 590), 255)
    scr.paste(scr_img, (575, 235), m)
    f = font("InterDisplay-Black.otf", 120)
    sd.text((1105, 470), "PRÓXIMAMENTE", font=f, fill=(255, 255, 255, 235), anchor="mm")
    sd.text((1105, 600), "?", font=font("InterDisplay-Black.otf", 150), fill=(255, 255, 255, 200), anchor="mm")
    fg.alpha_composite(scr)
    return [(bg, 0.2), (fg, 0.8)]


def sc_online():
    bg = tech_bg(29, "#071a2a", "#02060c", "#22d3c5")
    g = layer(); d = ImageDraw.Draw(g)
    cx, cy, R = LW // 2, LH // 2 + 40, 420
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=hexc("#22d3c5", 200), width=4)
    for k in range(1, 6):
        ry = R * math.cos(k * math.pi / 12) if False else R * (k / 6)
        d.ellipse([cx - R, cy - ry, cx + R, cy + ry], outline=hexc("#22d3c5", 70), width=2)
        d.ellipse([cx - ry, cy - R, cx + ry, cy + R], outline=hexc("#22d3c5", 70), width=2)
    rng = random.Random(3)
    pts = []
    for _ in range(26):
        a, r = rng.uniform(0, 2 * math.pi), R * math.sqrt(rng.random()) * 0.95
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            if rng.random() < 0.08:
                d.line([pts[i], pts[j]], fill=hexc("#ff3d8b", 140), width=2)
    for (x, y) in pts:
        d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=hexc("#ffffff"))
    g = glow(g, 10, 1.0)
    return [(bg, 0.2), (g, 0.7)]


def sc_outro():
    return sc_sunset_city()


def sc_chapter():
    return [(tech_bg(40, "#12062a", "#020108", "#ff3d8b"), 0.3)]


SCENE_ART = {k[3:]: v for k, v in globals().items() if k.startswith("sc_")}
