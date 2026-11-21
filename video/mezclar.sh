#!/usr/bin/env bash
# Mezcla final: video mudo + voz + musica (con ducking bajo la voz) + efectos
set -euo pipefail
cd "$(dirname "$0")/build"
ffmpeg -y -loglevel error -i video_mudo.mp4 -i voz.wav -i musica.wav -i sfx.wav -filter_complex "\
[1:a]aresample=48000,highpass=f=90,equalizer=f=250:t=q:w=1:g=-2,equalizer=f=3200:t=q:w=1.2:g=3,acompressor=threshold=-22dB:ratio=3:attack=5:release=90:makeup=2,pan=stereo|c0=c0|c1=c0,asplit=2[v][vsc];\
[2:a]aresample=48000,volume=0.30[m];\
[m][vsc]sidechaincompress=threshold=0.02:ratio=8:attack=30:release=500[md];\
[3:a]aresample=48000,volume=0.8[s];\
[v][md][s]amix=inputs=3:normalize=0,loudnorm=I=-15:TP=-1.5:LRA=11,aresample=48000[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -movflags +faststart -shortest ../GTA6_La_Historia_Completa.mp4
echo "Listo: video/GTA6_La_Historia_Completa.mp4"
