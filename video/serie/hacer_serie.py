# -*- coding: utf-8 -*-
"""Produce los 8 episodios de 30 s de la serie "Leonida" (ficcion de fans).

Por episodio: narracion ajustada a 30 s, linea de tiempo, musica, efectos,
render (motor de ../render.py) y mezcla final en serie/salida/.

Uso: python3 hacer_serie.py [numeros de episodio...] [--solo-audio]
"""
import json, os, subprocess, sys, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

import tts
import musica
from episodios import EPISODIOS, PRONUNCIACION_EXTRA
from piper import PiperVoice, SynthesisConfig

BUILD = os.path.join(HERE, "build")
SALIDA = os.path.join(HERE, "salida")
SR = tts.SR
DUR = 30.0
T_TITLE = 2.6          # cortinilla de titulo
T_VOICE = 2.85         # comienzo de la narracion
T_END = 27.0           # comienzo de "continuara"
GAP = 0.35

tts.PRONUNCIACION[:0] = PRONUNCIACION_EXTRA

PROGRESIONES = [
    ([[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]], [45, 41, 36, 43]),   # Am F C G
    ([[50, 53, 57], [46, 50, 53], [53, 57, 60], [48, 52, 55]], [38, 34, 41, 36]),   # Dm Bb F C
    ([[52, 55, 59], [48, 52, 55], [55, 59, 62], [50, 54, 57]], [40, 36, 43, 38]),   # Em C G D
    ([[57, 60, 64], [53, 57, 60], [50, 53, 57], [52, 56, 59]], [45, 41, 38, 40]),   # Am F Dm E
]


def speech_text(s):
    return tts.to_speech(s.replace("«", "").replace("»", ""))


def synth_all(voice, lines, ls):
    cfg = SynthesisConfig(length_scale=ls, noise_scale=0.6, noise_w_scale=0.7)
    return [tts.synth(voice, speech_text(l), cfg) for l in lines]


def build_episode(voice, ep, nxt):
    d = os.path.join(BUILD, f"ep{ep['num']:02d}")
    os.makedirs(d, exist_ok=True)
    lines = [l for sh in ep["shots"] for l in sh["lines"]]
    avail = T_END - T_VOICE - 0.35
    ls = 1.06
    for _ in range(4):
        audios = synth_all(voice, lines, ls)
        speech = sum(len(a) for a in audios) / SR
        total = speech + GAP * (len(lines) - 1)
        if total <= avail or ls <= 0.84:
            break
        ls = max(0.84, ls * (avail - GAP * (len(lines) - 1)) / speech * 0.99)
    gap = GAP
    if total < avail - 1.0:    # sobra tiempo: pausas algo mas largas
        gap = min(0.8, GAP + (avail - 1.0 - total) / max(1, len(lines) - 1))
    print(f"EP{ep['num']}: voz {speech:.1f}s, length_scale {ls:.2f}, pausa {gap:.2f}s", flush=True)

    voz = np.zeros(int(DUR * SR), np.int16)
    t = T_VOICE
    scenes = [dict(visual="ep_title", start=0.0, end=T_TITLE, lines=[])]
    subs = []
    li = 0
    for si, sh in enumerate(ep["shots"]):
        entry = {k: v for k, v in sh.items() if k != "lines"}
        entry["lines"] = []
        entry["start"] = T_TITLE if si == 0 else max(scenes[-1]["start"] + 0.5, t - 0.25)
        if si > 0:
            scenes[-1]["end"] = entry["start"]
        for line in sh["lines"]:
            a = audios[li]
            dur = len(a) / SR
            i0 = int(t * SR)
            voz[i0:i0 + len(a)] = a[:len(voz) - i0]
            entry["lines"].append({"text": line, "start": t, "end": t + dur})
            parts = tts.split_subs(line)
            tot = sum(len(p) for p in parts)
            st = t
            for p in parts:
                dd = dur * len(p) / tot
                subs.append({"text": p, "start": st, "end": st + dd})
                st += dd
            t += dur + gap
            li += 1
        scenes.append(entry)
    scenes[-1]["end"] = T_END
    scenes.append(dict(visual="ep_end", start=T_END, end=DUR, lines=[]))
    meta = dict(num=ep["num"], title=ep["title"], next=nxt, final=ep.get("final", False))
    tl = dict(scenes=scenes, subs=subs, duration=DUR, meta=meta)
    json.dump(tl, open(os.path.join(d, "timeline.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with wave.open(os.path.join(d, "voz.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(voz.tobytes())

    # musica y efectos
    prog = PROGRESIONES[3] if ep.get("final") else PROGRESIONES[(ep["num"] - 1) % 3]
    musica.CHORDS, musica.BASS = prog
    musica.rng = np.random.default_rng(ep["num"])
    musica.save(os.path.join(d, "musica.wav"), musica.make_music(DUR, [], intro_bars=1))
    sfx = np.zeros((int(DUR * musica.SR) + musica.SR * 3, 2))
    musica.add(sfx, musica.boom(2.0) * 0.6, 0.15)
    for sc in scenes:
        if sc["visual"].startswith("card_") or sc["visual"] == "ep_end":
            musica.add(sfx, musica.whoosh(1.0) * 0.8, max(0, sc["start"] - 0.5))
        if sc["visual"] == "ep_end":
            musica.add(sfx, musica.boom(2.5) * (0.9 if ep.get("final") else 0.5), sc["start"] + 0.1)
        if sc["visual"] == "black":
            musica.add(sfx, musica.boom(2.5), sc["start"] + 0.9)
        if sc.get("photo"):
            musica.add(sfx, musica.riser(2.0) * 0.7, sc["start"])
    musica.save(os.path.join(d, "sfx.wav"), sfx[:int(DUR * musica.SR)] * 0.8)
    return d


def render_episode(d):
    env = dict(os.environ, TIMELINE=os.path.join(d, "timeline.json"), CHUNKS=os.path.join(d, "chunks"),
               OUT=os.path.join(d, "mudo.mp4"), STEP="225", FADE_OUT="0.7")
    subprocess.run([sys.executable, os.path.join(HERE, "render_serie.py")], env=env, check=True)


def mix_episode(d, ep):
    os.makedirs(SALIDA, exist_ok=True)
    name = f"EP{ep['num']:02d}_" + "".join(c if c.isalnum() else "_" for c in
                                           ep["title"].replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")) + ".mp4"
    out = os.path.join(SALIDA, name)
    fc = ("[1:a]aresample=48000,highpass=f=90,equalizer=f=250:t=q:w=1:g=-2,equalizer=f=3200:t=q:w=1.2:g=3,"
          "acompressor=threshold=-22dB:ratio=3:attack=5:release=90:makeup=2,pan=stereo|c0=c0|c1=c0,asplit=2[v][vsc];"
          "[2:a]aresample=48000,volume=0.34[m];[m][vsc]sidechaincompress=threshold=0.02:ratio=8:attack=30:release=400[md];"
          "[3:a]aresample=48000,volume=0.8[s];[v][md][s]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=9,aresample=48000[a]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(d, "mudo.mp4"), "-i", os.path.join(d, "voz.wav"),
                    "-i", os.path.join(d, "musica.wav"), "-i", os.path.join(d, "sfx.wav"), "-filter_complex", fc,
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", str(DUR), out], check=True)
    print("listo:", out, flush=True)
    return out


def main():
    nums = [int(a) for a in sys.argv[1:] if a.isdigit()] or [e["num"] for e in EPISODIOS]
    voice = PiperVoice.load(tts.VOICE)
    for ep in EPISODIOS:
        if ep["num"] not in nums:
            continue
        nxt = next((e["title"] for e in EPISODIOS if e["num"] == ep["num"] + 1), None)
        d = build_episode(voice, ep, nxt)
        if "--solo-audio" in sys.argv:
            continue
        render_episode(d)
        mix_episode(d, ep)


if __name__ == "__main__":
    main()
