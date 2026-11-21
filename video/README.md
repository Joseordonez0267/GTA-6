# GTA VI: La historia completa — video generado por código

Video largo (~9 min, 1080p30) sobre el lanzamiento de *Grand Theft Auto VI*
(19 de noviembre de 2026): guion, narración, ilustraciones, música y montaje,
todo producido con scripts en este directorio.

| Archivo | Qué hace |
|---|---|
| `guion.py` | Guion completo (escenas, frases, rótulos) y diccionario de pronunciación |
| `GUION.md` | El guion en formato legible |
| `tts.py` | Narración con voz sintética offline (Piper, voz `es-carlfm-x-low`) y línea de tiempo con subtítulos |
| `arte.py` | Ilustraciones originales por capas (Vice City, Keys, pantanos, puerto, etc.) |
| `render.py` | Montaje: cámara con paralaje, gráficos animados, rótulos, subtítulos y transiciones |
| `musica.py` | Música synthwave original y efectos de sonido sintetizados |
| `mezclar.sh` | Mezcla final con ffmpeg (ducking de la música bajo la voz, loudnorm) |

## Reproducir

```bash
pip install piper-tts numpy pillow scipy
python3 tts.py        # build/voz.wav + build/timeline.json
python3 musica.py     # build/musica.wav + build/sfx.wav
python3 render.py     # build/video_mudo.mp4  (python3 render.py --preview 30 60 para cuadros sueltos)
./mezclar.sh          # GTA6_La_Historia_Completa.mp4
```

El modelo de voz está en `voices/` (descargado de los releases de rhasspy/piper, licencia en su MODEL_CARD).

## Fuentes

CBS News, Al Jazeera, Variety (Metacritic 99), Rolling Stone / CBC (3.790 M USD en 24 h),
TechRadar y otros (precio 79,99 / 99,99 USD), Vice (PC y Online). Las cifras de la empresa se
atribuyen como tales en la narración.

Video de fans, sin afiliación con Rockstar Games ni Take-Two. No usa imágenes, música ni logotipos oficiales.
