# -*- coding: utf-8 -*-
"""Musica synthwave original y efectos de sonido, sintetizados con numpy/scipy.

Salida: build/musica.wav y build/sfx.wav (44.1 kHz estereo), con la misma
duracion que la narracion.
"""
import json, os, wave
import numpy as np
from scipy.signal import butter, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
SR = 44100
BPM = 96
BEAT = 60 / BPM
BAR = 4 * BEAT
rng = np.random.default_rng(7)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, "low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def saw(f, n, phase=0.0):
    t = np.arange(n) / SR
    return 2 * ((t * f + phase) % 1.0) - 1


def env_adsr(n, a, d, s, r):
    e = np.ones(n) * s
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    na, nd = min(na, n), min(nd, max(0, n - na))
    e[:na] = np.linspace(0, 1, na)
    e[na:na + nd] = np.linspace(1, s, nd)
    if nr and n > nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


# progresion: Am - F - C - G  (i - VI - III - VII)
CHORDS = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
BASS = [45, 41, 36, 43]


def add(buf, sig, start):
    i = int(start * SR)
    if i >= buf.shape[0]:
        return
    j = min(buf.shape[0], i + sig.shape[0])
    buf[i:j] += sig[:j - i]


def pad_chord(notes, dur):
    n = int(dur * SR)
    out = np.zeros((n, 2))
    for k, m in enumerate(notes + [notes[0] + 12]):
        for det, ch in ((-0.12, 0), (0.12, 1), (0.0, 0), (0.0, 1)):
            f = midi(m) * 2 ** (det / 12)
            out[:, ch] += saw(f, n, rng.random()) * 0.25
    e = env_adsr(n, 0.8, 0.5, 0.85, 0.9)[:, None]
    out = np.stack([lp(out[:, c], 1400) for c in range(2)], 1)
    return out * e * 0.18


def bass_note(m, dur):
    n = int(dur * SR)
    x = saw(midi(m), n) * 0.7 + np.sign(np.sin(2 * np.pi * midi(m - 12) * np.arange(n) / SR)) * 0.3
    x = lp(x, 500)
    e = env_adsr(n, 0.005, 0.12, 0.6, 0.05)
    return np.stack([x * e, x * e], 1) * 0.32


def arp_note(m, dur, pan):
    n = int(dur * SR)
    x = saw(midi(m), n) + saw(midi(m) * 1.003, n)
    x = lp(x, 3000)
    e = env_adsr(n, 0.003, 0.15, 0.2, 0.05)
    s = x * e * 0.07
    return np.stack([s * (1 - pan), s * pan], 1)


def kick():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 50 + 120 * np.exp(-t * 30)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
    return np.stack([x, x], 1) * 0.55


def snare():
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    x = bp(rng.standard_normal(n), 1200, 7000) * np.exp(-t * 18) * 0.5 + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25) * 0.3
    return np.stack([x, x], 1) * 0.5


def hat():
    n = int(0.06 * SR)
    t = np.arange(n) / SR
    x = hp(rng.standard_normal(n), 8000) * np.exp(-t * 60)
    return np.stack([x * 0.8, x], 1) * 0.12


def simple_reverb(x, mix=0.25):
    out = x.copy()
    for d, g in ((0.031, 0.5), (0.047, 0.45), (0.071, 0.4), (0.113, 0.33), (0.171, 0.27), (0.263, 0.2)):
        k = int(d * SR)
        out[k:, 0] += x[:-k, 1] * g * mix
        out[k:, 1] += x[:-k, 0] * g * mix
    return out


def make_music(duration, chapters):
    n = int(duration * SR) + SR
    pads = np.zeros((n, 2)); bass = np.zeros((n, 2)); arps = np.zeros((n, 2)); drums = np.zeros((n, 2))
    K, S, Hh = kick(), snare(), hat()
    bars = int(duration / BAR) + 2
    intro_bars = 4
    for b in range(bars):
        t0 = b * BAR
        ci = b % 4
        add(pads, pad_chord(CHORDS[ci], BAR + 0.6), t0)
        section = (b // 16) % 4          # cada 16 compases cambia la textura
        breakdown = (b % 16) >= 14       # dos compases sin bateria al final de cada bloque
        if b >= intro_bars:
            for e in range(8):
                note = BASS[ci] + (12 if e in (3, 7) else 0)
                add(bass, bass_note(note, BEAT / 2 * 0.9), t0 + e * BEAT / 2)
        if b >= intro_bars + 4 and section != 2:
            ch = CHORDS[ci]
            seq = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[1] + 12]
            for e in range(16):
                add(arps, arp_note(seq[e % 4] + (12 if section == 3 and e % 8 >= 4 else 0), BEAT / 4, 0.3 + 0.4 * (e % 2)), t0 + e * BEAT / 4)
        if b >= intro_bars + 2 and not breakdown:
            for q in range(4):
                add(drums, K, t0 + q * BEAT)
                if q in (1, 3):
                    add(drums, S, t0 + q * BEAT)
            for e in range(8):
                add(drums, Hh * (1.0 if e % 2 else 0.6), t0 + e * BEAT / 2)
    music = pads + bass + simple_reverb(arps, 0.6) + drums * 0.9
    music = simple_reverb(music, 0.15)
    # fundido final
    music = music[:int(duration * SR)]
    fo = int(5 * SR)
    music[-fo:] *= np.linspace(1, 0, fo)[:, None]
    fi = int(2 * SR)
    music[:fi] *= np.linspace(0, 1, fi)[:, None]
    music /= np.max(np.abs(music)) + 1e-9
    return music * 0.9


def whoosh(dur=1.2):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    blk = 1024
    for i in range(0, n, blk):
        fc = 300 + 5000 * np.sin(np.pi * t[i]) ** 2
        seg = x[i:i + blk]
        out[i:i + blk] = bp(seg, max(100, fc * 0.6), min(18000, fc * 1.4), 1)
    e = np.sin(np.pi * t) ** 2
    pan = t
    s = out * e * 0.6
    return np.stack([s * (1 - pan * 0.6), s * (0.4 + pan * 0.6)], 1)


def boom(dur=2.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 40 + 60 * np.exp(-t * 6)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)
    x += lp(rng.standard_normal(n), 300) * np.exp(-t * 4) * 0.5
    return np.stack([x, x], 1) * 0.8


def riser(dur=3.0):
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    blk = 1024
    for i in range(0, n, blk):
        fc = 400 + 6000 * t[i] ** 2
        out[i:i + blk] = bp(x[i:i + blk], fc * 0.7, min(18000, fc * 1.3), 1)
    s = out * t ** 2 * 0.5
    return np.stack([s, s], 1)


def save(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def main():
    tl = json.load(open(os.path.join(BUILD, "timeline.json"), encoding="utf-8"))
    dur = tl["duration"]
    chapters = [s["start"] for s in tl["scenes"] if s["visual"] == "chapter"]
    save(os.path.join(BUILD, "musica.wav"), make_music(dur, chapters))
    sfx = np.zeros((int(dur * SR) + SR * 3, 2))
    for c in chapters:
        add(sfx, whoosh(1.2), max(0, c - 0.6))
        add(sfx, boom(2.0) * 0.5, c + 0.25)
    sc0 = tl["scenes"][0]
    if len(sc0["lines"]) >= 4:
        r = sc0["lines"][3]["start"]
        add(sfx, riser(3.0), max(0, r - 3.0))
        add(sfx, boom(2.5), r)
    outro = tl["scenes"][-1]
    if len(outro["lines"]) >= 3:
        add(sfx, boom(2.5) * 0.7, outro["lines"][2]["start"])
    save(os.path.join(BUILD, "sfx.wav"), sfx[:int(dur * SR)] * 0.8)
    print("musica.wav y sfx.wav listos")


if __name__ == "__main__":
    main()
