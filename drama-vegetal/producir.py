# -*- coding: utf-8 -*-
"""DRAMA VEGETAL · Ep. 1 "El secreto de la berenjena" — produccion completa.

1) Voces (narrador + berenjena) con Piper, colocadas en su segundo exacto
2) Musica de suspenso y efectos sintetizados
3) Render de los 900 cuadros (escenas.py) en paralelo
4) Mezcla final -> salida/DRAMA_VEGETAL_EP01_El_secreto_de_la_berenjena.mp4

Uso: python3 producir.py [audio|render|mezcla]   (sin argumento: todo)
"""
import json, os, subprocess, sys, wave
import numpy as np
from scipy.signal import butter, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
SALIDA = os.path.join(HERE, "salida")
VOICE = os.path.join(os.path.dirname(HERE), "video", "voices", "es-carlfm-x-low.onnx")
SR = 44100
DUR = 30.0

# ------------------------------------------------------------------ guion
# (id, quien, texto en pantalla, texto para la voz, inicio, fin maximo)
VOCES = [
    ("n1", "narrador", "Pensaba que su relación era perfecta… hasta que encontró ese mensaje.",
     "Pensaba que su relación era perfecta... hasta que encontró ese mensaje.", 0.55, 4.9),
    ("b1", "berenjena", "¡¿Con él?! ¡No puedo creerlo!", "¿Con él? ¡No puedo creerlo!", 12.75, 15.7),
    ("n2", "narrador", "Pero lo peor no era que le estuviera siendo infiel…",
     "Pero lo peor... no era que le estuviera siendo infiel.", 16.3, 19.75),
    ("n3", "narrador", "Lo que descubrió esa noche cambiaría todo el huerto para siempre.",
     "Lo que descubrió esa noche... cambiaría todo el huerto para siempre.", 24.0, 27.35),
]


def lp(x, fc, o=2):
    return sosfilt(butter(o, fc, "low", fs=SR, output="sos"), x)


def hp(x, fc, o=2):
    return sosfilt(butter(o, fc, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, o=2):
    return sosfilt(butter(o, [lo, hi], "band", fs=SR, output="sos"), x)


def wav_write(path, x, sr=SR, ch=1):
    x = np.clip(x, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def wav_read(path):
    with wave.open(path) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        if w.getnchannels() == 2:
            x = x.reshape(-1, 2).mean(1)
    return x, sr


# ------------------------------------------------------------------ voces
def make_voices():
    from piper import PiperVoice, SynthesisConfig
    voice = PiperVoice.load(VOICE)
    os.makedirs(BUILD, exist_ok=True)
    track = np.zeros(int(DUR * SR), np.float32)
    timing = {}
    for vid, who, shown, spoken, t0, tmax in VOCES:
        ls = 1.12 if who == "narrador" else 0.95
        for _ in range(5):
            cfg = SynthesisConfig(length_scale=ls, noise_scale=0.62, noise_w_scale=0.75)
            a = np.concatenate([c.audio_int16_array for c in voice.synthesize(spoken, syn_config=cfg)])
            nz = np.where(np.abs(a) > 300)[0]
            a = a[max(0, nz[0] - 300): nz[-1] + 1200]
            dur = len(a) / 16000
            if t0 + dur <= tmax or ls < 0.8:
                break
            ls *= (tmax - t0) / dur * 0.98
        raw = os.path.join(BUILD, f"{vid}_raw.wav")
        wav_write(raw, a.astype(np.float32) / 32768, 16000)
        out = os.path.join(BUILD, f"{vid}.wav")
        if who == "berenjena":   # voz propia: mas aguda y con mas energia
            af = "asetrate=16000*1.22,aresample=44100,atempo=0.86,highpass=f=120,acompressor=threshold=-18dB:ratio=3"
        else:                    # narrador: grave y cinematografico
            af = "asetrate=16000*0.93,aresample=44100,atempo=1.075,highpass=f=70,equalizer=f=180:t=q:w=1:g=3,aecho=0.8:0.5:40:0.12"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af", af, "-ac", "1", "-ar", str(SR), out], check=True)
        x, _ = wav_read(out)
        x = x / (np.max(np.abs(x)) + 1e-9) * 0.9
        i0 = int(t0 * SR)
        n = min(len(x), len(track) - i0)
        track[i0:i0 + n] += x[:n]
        timing[vid] = dict(who=who, text=shown, start=t0, end=t0 + n / SR)
        # envolvente para la sincronizacion labial (30 fps)
        if who == "berenjena":
            hop = SR // 30
            env = [float(np.sqrt(np.mean(x[i:i + hop] ** 2))) for i in range(0, len(x), hop)]
            m = max(env) + 1e-9
            timing[vid]["env"] = [min(1.0, e / m * 1.25) for e in env]
        print(f"{vid}: {t0:.2f}-{t0 + n / SR:.2f}s (length_scale {ls:.2f})")
    wav_write(os.path.join(BUILD, "voces.wav"), track)
    json.dump(timing, open(os.path.join(BUILD, "voces.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


# ------------------------------------------------------------------ musica y efectos
rng = np.random.default_rng(11)


def add(buf, sig, t):
    i = int(t * SR)
    j = min(len(buf), i + len(sig))
    if i < len(buf):
        buf[i:j] += sig[:j - i]


def tone(f, dur, kind="sin"):
    t = np.arange(int(dur * SR)) / SR
    if kind == "saw":
        return 2 * ((t * f) % 1) - 1
    return np.sin(2 * np.pi * f * t)


def env(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na)
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def music():
    n = int(DUR * SR)
    m = np.zeros(n)
    t = np.arange(n) / SR
    # dron grave en La menor que crece
    drone = (tone(55, DUR, "saw") + tone(55 * 1.005, DUR, "saw") * 0.8 + tone(82.4, DUR, "saw") * 0.5)
    drone = lp(drone, 260)
    inten = np.interp(t, [0, 10, 20, 20.01, 20.6, 27.3, 27.4, 30], [0.35, 0.6, 0.85, 0, 0, 1.0, 0, 0])
    m += drone * inten * 0.35
    # pulso tipo latido grave (70 bpm, mas rapido despues)
    beat = 60 / 70
    tt = 0.3
    while tt < 27.4:
        if not (20.0 <= tt < 20.6):
            k = tone(48, 0.4) * np.exp(-np.arange(int(0.4 * SR)) / SR * 9)
            add(m, k * 0.55 * np.interp(tt, [0, 20, 21, 27.4], [0.6, 0.9, 0.8, 1.2]), tt)
        tt += beat if tt < 20.6 else beat * 0.75
    # cuerdas agudas en tremolo (tension)
    strings = (tone(440, DUR) + tone(523.25, DUR) * 0.6 + tone(659.3, DUR) * 0.4)
    trem = 0.5 + 0.5 * np.sin(2 * np.pi * 9 * t)
    sint = np.interp(t, [0, 8, 10, 20, 20.01, 20.6, 23.8, 27.3, 27.4], [0, 0, 0.25, 0.4, 0, 0, 0.3, 0.75, 0])
    m += lp(strings * trem, 3000) * sint * 0.08
    # acorde final (golpe de "continuara")
    hit = sum(tone(f, 3.0, "saw") for f in (55, 110, 130.8, 164.8, 220)) * np.exp(-np.arange(int(3.0 * SR)) / SR * 1.6)
    add(m, lp(hit, 1500) * 0.25, 27.4)
    m = np.stack([m, m], 1)
    m[:, 1] = np.roll(m[:, 1], 300)
    return m / (np.max(np.abs(m)) + 1e-9) * 0.8


def sfx():
    n = int(DUR * SR)
    s = np.zeros(n)

    def buzz(d=0.38):
        x = np.sign(tone(150, d)) * (0.5 + 0.5 * np.sign(tone(18, d)))
        return lp(x, 900) * env(len(x), 0.01, 0.03) * 0.35

    def ding(f=1318):
        d = 0.9
        x = (tone(f, d) + tone(f * 1.5, d) * 0.5 + tone(f * 2, d) * 0.25) * np.exp(-np.arange(int(d * SR)) / SR * 5)
        return x * 0.3

    def whoosh(d=0.6):
        x = rng.standard_normal(int(d * SR))
        out = np.zeros_like(x)
        tt = np.linspace(0, 1, len(x))
        for i in range(0, len(x), 1024):
            fc = 300 + 4000 * np.sin(np.pi * tt[i]) ** 2
            out[i:i + 1024] = bp(x[i:i + 1024], fc * 0.6, min(18000, fc * 1.4), 1)
        return out * np.sin(np.pi * tt) ** 2 * 0.35

    def boom(d=2.2, g=0.9):
        tt = np.arange(int(d * SR)) / SR
        f = 38 + 70 * np.exp(-tt * 7)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 2.5) + lp(rng.standard_normal(len(tt)), 400) * np.exp(-tt * 5) * 0.6
        return x * g

    def sting():
        d = 1.5
        tt = np.arange(int(d * SR)) / SR
        x = sum(tone(f, d, "saw") for f in (233, 247, 466, 494)) * np.exp(-tt * 3)
        return lp(x, 5000) * 0.12

    def tap():
        x = hp(rng.standard_normal(int(0.04 * SR)), 2500) * np.exp(-np.arange(int(0.04 * SR)) / SR * 120)
        return x * 0.25

    def heartbeat():
        out = np.zeros(int(0.8 * SR))
        for off, g in ((0, 1.0), (0.22, 0.7)):
            k = tone(55, 0.25) * np.exp(-np.arange(int(0.25 * SR)) / SR * 18) * g
            i = int(off * SR)
            out[i:i + len(k)] += k
        return lp(out, 200) * 0.9

    add(s, buzz(), 0.2); add(s, buzz(), 1.0)
    for c in (2.0, 4.6, 10.0, 12.4, 16.0, 23.8):
        add(s, whoosh(), c - 0.3)
    add(s, ding(), 5.55)                    # primer mensaje
    add(s, sting(), 7.6); add(s, boom(1.5, 0.5), 7.6)
    add(s, ding(1175), 10.95)               # llega la foto
    add(s, boom(2.4, 1.0), 11.6)            # golpe dramatico al ver la foto
    for k in range(7):                      # escribiendo...
        add(s, tap(), 20.75 + k * 0.1)
    add(s, ding(1568), 21.45)               # mensaje final
    add(s, boom(2.5, 0.8), 22.3)
    for k in range(5):
        add(s, heartbeat(), 23.9 + k * 0.72)
    add(s, boom(3.0, 1.0), 27.4)
    return np.stack([s, s], 1)


def make_audio():
    os.makedirs(BUILD, exist_ok=True)
    make_voices()
    wav_write(os.path.join(BUILD, "musica.wav"), music().reshape(-1), ch=2)
    wav_write(os.path.join(BUILD, "sfx.wav"), np.clip(sfx(), -1, 1).reshape(-1), ch=2)


def render():
    subprocess.run([sys.executable, os.path.join(HERE, "escenas.py")], check=True)


def mezcla():
    os.makedirs(SALIDA, exist_ok=True)
    out = os.path.join(SALIDA, "DRAMA_VEGETAL_EP01_El_secreto_de_la_berenjena.mp4")
    fc = ("[1:a]acompressor=threshold=-20dB:ratio=3:attack=5:release=80:makeup=2,equalizer=f=3000:t=q:w=1.2:g=2,"
          "pan=stereo|c0=c0|c1=c0,asplit=2[v][vsc];"
          "[2:a]volume=0.55[m];[m][vsc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[md];"
          "[3:a]volume=0.9[s];[v][md][s]amix=inputs=3:normalize=0,loudnorm=I=-13:TP=-1.0:LRA=9,aresample=48000[a]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(BUILD, "mudo.mp4"),
                    "-i", os.path.join(BUILD, "voces.wav"), "-i", os.path.join(BUILD, "musica.wav"), "-i", os.path.join(BUILD, "sfx.wav"),
                    "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", "-t", str(DUR), out], check=True)
    print("listo:", out)


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "todo"
    if step in ("audio", "todo"):
        make_audio()
    if step in ("render", "todo"):
        render()
    if step in ("mezcla", "todo"):
        mezcla()
