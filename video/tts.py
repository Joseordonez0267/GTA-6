# -*- coding: utf-8 -*-
"""Genera la narracion (voz offline con Piper) y la linea de tiempo del video.

Salida (en build/):
  voz.wav        narracion completa, 16 kHz mono
  timeline.json  escenas, frases y subtitulos con tiempos exactos
"""
import json, os, re, sys, wave
import numpy as np
from piper import PiperVoice, SynthesisConfig

from guion import SCENES, PRONUNCIACION

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")
VOICE = os.environ.get("VOICE_MODEL", os.path.join(HERE, "voices", "es-carlfm-x-low.onnx"))

SR = 16000
INTRO_PAD = 1.2      # silencio antes de la primera frase
SCENE_PRE = 0.5      # silencio al comienzo de cada escena
LINE_GAP = 0.55      # pausa entre frases
SCENE_POST = 0.9     # silencio al final de cada escena
CHAPTER_DUR = 3.2    # duracion de las cortinillas de capitulo
OUTRO_TAIL = 6.0     # cola final con la musica


def to_speech(text):
    for a, b in PRONUNCIACION:
        text = re.sub(r"(?<![\wÁÉÍÓÚáéíóúñ])" + re.escape(a) + r"(?![\wÁÉÍÓÚáéíóúñ])", b, text)
    return text.replace("...", ",")


def split_subs(text, maxlen=78):
    """Divide una frase en trozos de subtitulo legibles."""
    if len(text) <= maxlen:
        return [text]
    parts = re.split(r"(?<=[,:;.])\s+", text)
    out, cur = [], ""
    for p in parts:
        if cur and len(cur) + 1 + len(p) > maxlen:
            out.append(cur)
            cur = p
        else:
            cur = (cur + " " + p).strip()
    if cur:
        out.append(cur)
    # trozos aun demasiado largos: cortar por palabras
    final = []
    for c in out:
        while len(c) > maxlen + 20:
            words = c.split()
            acc = ""
            while words and len(acc) + len(words[0]) + 1 <= maxlen:
                acc = (acc + " " + words.pop(0)).strip()
            final.append(acc)
            c = " ".join(words)
        final.append(c)
    return final


def synth(voice, text, cfg):
    chunks = list(voice.synthesize(text, syn_config=cfg))
    audio = np.concatenate([c.audio_int16_array for c in chunks])
    # recorta silencios de los extremos
    nz = np.where(np.abs(audio) > 300)[0]
    if len(nz):
        audio = audio[max(0, nz[0] - 400): nz[-1] + 1600]
    return audio


def main():
    os.makedirs(BUILD, exist_ok=True)
    voice = PiperVoice.load(VOICE)
    cfg = SynthesisConfig(length_scale=1.06, noise_scale=0.6, noise_w_scale=0.7)

    pieces = []
    t = 0.0

    def silence(sec):
        nonlocal t
        pieces.append(np.zeros(int(round(sec * SR)), dtype=np.int16))
        t += sec

    timeline = {"scenes": [], "subs": []}
    silence(INTRO_PAD)
    for i, sc in enumerate(SCENES):
        start = 0.0 if i == 0 else t
        entry = {k: v for k, v in sc.items() if k != "lines"}
        entry["lines"] = []
        if sc["visual"] == "chapter":
            silence(CHAPTER_DUR)
        else:
            silence(SCENE_PRE)
            for j, line in enumerate(sc["lines"]):
                a = synth(voice, to_speech(line), cfg)
                dur = len(a) / SR
                entry["lines"].append({"text": line, "start": t, "end": t + dur})
                subs = split_subs(line)
                total = sum(len(s) for s in subs)
                st = t
                for s in subs:
                    d = dur * len(s) / total
                    timeline["subs"].append({"text": s, "start": st, "end": st + d})
                    st += d
                pieces.append(a)
                t += dur
                if j < len(sc["lines"]) - 1:
                    silence(LINE_GAP)
            silence(SCENE_POST)
            print(f"[{i:02d}] {sc['visual']:12s} {t:7.1f}s", flush=True)
        if i == len(SCENES) - 1:
            silence(OUTRO_TAIL)
        entry["start"] = start
        entry["end"] = t
        timeline["scenes"].append(entry)

    audio = np.concatenate(pieces)
    with wave.open(os.path.join(BUILD, "voz.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(audio.tobytes())
    timeline["duration"] = t
    with open(os.path.join(BUILD, "timeline.json"), "w", encoding="utf-8") as f:
        json.dump(timeline, f, ensure_ascii=False, indent=1)
    print(f"Duracion total: {t/60:.2f} min")


if __name__ == "__main__":
    main()
