"""Paso 1 — Analiza canción y fotos.
Uso: python analizar.py <carpeta_video> <audio.mp3> <carpeta_fotos> [prompt_letra]
Genera en carpeta_video: words.json (Whisper por palabra), beats.json (tempo + beats),
fotos.json (lista ordenada + tamaños + si tienen barras negras), hoja-fotos.jpg (contact sheet numerado).
"""
import glob, json, os, sys
import numpy as np
from PIL import Image, ImageOps, ImageDraw

out_dir, audio, fotos_dir = sys.argv[1], sys.argv[2], sys.argv[3]
prompt = sys.argv[4] if len(sys.argv) > 4 else None
os.makedirs(out_dir, exist_ok=True)
EXT = ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.JPG", "*.JPEG", "*.PNG")

# --- fotos ---
files = sorted({f for e in EXT for f in glob.glob(os.path.join(fotos_dir, e))})
info, W = [], 300
sheet = Image.new("RGB", (W * 5, (W + 40) * ((len(files) + 4) // 5)), "white")
d = ImageDraw.Draw(sheet)
for i, f in enumerate(files):
    im = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
    a = np.asarray(im.convert("L"))
    bars = bool((a.mean(axis=1) <= 18).sum() > a.shape[0] * 0.05)
    info.append(dict(n=i + 1, file=os.path.basename(f), w=im.width, h=im.height, barras_negras=bars))
    im.thumbnail((W - 10, W - 10))
    x, y = (i % 5) * W, (i // 5) * (W + 40)
    sheet.paste(im, (x + 5, y + 35)); d.text((x + 8, y + 8), f"#{i + 1}", fill="red")
sheet.save(os.path.join(out_dir, "hoja-fotos.jpg"), quality=85)
json.dump(info, open(os.path.join(out_dir, "fotos.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(files)} fotos -> hoja-fotos.jpg")
for x in info:
    print(f"  #{x['n']:2d} {x['w']}x{x['h']} {'(barras negras)' if x['barras_negras'] else ''}")

# --- beats ---
import librosa
y, sr = librosa.load(audio, sr=22050)
tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
dur = float(len(y) / sr)
rms = librosa.feature.rms(y=y)[0]; t = librosa.times_like(rms, sr=sr)
json.dump(dict(tempo=float(np.atleast_1d(tempo)[0]), duration=dur, beats=[float(b) for b in beats]),
          open(os.path.join(out_dir, "beats.json"), "w"))
print(f"\nduración {dur:.2f}s  tempo {float(np.atleast_1d(tempo)[0]):.1f} BPM  beats {len(beats)}")
print("energía cada 10s:", " ".join(f"{a}:{rms[(t >= a) & (t < a + 10)].mean():.3f}" for a in range(0, int(dur), 10)))

# --- transcripción por palabra ---
from faster_whisper import WhisperModel
model = WhisperModel("medium", device="cpu", compute_type="int8")
segs, _ = model.transcribe(audio, language="es", word_timestamps=True, initial_prompt=prompt, beam_size=5)
res = []
print("\nTRANSCRIPCIÓN:")
for s in segs:
    res.append(dict(start=s.start, end=s.end, text=s.text,
                    words=[dict(w=w.word, s=w.start, e=w.end, p=w.probability) for w in s.words]))
    print(f"[{s.start:6.2f}-{s.end:6.2f}] {s.text}", flush=True)
json.dump(res, open(os.path.join(out_dir, "words.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ok")
