"""Paso 3b — Alinea la letra oficial (lineas.txt) con los tiempos por palabra de Whisper y genera karaoke.ass
Uso: python karaoke.py <carpeta_video>
Lee proyecto.json (titulo, nombre, cierre, gaps, lineas), words.json y beats.json.
lineas.txt: una línea cantada por renglón, en el ORDEN en que se canta (repetir coros). '#' = comentario.
"""
import json, os, re, sys, unicodedata, difflib

def norm(w):
    w = unicodedata.normalize("NFD", w.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-zñ]", "", w)

vd = sys.argv[1]
P = json.load(open(os.path.join(vd, "proyecto.json"), encoding="utf-8"))
words = [w for s in json.load(open(os.path.join(vd, "words.json"), encoding="utf-8")) for w in s["words"]]
lines = [l.strip() for l in open(os.path.join(vd, P.get("lineas", "lineas.txt")), encoding="utf-8")
         if l.strip() and not l.startswith("#")]
out = os.path.join(vd, "karaoke.ass")
dur = json.load(open(os.path.join(vd, "beats.json")))["duration"]
TIT, NOM, CIE = P.get("titulo", "Feliz Cumpleaños"), P["nombre"], P.get("cierre", "Con todo mi amor, hoy y siempre")
lyr = []  # (line_idx, token_text)
for i, l in enumerate(lines):
    for tok in l.split():
        lyr.append([i, tok, None, None])
A = [norm(t[1]) for t in lyr]
B = [norm(w["w"]) for w in words]
sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
for blk in sm.get_matching_blocks():
    for k in range(blk.size):
        w = words[blk.b + k]
        lyr[blk.a + k][2], lyr[blk.a + k][3] = w["s"], w["e"]
# reemplazos 1:1 (palabras mal transcritas)
for op, a1, a2, b1, b2 in sm.get_opcodes():
    if op == "replace":
        n = min(a2 - a1, b2 - b1)
        for k in range(n):
            lyr[a1 + k][2], lyr[a1 + k][3] = words[b1 + k]["s"], words[b1 + k]["e"]
# interpolar huecos
known = [i for i, t in enumerate(lyr) if t[2] is not None]
for i, t in enumerate(lyr):
    if t[2] is None:
        prv = max([k for k in known if k < i], default=None)
        nxt = min([k for k in known if k > i], default=None)
        if prv is not None and nxt is not None:
            a, b = lyr[prv][3], lyr[nxt][2]
            frac = (i - prv) / (nxt - prv)
            t[2] = a + (b - a) * frac; t[3] = t[2] + max(0.15, (b - a) / (nxt - prv))
        elif prv is not None:
            t[2] = lyr[prv][3] + 0.1 * (i - prv); t[3] = t[2] + 0.3
        else:
            t[2] = lyr[nxt][2] - 0.3 * (nxt - i); t[3] = t[2] + 0.25
missing = sum(1 for i in range(len(lyr)) if i not in set(known))
print(f"palabras: {len(lyr)}  sin match: {missing}  (si es alto, lineas.txt no coincide con lo cantado)")

def ts(t):
    t = max(0, t); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def esc(s):
    return s.replace("{", "(").replace("}", ")")

# líneas con tiempos
L = []
for i, l in enumerate(lines):
    toks = [t for t in lyr if t[0] == i]
    # suavizar: forzar monotonía
    for k in range(1, len(toks)):
        if toks[k][2] < toks[k - 1][2]: toks[k][2] = toks[k - 1][2] + 0.05
        if toks[k][3] < toks[k][2]: toks[k][3] = toks[k][2] + 0.2
    L.append(dict(text=l, toks=toks, s=toks[0][2], e=toks[-1][3]))
    print(f"{toks[0][2]:7.2f}-{toks[-1][3]:7.2f}  {l}")

FT = P.get("fuente_titulo", "Segoe Script")  # infantil: "Segoe Print"
hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Kara,Segoe UI Black,74,&H0000D7FF,&H00FFFFFF,&H00401020,&H96000000,-1,0,0,0,100,100,0,0,1,6,4,2,60,60,300,1
Style: Next,Segoe UI Black,52,&H50FFFFFF,&H50FFFFFF,&H64401020,&H96000000,-1,0,0,0,100,100,0,0,1,4,2,2,80,80,190,1
Style: Title,{FT},118,&H00FFFFFF,&H00FFFFFF,&H009A2BFF,&H96000000,-1,0,0,0,100,100,0,0,1,7,5,5,40,40,0,1
Style: Sub,Segoe UI Black,62,&H0000D7FF,&H0000D7FF,&H00401020,&H96000000,-1,0,0,0,100,100,2,0,1,5,3,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
ev = []
for i, l in enumerate(L):
    st = l["s"] - 0.35
    nxt = L[i + 1]["s"] if i + 1 < len(L) else dur
    en = min(nxt - 0.35, l["e"] + 1.6) if nxt - l["e"] > 2.0 else nxt - 0.35
    en = max(en, l["e"] + 0.3)
    # Líneas pegadas (Whisper: fin de una = inicio de la otra) se encimaban 0.6 s (CNA-WUA5UN): nunca pasar el inicio de la siguiente.
    if i + 1 < len(L): en = min(en, nxt - 0.35)
    # karaoke con \kf (barrido); tiempo de cada palabra hasta el inicio de la siguiente
    parts = []
    lead = max(0, int(round((l["s"] - st) * 100)))
    parts.append(f"{{\\k{lead}}}")
    for k, t in enumerate(l["toks"]):
        endw = l["toks"][k + 1][2] if k + 1 < len(l["toks"]) else t[3]
        cs = max(5, int(round((endw - t[2]) * 100)))
        parts.append(f"{{\\kf{cs}}}{esc(t[1])} ")
    anim = "{\\fad(120,150)\\t(0,180,\\fscx106\\fscy106)\\t(180,320,\\fscx100\\fscy100)}"
    # Canciones que cantan hasta el final: la última línea chocaba con el título de cierre (CNA-WUA5UN) → arriba.
    cierre_choca = en > dur - 6
    if cierre_choca: anim = anim[:-1] + "\\pos(540,270)}"
    ev.append(f"Dialogue: 1,{ts(st)},{ts(en)},Kara,,0,0,0,,{anim}{''.join(parts).rstrip()}")
    # vista previa de la siguiente línea (solo si viene pegada)
    if i + 1 < len(L) and L[i + 1]["s"] - l["e"] < 2.5 and not cierre_choca:
        ev.append(f"Dialogue: 0,{ts(st)},{ts(en)},Next,,0,0,0,,{{\\fad(120,150)}}{esc(L[i + 1]['text'])}")

# títulos de intro y cierre
NOMC = r"\3c&H281410&\c&H9CDCF8&" if P.get("tema") == "nostalgia" else r"\3c&H00D7FF&"
if P.get("tema") in ("nostalgia", "epico"):  # sobrio: blanco/crema con contorno oscuro, sin rosa ni amarillo chillón
    hdr = hdr.replace("&H009A2BFF,&H96000000", "&H00281410,&H96000000")
first = L[0]["s"]
# Nombres largos (p. ej. "Fabián Alejandro ♥", CNA-JMP4GR) partían en 2 líneas y se montaban sobre el título: achicar para que quepa en una.
def fs_nombre(base, txt): return min(base, int(1000 / (len(txt) * 0.37)))
intro_end = P.get("intro_fin", min(first - 0.4, 4.6))  # canciones que arrancan cantando: alargar el título
ev.append(f"Dialogue: 2,{ts(0.4)},{ts(intro_end)},Title,,0,0,0,,{{\\fad(400,300)\\pos(540,1420)\\t(0,500,\\fscx108\\fscy108)}}{TIT}")
ev.append(f"Dialogue: 2,{ts(0.9)},{ts(intro_end)},Title,,0,0,0,,{{\\fad(400,300)\\pos(540,1610)\\fs{fs_nombre(170, NOM)}{NOMC}}}{NOM}")
gap_titles = P.get("gaps", [])
for g in gap_titles:
    a, b, txt = g[:3]; y = g[3] if len(g) > 3 else 1500
    ev.append(f"Dialogue: 2,{ts(a)},{ts(b)},Sub,,0,0,0,,{{\\fad(300,300)\\pos(540,{y})}}{txt}")
ev.append(f"Dialogue: 2,{ts(dur - 6)},{ts(dur)},Title,,0,0,0,,{{\\fad(600,800)\\pos(540,1400)}}{TIT}")
ev.append(f"Dialogue: 2,{ts(dur - 5.5)},{ts(dur)},Title,,0,0,0,,{{\\fad(600,800)\\pos(540,1590)\\fs{fs_nombre(180, NOM + ' ♥')}{NOMC}}}{NOM}{'' if P.get('tema') == 'epico' else ' ♥'}")
ev.append(f"Dialogue: 2,{ts(dur - 4.8)},{ts(dur)},Sub,,0,0,0,,{{\\fad(600,800)\\pos(540,1780)\\fs48\\c&HFFFFFF&}}{CIE}")
if P.get("letra", True) is False:  # plan "video con fotos": solo títulos, sin karaoke
    ev = [e for e in ev if ",Kara," not in e and ",Next," not in e]
open(out, "w", encoding="utf-8-sig").write(hdr + "\n".join(ev) + "\n")
print("ok", out)
