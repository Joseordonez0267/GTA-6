# -*- coding: utf-8 -*-
"""DRAMA VEGETAL · Ep. 2 "El hermano perdido" (45 s, realista) — produccion completa.

Uso: python3 producir_ep2.py [audio|render|mezcla]   (sin argumento: todo)
"""
import json, os, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "v2"))
import producir2 as P                     # utilidades de audio del episodio 1
from producir2 import SR, add, tone, lp, hp, bp, wav_write, wav_read, env

BUILD = os.path.join(HERE, "build")
SALIDA = os.path.join(HERE, "salida")
DUR = 45.0
P.BUILD = BUILD
P.DUR = DUR

# (id, quien, texto en pantalla, texto hablado, inicio, fin maximo)
P.VOCES = [
    ("n1", "narrador", "La noche apenas empezaba… y alguien tocaba la ventana.",
     "La noche apenas empezaba... y alguien tocaba la ventana.", 3.2, 7.0),
    ("p1", "pepino", "No vine a quitarte nada… vine a decirte la verdad.",
     "No vine a quitarte nada... vine a decirte la verdad.", 7.3, 10.9),
    ("b1", "berenjena", "¿Hermano? ¡Tú eres verde y yo soy morado!", "¿Hermano? ¡Tú eres verde, y yo soy morado!", 11.2, 14.3),
    ("n2", "narrador", "Hace años, una tormenta arrasó el huerto y separó a dos pequeñas semillas.",
     "Hace años... una tormenta arrasó el huerto, y separó a dos pequeñas semillas.", 14.8, 19.4),
    ("p2", "pepino", "Mamá Calabaza nos cuidó… hasta que te perdimos.",
     "Mamá Calabaza nos cuidó... hasta que te perdimos.", 19.6, 22.6),
    ("t1", "tomate", "Te lo iba a decir… solo quería que encontraras a tu familia.",
     "Te lo iba a decir... solo quería que encontraras a tu familia.", 23.0, 26.9),
    ("b2", "berenjena", "¡Tengo un hermano!", "¡Tengo un hermano!", 27.4, 28.9),
    ("n3", "narrador", "Por fin, la verdad salió a la luz… o eso creían.",
     "Por fin, la verdad salió a la luz... o eso creían.", 29.1, 32.0),
    ("n4", "narrador", "Porque el pepino no había venido solo a buscar a su hermano…",
     "Porque el pepino... no había venido solo a buscar a su hermano.", 37.0, 41.3),
]


def make_voices():
    from piper import PiperVoice, SynthesisConfig
    voice = PiperVoice.load(P.VOICE)
    os.makedirs(BUILD, exist_ok=True)
    track = np.zeros(int(DUR * SR), np.float32)
    timing = {}
    for vid, who, shown, spoken, t0, tmax in P.VOCES:
        ls = {"narrador": 1.12, "berenjena": 0.98, "pepino": 1.12, "tomate": 1.0}[who]
        for _ in range(5):
            cfg = SynthesisConfig(length_scale=ls, noise_scale=0.62, noise_w_scale=0.75)
            a = np.concatenate([c.audio_int16_array for c in voice.synthesize(spoken, syn_config=cfg)])
            nz = np.where(np.abs(a) > 300)[0]
            a = a[max(0, nz[0] - 300): nz[-1] + 1200]
            k = {"berenjena": 1 / 0.86, "pepino": 1 / 1.2, "tomate": 1 / 0.8, "narrador": 1 / 1.075}[who]
            dur = len(a) / 16000 * k
            if t0 + dur <= tmax or ls < 0.8:
                break
            ls *= (tmax - t0) / dur * 0.98
        raw = os.path.join(BUILD, f"{vid}_raw.wav")
        wav_write(raw, a.astype(np.float32) / 32768, 16000)
        out = os.path.join(BUILD, f"{vid}.wav")
        af = {
            "berenjena": "asetrate=16000*1.22,aresample=44100,atempo=0.86,highpass=f=120,acompressor=threshold=-18dB:ratio=3",
            "pepino": "asetrate=16000*0.80,aresample=44100,atempo=1.2,highpass=f=60,equalizer=f=120:t=q:w=1:g=4,aecho=0.8:0.6:60|120:0.25|0.15",
            "tomate": "asetrate=16000*1.42,aresample=44100,atempo=0.8,highpass=f=180,equalizer=f=3500:t=q:w=1:g=3,acompressor=threshold=-18dB:ratio=2.5",
            "narrador": "asetrate=16000*0.93,aresample=44100,atempo=1.075,highpass=f=70,equalizer=f=180:t=q:w=1:g=3,aecho=0.8:0.5:40:0.12",
        }[who]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af", af, "-ac", "1", "-ar", str(SR), out], check=True)
        x, _ = wav_read(out)
        x = x / (np.max(np.abs(x)) + 1e-9) * 0.9
        i0 = int(t0 * SR)
        n = min(len(x), len(track) - i0)
        track[i0:i0 + n] += x[:n]
        timing[vid] = dict(who=who, text=shown, start=t0, end=t0 + n / SR)
        if who != "narrador":
            hop = SR // 30
            e = [float(np.sqrt(np.mean(x[i:i + hop] ** 2))) for i in range(0, len(x), hop)]
            mx = max(e) + 1e-9
            timing[vid]["env"] = [min(1.0, v / mx * 1.25) for v in e]
        print(f"{vid}: {t0:.2f}-{t0 + n / SR:.2f}s")
    wav_write(os.path.join(BUILD, "voces.wav"), track)
    json.dump(timing, open(os.path.join(BUILD, "voces.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def music():
    n = int(DUR * SR)
    t = np.arange(n) / SR
    m = np.zeros(n)
    drone = lp(tone(55, DUR, "saw") + tone(55 * 1.005, DUR, "saw") * 0.8 + tone(82.4, DUR, "saw") * 0.5, 260)
    inten = np.interp(t, [0, 14, 14.5, 22.5, 27, 31.5, 31.51, 32.2, 42.5, 42.6, 45], [0.5, 0.6, 0.3, 0.3, 0.2, 0.2, 0, 0, 1.0, 0, 0])
    m += drone * inten * 0.35
    # musica tierna (flashback y reencuentro): arpegio en Do mayor con caja de musica
    sweet = np.zeros(n)
    notes = [523.25, 659.25, 783.99, 1046.5, 783.99, 659.25]
    k = 0
    tt = 14.6
    while tt < 31.4:
        d = 0.9
        x = tone(notes[k % len(notes)], d) * np.exp(-np.arange(int(d * SR)) / SR * 4) + tone(notes[k % len(notes)] * 2, d) * 0.2 * np.exp(-np.arange(int(d * SR)) / SR * 6)
        add(sweet, x * 0.18, tt)
        tt += 0.32; k += 1
    pad = lp(tone(261.6, DUR, "saw") + tone(329.6, DUR, "saw") + tone(392, DUR, "saw"), 900)
    m += sweet + pad * np.interp(t, [14, 15, 31, 31.5], [0, 0.05, 0.05, 0])
    # latido grave de suspenso (inicio y final)
    beat = 60 / 70
    tt = 0.3
    while tt < 42.6:
        if tt < 14.4 or tt > 32.2:
            kk = tone(48, 0.4) * np.exp(-np.arange(int(0.4 * SR)) / SR * 9)
            add(m, kk * 0.55 * (1.2 if tt > 32 else 0.7), tt)
        tt += beat if tt < 32.2 else beat * 0.72
    strings = (tone(440, DUR) + tone(466.2, DUR) * 0.6)  # disonante
    trem = 0.5 + 0.5 * np.sin(2 * np.pi * 9 * t)
    m += lp(strings * trem, 3000) * np.interp(t, [0, 32.2, 33, 42.5, 42.6], [0, 0, 0.3, 0.8, 0]) * 0.08
    hit = sum(tone(f, 3.0, "saw") for f in (55, 110, 130.8, 164.8, 220)) * np.exp(-np.arange(int(3.0 * SR)) / SR * 1.6)
    add(m, lp(hit, 1500) * 0.25, 42.6)
    m = np.stack([m, m], 1)
    m[:, 1] = np.roll(m[:, 1], 300)
    return m / (np.max(np.abs(m)) + 1e-9) * 0.8


def sfx():
    n = int(DUR * SR)
    s = np.zeros(n)
    rng = np.random.default_rng(5)

    def knock():
        d = 0.18
        x = lp(rng.standard_normal(int(d * SR)), 900) * np.exp(-np.arange(int(d * SR)) / SR * 30) + tone(180, d) * np.exp(-np.arange(int(d * SR)) / SR * 25) * 0.6
        return x * 0.9

    def thunder(d=3.5):
        x = lp(rng.standard_normal(int(d * SR)), 220) * np.exp(-np.arange(int(d * SR)) / SR * 1.2)
        x[: int(0.08 * SR)] += hp(rng.standard_normal(int(0.08 * SR)), 2000) * 0.8
        return x * 1.2

    def rain(d):
        return bp(rng.standard_normal(int(d * SR)), 1500, 8000) * 0.05

    for k in (0.4, 0.7, 1.0, 2.0, 2.3):
        add(s, knock(), k)
    # ventana que se abre (chirrido)
    sq = np.sin(2 * np.pi * np.cumsum(np.linspace(700, 1100, int(0.7 * SR))) / SR) * np.exp(-np.linspace(0, 3, int(0.7 * SR))) * 0.08
    add(s, sq, 6.9)
    add(s, rain(7.6), 14.6)
    add(s, thunder(), 15.0); add(s, thunder(2.5) * 0.7, 18.7)
    w = rng.standard_normal(int(0.6 * SR))
    whoosh = np.zeros_like(w)
    tt = np.linspace(0, 1, len(w))
    for i in range(0, len(w), 1024):
        fc = 300 + 4000 * np.sin(np.pi * tt[i]) ** 2
        whoosh[i:i + 1024] = bp(w[i:i + 1024], fc * 0.6, min(18000, fc * 1.4), 1)
    whoosh *= np.sin(np.pi * tt) ** 2 * 0.35
    for c in (3.0, 7.0, 11.0, 14.5, 22.6, 27.0, 36.0, 41.0):
        add(s, whoosh, c - 0.3)
    # vibracion + ding del mensaje siniestro
    bz = np.sign(tone(150, 0.38)) * (0.5 + 0.5 * np.sign(tone(18, 0.38)))
    add(s, lp(bz, 900) * env(len(bz), 0.01, 0.03) * 0.35, 32.4)
    dd = (tone(880, 0.9) + tone(1320, 0.9) * 0.5) * np.exp(-np.arange(int(0.9 * SR)) / SR * 5) * 0.3
    add(s, dd, 33.4)
    tb = np.arange(int(2.4 * SR)) / SR
    boom = np.sin(2 * np.pi * np.cumsum(38 + 70 * np.exp(-tb * 7)) / SR) * np.exp(-tb * 2.5)
    add(s, boom * 0.8, 34.4)
    for k in range(6):
        hb = np.zeros(int(0.8 * SR))
        for off, g in ((0, 1.0), (0.22, 0.7)):
            kk = tone(55, 0.25) * np.exp(-np.arange(int(0.25 * SR)) / SR * 18) * g
            hb[int(off * SR):int(off * SR) + len(kk)] += kk
        add(s, lp(hb, 200) * 0.9, 36.4 + k * 0.72)
    add(s, boom * 1.0, 42.6)
    return np.stack([s, s], 1)


def make_audio():
    os.makedirs(BUILD, exist_ok=True)
    make_voices()
    wav_write(os.path.join(BUILD, "musica.wav"), music().reshape(-1), ch=2)
    wav_write(os.path.join(BUILD, "sfx.wav"), np.clip(sfx(), -1, 1).reshape(-1), ch=2)


def mezcla():
    os.makedirs(SALIDA, exist_ok=True)
    out = os.path.join(SALIDA, "DRAMA_VEGETAL_EP02_El_hermano_perdido_45s.mp4")
    fc = ("[1:a]acompressor=threshold=-20dB:ratio=3:attack=5:release=80:makeup=2,equalizer=f=3000:t=q:w=1.2:g=2,"
          "pan=stereo|c0=c0|c1=c0,asplit=2[v][vsc];"
          "[2:a]volume=0.55[m];[m][vsc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[md];"
          "[3:a]volume=0.9[s];[v][md][s]amix=inputs=3:normalize=0,loudnorm=I=-13:TP=-1.0:LRA=9,aresample=48000[a]")
    tmp = os.path.join(BUILD, "final_hq.mp4")
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
        subprocess.run([sys.executable, os.path.join(HERE, "escenas_ep2.py")], check=True)
    if step in ("mezcla", "todo"):
        mezcla()
