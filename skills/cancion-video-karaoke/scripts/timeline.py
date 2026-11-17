"""Paso 3a — proyecto.json + beats.json -> timeline.json (segmentos de foto cortados en beats).
Uso: python timeline.py <carpeta_video>
"""
import json, os, sys
import numpy as np

vd = sys.argv[1]
P = json.load(open(os.path.join(vd, "proyecto.json"), encoding="utf-8"))
B = json.load(open(os.path.join(vd, "beats.json")))
beats, dur = np.array(B["beats"]), B["duration"]
spb = 60.0 / B["tempo"]

def snap(t):
    if t <= 0.2 or t >= dur - 0.2:
        return t
    return float(beats[np.argmin(abs(beats - t))])

segs, hearts = [], []
for a, b, nb, fotos, flash, hrt in P["sections"]:
    a, b = snap(a), snap(min(b, dur))
    if hrt:
        hearts.append([a, b])
    bi = [x for x in beats if a <= x < b]
    cuts = [a] + [float(x) for x in bi[nb::nb]]
    if b - cuts[-1] < nb * spb * 0.6 and len(cuts) > 1:   # evita fotos "relámpago" al final
        cuts.pop()
    cuts.append(b)
    for k in range(len(cuts) - 1):
        segs.append(dict(start=cuts[k], end=cuts[k + 1], photo=fotos[k % len(fotos)],
                         pan=-1 if len(segs) % 2 == 0 else 1, flash=flash and k == 0))
segs[-1]["end"] = dur
fotos_dir = os.path.normpath(os.path.join(vd, P["fotos_dir"]))
files = [os.path.join(fotos_dir, x["file"]) for x in json.load(open(os.path.join(vd, "fotos.json"), encoding="utf-8"))]
json.dump(dict(fps=30, duration=dur, beats=beats.tolist(), segments=segs, hearts=hearts,
               files=files, focus=P.get("focus", {}), pulso=P.get("pulso", True), tema=P.get("tema"), crossfade=P.get("crossfade"),
               clip=os.path.normpath(os.path.join(vd, P["clip"])) if P.get("clip") else None,
               clip_inicio=P.get("clip_inicio", 0.0)),
          open(os.path.join(vd, "timeline.json"), "w"), indent=0)
for s in segs:
    print(f"{s['start']:7.2f}-{s['end']:7.2f}  foto {s['photo']!s:>4} {'FLASH' if s['flash'] else ''}")
