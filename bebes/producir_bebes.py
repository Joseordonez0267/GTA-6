# -*- coding: utf-8 -*-
"""BEBÉS EN MISIÓN · Ep. 1 "Rescate en la cuna" — 45 s vertical, voces neuronales (Microsoft Edge TTS).

Uso: python3 producir_bebes.py [audio|render|mezcla]   (sin argumento: todo)
"""
import json, os, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "drama-vegetal", "v2"))
import producir2 as P
from producir2 import SR, add, tone, lp, hp, bp, wav_write, wav_read, env

BUILD = os.path.join(HERE, "build")
SALIDA = os.path.join(HERE, "salida")
DUR = 45.0

# voz neuronal, tono y velocidad por personaje
VOZ = {
    "narrador": ("es-MX-JorgeNeural", "-2Hz", "-6%"),
    "mateo": ("es-US-AlonsoNeural", "+48Hz", "+6%"),
    "lucas": ("es-MX-DaliaNeural", "+75Hz", "+8%"),
    "mama": ("es-CO-SalomeNeural", "+0Hz", "-4%"),
}

# (id, quien, texto, inicio, fin maximo)
LINEAS = [
    ("l1", "lucas", "¡Mateooo! ¡Sácame de aquí!", 0.4, 2.9),
    ("n1", "narrador", "Mateo tiene un año… y una sola misión: rescatar a su hermanito de la cuna.", 3.2, 7.4),
    ("m1", "mateo", "Tranquilo, hermano. Tengo un plan.", 7.7, 10.4),
    ("n2", "narrador", "Paso uno: cruzar el gran desierto de la alfombra.", 10.7, 14.8),
    ("n3", "narrador", "Paso dos: construir una escalera.", 15.2, 17.4),
    ("m2", "mateo", "¡Ingeniería de bebé!", 17.6, 19.4),
    ("m3", "mateo", "¡Ya casi, Lucas!", 19.7, 21.2),
    ("l2", "lucas", "¡Eres mi héroe!", 21.4, 22.9),
    ("m4", "mateo", "¡Viene mamá! ¡Hazte el dormido!", 23.1, 25.0),
    ("a1", "mama", "¿Quién anda despierto a estas horas?", 25.5, 27.6),
    ("a2", "mama", "Mmm… qué angelitos.", 27.8, 29.4),
    ("l3", "lucas", "Oye, Mateo… la cuna tenía puerta.", 31.0, 35.2),
    ("m5", "mateo", "¿Y me lo dices AHORA?", 35.8, 39.2),
    ("n4", "narrador", "Misión cumplida… más o menos.", 39.8, 42.4),
]


def tts(text, who, rate_extra=0, out=None):
    voice, pitch, rate = VOZ[who]
    r = int(rate.replace("%", "")) + rate_extra
    cmd = ["edge-tts", "--voice", voice, f"--pitch={pitch}", f"--rate={r:+d}%", "--text", text, "--write-media", out]
    px = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if px:
        cmd[1:1] = ["--proxy", px]
    subprocess.run(cmd, check=True, capture_output=True)


def make_voices():
    os.makedirs(BUILD, exist_ok=True)
    track = np.zeros(int(DUR * SR), np.float32)
    timing = {}
    for vid, who, text, t0, tmax in LINEAS:
        extra = 0
        for _ in range(4):
            mp3 = os.path.join(BUILD, f"{vid}.mp3")
            tts(text.replace("…", "...").replace("AHORA", "ahora"), who, extra, mp3)
            wav = os.path.join(BUILD, f"{vid}.wav")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-af", "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                            "silenceremove=start_periods=1:start_threshold=-45dB,areverse", "-ac", "1", "-ar", str(SR), wav], check=True)
            x, _ = wav_read(wav)
            if t0 + len(x) / SR <= tmax or extra >= 30:
                break
            extra += int(((t0 + len(x) / SR) / tmax - 1) * 100) + 6
        x = x / (np.max(np.abs(x)) + 1e-9) * 0.9
        i0 = int(t0 * SR)
        n = min(len(x), len(track) - i0)
        track[i0:i0 + n] += x[:n]
        hop = SR // 30
        e = [float(np.sqrt(np.mean(x[i:i + hop] ** 2))) for i in range(0, len(x), hop)]
        mx = max(e) + 1e-9
        timing[vid] = dict(who=who, text=text, start=t0, end=t0 + n / SR, env=[min(1.0, v / mx * 1.25) for v in e])
        print(f"{vid} ({who}): {t0:.2f}-{t0 + n / SR:.2f}s")
    wav_write(os.path.join(BUILD, "voces.wav"), track)
    json.dump(timing, open(os.path.join(BUILD, "voces.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def music():
    """Musica de mision comica: pizzicato + bombo, se corta en el silencio y vuelve al final."""
    n = int(DUR * SR)
    t = np.arange(n) / SR
    m = np.zeros(n)
    bpm = 112
    beat = 60 / bpm
    scale = [220, 246.9, 261.6, 293.7, 329.6, 349.2, 392]
    pattern = [0, 2, 4, 2, 5, 4, 2, 1, 0, 2, 4, 6, 5, 4, 2, 0]
    k = 0
    tt = 3.0
    while tt < 42.6:
        quiet = 23.0 <= tt < 30.3          # mama llega: casi silencio
        if not (29.5 <= tt < 30.3):
            f = scale[pattern[k % 16]]
            d = 0.25
            pl = (tone(f, d) + tone(f * 2, d) * 0.3) * np.exp(-np.arange(int(d * SR)) / SR * 14)
            add(m, pl * (0.05 if quiet else 0.2), tt)
            if k % 2 == 0 and not quiet:
                kk = tone(55, 0.3) * np.exp(-np.arange(int(0.3 * SR)) / SR * 12)
                add(m, kk * 0.5, tt)
        tt += beat / 2
        k += 1
    # tension (cuerdas) cuando se acerca mama
    st = lp(tone(110, DUR, "saw") + tone(116.5, DUR, "saw"), 600)
    m += st * np.interp(t, [0, 23, 23.5, 29.4, 29.5, 45], [0, 0, 0.15, 0.15, 0, 0])
    # fanfarria final
    for i, f in enumerate((392, 523.25, 659.25, 783.99)):
        d = 0.6 if i < 3 else 1.6
        x = (tone(f, d, "saw") * 0.5 + tone(f, d)) * np.exp(-np.arange(int(d * SR)) / SR * (3 if i < 3 else 1.5))
        add(m, lp(x, 3000) * 0.12, 39.8 + i * 0.18)
    m = np.stack([m, m], 1)
    m[:, 1] = np.roll(m[:, 1], 250)
    return m / (np.max(np.abs(m)) + 1e-9) * 0.75


def sfx():
    n = int(DUR * SR)
    s = np.zeros(n)
    rng = np.random.default_rng(3)

    def step():
        d = 0.15
        return lp(rng.standard_normal(int(d * SR)), 300) * np.exp(-np.arange(int(d * SR)) / SR * 30) * 0.9

    def block():
        d = 0.2
        return (tone(900, d) * 0.4 + lp(rng.standard_normal(int(d * SR)), 2500)) * np.exp(-np.arange(int(d * SR)) / SR * 35) * 0.6

    def whoosh(d=0.5):
        w = rng.standard_normal(int(d * SR)); o = np.zeros_like(w); tt = np.linspace(0, 1, len(w))
        for i in range(0, len(w), 1024):
            fc = 300 + 4000 * np.sin(np.pi * tt[i]) ** 2
            o[i:i + 1024] = bp(w[i:i + 1024], fc * 0.6, min(18000, fc * 1.4), 1)
        return o * np.sin(np.pi * tt) ** 2 * 0.3

    for c in (3.0, 7.5, 10.5, 15.0, 19.5, 23.0, 25.0, 30.3, 35.5, 39.5):
        add(s, whoosh(), c - 0.25)
    for k in range(8):                       # gateo
        add(s, step() * 0.4, 10.8 + k * 0.5)
    for k in range(4):                       # bloques apilandose
        add(s, block(), 15.4 + k * 0.9)
    for k in range(5):                       # pasos de mama
        add(s, step(), 22.9 + k * 0.42)
    door = lp(rng.standard_normal(int(0.6 * SR)), 500) * np.exp(-np.linspace(0, 6, int(0.6 * SR))) * 0.8
    add(s, door, 25.1)
    add(s, door * 0.9, 29.55)
    # "ding" comico al descubrir la puerta de la cuna
    dd = (tone(1046, 0.8) + tone(1568, 0.8) * 0.5) * np.exp(-np.arange(int(0.8 * SR)) / SR * 5) * 0.3
    add(s, dd, 33.2)
    tb = np.arange(int(0.6 * SR)) / SR
    add(s, np.sin(2 * np.pi * (300 - 250 * tb) * tb) * np.exp(-tb * 4) * 0.4, 35.6)  # "boing" descendente
    return np.stack([s, s], 1)


def make_audio():
    os.makedirs(BUILD, exist_ok=True)
    make_voices()
    wav_write(os.path.join(BUILD, "musica.wav"), music().reshape(-1), ch=2)
    wav_write(os.path.join(BUILD, "sfx.wav"), np.clip(sfx(), -1, 1).reshape(-1), ch=2)


def mezcla():
    os.makedirs(SALIDA, exist_ok=True)
    out = os.path.join(SALIDA, "BEBES_EN_MISION_EP01_Rescate_en_la_cuna_45s.mp4")
    fc = ("[1:a]acompressor=threshold=-20dB:ratio=2.5:attack=5:release=80:makeup=1.5,pan=stereo|c0=c0|c1=c0,asplit=2[v][vsc];"
          "[2:a]volume=0.6[m];[m][vsc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[md];"
          "[3:a]volume=0.9[s];[v][md][s]amix=inputs=3:normalize=0,loudnorm=I=-13:TP=-1.0:LRA=9,aresample=48000[a]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(BUILD, "mudo.mp4"),
                    "-i", os.path.join(BUILD, "voces.wav"), "-i", os.path.join(BUILD, "musica.wav"), "-i", os.path.join(BUILD, "sfx.wav"),
                    "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "slow", "-crf", "24",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", str(DUR), out], check=True)
    print("listo:", out)


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "todo"
    if step in ("audio", "todo"):
        make_audio()
    if step in ("render", "todo"):
        subprocess.run([sys.executable, os.path.join(HERE, "escenas_bebes.py")], check=True)
    if step in ("mezcla", "todo"):
        mezcla()
