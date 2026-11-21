# DRAMA VEGETAL 🍆 · Episodio 1: EL SECRETO DE LA BERENJENA

Formato: YouTube Shorts · 9:16 · 1080×1920 · 30 s · español latino neutro

## 0. Qué incluye esta entrega

| Pieza | Estado |
|---|---|
| `salida/DRAMA_VEGETAL_EP01_El_secreto_de_la_berenjena.mp4` | **Video terminado y producido aquí.** Animación 2D con sombreado de volumen (no es 3D real), con voces, subtítulos animados, música, efectos y movimiento de labios básico |
| Este documento | Paquete para producir la **versión 3D estilo Pixar** con un generador de video (Veo, Kling, Runway, Sora, Hailuo…) |
| `vegetales.py`, `escenas.py`, `producir.py` | Código que genera el video (para modificarlo o hacer el episodio 2) |

> Importante: en este entorno no hay un generador de video 3D. El MP4 entregado es una animación 2D hecha por código. Los prompts de abajo son para producir la versión 3D con una herramienta externa.

---

## 1. Guía de consistencia visual (pegar al inicio de CADA prompt)

**Bloque de estilo global**
```
3D animated feature film still, Pixar-quality stylized CGI, soft global illumination, subsurface scattering on vegetable skin, cinematic shallow depth of field, rich saturated colors, dramatic moody night lighting, cool blue moonlight key with warm practical accents, 9:16 vertical composition, 1080x1920. Characters are ONLY anthropomorphic vegetables with expressive cartoon faces. NO human bodies, NO arms, NO hands, NO legs, NO human skin. Vegetables move by hopping, leaning and tilting.
```

**Fichas fijas de personaje** (copiar textualmente, sin cambiar palabras)

- **BERENJENA (él):** `a glossy deep-purple eggplant character, pear-shaped with a narrow neck and round bulbous bottom, green star-shaped calyx cap with a short curved stem on top, large brown expressive eyes with white highlights, thick dark eyebrows, small mouth, no arms, no legs`
- **TOMATE (ella):** `a shiny round bright-red tomato character, smooth skin with subtle lobes, small green leafy calyx and tiny stem on top, big green eyes with delicate eyelashes, soft pink cheeks, charming smile, no arms, no legs`
- **PEPINO:** `a tall slim dark-green cucumber character with light bumpy spots and faint lighter stripes, half-closed mysterious amber eyes, heavy eyelids, sly smirk, no arms, no legs`

**Escenario fijo:** `a cozy bedroom at night: window with a full moon and starry sky on the left, purple curtains, wooden headboard bed with a purple blanket and a pale blue pillow, small wooden nightstand with a lamp turned off, moonlight beam crossing the room`

**Reglas para que no cambien los personajes:**
1. Genera primero **una imagen de referencia de cada personaje** (con los bloques de arriba sobre fondo neutro) y úsala como *image reference / character reference* en todas las escenas.
2. Usa la misma **seed** en todas las tomas si la herramienta lo permite.
3. No describas nunca ropa, manos ni cuerpo. Si la herramienta añade brazos, agrega en el *negative prompt*: `arms, hands, fingers, legs, human body, human skin, clothes`.
4. Mantén la paleta: berenjena #5B2A86, tomate #E0262B, pepino #2F7A3A, luz de luna #8CAAFF.
5. Genera clips de 3 a 5 s (una toma por clip) y únelos en edición; no pidas 10 s seguidos.

**Negative prompt general:**
```
human, person, arms, hands, fingers, legs, feet, human skin, clothing, text, watermark, logo, deformed face, extra eyes, changing character design, realistic photo
```

---

## 2. Prompts por toma

### ESCENA 1 · 0–10 s

**T1 · Gancho (0–2 s)**
```
[ESTILO GLOBAL] [ESCENARIO]. Wide shot. The TOMATE [FICHA TOMATE] sleeps peacefully on the pillow, eyes closed, smiling. Under the pillow a hidden smartphone vibrates and glows cyan, making the pillow shake. In the foreground, the BERENJENA [FICHA BERENJENA] slowly turns his eyes toward the glowing pillow, eyebrows raising with suspicion. Slow push-in camera.
```

**T2 · Se acerca (2–4,6 s)**
```
[ESTILO GLOBAL] [ESCENARIO]. Medium shot of the BERENJENA [FICHA] hopping softly toward the bed, cyan phone light illuminating his face from the right, curious worried expression, eyes wide. Handheld camera, slight dolly-in.
```

**T3 · El teléfono (4,6–7,6 s)**
```
[ESTILO GLOBAL]. Close-up of a smartphone lying on a purple blanket at night, screen unlocking, lock icon opens, chat app shows an incoming message bubble from "Número oculto". Blurred bokeh bedroom background, cinematic glow from the screen.
```
*(El texto del mensaje se añade en edición; los generadores escriben mal el texto.)*

**T4 · Ojos abiertos (7,6–10 s)**
```
[ESTILO GLOBAL]. Extreme close-up of the BERENJENA's [FICHA] face, eyes snap wide open in shock, pupils shrink, eyebrows shoot up, tiny "o" mouth, a sweat drop appears. Fast crash zoom-in, purple dramatic rim light, dark background with subtle speed lines.
```

### ESCENA 2 · 10–20 s

**T5 · La foto (10–12,4 s)**
```
[ESTILO GLOBAL]. Close-up of the smartphone screen scrolling a chat; a photo appears: the TOMATE [FICHA] blushing and the PEPINO [FICHA] smirking, pressed cheek to cheek in a loving hug-lean (no arms), sunset beach behind them, a heart floating above. Quick screen shake.
```

**T6 · Furia (12,4–16 s)**
```
[ESTILO GLOBAL] [ESCENARIO], red emotional lighting. Medium close-up of the BERENJENA [FICHA] trembling with sadness and fury, angry slanted eyebrows, tears streaming, shouting with mouth wide open. Camera shakes subtly, red vignette.
```
*(Lip-sync: usa la función de sincronización labial de la herramienta con el audio `¡¿Con él?! ¡No puedo creerlo!`, o anima la boca en edición.)*

**T7 · Tristeza (16–20 s)**
```
[ESTILO GLOBAL] [ESCENARIO], rain drops sliding on the window. Wide shot: the BERENJENA [FICHA] slumped and crying alone in the foreground while the TOMATE [FICHA] keeps sleeping happily on the pillow in the background. Slow push-in, melancholic blue light.
```

### ESCENA 3 · 20–30 s

**T8 · Revelación (20,6–23,8 s)**
```
[ESTILO GLOBAL]. Smartphone screen in total darkness, the only light source; typing indicator dots, then a new message bubble appears. Slight camera shake on arrival.
```
*(Texto en edición: «Él todavía no sabe que el pepino es su verdadero hermano…».)*

**T9 · Paralizado (23,8–27,4 s)**
```
[ESTILO GLOBAL] [ESCENARIO], very dark. Very slow dolly-in to the BERENJENA's [FICHA] frozen face: wide eyes, tiny pupils, small open mouth, sweat drop, completely paralyzed. Behind him, outside the window, the silhouette of the PEPINO [FICHA] appears in the moonlight with softly glowing amber eyes and a sly smirk.
```

**T10 · Cierre (27,4–30 s):** pantalla negra hecha en edición (no hace falta generarla).

---

## 3. Narración y diálogos (separados)

| Tiempo | Quién | Texto | Indicación de voz |
|---|---|---|---|
| 0,5–4,2 s | Narrador | «Pensaba que su relación era perfecta… hasta que encontró ese mensaje.» | Grave, íntimo, pausa en «perfecta…» |
| 12,7–14,2 s | Berenjena | «¡¿Con él?! ¡No puedo creerlo!» | Aguda, quebrada, entre llanto y grito |
| 16,3–18,7 s | Narrador | «Pero lo peor no era que le estuviera siendo infiel…» | Lento, misterioso |
| 24,0–27,3 s | Narrador | «Lo que descubrió esa noche cambiaría todo el huerto para siempre.» | Susurrado y épico, cierre fuerte en «para siempre» |

**Textos en pantalla (mensajes del teléfono):**
1. «No puedo seguir ocultándote lo de la berenjena…» (5,5 s)
2. Foto de la tomate con el pepino (10,95 s)
3. «Él todavía no sabe que el pepino es su verdadero hermano…» (21,45 s, con «verdadero hermano» resaltado en amarillo)

**Texto de gancho (0–2 s):** «¿QUÉ ESCONDE ELLA?»
**Cierre:** «CONTINUARÁ…» + «¿QUIERES LA PARTE 2? COMENTA 🍆»

> Voces: en el MP4 entregado se usan voces sintéticas (no hay voces humanas en este entorno). Para la versión final se recomienda grabar con locutores o usar una voz de IA en español latino con emoción (por ejemplo, ElevenLabs).

---

## 4. Música y efectos de sonido

| Tiempo | Sonido |
|---|---|
| 0–20 s | Música de suspenso: dron grave en La menor + latido de bajo a 70 BPM; desde los 10 s entran cuerdas en trémolo |
| 0,2 s y 1,0 s | Vibración de teléfono (bzzz) |
| Cada corte | *Whoosh* corto |
| 5,55 s | *Ding* de mensaje |
| 7,6 s | Golpe orquestal + *sting* disonante (ojos abiertos) |
| 10,95 s | *Ding* (llega la foto) |
| 11,6 s | **Golpe dramático** (*boom*) + destello blanco |
| **20,0–20,6 s** | **SILENCIO TOTAL** (la música se corta) |
| 20,75–21,4 s | Clics de teclado (escribiendo…) |
| 21,45 s | *Ding* agudo (mensaje final) |
| 22,3 s | *Boom* grave |
| 23,8–27,4 s | Latidos de corazón + música que crece al máximo |
| 27,4 s | Golpe final y acorde que se apaga sobre «CONTINUARÁ…» |

Bibliotecas libres recomendadas: YouTube Audio Library (filtro «Dramatic / Suspense»), Pixabay Sound Effects.

---

## 5. Plan de edición (CapCut / Premiere / DaVinci)

1. **Proyecto** 1080×1920, 30 fps, 30,0 s exactos.
2. **Pistas de video:** T1–T9 en orden con los tiempos de la sección 2. Cortes secos con un flash negro de 2 cuadros; destello blanco de 0,4 s en 11,6 s.
3. **Movimiento:** si un clip queda estático, añade zoom digital (Ken Burns): 100→108 % en planos generales, 100→135 % rápido en T4 y 100→125 % lento en T9. Sacudida de cámara en T5 (11,6 s), T6 completo y T8 (22,3 s).
4. **Teléfono:** pon los mensajes como capas de texto/imagen sobre T3, T5 y T8 con animación *pop* (escala 60→100 % con rebote, 0,35 s).
5. **Subtítulos:** Inter/Montserrat Black, 80–92 px, mayúsculas, blanco con borde negro de 9 px, 3 palabras por bloque y la palabra actual en **amarillo** (#FFE232). Para el diálogo de la berenjena, palabra actual en **morado** (#C88CFF) con 🍆 encima. Colócalos en el 40 % superior cuando la cara está abajo, y nunca en el 15 % inferior (ahí está la interfaz de Shorts).
6. **Marca:** «🍆 DRAMA VEGETAL · EP. 1» arriba al centro (y = 210 px), oculto en los planos del teléfono y en el cierre.
7. **Audio:** voces a −14 LUFS, música con *ducking* (−8 dB bajo la voz), efectos por encima de la música. Volumen final −13 LUFS, pico −1 dBTP.
8. **Exportar:** H.264, 1080×1920, 30 fps, 12–16 Mbps, AAC 192 kbps.

---

## 6. Publicación en YouTube Shorts

- **Título:** `Encontró el teléfono secreto de su novia… 😱🍆 | DRAMA VEGETAL Ep. 1`
- **Descripción:**
  ```
  La berenjena creía que su relación con la tomate era perfecta… hasta esa noche. 🍅🥒
  ¿Qué harías tú en su lugar? 👇 Comenta "PARTE 2" si quieres saber qué pasa.
  #dramavegetal #shorts #animacion #drama #berenjena #historias #plottwist
  ```
- **Comentario fijado:** `¿Team Berenjena 🍆 o Team Pepino 🥒? La parte 2 sale cuando lleguemos a 1.000 comentarios 👀`
- **Miniatura / primer cuadro:** primerísimo plano de la berenjena con los ojos abiertos y el texto «¿QUÉ ESCONDE ELLA?».
- **Bucle:** el final en negro con «CONTINUARÁ…» corta antes de que se apague la música, así el Short tiende a repetirse solo.
