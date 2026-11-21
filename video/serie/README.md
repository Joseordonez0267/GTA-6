# Serie "Leonida" — 8 episodios de 30 s (ficción de fans)

Continuación inventada del documental, con personajes: Brian Heder, Cal Hampton,
Boobie Ike, Dre'Quan Priest, Real Dimez y Raul Bautista se suman a Lucía y Jason.

- `episodios.py` — guion de los 8 episodios y fichas de personajes
- `GUION_SERIE.md` — el guion en formato legible
- `personajes.py` — siluetas estilizadas de los personajes y escenarios nuevos
- `render_serie.py` — gráficos de la serie (fichas, título, "continuará", etc.) sobre el motor de `../render.py`
- `hacer_serie.py` — produce todo: voz ajustada a 30 s, música, efectos, render y mezcla
- `salida/` — los episodios terminados (1080p, 30 s)

```bash
python3 hacer_serie.py          # los 8 episodios
python3 hacer_serie.py 3 4      # solo algunos
```

Historia inventada por fans, sin relación con la trama oficial ni con Rockstar Games.
