# -*- coding: utf-8 -*-
"""DRAMA VEGETAL Ep. 2 "El hermano perdido" — 45 s, 1080x1920, 30 fps.

Reutiliza el motor realista del episodio 1 (../v2/escenas2.py) y sus recursos 3D,
mas Mama Calabaza y el huerto (assets_ep2.py).

  0.0- 3.0  gancho: alguien toca la ventana (el pepino, ojos brillantes)
  3.0- 7.0  la berenjena tiembla                       · narrador
  7.0-11.0  el pepino en la ventana: "No vine a quitarte nada…"
 11.0-14.5  berenjena: "¿Hermano? ¡Tú eres verde y yo soy morado!"
 14.5-22.6  FLASHBACK en el huerto: Mama Calabaza, dos semillas, la tormenta
 22.6-27.0  la tomate despierta: "Te lo iba a decir…"
 27.0-31.5  reencuentro: "¡Tengo un hermano!"           · narrador
 31.5-32.2  silencio
 32.2-36.0  mensaje de "Mama Calabaza": el plan
 36.0-41.0  el pepino sonrie con malicia delante de la pareja feliz · narrador
 41.0-42.6  la berenjena, feliz, sin sospechar nada
 42.6-45.0  CONTINUARA…
"""
import json, math, os, random, subprocess, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "v2"))
import escenas2 as E
from escenas2 import (W, H, FPS, put, text, emoji, rrect, glow_spr, plate, plate_xy, camera, character, contact_shadow,
                      clamp, ease, eout, back, blink, bubble, persp_coeffs, grade, ANC, SCR_W, SCR_H)

BUILD = os.path.join(HERE, "build")
DUR = 45.0
E.VOCES = json.load(open(os.path.join(BUILD, "voces.json"), encoding="utf-8"))
E.EYE_PREFIX["calabaza"] = "eye_cal"
E.SKIN_DARK["calabaza"] = (60, 18, 2)
E.SUB_COL["tomate"] = (255, 120, 120)


def sub_y(t):
    if t < 3.0:
        return 1560
    if t < 7.0 or 11.0 <= t < 14.5:
        return 720
    if 7.0 <= t < 11.0:
        return 1500
    if 14.5 <= t < 22.6:
        return 500
    if 22.6 <= t < 27.0:
        return 600
    if 27.0 <= t < 31.5:
        return 560
    if 36.0 <= t < 41.0:
        return 1560
    return 1560


E.sub_y = sub_y
_orig_subtitle = E.subtitle


def subtitle(fr, t):
    # emoji del personaje que habla (anadimos tomate)
    for vid, v in E.VOCES.items():
        if v["who"] == "tomate" and v["start"] - 0.05 <= t <= v["end"] + 0.35:
            put(fr, emoji("🍅", 68), W / 2, sub_y(t) - 105)
            v2 = dict(v); v2["who"] = "narrador"
            saved = E.VOCES
            E.VOCES = {vid: v2}
            E.SUB_COL["narrador"] = (255, 120, 120)
            _orig_subtitle(fr, t)
            E.SUB_COL["narrador"] = (255, 226, 50)
            E.VOCES = saved
            return
    _orig_subtitle(fr, t)


def watermark(fr):
    put(fr, text("DRAMA VEGETAL", 38, stroke=4), W / 2 + 26, 210, 0.85)
    put(fr, emoji("🍆", 44), W / 2 - 205, 210, 0.85)
    put(fr, text("EP. 2", 28, (255, 226, 50), stroke=3), W / 2, 262, 0.8)


def env(vid, t):
    return E.mouth_env(vid, t)


# ------------------------------------------------------------------ planos
KNOCKS = (0.4, 0.7, 1.0, 2.0, 2.3)


def shot_hook(t):
    fr = camera(plate("room_window"), 1.08 + 0.02 * t, 0.5, 0.42)
    wx, wy, s = plate_xy("room_window", ANC["rooms"]["window"]["window"], 1.08 + 0.02 * t, 0.5, 0.42)
    bump = max([math.exp(-((t - k) * 25) ** 2) for k in KNOCKS])
    pep = character("pepino", "pepB_back_knock", 1250, dict(lid=0.5, mouth="smirk", glow_eyes=0.9))
    put(fr, pep, wx - 260, wy + 300 + bump * 10, 0.95, scale=1 + bump * 0.03)
    ber = character("berenjena", "berB_moon_fear", 2250, dict(big=1.15, brow_up=1.4, mouth="o", py=-1.0, px=-0.4, sweat=1.0))
    jx = math.sin(t * 50) * 4
    put(fr, ber, W / 2 + 140 + jx, 2700, anchor="mb")
    k = back(t / 0.35)
    put(fr, text("¿QUIÉN TOCA", 100, (255, 226, 50), stroke=10), W / 2, 420, clamp(t / 0.1), scale=0.6 + 0.4 * k)
    put(fr, text("LA VENTANA?", 110, stroke=12), W / 2, 545, clamp((t - 0.15) / 0.1), scale=0.6 + 0.4 * back((t - 0.15) / 0.35))
    return fr


def shot_scared(t):
    fr = camera(plate("room_corner", 6), 1.15, 0.5, 0.55)
    tr = 4 + 2 * math.sin(t * 4)
    jx = random.Random(int(t * 30)).uniform(-tr, tr)
    ber = character("berenjena", "berB_moon_fear", 1700, dict(brow=0.6, brow_up=1.0, mouth="wobbly", px=-1.0, py=-0.5, sweat=1.0, open=blink(t, 2.2)))
    put(fr, contact_shadow(600), W / 2 + 40, 1800)
    put(fr, ber, W / 2 + 40 + jx, 1860, anchor="mb")
    return fr


def shot_pepino_window(t):
    fr = camera(plate("room_window", 3), 1.5, 0.42, 0.42)
    fr = Image.blend(fr, Image.new("RGBA", (W, H), (0, 10, 25, 255)), 0.25)
    mo = env("p1", t + 7.0)
    pep = character("pepino", "pepB_moon_crossed", 3300, dict(lid=0.35, brow=0.3, mouth="neutral", mo=mo, px=0.0, open=blink(t, 2.9, 0.4)))
    put(fr, pep, W / 2 + 30, 1900, scale=1.0 + 0.02 * t)
    return fr


def shot_ber_confused(t):
    fr = camera(plate("room_corner", 8), 1.3, 0.45, 0.5)
    mo = env("b1", t + 11.0)
    angry = t > 1.1
    ber = character("berenjena", "berB_moon_point" if angry else "berB_moon_angry", 2100,
                    dict(brow=-0.7 if angry else 0.2, brow_up=0.0 if angry else 1.2, mo=mo, mouth="frown" if angry else "o", px=0.6, open=blink(t, 2.5)))
    put(fr, ber, W / 2 - (90 if angry else 0), 2120 + math.sin(t * 9) * (4 if angry else 0), anchor="mb")
    return fr


def sepia(img, amount=1.0, t=0.0):
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    g = a @ np.array([0.299, 0.587, 0.114])
    sep = np.stack([g * 1.07 + 18, g * 0.92 + 8, g * 0.72], -1)
    a = a * (1 - amount) + sep * amount
    out = Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(out)
    rr = random.Random(int(t * 24))
    for _ in range(4):  # rayas de pelicula vieja
        x = rr.uniform(0, W)
        d.line([(x, 0), (x + rr.uniform(-6, 6), H)], fill=(255, 240, 210, rr.randint(30, 80)), width=rr.randint(1, 3))
    for _ in range(25):
        x, y = rr.uniform(0, W), rr.uniform(0, H)
        r = rr.uniform(1, 4)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(30, 20, 10, rr.randint(60, 150)))
    return out


def shot_flashback(t):
    z = 1.05 + 0.05 * t / 8.1
    fr = camera(plate("huerto"), z, 0.5, 0.6)
    storm = t > 0.5
    # lluvia
    if storm:
        d = ImageDraw.Draw(fr)
        rr = random.Random(int(t * 30))
        for _ in range(140):
            x, y = rr.uniform(0, W), rr.uniform(0, H)
            d.line([(x, y), (x - 10, y + 60)], fill=(200, 210, 230, 110), width=2)
    sad = t > 3.2
    cal = character("calabaza", "calB_moon_fear" if sad else "calB_moon_protect", 880, dict(mouth="frown" if sad else "smile", brow=0.9 if sad else 0.2, tears=0.8 if sad else 0.0,
                                                       px=0.0, py=0.5 if sad else 0.0, open=blink(t, 3.1)))
    put(fr, contact_shadow(700), W / 2, 1480)
    put(fr, cal, W / 2, 1530, anchor="mb")
    # las dos semillas: juntas al principio, la tormenta las separa
    sep = eout((t - 3.2) / 1.6) if sad else 0.0
    bb = character("berenjena", "berB_moon_fear" if sad else "berB_moon_happy", 470, dict(mouth="smile" if not sad else "o", brow_up=0.8 if sad else 0.0, px=-0.6, open=blink(t, 2.4)))
    pb = character("pepino", "pepB_moon_open", 560, dict(mouth="smile" if not sad else "o", brow_up=0.8 if sad else 0.0, px=0.6, open=blink(t, 2.7, 1.0)))
    put(fr, contact_shadow(220), W / 2 - 230 - sep * 700, 1640)
    put(fr, bb, W / 2 - 230 - sep * 700, 1680, anchor="mb")
    put(fr, contact_shadow(160), W / 2 + 230 + sep * 700, 1640)
    put(fr, pb, W / 2 + 230 + sep * 700, 1680, anchor="mb")
    # relampagos
    for tf in (0.5, 4.2):
        if tf <= t < tf + 0.25:
            fr = Image.blend(fr, Image.new("RGBA", (W, H), (230, 235, 255, 255)), 0.6 * (1 - (t - tf) / 0.25))
    return fr


def shot_tomate_wakes(t):
    fr = camera(plate("room_bed", 5), 1.35, 0.55, 0.5)
    mo = env("t1", t + 22.6)
    op = clamp((t - 0.2) / 0.3)
    tom = character("tomate", "tomB_moon_clasp", 1450, dict(open=op if op > 0.1 else 0.0, brow=0.8, mo=mo, mouth="frown", px=-0.4, py=0.2,
                                                      tears=0.5 if t > 1.5 else 0.0))
    put(fr, tom, W / 2 + 20, 1330 + math.sin(t * 2) * 5)
    return fr


def shot_reunion(t):
    fr = camera(plate("room_corner", 7), 1.15, 0.5, 0.55)
    fr = Image.blend(fr, Image.new("RGBA", (W, H), (255, 170, 90, 255)), 0.12)
    mo = env("b2", t + 27.0)
    lean = math.sin(t * 2.2) * 0.02
    ber = character("berenjena", "berB_moon_happy", 1400, dict(mouth="smile", mo=mo, brow=0.6, brow_up=0.6, tears=0.7, px=0.7, open=blink(t, 2.8)))
    pep = character("pepino", "pepB_moon_open", 1550, dict(mouth="smile", brow=0.3, px=-0.7, lid=0.15, open=blink(t, 3.2, 1.3)))
    tom = character("tomate", "tomB_moon_happy", 760, dict(mouth="smile", px=0.0, py=-0.6, brow=0.4))
    put(fr, contact_shadow(520), 300, 1790); put(fr, contact_shadow(380), 800, 1790)
    put(fr, ber, 300, 1830, anchor="mb", scale=1 + lean)
    put(fr, pep, 800, 1830, anchor="mb", scale=1 - lean)
    put(fr, contact_shadow(380), W / 2 + 10, 1840)
    put(fr, tom, W / 2 + 10, 1880, anchor="mb")
    # corazones flotando
    rr = random.Random(2)
    for k in range(10):
        st = rr.uniform(0, 4)
        ph = ((t + st) % 4) / 4
        put(fr, emoji("💜", 60), rr.uniform(150, W - 150) + math.sin(t * 2 + k) * 20, 1400 - ph * 700, math.sin(ph * math.pi) * 0.9)
    return fr


def screen_plan(t):
    scr = Image.new("RGBA", (SCR_W, SCR_H), (10, 10, 14, 255))
    m1 = bubble("¿Ya estás dentro de la casa? No olvides el plan.", size=56, maxw=680, hl=("plan.",))
    put(scr, m1, 30, 300, clamp((t - 1.0) / 0.15), "lt", scale=0.6 + 0.4 * back((t - 1.0) / 0.35))
    if t > 2.3:
        m2 = bubble("El huerto será nuestro.", size=64, maxw=680, hl=("nuestro.",))
        put(scr, m2, 30, 300 + m1.height + 40, clamp((t - 2.3) / 0.15), "lt", scale=0.6 + 0.4 * back((t - 2.3) / 0.35))
    d = ImageDraw.Draw(scr)
    d.rectangle([0, 0, SCR_W, 190], fill=(22, 22, 28, 255))
    d.ellipse([34, 70, 134, 170], fill=(230, 110, 20, 255))
    put(scr, text("Mamá Calabaza", 42, font="Inter-Bold.otf", shadow=False), 160, 100, anchor="lm")
    put(scr, text("en línea", 30, (120, 220, 140), font="Inter-Medium.otf", shadow=False), 160, 148, anchor="lm")
    return scr


def shot_phone_plan(t):
    z = 1.0 + 0.12 * ease(t / 3.8)
    sh = 8 if 2.2 < t < 2.5 else 0
    sx = random.Random(int(t * 40)).uniform(-sh, sh) if sh else 0
    fr = camera(plate("phone_plate"), z, 0.5, 0.5, sx, 0)
    corners = [plate_xy("phone_plate", c, z, 0.5, 0.5, sx, 0)[:2] for c in ANC["phone"]]
    ui = screen_plan(t)
    co = persp_coeffs([(0, 0), (SCR_W, 0), (SCR_W, SCR_H), (0, SCR_H)], corners)
    warped = ui.transform((W, H), Image.PERSPECTIVE, co, resample=Image.BICUBIC)
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).polygon([tuple(c) for c in corners], fill=255)
    fr.paste(warped, (0, 0), m.filter(ImageFilter.GaussianBlur(1.2)))
    return fr


def shot_pepino_evil(t):
    fr = camera(plate("room_corner", 10), 1.2, 0.5, 0.55)
    # la pareja feliz al fondo (desenfocada)
    bg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ber = character("berenjena", "berB_moon_happy", 950, dict(mouth="smile", brow=0.5, px=0.6))
    tom = character("tomate", "tomB_moon_happy", 560, dict(mouth="smile", px=-0.6))
    put(bg, ber, 300, 1250, anchor="mb"); put(bg, tom, 520, 1260, anchor="mb")
    fr.alpha_composite(bg.filter(ImageFilter.GaussianBlur(9)))
    fr = Image.blend(fr, Image.new("RGBA", (W, H), (10, 0, 20, 255)), 0.3)
    evil = ease((t - 1.2) / 1.5)
    pep = character("pepino", "pepB_moon_evil", 3200, dict(lid=0.25 + 0.4 * evil, brow=-0.8 * evil, mouth="smirk" if evil > 0.3 else "smile",
                                                            px=1.0 if t < 1.0 else 0.0, glow_eyes=evil))
    rub = math.sin(t * 14) * 6 * evil
    put(fr, pep, W / 2 + 200 + rub, 1650 + 30 * (1 - evil), scale=1.0 + 0.04 * t)
    return fr


def shot_ber_innocent(t):
    fr = camera(plate("room_corner", 8), 1.3, 0.45, 0.5)
    fr = Image.blend(fr, Image.new("RGBA", (W, H), (255, 170, 90, 255)), 0.1)
    ber = character("berenjena", "berB_moon_idle", 2300, dict(mouth="smile", brow=0.4, brow_up=0.5, open=blink(t, 1.0, 0.7) if t > 0.6 else 1.0))
    put(fr, ber, W / 2, 2500, anchor="mb", scale=1 + 0.03 * t)
    return fr


def shot_end(t):
    fr = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    k = back(t / 0.5)
    put(fr, text("CONTINUARÁ…", 130, font="InterDisplay-Black.otf"), W / 2, 820, clamp(t / 0.3), scale=0.7 + 0.3 * k)
    if t > 0.6:
        a = clamp((t - 0.6) / 0.3)
        put(fr, text("¿QUÉ QUIERE EL PEPINO?", 64, (140, 240, 120), stroke=6), W / 2, 1010, a)
        put(fr, text("COMENTA", 64, stroke=6), W / 2 - 60, 1110, a)
        put(fr, emoji("🥒", 80), W / 2 + 190, 1110, a, scale=1 + 0.1 * math.sin(t * 8))
    if t > 1.1:
        put(fr, text("DRAMA VEGETAL · EPISODIO 2", 34, (180, 170, 220), "Inter-Bold.otf"), W / 2, 1260, clamp((t - 1.1) / 0.3))
    return fr


SHOTS = [
    (0.0, 3.0, shot_hook),
    (3.0, 7.0, shot_scared),
    (7.0, 11.0, shot_pepino_window),
    (11.0, 14.5, shot_ber_confused),
    (14.5, 22.6, shot_flashback),
    (22.6, 27.0, shot_tomate_wakes),
    (27.0, 31.5, shot_reunion),
    (31.5, 32.2, None),
    (32.2, 36.0, shot_phone_plan),
    (36.0, 41.0, shot_pepino_evil),
    (41.0, 42.6, shot_ber_innocent),
    (42.6, 45.0, shot_end),
]
NO_MARK = {8, 11}


def frame(tt):
    idx = 0
    for i, (a, b, fn) in enumerate(SHOTS):
        if a <= tt < b or (i == len(SHOTS) - 1 and tt >= a):
            idx = i; break
    a, b, fn = SHOTS[idx]
    t = tt - a
    if fn is None:
        fr = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    else:
        fr = fn(t)
    out = grade(fr, tt).convert("RGBA")
    if fn is shot_flashback:
        out = sepia(out, 0.6, tt)
        put(out, text("HACE AÑOS…", 70, (255, 235, 200), "InterDisplay-BoldItalic.otf", stroke=5), W / 2, 340, clamp(t / 0.4) * (1 - clamp((t - 3.0) / 0.5)))
    for (a2, _, _) in SHOTS[1:]:
        if abs(tt - a2) < 0.05:
            out = Image.blend(out, Image.new("RGBA", (W, H), (0, 0, 0, 255)), 0.55)
    if idx not in NO_MARK and fn is not None:
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
    jobs = [(i, f0, min(total, f0 + 75)) for i, f0 in enumerate(range(0, total, 75))]
    with Pool(os.cpu_count() or 4) as pool:
        paths = pool.map(render_chunk, jobs, chunksize=1)
    lst = os.path.join(BUILD, "chunks", "list.txt")
    open(lst, "w").write("".join(f"file '{os.path.basename(p)}'\n" for p in paths))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                    os.path.join(BUILD, "mudo.mp4")], check=True)
    print("mudo.mp4 listo")


if __name__ == "__main__":
    main()
