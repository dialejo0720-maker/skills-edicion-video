---
name: cancion-video-karaoke
description: Crea canciones personalizadas (letra + estilo para Suno) y su video vertical tipo karaoke con las fotos del cliente, sincronizado al ritmo y con la letra palabra por palabra. Producto Musical. Actívala cuando el usuario quiera "hacer una canción para alguien", "canción de cumpleaños/aniversario/regalo", "letra para Suno", "video con la canción y las fotos", "video karaoke", "video con subtítulos de la canción", o mencione una canción personalizada, Suno, karaoke, o un pedido de un cliente con fotos y dedicatoria.
---

# Canción personalizada + video karaoke

Proceso probado con pedidos reales (cumpleaños, merengue — el cliente dijo que quedó "espectacular").
Dos fases: **(A) letra para Suno** y **(B) video vertical 1080×1920** con fotos + karaoke.
Todo en español LATAM, cálido y cercano. Responder al usuario en español.

## Estructura de carpetas (una por pedido)
```
<carpeta de pedidos>/cancion-<nombre>/
  letra-suno.md          ← fase A
  fotos/                 ← el usuario sube las fotos
  <cancion>.mp3          ← el usuario sube el MP3 de Suno (cualquier nombre)
  video/                 ← todo lo técnico (proyecto.json, lineas.txt, json, chunks…)
  Feliz-Cumpleanos-<Nombre>.mp4 / -WhatsApp.mp4   ← entregables
```
Scripts en `${CLAUDE_SKILL_DIR}/scripts/` (referirse como `$S`). Ejecutarlos con `python` normal
(NO `python -I`: no ve faster_whisper/librosa instalados en site-packages del usuario).

Requisitos: ffmpeg con libass, Python con faster-whisper, librosa, numpy, Pillow (`pip install faster-whisper librosa numpy pillow`). La primera vez compruébalos (`ffmpeg -version`, `python -c "import faster_whisper, librosa"`) e instala lo que falte con permiso de la persona.
Fuentes: Segoe UI Black (letra), Segoe Script (títulos) en Windows; en Mac/Linux usa equivalentes instaladas.

---

## FASE A — Letra para Suno

1. Leer lo que mandó el cliente: para quién, relación, ocasión, mensaje, género deseado.
2. **Meter TODAS las ideas del mensaje del cliente** en la letra (si dice "compañero, amigo y pareja", que aparezca tal cual de forma natural). Esto es lo que le toca fibras a quien la recibe.
3. Estructura: `[Intro]` con grito/dedicatoria con el nombre → `[Verse 1]` 8 líneas → `[Pre-Chorus]` 2 → `[Chorus]` 8 (el nombre repetido al inicio: "¡Valentina, Valentina!") → `[Verse 2]` → `[Pre-Chorus]` → `[Chorus]` → `[Instrumental Break]` → `[Bridge]` festivo ("¡que suene la güira!", "¡Felicidades!") → `[Final Chorus]` → `[Outro]` ("¡Te amo, X!") → `[End]`.
4. Rima consonante/asonante limpia, versos de 9–12 sílabas, coro pegajoso.
5. Dar 2 prompts de estilo (en inglés, para "Style of Music"). Ejemplos:
   - Merengue: `festive dominican merengue, accordion, güira, tambora, bright saxophone section, warm joyful male vocal, party backing choir, romantic birthday celebration, danceable, 140 bpm, spanish`
   - Cumbia: `colombian cumbia, accordion lead, guacharaca, caja vallenata, bass, warm romantic male vocal, festive choir shouts, birthday celebration, danceable, 95 bpm, spanish`
   - Adaptar: balada, vallenato, bachata, ranchera, salsa según pedido; voz masculina/femenina según quién regala.
6. Guardar en `cancion-<nombre>/letra-suno.md` (título, style A/B, letra en bloque de código, tips: generar 2–4 versiones, si pronuncia mal el nombre escribirlo fonético). Crear `fotos/` vacía y pedir fotos + MP3.

---

## FASE B — Video karaoke

### B1. Analizar (≈4–6 min, correr en background)
```
python $S/analizar.py <video_dir> <ruta_mp3> <fotos_dir> "<primeras líneas de la letra como prompt>"
```
Genera `words.json`, `beats.json`, `fotos.json`, `hoja-fotos.jpg` e imprime la transcripción con tiempos (= mapa de secciones).

### B2. Revisar fotos (mirar `hoja-fotos.jpg` con Read)
- Clasificar: **solo festejada**, **pareja/familia**, **grupo/fiesta**. Detectar capturas con barras negras (render.py las recorta solo).
- Para cada foto anotar `focus` = posición horizontal (0..1) de la cara/persona principal. Clave para que el paneo no corte a nadie.
- Fotos horizontales (ancho/alto > 0.75) → se muestran como "tarjeta" con borde blanco y paneo; verticales → pantalla completa con Ken Burns.

- **Capturas de estados de WhatsApp/Facebook** (barra "Responder", barra de estado, botones): render.py solo recorta negro puro, NO la interfaz. Recortar a mano a `fotos-limpias/NN.jpg` (fracciones arriba/abajo por foto), reescribir `fotos.json` con esos nombres y `fotos_dir: "../fotos-limpias"`. Descartar duplicados (misma foto en captura y original).

### B2b. Video del cliente (opcional)
Mover a `clip/video.mp4`. En proyecto.json: `"clip": "../clip/video.mp4"` (opcional `clip_inicio`), y una sección con fotos `["clip"]` y beats_por_foto 99, de duración ≈ la del clip (se reproduce a velocidad real, sin su audio; vertical = pantalla completa). Ideal en un instrumental + inicio de verso. `focus` acepta `"clip"`.

### B3. Escribir `video/lineas.txt`
Letra oficial **en el orden exacto en que Suno la cantó** (ver transcripción: Suno a veces omite o cambia versos — p.ej. omitió el 2º "¡Valentina, Valentina!" del coro). Una línea por renglón, coros repetidos completos, `#` para comentarios de sección.

### B4. Escribir `video/proyecto.json` (ver `ejemplo-proyecto.json`)
- `audio`, `fotos_dir`, `salida` (relativos a video/), `nombre`, `titulo`, `cierre`, `lineas`.
- `focus`: {"n": x}.
- `pulso`: **"suave" por defecto en pedidos nuevos** = solo en coros, un respiro lento cada compás (el zoom en cada beat marea; caso María Paula). `false` = sin pulso; `true` = cada beat (no usar salvo que lo pidan).
- `letra`: `false` para el plan Cancionarte "Canción + video con fotos" (14.90): solo títulos, sin karaoke. Plan karaoke (19.90): omitir o `true`.
- `tema: "infantil"` (niños/bebés): globos por los costados, estrellas que titilan, burbujas, confeti suave; corazones en coros. Con `"fuente_titulo": "Segoe Print"` (más juguetona que Segoe Script). Usar 8 beats por foto también en versos → dinámico.
- `tema: "nostalgia"` (ausencia, distancia, reconciliación, duelo; caso Mariana CNA-8YHTM2): nieve suave + luces cálidas tenues en coros, sin confeti ni corazones; títulos blanco/crema con contorno oscuro. Usar con `"pulso": false`, `"crossfade": 1.0`, sin `flash`, 12–16 beats por foto. **Leer la letra antes de elegir tema**: fotos de niña ≠ canción infantil.
- `gaps`: títulos en instrumentales `[inicio, fin, "texto"]` (ej. "Una canción hecha con amor", "¡A bailar, mi reina!", "¡Que viva la cumpleañera!").
- `sections`: `[inicio, fin, beats_por_foto, [fotos], flash, corazones]` cubriendo 0→duración sin huecos:
  - Versos / intro / instrumentales: **16 beats** por foto (~6–7 s a 140 BPM).
  - Coros y puente: **8 beats** (~3.3 s) → dinámico.
  - Coros: `corazones: true`. `flash: true` al entrar cada sección (excepto intro).
  - Narrativa: intro → la mejor foto de la festejada; versos de admiración → fotos de ella sola; coros de amor → fotos de pareja; puente/fiesta → fotos de grupo; cierre → la mejor foto de pareja (queda debajo del título final).
  - Repetir fotos está bien (17 fotos en 4 min → cada una sale ~2–3 veces); no repetir la misma foto seguida.

### B5. Generar timeline + karaoke
```
python $S/timeline.py <video_dir>
python $S/karaoke.py <video_dir>     # debe decir "sin match: 0" o casi; si no, corregir lineas.txt
```

### B6. Vista previa (~1 min) — SIEMPRE antes del render completo
```
python $S/build.py <video_dir> --preview 62 70     # entrada de un coro
```
Mirar `prev/preview.jpg` (Read). Revisar: caras no cortadas, texto legible, nada tapando caras.

### B7. Render final (en background)
```
python $S/build.py <video_dir>
```
8 bloques en paralelo → une → quema karaoke + audio → versión WhatsApp (crf 27, ~50 MB).
**Tiempo real medido (8 núcleos, canción 4:00): ~15 min render + ~3 min final + ~2 min WhatsApp ≈ 20 min.**
Esperar con `until grep -q "FINAL\|rror" <output>; do sleep 5; done` (Bash background), no con sleep.

### B8. Verificar y entregar
- `ffprobe` (1080x1920, duración = canción, h264+aac).
- Hoja de 8 cuadros (2, 20, 45, …, final) → revisar con Read. Si un título tapa caras o algo falla en el texto:
  `python $S/build.py <video_dir> --solo-karaoke` (~5 min, reusa las fotos ya renderizadas).
- Entregar con links a los dos MP4 (completo para TV/IG, WhatsApp para enviar), tiempo que tomó, y resumen de qué tiene.

---

## Estilo visual (ya implementado en los scripts)
- Fondo: la misma foto difuminada y oscurecida (nunca barras negras).
- Pulso de zoom en cada beat (más fuerte en beats pares), crossfade 0.35 s entre fotos, flash blanco al iniciar secciones.
- Confeti de colores todo el video; corazones rosados en coros.
- Karaoke abajo: línea actual 74 px, relleno dorado palabra por palabra (`\kf`) con pop de escala; siguiente línea en gris debajo.
- Títulos: "<titulo>" en Segoe Script rosa + "<nombre>" grande dorado, abajo (y 1400–1780) para no tapar caras; cierre con "<nombre> ♥" + frase.

## Movimiento con vida (al agregar títulos, temas o efectos nuevos)
Sigue las reglas de `${CLAUDE_SKILL_DIR}/../video-con-vida/references/principios.md`:
- Títulos y stickers nuevos entran con ease-out + rebote 5–10 % (íconos/corazones hasta 20 %) y salen con ease-in; nada lineal salvo el relleno del karaoke.
- Varios elementos a la vez → escalonados 80–120 ms; las palabras de un título, letra por letra 40–70 ms.
- Ken Burns siempre con ease-in-out, nunca lineal; ninguna foto completamente quieta (zoom 1–3 % mínimo).
- Sutil gana: el "pulso en cada beat" ya demostró que marea (caso María Paula). Si un movimiento se nota conscientemente, bájalo.
- Si el cliente manda un video suyo hablando a cámara (dedicatoria), se le pueden aplicar efectos de `video-con-vida` (p. ej. 16 portada con el nombre detrás de la cabeza, 14 garabato vivo con corazón) antes de meterlo como `clip`.

## Errores ya resueltos (no repetir)
- Partículas semitransparentes: `ImageDraw` sobre una imagen RGBA reemplaza píxeles (sale opaco). Dibujar en una capa aparte y `alpha_composite` (así lo hace `Snow`).
- Mosaicos/collages del cliente: detectar las franjas blancas, recortar cada foto, escalar ×3 Lanczos + UnsharpMask; separar fotos dobles y quitar marcas de agua.
- Whisper a veces amontona un verso entero en el mismo instante (todas las palabras con el mismo `s`): repartirlas a mano en words.json (guardar words-original.json) antes de karaoke.py.
- Globos al centro tapaban caras → van en los costados (x <190 o >890).
- `python -I` → ModuleNotFoundError faster_whisper. Usar python normal.
- Pasar JSON por argumento en PowerShell rompe las comillas → todo va en proyecto.json.
- Paneo/zoom fuerte en fotos horizontales cortaba a la persona → tarjeta de 940 px de alto + `focus`.
- Títulos centrados tapaban caras → van en la zona baja (sin karaoke en intro y cierre).
- Segmento final de sección muy corto (<60% del normal) se une al anterior (timeline.py lo hace).
