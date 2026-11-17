"""Paso 4 — Construye el video final.
Uso:
  python build.py <carpeta_video>                 render completo (bloques en paralelo) + karaoke + audio + versión WhatsApp
  python build.py <carpeta_video> --preview A B   vista previa con karaoke de A a B segundos (prev/preview.mp4 + cuadro .jpg)
  python build.py <carpeta_video> --solo-karaoke  reusa chunks/fotos.mp4 y solo re-quema karaoke/audio (cambios de texto)
  python build.py <carpeta_video> --reanudar      re-renderiza solo los bloques que fallaron (p. ej. MemoryError)
"""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
vd = os.path.abspath(sys.argv[1])
P = json.load(open(os.path.join(vd, "proyecto.json"), encoding="utf-8"))
audio = os.path.normpath(os.path.join(vd, P["audio"]))
salida = os.path.normpath(os.path.join(vd, P["salida"]))
dur = json.load(open(os.path.join(vd, "beats.json")))["duration"]
ff = ["ffmpeg", "-loglevel", "error", "-y"]

def run(cmd):
    subprocess.run(cmd, cwd=vd, check=True)

def final(fotos_mp4):
    # ass= se resuelve relativo a cwd (vd) -> evita problemas de escape de rutas Windows
    run(ff + ["-i", fotos_mp4, "-i", audio, "-vf", "ass=karaoke.ass", "-c:v", "libx264", "-preset", "medium",
              "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
              "-movflags", "+faststart", salida + ".mp4"])
    run(ff + ["-i", salida + ".mp4", "-c:v", "libx264", "-preset", "slow", "-crf", "27", "-maxrate", "2500k",
              "-bufsize", "5000k", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", salida + "-WhatsApp.mp4"])
    for f in (salida + ".mp4", salida + "-WhatsApp.mp4"):
        print(f"{f}  {os.path.getsize(f) / 1e6:.1f} MB")

t0 = time.time()
render = os.path.join(HERE, "render.py")
if len(sys.argv) > 2 and sys.argv[2] == "--preview":
    a, b = float(sys.argv[3]), float(sys.argv[4])
    os.makedirs(os.path.join(vd, "prev"), exist_ok=True)
    run([sys.executable, render, "timeline.json", "prev/p.mp4", "--range", str(a), str(b)])
    run(ff + ["-i", "prev/p.mp4", "-ss", str(a), "-i", audio, "-vf", f"setpts=PTS+{a}/TB,ass=karaoke.ass,setpts=PTS-STARTPTS",
              "-c:v", "libx264", "-crf", "20", "-c:a", "aac", "-shortest", "prev/preview.mp4"])
    run(ff + ["-ss", str((b - a) / 2), "-i", "prev/preview.mp4", "-frames:v", "1", "prev/preview.jpg"])
    print(f"preview listo en {time.time() - t0:.0f}s -> prev/preview.mp4, prev/preview.jpg")
    sys.exit()
if len(sys.argv) > 2 and sys.argv[2] == "--solo-karaoke":
    final("chunks/fotos.mp4"); print(f"listo en {time.time() - t0:.0f}s"); sys.exit()

n = os.cpu_count() or 4
n = max(2, min(8, n))
step = -(-dur // n)
os.makedirs(os.path.join(vd, "chunks"), exist_ok=True)
# Con poca RAM libre, 8 renders a la vez fallan por memoria (CNA-5GN98P): RENDER_PARALELO=3 limita cuántos corren juntos.
paralelo = int(os.environ.get("RENDER_PARALELO", n))
procs = []
# --reanudar: si un bloque falló por memoria (CNA-G5E6A6, 34 fotos), reusa los bloques que ya salieron completos.
reanudar = "--reanudar" in sys.argv
def bloque_ok(i, a, b):
    f = os.path.join(vd, "chunks", f"c{i}.mp4")
    if not os.path.exists(f): return False
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    try: return abs(float(r.stdout.strip()) - (b - a)) < 0.5
    except ValueError: return False
for i in range(n):
    a, b = i * step, min(dur, (i + 1) * step)
    if reanudar and bloque_ok(i, a, b):
        print(f"bloque {i} ya estaba", flush=True); continue
    while sum(p.poll() is None for p in procs) >= paralelo:
        time.sleep(2)
    log = open(os.path.join(vd, "chunks", f"log{i}.txt"), "w")
    procs.append(subprocess.Popen([sys.executable, render, "timeline.json", f"chunks/c{i}.mp4", "--range", str(a), str(b)],
                                  cwd=vd, stdout=log, stderr=subprocess.STDOUT))
for p in procs:
    if p.wait() != 0:
        sys.exit("falló un bloque: revisa chunks/log*.txt")
print(f"render listo en {time.time() - t0:.0f}s", flush=True)
with open(os.path.join(vd, "chunks", "list.txt"), "w") as f:
    f.writelines(f"file 'c{i}.mp4'\n" for i in range(n))
run(ff + ["-f", "concat", "-safe", "0", "-i", "chunks/list.txt", "-c", "copy", "chunks/fotos.mp4"])
final("chunks/fotos.mp4")
print(f"FINAL listo en {time.time() - t0:.0f}s")
