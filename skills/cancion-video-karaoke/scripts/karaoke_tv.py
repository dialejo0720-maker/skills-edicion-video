"""Karaoke clásico para TV (CNA-G5E6A6, don Norberto: "solo la letra, sin fotos, para cantarla").
Video horizontal 1920x1080: fondo oscuro, letra grande al centro que se pinta palabra por palabra,
siguiente línea debajo y cuenta 3-2-1 antes de cada entrada tras un instrumental. Audio = pista instrumental.

Uso: python karaoke_tv.py <carpeta> <cancion_con_voz.mp3> <instrumental.mp3> "<Título>" <salida.mp4>
La carpeta debe tener words.json (Whisper sobre la canción CON voz) y lineas.txt (una línea cantada por
renglón, en el orden en que se canta, coros repetidos; '#' = comentario).
"""
import json, os, re, subprocess, sys, unicodedata, difflib
from PIL import Image, ImageDraw, ImageFilter

vd, con_voz, instr, TIT, salida = sys.argv[1:6]
W, H = 1920, 1080

def norm(w):
    w = unicodedata.normalize("NFD", w.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-zñ]", "", w)

words = [w for s in json.load(open(os.path.join(vd, "words.json"), encoding="utf-8")) for w in s["words"]]
lines = [l.strip() for l in open(os.path.join(vd, "lineas.txt"), encoding="utf-8") if l.strip() and not l.startswith("#")]
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", instr],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout)

# --- alinear letra oficial con los tiempos de Whisper (misma lógica que karaoke.py) ---
lyr = [[i, tok, None, None] for i, l in enumerate(lines) for tok in l.split()]
A, B = [norm(t[1]) for t in lyr], [norm(w["w"]) for w in words]
sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
for blk in sm.get_matching_blocks():
    for k in range(blk.size):
        lyr[blk.a + k][2], lyr[blk.a + k][3] = words[blk.b + k]["s"], words[blk.b + k]["e"]
for op, a1, a2, b1, b2 in sm.get_opcodes():
    if op == "replace":
        for k in range(min(a2 - a1, b2 - b1)):
            lyr[a1 + k][2], lyr[a1 + k][3] = words[b1 + k]["s"], words[b1 + k]["e"]
known = [i for i, t in enumerate(lyr) if t[2] is not None]
for i, t in enumerate(lyr):
    if t[2] is None:
        prv = max([k for k in known if k < i], default=None); nxt = min([k for k in known if k > i], default=None)
        if prv is not None and nxt is not None:
            a, b = lyr[prv][3], lyr[nxt][2]; t[2] = a + (b - a) * (i - prv) / (nxt - prv); t[3] = t[2] + max(0.15, (b - a) / (nxt - prv))
        elif prv is not None: t[2] = lyr[prv][3] + 0.1 * (i - prv); t[3] = t[2] + 0.3
        else: t[2] = lyr[nxt][2] - 0.3 * (nxt - i); t[3] = t[2] + 0.25
print(f"palabras: {len(lyr)}  sin match: {len(lyr) - len(known)}")
L = []
for i, l in enumerate(lines):
    toks = [t for t in lyr if t[0] == i]
    for k in range(1, len(toks)):
        if toks[k][2] < toks[k - 1][2]: toks[k][2] = toks[k - 1][2] + 0.05
        if toks[k][3] < toks[k][2]: toks[k][3] = toks[k][2] + 0.2
    L.append(dict(text=l, toks=toks, s=toks[0][2], e=toks[-1][3]))
    print(f"{toks[0][2]:7.2f}-{toks[-1][3]:7.2f}  {l}")

def ts(t):
    t = max(0, t); return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"
esc = lambda s: s.replace("{", "(").replace("}", ")")

hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Kara,Segoe UI Black,104,&H0000D7FF,&H00FFFFFF,&H00301018,&H96000000,-1,0,0,0,100,100,1,0,1,6,3,5,80,80,0,1
Style: Next,Segoe UI Black,64,&H70FFFFFF,&H70FFFFFF,&H80301018,&H96000000,-1,0,0,0,100,100,1,0,1,4,0,5,120,120,0,1
Style: Title,Segoe Script,130,&H00FFFFFF,&H00FFFFFF,&H009A2BFF,&H96000000,-1,0,0,0,100,100,0,0,1,7,4,5,60,60,0,1
Style: Sub,Segoe UI Black,54,&H0000D7FF,&H0000D7FF,&H00301018,&H96000000,-1,0,0,0,100,100,6,0,1,4,2,5,60,60,0,1
Style: Head,Segoe UI,36,&H90FFFFFF,&H90FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,2,0,1,0,0,8,60,60,40,1
Style: Count,Segoe UI Black,150,&H0000D7FF,&H0000D7FF,&H00301018,&H96000000,-1,0,0,0,100,100,0,0,1,7,3,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
ev = []
first = L[0]["s"]
# portada: título + "Karaoke" hasta 1.5 s antes del primer verso
ev.append(f"Dialogue: 3,{ts(0.3)},{ts(max(1.5, first - 3.3))},Title,,0,0,0,,{{\\fad(600,400)\\pos(960,450)}}{esc(TIT)}")
ev.append(f"Dialogue: 3,{ts(0.8)},{ts(max(1.5, first - 3.3))},Sub,,0,0,0,,{{\\fad(600,400)\\pos(960,620)}}♪ KARAOKE ♪")
ev.append(f"Dialogue: 0,{ts(first - 1.6)},{ts(dur - 5)},Head,,0,0,0,,{{\\fad(800,800)}}{esc(TIT)}  ·  Karaoke")
for i, l in enumerate(L):
    nxt = L[i + 1]["s"] if i + 1 < len(L) else dur
    st = l["s"] - (0.9 if i == 0 or l["s"] - L[i - 1]["e"] > 3.5 else 0.35)
    en = min(nxt - 0.35, l["e"] + 1.8) if nxt - l["e"] > 2.0 else nxt - 0.35
    en = max(en, l["e"] + 0.3)
    if i + 1 < len(L): en = min(en, nxt - 0.35)
    if i == len(L) - 1: en = min(en, dur - 4.7)  # que no choque con el título de cierre (merengue de Edith)
    parts = [f"{{\\k{max(0, int(round((l['s'] - st) * 100)))}}}"]
    for k, t in enumerate(l["toks"]):
        endw = l["toks"][k + 1][2] if k + 1 < len(l["toks"]) else t[3]
        parts.append(f"{{\\kf{max(5, int(round((endw - t[2]) * 100)))}}}{esc(t[1])} ")
    ev.append(f"Dialogue: 2,{ts(st)},{ts(en)},Kara,,0,0,0,,{{\\fad(150,200)\\pos(960,500)}}{''.join(parts).rstrip()}")
    if i + 1 < len(L) and L[i + 1]["s"] - l["e"] < 4.0:
        ev.append(f"Dialogue: 1,{ts(st)},{ts(en)},Next,,0,0,0,,{{\\fad(150,200)\\pos(960,700)}}{esc(L[i + 1]['text'])}")
    # tras un instrumental largo: la línea que viene, en gris, y cuenta 3-2-1
    if i + 1 < len(L) and L[i + 1]["s"] - l["e"] > 4.0:
        s2 = L[i + 1]["s"]
        if s2 - 3.7 - (en + 0.3) > 1.5:  # instrumental: notas para que no quede la pantalla vacía
            ev.append(f"Dialogue: 1,{ts(en + 0.3)},{ts(s2 - 3.7)},Sub,,0,0,0,,{{\\fad(500,400)\\pos(960,520)\\fs90}}♪   ♪   ♪")
        ev.append(f"Dialogue: 1,{ts(s2 - 3.6)},{ts(s2 - 0.9)},Next,,0,0,0,,{{\\fad(300,150)\\pos(960,680)}}{esc(L[i + 1]['text'])}")
        for n, c in enumerate(["3", "2", "1"]):
            a = s2 - 3.0 + n * 0.75
            ev.append(f"Dialogue: 3,{ts(a)},{ts(a + 0.7)},Count,,0,0,0,,{{\\fad(80,200)\\pos(960,470)\\t(0,250,\\fscx115\\fscy115)}}{c}")
if first > 4.0:
    for n, c in enumerate(["3", "2", "1"]):
        a = first - 3.0 + n * 0.75
        ev.append(f"Dialogue: 3,{ts(a)},{ts(a + 0.7)},Count,,0,0,0,,{{\\fad(80,200)\\pos(960,470)\\t(0,250,\\fscx115\\fscy115)}}{c}")
ev.append(f"Dialogue: 3,{ts(dur - 4.5)},{ts(dur)},Title,,0,0,0,,{{\\fad(700,900)\\pos(960,480)}}{esc(TIT)}")
ev.append(f"Dialogue: 3,{ts(dur - 4.0)},{ts(dur)},Sub,,0,0,0,,{{\\fad(700,900)\\pos(960,640)}}Cancionarte")
ass = os.path.join(vd, "karaoke-tv.ass")
open(ass, "w", encoding="utf-8-sig").write(hdr + "\n".join(ev) + "\n")

# fondo: degradado azul noche → violeta con viñeta suave
bg = Image.new("RGB", (W, H))
d = ImageDraw.Draw(bg)
for y in range(H):
    f = y / H
    d.line([(0, y), (W, y)], fill=(int(14 + 30 * f), int(14 + 6 * f), int(40 + 30 * f)))
glow = Image.new("L", (W, H), 0); ImageDraw.Draw(glow).ellipse([W * 0.15, H * 0.1, W * 0.85, H * 0.95], fill=90)
glow = glow.filter(ImageFilter.GaussianBlur(160))
bg = Image.composite(Image.new("RGB", (W, H), (70, 40, 110)), bg, glow)
fondo = os.path.join(vd, "fondo-tv.png"); bg.save(fondo)

rel = os.path.relpath(ass, vd).replace("\\", "/")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", "30", "-i", "fondo-tv.png", "-i", os.path.abspath(instr),
                "-vf", f"ass={rel}", "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-tune", "stillimage", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-t", f"{dur:.3f}", os.path.abspath(salida)],
               cwd=vd, check=True, stdin=subprocess.DEVNULL)
print("ok", salida)
