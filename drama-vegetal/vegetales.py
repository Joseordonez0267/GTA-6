# -*- coding: utf-8 -*-
"""Personajes de DRAMA VEGETAL: Berenjena, Tomate y Pepino.

Dibujados por codigo con sombreado de volumen (luz principal, contraluz y
brillo especular) para dar aspecto tridimensional. Solo vegetales: sin
brazos, piernas ni rasgos humanos fuera de la cara.

draw(kind, h, expr) -> sprite RGBA de altura ~h pixeles.
"""
import math
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SS = 2  # supermuestreo


def _rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)


def shade(mask, base, light, dark, rim=(120, 150, 255), light_pos=(0.32, 0.25), spec=0.55, rim_amt=0.55):
    """Rellena una mascara con iluminacion de volumen. Devuelve RGBA."""
    m = np.asarray(mask).astype(np.float32) / 255
    h, w = m.shape
    ys, xs = np.nonzero(m > 0.5)
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nx = (xx - x0) / max(1, x1 - x0)
    ny = (yy - y0) / max(1, y1 - y0)
    # "profundidad" aproximada: distancia al borde, suavizada
    edge = np.asarray(mask.filter(ImageFilter.GaussianBlur(max(4, (x1 - x0) * 0.18)))).astype(np.float32) / 255
    d = np.sqrt((nx - light_pos[0]) ** 2 + (ny - light_pos[1]) ** 2)
    lum = np.clip(1.15 - d * 1.25, 0, 1) * 0.65 + edge * 0.35
    base, light, dark = _rgb(base), _rgb(light), _rgb(dark)
    col = np.where(lum[..., None] > 0.5,
                   base + (light - base) * ((lum[..., None] - 0.5) * 2),
                   dark + (base - dark) * (lum[..., None] * 2))
    # contraluz azul (luz de luna) en el borde derecho-inferior
    inner = np.asarray(mask.filter(ImageFilter.GaussianBlur(max(3, (x1 - x0) * 0.05)))).astype(np.float32) / 255
    rimm = np.clip((1 - inner) * 2.2, 0, 1) * np.clip((nx - 0.45) * 2 + (ny - 0.4), 0, 1) * rim_amt
    col = col * (1 - rimm[..., None]) + np.array(rim, np.float32) * rimm[..., None]
    out = np.zeros((h, w, 4), np.uint8)
    out[..., :3] = np.clip(col, 0, 255)
    out[..., 3] = (m * 255).astype(np.uint8)
    img = Image.fromarray(out)
    # brillo especular
    sp = Image.new("L", (w, h), 0)
    sx, sy = x0 + (x1 - x0) * light_pos[0], y0 + (y1 - y0) * light_pos[1]
    rw, rh = (x1 - x0) * 0.13, (y1 - y0) * 0.07
    ImageDraw.Draw(sp).ellipse([sx - rw, sy - rh, sx + rw, sy + rh], fill=int(255 * spec))
    sp = sp.filter(ImageFilter.GaussianBlur(rw * 0.5))
    sp = Image.fromarray(np.minimum(np.asarray(sp), np.asarray(mask)))
    white = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    img.paste(white, (0, 0), sp)
    return img


def leaf_star(d, cx, cy, r, n, color, droop=0.6, rot=0.0, width=0.32):
    for k in range(n):
        a = rot + k / n * 2 * math.pi
        pts = []
        for s in range(13):
            t = s / 12
            ang = a + (t - 0.5) * width * 2 * (1 - t) * 1.6
            rr = r * t
            pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr * 0.55 + droop * r * t * t))
        back = []
        for s in range(12, -1, -1):
            t = s / 12
            ang = a - (t - 0.5) * width * 2 * (1 - t) * 1.6
            rr = r * t
            back.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr * 0.55 + droop * r * t * t))
        d.polygon(pts + back, fill=color)


# ------------------------------------------------------------------ cuerpos
@lru_cache(maxsize=16)
def body(kind, h):
    H = h * SS
    if kind == "berenjena":
        Wd = int(H * 0.62)
        m = Image.new("L", (Wd, H), 0)
        d = ImageDraw.Draw(m)
        top = H * 0.14
        nx, ny, nr = Wd * 0.5, H * 0.30, Wd * 0.19          # cuello
        bx, by, brx, bry = Wd * 0.52, H * 0.70, Wd * 0.47, H * 0.28   # bulbo
        d.ellipse([nx - nr, top, nx + nr, ny + nr * 1.2], fill=255)
        d.ellipse([bx - brx, by - bry, bx + brx, by + bry], fill=255)
        pts = []
        for i in range(41):  # union suave entre cuello y bulbo
            t = i / 40
            y = ny + (by - ny) * t
            hw = nr + (brx - nr) * (math.sin(t * math.pi / 2) ** 2.2)
            pts.append((nx + (bx - nx) * t - hw, y))
        pts2 = []
        for i in range(41):
            t = i / 40
            y = ny + (by - ny) * t
            hw = nr + (brx - nr) * (math.sin(t * math.pi / 2) ** 2.2)
            pts2.append((nx + (bx - nx) * t + hw, y))
        d.polygon(pts + pts2[::-1], fill=255)
        m = m.filter(ImageFilter.GaussianBlur(SS))
        img = shade(m, "#5b2a86", "#a66ad6", "#1c0a2e", rim=(120, 160, 255))
        cal = Image.new("RGBA", img.size, (0, 0, 0, 0))
        cd = ImageDraw.Draw(cal)
        cx, cy = Wd / 2, top + Wd * 0.03
        leaf_star(cd, cx, cy, Wd * 0.26, 6, (40, 100, 48, 255), droop=0.55, rot=0.3, width=0.55)
        leaf_star(cd, cx, cy, Wd * 0.2, 5, (66, 140, 64, 255), droop=0.5, rot=0.9, width=0.55)
        cd.ellipse([cx - Wd * 0.11, cy - Wd * 0.07, cx + Wd * 0.11, cy + Wd * 0.07], fill=(60, 130, 60, 255))
        # tallo
        cd.line([(cx, cy), (cx + Wd * 0.04, cy - Wd * 0.14), (cx + Wd * 0.1, cy - Wd * 0.2)], fill=(80, 120, 60, 255), width=int(Wd * 0.06), joint="curve")
        img.alpha_composite(cal)
        face = dict(cx=0.51, eye_y=0.47, eye_dx=0.15, eye_r=0.1, mouth_y=0.64, brow_y=0.37, scale=Wd)
    elif kind == "tomate":
        Wd = int(H * 1.0)
        m = Image.new("L", (Wd, H), 0)
        d = ImageDraw.Draw(m)
        cx, cy, R = Wd / 2, H * 0.55, Wd * 0.44
        pts = []
        for i in range(180):
            a = i / 180 * 2 * math.pi
            r = R * (1 + 0.018 * math.cos(6 * a))
            pts.append((cx + math.cos(a) * r * 1.04, cy + math.sin(a) * r * 0.94))
        d.polygon(pts, fill=255)
        m = m.filter(ImageFilter.GaussianBlur(SS))
        img = shade(m, "#e0262b", "#ff7a62", "#5e0710", rim=(255, 160, 200), spec=0.7)
        cal = Image.new("RGBA", img.size, (0, 0, 0, 0))
        cd = ImageDraw.Draw(cal)
        ty = cy - R * 0.9
        leaf_star(cd, cx, ty, Wd * 0.22, 5, (40, 120, 50, 255), droop=0.5, rot=-0.3, width=0.22)
        cd.ellipse([cx - Wd * 0.04, ty - Wd * 0.03, cx + Wd * 0.04, ty + Wd * 0.03], fill=(50, 130, 55, 255))
        cd.line([(cx, ty), (cx - Wd * 0.02, ty - Wd * 0.08)], fill=(70, 120, 55, 255), width=int(Wd * 0.03))
        img.alpha_composite(cal)
        face = dict(cx=0.5, eye_y=0.5, eye_dx=0.15, eye_r=0.085, mouth_y=0.68, brow_y=0.39, scale=Wd)
    else:  # pepino
        Wd = int(H * 0.42)
        m = Image.new("L", (Wd, H), 0)
        d = ImageDraw.Draw(m)
        d.rounded_rectangle([Wd * 0.12, H * 0.04, Wd * 0.88, H * 0.98], int(Wd * 0.36), fill=255)
        m = m.filter(ImageFilter.GaussianBlur(SS))
        img = shade(m, "#2f7a3a", "#7fc070", "#0c2a12", rim=(160, 255, 200), spec=0.4)
        dd = ImageDraw.Draw(img)
        mk = np.asarray(m)
        import random
        rng = random.Random(3)
        for _ in range(70):  # rayas claras y verrugas
            x, y = rng.uniform(Wd * 0.18, Wd * 0.82), rng.uniform(H * 0.08, H * 0.95)
            if mk[int(y), int(x)] > 200:
                r = Wd * 0.012
                dd.ellipse([x - r, y - r, x + r, y + r], fill=(200, 235, 170, 200))
        st = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(st)
        for k in range(4):
            x = Wd * (0.3 + k * 0.13)
            sd.line([(x, H * 0.1), (x + Wd * 0.02, H * 0.92)], fill=(170, 225, 140, 45), width=int(Wd * 0.05))
        st = st.filter(ImageFilter.GaussianBlur(Wd * 0.02))
        st.putalpha(Image.fromarray(np.minimum(np.asarray(st.getchannel("A")), np.asarray(m))))
        img.alpha_composite(st)
        dd = ImageDraw.Draw(img)
        dd.ellipse([Wd * 0.44, H * 0.015, Wd * 0.56, H * 0.06], fill=(150, 130, 70, 255))
        face = dict(cx=0.5, eye_y=0.24, eye_dx=0.17, eye_r=0.1, mouth_y=0.38, brow_y=0.17, scale=Wd)
    return img, face


# ------------------------------------------------------------------ cara
def _eye(d, cx, cy, r, open_, px, py, lashes=False, iris=(90, 60, 30), lid_angle=0.0, side=1):
    if open_ <= 0.06:
        d.arc([cx - r, cy - r * 0.5, cx + r, cy + r * 0.5], 10, 170, fill=(20, 10, 15, 255), width=int(r * 0.22))
        if lashes:
            for k in range(3):
                a = math.radians(40 + k * 45)
                x, y = cx + math.cos(a) * r, cy + math.sin(a) * r * 0.5
                d.line([(x, y), (x + math.cos(a) * r * 0.35, y + math.sin(a) * r * 0.35)], fill=(20, 10, 15, 255), width=int(r * 0.12))
        return
    ry = r * 1.12 * open_
    d.ellipse([cx - r, cy - ry, cx + r, cy + ry], fill=(250, 250, 252, 255), outline=(30, 15, 25, 255), width=max(2, int(r * 0.08)))
    ir = r * 0.62
    ix, iy = cx + px * r * 0.35, cy + py * ry * 0.35
    d.ellipse([ix - ir, iy - ir, ix + ir, iy + ir], fill=iris + (255,))
    pr = ir * 0.55
    d.ellipse([ix - pr, iy - pr, ix + pr, iy + pr], fill=(8, 6, 10, 255))
    hr = ir * 0.32
    d.ellipse([ix - ir * 0.45 - hr, iy - ir * 0.45 - hr, ix - ir * 0.45 + hr, iy - ir * 0.45 + hr], fill=(255, 255, 255, 255))
    d.ellipse([ix + ir * 0.3, iy + ir * 0.25, ix + ir * 0.3 + hr * 0.6, iy + ir * 0.25 + hr * 0.6], fill=(255, 255, 255, 220))
    if lid_angle:  # parpado (desconfianza / misterio)
        drop = r * lid_angle
        d.polygon([(cx - r * 1.2, cy - ry * 1.3), (cx + r * 1.2, cy - ry * 1.3), (cx + r * 1.2, cy - ry + drop * (1.2 if side > 0 else 0.6)),
                   (cx - r * 1.2, cy - ry + drop * (0.6 if side > 0 else 1.2))], fill=(0, 0, 0, 0))
    if lashes:
        for k in range(3):
            a = math.radians(-150 + k * 30) if side < 0 else math.radians(-30 - k * 30)
            x, y = cx + math.cos(a) * r, cy + math.sin(a) * ry
            d.line([(x, y), (x + math.cos(a) * r * 0.4, y + math.sin(a) * r * 0.4)], fill=(20, 10, 15, 255), width=max(2, int(r * 0.12)))


def draw(kind, h, expr=None):
    """expr: open, px, py, brow (-1 enfadado .. 1 triste), brow_up, mouth, mouth_open, tears, blush, lid"""
    e = dict(open=1.0, px=0.0, py=0.0, brow=0.0, brow_up=0.0, mouth="smile", mouth_open=0.0, tears=0.0, blush=0.0, lid=0.0, sweat=0.0)
    if expr:
        e.update(expr)
    base, f = body(kind, h)
    img = base.copy()
    lid_mask = None
    d = ImageDraw.Draw(img)
    S = f["scale"]
    W, H = img.size
    cx = W * f["cx"]
    ey = H * f["eye_y"] if kind != "tomate" else H * f["eye_y"]
    r = S * f["eye_r"]
    lashes = kind == "tomate"
    iris = {"berenjena": (120, 80, 40), "tomate": (40, 110, 60), "pepino": (200, 160, 40)}[kind]
    # parpados de desconfianza: se dibujan como piel sobre el ojo
    for side in (-1, 1):
        ex = cx + side * S * f["eye_dx"]
        _eye(d, ex, ey, r, e["open"], e["px"], e["py"], lashes, iris, 0, side)
        if e["lid"] > 0 and e["open"] > 0.06:
            col = {"berenjena": (70, 35, 105, 255), "tomate": (200, 30, 40, 255), "pepino": (40, 105, 50, 255)}[kind]
            ry = r * 1.12 * e["open"]
            yb = ey - ry + 2 * ry * e["lid"] * 0.6
            d.chord([ex - r * 1.08, ey - ry * 1.08, ex + r * 1.08, ey + ry * 1.08], 180, 360, fill=col) if e["lid"] >= 0.8 else \
                d.polygon([(ex - r * 1.1, ey - ry * 1.15), (ex + r * 1.1, ey - ry * 1.15), (ex + r * 1.1, yb), (ex - r * 1.1, yb)], fill=col)
            d.line([(ex - r * 1.05, yb), (ex + r * 1.05, yb)], fill=(20, 10, 15, 255), width=max(2, int(r * 0.12)))
    # cejas
    by = H * f["brow_y"] - e["brow_up"] * r * 0.8
    bw = max(3, int(r * (0.32 if kind != "tomate" else 0.18)))
    for side in (-1, 1):
        ex = cx + side * S * f["eye_dx"]
        inner = (ex - side * r * 0.9, by + e["brow"] * -r * 0.0 + (r * 0.45 if e["brow"] < 0 else -r * 0.35 * e["brow"]))
        outer = (ex + side * r * 1.0, by + (-r * 0.15 if e["brow"] < 0 else r * 0.25 * e["brow"]))
        if e["brow"] < 0:
            inner = (inner[0], by + r * 0.5 * -e["brow"])
            outer = (outer[0], by - r * 0.15 * -e["brow"])
        d.line([inner, outer], fill=(25, 10, 20, 255), width=bw)
        d.ellipse([inner[0] - bw / 2, inner[1] - bw / 2, inner[0] + bw / 2, inner[1] + bw / 2], fill=(25, 10, 20, 255))
        d.ellipse([outer[0] - bw / 2, outer[1] - bw / 2, outer[0] + bw / 2, outer[1] + bw / 2], fill=(25, 10, 20, 255))
    # boca
    my = H * f["mouth_y"]
    mw = S * (0.13 if kind != "tomate" else 0.11)
    mo = e["mouth_open"]
    dark = (60, 10, 25, 255)
    if mo > 0.05 or e["mouth"] in ("o", "shout"):
        mo = max(mo, 0.35 if e["mouth"] == "o" else mo)
        ow = mw * (0.55 if e["mouth"] == "o" else 1.0)
        d.ellipse([cx - ow, my - mw * 0.25 * mo - 2, cx + ow, my + mw * 0.9 * mo + 2], fill=dark, outline=(25, 5, 12, 255), width=3)
        d.ellipse([cx - ow * 0.55, my + mw * 0.45 * mo, cx + ow * 0.55, my + mw * 0.85 * mo], fill=(220, 90, 110, 255))
    elif e["mouth"] == "smile":
        d.arc([cx - mw, my - mw * 0.6, cx + mw, my + mw * 0.6], 15, 165, fill=(30, 8, 15, 255), width=max(3, int(mw * 0.14)))
    elif e["mouth"] == "smirk":
        d.arc([cx - mw * 0.6, my - mw * 0.5, cx + mw * 1.1, my + mw * 0.4], 20, 120, fill=(30, 8, 15, 255), width=max(3, int(mw * 0.14)))
    elif e["mouth"] == "frown":
        d.arc([cx - mw * 0.9, my, cx + mw * 0.9, my + mw * 0.9], 200, 340, fill=(30, 8, 15, 255), width=max(3, int(mw * 0.14)))
    elif e["mouth"] == "wobbly":
        pts = [(cx - mw + i * mw / 6, my + math.sin(i * 1.7) * mw * 0.12) for i in range(13)]
        d.line(pts, fill=(30, 8, 15, 255), width=max(3, int(mw * 0.13)), joint="curve")
    else:
        d.line([(cx - mw * 0.7, my), (cx + mw * 0.7, my)], fill=(30, 8, 15, 255), width=max(3, int(mw * 0.13)))
    if e["blush"] > 0:
        bl = Image.new("RGBA", img.size, (0, 0, 0, 0))
        bd = ImageDraw.Draw(bl)
        for side in (-1, 1):
            x = cx + side * S * f["eye_dx"] * 1.35
            bd.ellipse([x - r * 0.8, ey + r * 1.2, x + r * 0.8, ey + r * 1.9], fill=(255, 120, 150, int(140 * e["blush"])))
        img.alpha_composite(bl.filter(ImageFilter.GaussianBlur(r * 0.3)))
    if e["tears"] > 0:
        tl = Image.new("RGBA", img.size, (0, 0, 0, 0))
        td = ImageDraw.Draw(tl)
        for side in (-1, 1):
            x = cx + side * S * f["eye_dx"] + side * r * 0.4
            y0 = ey + r * 0.9
            L = r * 3.0 * e["tears"]
            td.line([(x, y0), (x + side * r * 0.1, y0 + L)], fill=(150, 210, 255, 210), width=int(r * 0.28))
            td.ellipse([x - r * 0.2, y0 + L - r * 0.1, x + r * 0.25, y0 + L + r * 0.35], fill=(170, 225, 255, 230))
        img.alpha_composite(tl)
    if e["sweat"] > 0:
        sd = ImageDraw.Draw(img)
        x, y = cx + S * f["eye_dx"] * 2.0, ey - r * 1.2
        sd.polygon([(x, y - r * 0.6), (x - r * 0.3, y + r * 0.1), (x + r * 0.3, y + r * 0.1)], fill=(170, 220, 255, 230))
        sd.ellipse([x - r * 0.3, y - r * 0.15, x + r * 0.3, y + r * 0.4], fill=(170, 220, 255, 230))
    return img.resize((W // SS, H // SS), Image.LANCZOS)


def shadow(w, h=None):
    h = h or int(w * 0.18)
    s = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(s).ellipse([0, 0, w - 1, h - 1], fill=(0, 0, 0, 150))
    return s.filter(ImageFilter.GaussianBlur(h * 0.25))
