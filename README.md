# Skills de edición de video para Claude Code 🎬

Tres skills para editar y crear videos con Claude Code:

| Skill | Qué hace | Pídelo así |
|---|---|---|
| **video-con-vida** | 17 efectos por capas para videos de alguien hablando a cámara (zoom a la cara, texto detrás de la cabeza, portada de revista, checklist, gráfica que crece, vértigo…) y reglas para que nada se mueva "como robot". | *"Ponle efectos a mi video `reel.mp4`"* |
| **video-pizarra** | Videos animados estilo pizarrón (mascota, texto escrito a mano, transiciones, efectos de sonido) y 4 estilos extra: acuarela, acuarela viva, cuaderno y minimal. | *"Hazme un video pizarra de 60 s explicando qué es el interés compuesto"* |
| **cancion-video-karaoke** | Letra lista para Suno y video vertical tipo karaoke con tus fotos, sincronizado al ritmo y palabra por palabra. | *"Hazme una canción de cumpleaños para Ana y su video con estas fotos"* |

> Funcionan en **Claude Code** (terminal, app de escritorio o extensión de VS Code), porque usan ffmpeg, Python y Node en tu computadora. No funcionan en el chat web de claude.ai.

---

## 1. Instalar (2 comandos)

Abre Claude Code y escribe, uno por uno:

```
/plugin marketplace add dialejo0720-maker/skills-edicion-video
```

```
/plugin install edicion-video@skills-edicion
```

Cierra y vuelve a abrir Claude Code. Listo: las skills se activan solas cuando pides algo como los ejemplos de arriba.

**Para actualizar** cuando haya cambios:

```
/plugin marketplace update skills-edicion
```

<details>
<summary>Instalación manual (sin plugin)</summary>

```bash
git clone https://github.com/dialejo0720-maker/skills-edicion-video.git
```

Copia las 3 carpetas de `skills/` a:
- Mac / Linux: `~/.claude/skills/`
- Windows: `%USERPROFILE%\.claude\skills\`

Copia las tres juntas: `video-pizarra` y `cancion-video-karaoke` usan las reglas de movimiento de `video-con-vida`.
</details>

## 2. Programas que necesitas (una sola vez)

- **ffmpeg**: Windows `winget install ffmpeg` · Mac `brew install ffmpeg` · Linux `sudo apt install ffmpeg`
- **Python 3.10+**: https://python.org (en Windows marca "Add Python to PATH")
- **Node.js 18+**: https://nodejs.org (solo para video-pizarra)
- Librerías de Python:
  ```bash
  pip install numpy scipy pillow rembg opencv-python-headless faster-whisper librosa
  ```

¿No sabes cómo? Pídeselo a Claude Code: *"Revisa si tengo ffmpeg, Python y Node, e instala lo que falte para las skills de edición"*.

## 3. Llaves opcionales

Las skills funcionan sin llaves. Con llaves, algunas partes quedan mejor:

| Llave | Para qué | Dónde se consigue |
|---|---|---|
| `SUNO_API_KEY` | Generar la música del video pizarra | https://sunoapi.org |
| `ASSEMBLYAI_API_KEY` | Tiempos más precisos de la voz en off | https://www.assemblyai.com |
| `GEMINI_API_KEY` | Fondo limpio detrás de la persona (video-con-vida). Necesita facturación activa. | https://aistudio.google.com |

Para guardarlas, dile a Claude: *"Guarda mi llave de Suno: …"*. No la pegues en ningún otro lado.

## 4. Consejos

- Trabaja cada video en su propia carpeta y abre Claude Code ahí.
- El primer video tarda más porque se descargan modelos (recorte de persona, transcripción).
- Un video pizarra toma de 20 a 40 minutos de trabajo del agente, más 3 a 5 minutos de render por minuto de video.
- Si algo no se ve bien, díselo con tus palabras ("el zoom no cae en mi cara", "la letra va adelantada") y Claude lo corrige.

---

Hecho con ❤️ por Horizontes IA.
