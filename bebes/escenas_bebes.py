# -*- coding: utf-8 -*-
"""BEBÉS EN MISIÓN · Ep. 1 "Rescate en la cuna" — 45 s, 1080x1920, 30 fps.

Motor de composicion de DRAMA VEGETAL (../drama-vegetal/v2/escenas2.py) con
los recursos 3D de los bebes (assets_bebes.py).
"""
import json, math, os, random, shutil, subprocess, sys, glob
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "drama-vegetal", "v2"))
BUILD = os.path.join(HERE, "build")
AS = os.path.join(BUILD, "assets")
# ojos 3D reutilizados de DRAMA VEGETAL
for f in glob.glob(os.path.join(ROOT, "drama-vegetal", "v2", "build", "assets", "eye_*.png")):
    dst = os.path.join(AS, os.path.basename(f))
    if not os.path.exists(dst):
        shutil.copy(f, dst)

import escenas2 as E
E.AS = AS
E.load.cache_clear(); E.plate.cache_clear()
E.ANC = json.load(open(os.path.join(AS, "anchors.json")))
E.VOCES = json.load(open(os.path.join(BUILD, "voces.json"), encoding="utf-8"))
E.EYE_PREFIX.update(mateo="eye_tom", lucas="eye_ber")
E.SKIN_DARK.update(mateo=(70, 36, 22), lucas=(45, 24, 14))
from escenas2 import (W, H, FPS, put, text, emoji, glow_spr, plate, plate_xy, camera, character, contact_shadow,
                      clamp, ease, eout, back, blink, grade)
ANC = E.ANC
DUR = 45.0
COL = {"narrador": (255, 226, 50), "mateo": (120, 220, 255), "lucas": (255, 170, 210), "mama": (255, 200, 120)}
EMO = {"mateo": "👶", "lucas": "🍼", "mama": "👩"}


def sub_y(t):
    if t < 3.0:
        return 1560
    if 7.5 <= t < 10.5 or 23.0 <= t < 25.0 or 35.5 <= t < 39.5:
        return 600
    return 1560


def subtitle(fr, t):
    for vid, v in E.VOCES.items():
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
            size = 86 if v["who"] != "narrador" else 78
            sprs = [text(w.upper(), size, COL[v["who"]] if blk * 3 + i == cur else (255, 255, 255), stroke=9) for i, w in enumerate(chunk)]
            tw = sum(s.width for s in sprs) - 30 * (len(sprs) - 1)
            fit = min(1.0, (W - 90) / tw)
            x = W / 2 - tw * fit / 2
            y = sub_y(t)
            pop = back((t - times[cur]) / 0.18) if t >= times[cur] else 1
            if v["who"] in EMO:
                put(fr, emoji(EMO[v["who"]], 66), W / 2, y - 105)
            for i, s in enumerate(sprs):
                sc = (0.85 + 0.15 * pop if blk * 3 + i == cur else 1.0) * fit
                put(fr, s, x + s.width * fit / 2, y, 1, "mm", scale=sc)
                x += (s.width - 30) * fit
            return


def watermark(fr):
    put(fr, text("BEBÉS EN MISIÓN", 38, stroke=4), W / 2 + 26, 210, 0.85)
    put(fr, emoji("👶", 44), W / 2 - 215, 210, 0.85)
    put(fr, text("EP. 1", 28, (255, 226, 50), stroke=3), W / 2, 262, 0.8)


def env(vid, t):
    return E.mouth_env(vid, t)


def crib_layer(fr, view, z, fx, fy):
    bar = camera(plate(f"cuarto_{view}_barrotes"), z, fx, fy)
    fr.alpha_composite(bar)


# ------------------------------------------------------------------ planos
def shot_hook(t):
    z, fx, fy = 1.05 + 0.02 * t, 0.5, 0.5
    fr = camera(plate("cuarto_crib"), z, fx, fy)
    lu = character("lucas", "lucas_reach", 1400, dict(brow=1.0, mouth="o", mo=env("l1", t), tears=0.7, py=0.2, open=blink(t, 2.5)))
    put(fr, lu, W / 2 + 20, 1720 + abs(math.sin(t * 8)) * -12, anchor="mb")
    crib_layer(fr, "crib", z, fx, fy)
    k = back(t / 0.35)
    put(fr, text("MISIÓN:", 92, (255, 226, 50), stroke=10), W / 2, 400, clamp(t / 0.1), scale=0.6 + 0.4 * k)
    put(fr, text("RESCATAR A LUCAS", 96, stroke=11), W / 2, 515, clamp((t - 0.15) / 0.1), scale=0.6 + 0.4 * back((t - 0.15) / 0.35))
    return fr


def wide_with_lucas(z, fx, fy, lucas_pose="lucas_reach", lucas_expr=None, show_lucas=True):
    fr = camera(plate("cuarto_wide"), z, fx, fy)
    cx, cy, s = plate_xy("cuarto_wide", ANC["cuarto"]["wide"]["crib"], z, fx, fy)
    if show_lucas:
        lu = character("lucas", lucas_pose, int(520 * s), lucas_expr or dict(brow=1.0, mouth="o"))
        put(fr, lu, cx, cy + 40 * s, anchor="mb")
    crib_layer(fr, "wide", z, fx, fy)
    return fr, (cx, cy, s)


def shot_intro(t):
    fr, _ = wide_with_lucas(1.05 + 0.03 * t / 4.5, 0.5, 0.6)
    ma = character("mateo", "mateo_sit", 900, dict(brow=-0.5, mouth="smirk", px=0.8, py=-0.4, open=blink(t, 2.9)))
    put(fr, contact_shadow(500), 300, 1800)
    put(fr, ma, 300, 1850, anchor="mb")
    return fr


def shot_plan(t):
    fr = camera(plate("cuarto_wide", 8), 1.4, 0.4, 0.62)
    ma = character("mateo", "mateo_sit", 1750, dict(brow=-0.6, mouth="smirk", mo=env("m1", t + 7.5), px=0.3, open=blink(t, 2.7)))
    put(fr, ma, W / 2, 2050, anchor="mb")
    return fr


def shot_crawl(t):
    fr, _ = wide_with_lucas(1.1, 0.5, 0.62)
    x = 140 + 700 * (t / 4.5)
    bob = abs(math.sin(t * 6.3)) * 14
    ma = character("mateo", "mateo_crawl", 780, dict(brow=-0.4, mouth="neutral", px=1.0, open=blink(t, 3.1)))
    put(fr, contact_shadow(420), x, 1830)
    put(fr, ma, x, 1860 - bob, anchor="mb")
    if t > 0.3:  # polvo del "desierto"
        rr = random.Random(int(t * 10))
        for k in range(6):
            put(fr, glow_spr(90, 60, (200, 190, 170), 70), x - 160 - k * 30 + rr.uniform(-10, 10), 1820 - rr.uniform(0, 40), 0.6)
    return fr


BLOCK_T = (15.4, 16.3, 17.2, 18.1)


def blocks(fr, x0, y0, size, tt):
    blk = E.load("bloque")
    n = sum(1 for b in BLOCK_T if tt >= b)
    for i in range(n):
        drop = eout((tt - BLOCK_T[i]) / 0.25)
        bs = blk.resize((size, size), Image.LANCZOS)
        put(fr, bs, x0 + (i % 2) * size * 0.1, y0 - i * size * 0.62 - (1 - drop) * 200, 1.0, "mb")


def shot_blocks(t):
    tt = t + 15.0
    fr, (cx, cy, s) = wide_with_lucas(1.6, 0.68, 0.6)
    blocks(fr, cx - 330, 1850, 230, tt)
    cheer = tt >= 17.6
    ma = character("mateo", "mateo_cheer" if cheer else "mateo_sit", 1000,
                   dict(brow=-0.3 if not cheer else 0.3, mouth="smile", mo=env("m2", tt), px=0.6, open=blink(t, 2.6)))
    put(fr, contact_shadow(520), 330, 1850)
    put(fr, ma, 330, 1890, anchor="mb")
    return fr


def shot_almost(t):
    tt = t + 19.5
    z, fx, fy = 1.08, 0.5, 0.5
    fr = camera(plate("cuarto_crib"), z, fx, fy)
    lu = character("lucas", "lucas_reach" if tt < 21.3 else "lucas_cheer", 1250, dict(brow=0.6, mouth="smile", mo=env("l2", tt), px=-0.5, open=blink(t, 2.2)))
    put(fr, lu, W / 2 + 140, 1650, anchor="mb")
    crib_layer(fr, "crib", z, fx, fy)
    blk = E.load("bloque").resize((300, 300), Image.LANCZOS)
    for i in range(3):
        put(fr, blk, 230 + (i % 2) * 20, 2050 - i * 185, 1, "mb")
    ma = character("mateo", "mateo_reach", 1200, dict(brow=-0.3, mouth="smile", mo=env("m3", tt), px=0.6, py=-0.6, open=blink(t, 2.9)))
    put(fr, ma, 260, 1560 + math.sin(t * 5) * 6, anchor="mb")
    return fr


def door_light(fr, amount):
    if amount <= 0:
        return fr
    li = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(li)
    w = 420 * amount
    d.polygon([(W, 300), (W, 1920), (W - w * 2.2, 1920), (W - w, 300)], fill=(255, 200, 120, int(70 * amount)))
    fr.alpha_composite(li.filter(ImageFilter.GaussianBlur(30)))
    return fr


def shot_mama_comes(t):
    fr = camera(plate("cuarto_wide", 8), 1.4, 0.4, 0.62)
    fr = door_light(fr, eout(t / 1.5))
    ma = character("mateo", "mateo_sit", 1750, dict(big=1.15, brow_up=1.5, mouth="o", mo=env("m4", t + 23.0), px=1.0, sweat=1.0))
    jx = math.sin(t * 40) * 4
    put(fr, ma, W / 2 + jx, 2050, anchor="mb")
    return fr


def shot_pretend(t):
    tt = t + 25.0
    fr, _ = wide_with_lucas(1.1, 0.5, 0.62, "lucas_sleep", dict(open=0.0, mouth="smile"))
    fr = door_light(fr, 1.0 if tt < 29.4 else 0.0)
    ma = character("mateo", "mateo_sleep", 860, dict(open=0.0, mouth="smile"))
    put(fr, contact_shadow(480), 330, 1820)
    put(fr, ma, 330, 1860 + math.sin(t * 2.5) * 4, anchor="mb")
    for k in range(3):  # "Zzz" fingido
        ph = ((t * 0.6 + k / 3) % 1)
        put(fr, text("z", 60 + k * 10, (220, 230, 255), "InterDisplay-BoldItalic.otf", stroke=4), 430 + ph * 120, 1200 - ph * 250, math.sin(ph * math.pi))
    return fr


def shot_dark(t):
    fr, _ = wide_with_lucas(1.1, 0.5, 0.62, "lucas_sleep", dict(open=0.0, mouth="smile"))
    fr = door_light(fr, max(0.0, 1 - t / 0.5))
    return Image.blend(fr, Image.new("RGBA", (W, H), (0, 0, 0, 255)), 0.55)


def shot_twist(t):
    fr, _ = wide_with_lucas(1.25, 0.45, 0.62, show_lucas=False)
    peek = t > 0.4
    ma = character("mateo", "mateo_sleep" if t < 2.4 else "mateo_sit", 1000,
                   dict(open=0.35 if peek else 0.0, lid=0.5 if peek else 0.0, px=0.9, mouth="neutral" if t > 2.4 else "smile",
                        big=1.0 if t < 2.4 else 1.1, brow_up=0.0 if t < 2.4 else 1.2))
    put(fr, contact_shadow(520), 300, 1840)
    put(fr, ma, 300, 1880, anchor="mb")
    a = clamp((t - 0.6) / 0.3)
    lu = character("lucas", "lucas_stand", 1000, dict(mouth="smile", mo=env("l3", t + 30.3), px=-0.8, brow=0.2, open=blink(t, 2.4)))
    put(fr, contact_shadow(420), 780, 1860)
    put(fr, lu, 780, 1900 - (1 - a) * 60, a, anchor="mb")
    return fr


def shot_facepalm(t):
    fr = camera(plate("cuarto_wide", 8), 1.4, 0.4, 0.62)
    ma = character("mateo", "mateo_facepalm", 1750, dict(brow=0.5, lid=0.6, mouth="frown", mo=env("m5", t + 35.5), px=0.0))
    put(fr, ma, W / 2, 2050 + math.sin(t * 2) * 4, anchor="mb")
    return fr


def shot_cheer(t):
    fr, _ = wide_with_lucas(1.25, 0.45, 0.62, show_lucas=False)
    hop = abs(math.sin(t * 6)) * 30
    ma = character("mateo", "mateo_cheer", 1000, dict(mouth="smile", brow=0.3, px=0.6, open=blink(t, 2.0)))
    lu = character("lucas", "lucas_cheer", 1000, dict(mouth="smile", brow=0.3, px=-0.6, open=blink(t, 2.3, 0.6)))
    put(fr, contact_shadow(520), 320, 1840); put(fr, contact_shadow(420), 770, 1840)
    put(fr, ma, 320, 1880 - hop, anchor="mb")
    put(fr, lu, 770, 1880 - abs(math.sin(t * 6 + 1)) * 30, anchor="mb")
    rr = random.Random(7)
    for k in range(40):  # confeti
        x0 = rr.uniform(0, W)
        sp = rr.uniform(300, 600)
        y = (rr.uniform(-800, 0) + t * sp) % 2000 - 100
        col = rr.choice([(255, 90, 90), (90, 170, 255), (255, 220, 80), (120, 220, 140)])
        d = ImageDraw.Draw(fr)
        d.rectangle([x0 + math.sin(t * 4 + k) * 20, y, x0 + 14 + math.sin(t * 4 + k) * 20, y + 22], fill=col + (230,))
    return fr


def shot_end(t):
    fr = Image.new("RGBA", (W, H), (8, 10, 30, 255))
    k = back(t / 0.5)
    put(fr, text("CONTINUARÁ…", 130, font="InterDisplay-Black.otf"), W / 2, 820, clamp(t / 0.3), scale=0.7 + 0.3 * k)
    if t > 0.6:
        a = clamp((t - 0.6) / 0.3)
        put(fr, text("¿QUÉ MISIÓN HARÁN MAÑANA?", 58, (120, 220, 255), stroke=6), W / 2, 1010, a)
        put(fr, text("COMENTA", 64, stroke=6), W / 2 - 60, 1110, a)
        put(fr, emoji("👶", 80), W / 2 + 190, 1110, a, scale=1 + 0.1 * math.sin(t * 8))
    if t > 1.1:
        put(fr, text("BEBÉS EN MISIÓN · EPISODIO 1", 34, (180, 170, 220), "Inter-Bold.otf"), W / 2, 1260, clamp((t - 1.1) / 0.3))
    return fr


SHOTS = [
    (0.0, 3.0, shot_hook), (3.0, 7.5, shot_intro), (7.5, 10.5, shot_plan), (10.5, 15.0, shot_crawl),
    (15.0, 19.5, shot_blocks), (19.5, 23.0, shot_almost), (23.0, 25.0, shot_mama_comes), (25.0, 29.5, shot_pretend),
    (29.5, 30.3, shot_dark), (30.3, 35.5, shot_twist), (35.5, 39.5, shot_facepalm), (39.5, 42.6, shot_cheer), (42.6, 45.0, shot_end),
]


def frame(tt):
    idx = 0
    for i, (a, b, fn) in enumerate(SHOTS):
        if a <= tt < b or (i == len(SHOTS) - 1 and tt >= a):
            idx = i; break
    a, b, fn = SHOTS[idx]
    out = grade(fn(tt - a), tt).convert("RGBA")
    for (a2, _, _) in SHOTS[1:]:
        if abs(tt - a2) < 0.05:
            out = Image.blend(out, Image.new("RGBA", (W, H), (0, 0, 0, 255)), 0.5)
    if fn not in (shot_end, shot_dark):
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
