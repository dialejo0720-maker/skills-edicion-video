"""Renderiza el video vertical (1080x1920) de fotos sincronizado al ritmo.
Uso: python render.py timeline.json salida_sin_audio.mp4 [--range A B]
timeline.json lo genera timeline.py. --range A B renderiza solo de A a B segundos (para bloques en paralelo / vista previa).
"""
import json, math, random, subprocess, sys
import numpy as np
from PIL import Image, ImageOps, ImageFilter, ImageDraw

W, H = 1080, 1920

def trim_black(im):
    a = np.asarray(im.convert("L"))
    rows = np.where(a.mean(axis=1) > 18)[0]
    cols = np.where(a.mean(axis=0) > 18)[0]
    if len(rows) and len(cols):
        im = im.crop((cols[0], rows[0], cols[-1] + 1, rows[-1] + 1))
    return im

def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))

class Photo:
    def __init__(self, path):
        im = trim_black(ImageOps.exif_transpose(Image.open(path)).convert("RGB"))
        self.src = im
        w, h = im.size
        # fondo: cover + blur + oscurecido
        s = max(W / w, H / h) * 1.15
        bg = im.resize((int(w * s), int(h * s)), Image.BILINEAR)
        bg = bg.crop(((bg.width - W) // 2, (bg.height - H) // 2, (bg.width - W) // 2 + W, (bg.height - H) // 2 + H))
        bg = bg.filter(ImageFilter.GaussianBlur(40))
        self.bg = Image.blend(bg, Image.new("RGB", (W, H), (20, 8, 30)), 0.45)
        self.wide = w / h > 0.75
        if self.wide:
            # tarjeta horizontal grande con paneo
            ch = 940
            s = ch / h
            if w * s < W * 1.12:
                s = W * 1.12 / w
            self.fg = im.resize((int(w * s), int(h * s)), Image.LANCZOS)
        else:
            s = max(W / w, H / h) * 1.14
            self.fg = im.resize((int(w * s), int(h * s)), Image.LANCZOS)

    def frame(self, p, pan, pulse, focus=0.5, seg_dur=0):
        """p: progreso 0..1; pan: -1/1 dirección del paneo; focus: x (0..1) donde está la persona."""
        fw, fh = self.fg.size
        drift = pan * 0.09 * fw * (ease(p) - 0.5)
        if self.wide:
            out = self.bg.copy()
            z = 1.0 + 0.06 * p + pulse
            vis_w = min(fw, W / z)
            vis_h = fh / z
            x0 = max(0, min(fw - vis_w, focus * fw + drift - vis_w / 2))
            y0 = (fh - vis_h) / 2
            crop = self.fg.transform((W, int(fh)), Image.EXTENT, (x0, y0, x0 + vis_w, y0 + vis_h), Image.BILINEAR)
            out.paste(crop, (0, 300))
            d = ImageDraw.Draw(out)
            d.rectangle((0, 290, W, 299), fill=(255, 255, 255))
            d.rectangle((0, 300 + crop.height, W, 309 + crop.height), fill=(255, 255, 255))
        else:
            z = 1.0 + 0.10 * ease(p) + pulse  # Ken Burns
            # región visible en coords de fg
            base = min(fw / W, fh / H)
            vw, vh = W * base / z, H * base / z
            cx = focus * fw + drift
            cy = fh * 0.45
            x0 = max(0, min(fw - vw, cx - vw / 2)); y0 = max(0, min(fh - vh, cy - vh / 2))
            out = self.fg.transform((W, H), Image.EXTENT, (x0, y0, x0 + vw, y0 + vh), Image.BILINEAR)
        return out

class Clip:
    """Video del cliente (sin su audio): se reproduce a velocidad real dentro del segmento.
    Vertical -> pantalla completa; horizontal -> tarjeta sobre fondo difuminado."""
    def __init__(self, path, start=0.0, fps=30):
        pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                             "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip().split(",")
        w, h = int(pr[0]), int(pr[1])
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(start), "-i", path, "-r", str(fps), "-an",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        n = len(raw) // (w * h * 3)
        self.frames = np.frombuffer(raw[:n * w * h * 3], np.uint8).reshape(n, h, w, 3)
        self.fps, self.w, self.h = fps, w, h
        self.wide = w / h > 0.75
        mid = Image.fromarray(self.frames[n // 2])
        sc = max(W / w, H / h) * 1.15
        bg = mid.resize((int(w * sc), int(h * sc)), Image.BILINEAR)
        bg = bg.crop(((bg.width - W) // 2, (bg.height - H) // 2, (bg.width - W) // 2 + W, (bg.height - H) // 2 + H))
        self.bg = Image.blend(bg.filter(ImageFilter.GaussianBlur(40)), Image.new("RGB", (W, H), (20, 8, 30)), 0.45)

    def frame(self, p, pan, pulse, focus=0.5, seg_dur=0):
        i = min(len(self.frames) - 1, int(p * seg_dur * self.fps))
        im = Image.fromarray(self.frames[i])
        z = 1.0 + 0.03 * p + pulse
        if self.wide:
            out = self.bg.copy()
            cw = W; ch = int(self.h * W / self.w)
            fr = im.resize((cw, ch), Image.BILINEAR)
            y = (H - ch) // 2 - 120
            out.paste(fr, (0, y))
            d = ImageDraw.Draw(out)
            d.rectangle((0, y - 10, W, y - 1), fill=(255, 255, 255)); d.rectangle((0, y + ch, W, y + ch + 9), fill=(255, 255, 255))
            return out
        sc = max(W / self.w, H / self.h) * z
        fr = im.resize((int(self.w * sc), int(self.h * sc)), Image.BILINEAR)
        x0 = int(max(0, min(fr.width - W, focus * fr.width - W / 2))); y0 = (fr.height - H) // 2
        return fr.crop((x0, y0, x0 + W, y0 + H))

def make_overlay():
    g = np.zeros((H, W, 4), np.uint8)
    for y in range(H):
        a = 0
        if y > 1250: a = min(215, int((y - 1250) / 670 * 260))
        if y < 220: a = int((220 - y) / 220 * 120)
        g[y, :, 3] = a
    g[..., 0] = 18; g[..., 1] = 6; g[..., 2] = 28
    return Image.fromarray(g, "RGBA")

COLORS = [(255, 214, 0), (255, 79, 154), (0, 212, 255), (124, 255, 107), (255, 140, 0), (186, 104, 255), (255, 255, 255)]

class Confetti:
    def __init__(self, n=55, seed=7):
        r = random.Random(seed)
        self.p = [dict(x=r.uniform(0, W), y0=r.uniform(-H, H), v=r.uniform(90, 240), sw=r.uniform(20, 60),
                       f=r.uniform(0.5, 2.0), ph=r.uniform(0, 6.28), c=r.choice(COLORS), s=r.uniform(8, 18),
                       rot=r.uniform(1, 5)) for _ in range(n)]

    def draw(self, img, t, hearts):
        d = ImageDraw.Draw(img, "RGBA")
        for q in self.p:
            y = (q["y0"] + q["v"] * t) % (H + 100) - 50
            x = q["x"] + q["sw"] * math.sin(q["f"] * t + q["ph"])
            s = q["s"]; w = s * abs(math.cos(q["rot"] * t + q["ph"])) + 2
            c = q["c"] + (220,)
            if hearts and q["s"] > 15.5:
                heart(d, x, y, s * 1.6, (255, 60, 120, 230))
            else:
                d.rectangle((x - w / 2, y - s / 3, x + w / 2, y + s / 3), fill=c)

PASTEL = [(255, 120, 180), (255, 214, 60), (110, 200, 255), (140, 230, 140), (190, 140, 255), (255, 160, 90)]

class Kids:
    """Tema infantil: globos que suben, estrellas que giran y titilan, burbujas, confeti suave.
    En coros: más estrellas + corazones."""
    def __init__(self, seed=11):
        r = random.Random(seed)
        side = lambda: r.uniform(30, 190) if r.random() < 0.5 else r.uniform(W - 190, W - 30)
        self.balloons = [dict(x=side(), y0=r.uniform(0, H + 400), v=r.uniform(70, 140), sw=r.uniform(15, 35),
                              f=r.uniform(0.4, 1.0), ph=r.uniform(0, 6.28), c=r.choice(PASTEL), s=r.uniform(55, 85))
                         for _ in range(7)]
        self.stars = [dict(x=r.uniform(0, W), y=r.uniform(0, H), s=r.uniform(14, 30), ph=r.uniform(0, 6.28),
                           f=r.uniform(1.5, 3.5), rot=r.uniform(-1.5, 1.5),
                           c=r.choice([(255, 230, 90), (255, 255, 255), (255, 180, 220)]),
                           vy=r.uniform(-25, 25), chorus=i % 2 == 1) for i in range(30)]
        self.bubbles = [dict(x=side() if r.random() < 0.7 else r.uniform(0, W), y0=r.uniform(0, H + 200), v=r.uniform(50, 110), sw=r.uniform(20, 50),
                             f=r.uniform(0.6, 1.4), ph=r.uniform(0, 6.28), s=r.uniform(18, 46)) for _ in range(14)]
        self.conf = Confetti(n=28, seed=seed)

    def draw(self, img, t, hearts):
        d = ImageDraw.Draw(img, "RGBA")
        for b in self.bubbles:
            y = H + 100 - (b["y0"] + b["v"] * t) % (H + 300)
            x = b["x"] + b["sw"] * math.sin(b["f"] * t + b["ph"]); r = b["s"]
            d.ellipse((x - r, y - r, x + r, y + r), fill=(200, 235, 255, 40), outline=(255, 255, 255, 150), width=3)
            d.ellipse((x - r * 0.55, y - r * 0.6, x - r * 0.2, y - r * 0.25), fill=(255, 255, 255, 170))
        self.conf.draw(img, t, False)
        for st in self.stars:
            if st["chorus"] and not hearts:
                continue
            tw = 0.6 + 0.4 * math.sin(st["f"] * t + st["ph"])
            y = (st["y"] + st["vy"] * t) % H
            star(d, st["x"], y, st["s"] * (0.8 + 0.3 * tw), st["rot"] * t + st["ph"], st["c"] + (int(120 + 130 * tw),))
        for b in self.balloons:
            y = H + 250 - (b["y0"] + b["v"] * t) % (H + 600)
            x = b["x"] + b["sw"] * math.sin(b["f"] * t + b["ph"]); s = b["s"]; c = b["c"]
            pts = [(x + 3 * math.sin(k * 0.7 + t * 2), y + s * 1.15 + k * 14) for k in range(12)]
            d.line(pts, fill=(255, 255, 255, 170), width=2)
            d.ellipse((x - s * 0.8, y - s, x + s * 0.8, y + s * 1.1), fill=c + (215,))
            d.polygon([(x - 9, y + s * 1.2), (x + 9, y + s * 1.2), (x, y + s * 1.02)], fill=c + (230,))
            d.ellipse((x - s * 0.45, y - s * 0.7, x - s * 0.15, y - s * 0.2), fill=(255, 255, 255, 120))
        if hearts:
            for k in range(8):
                hx = (k * 157 + 40 * math.sin(t + k)) % W
                hy = H + 50 - (k * 260 + 160 * t) % (H + 100)
                heart(d, hx, hy, 34, (255, 90, 150, 220))

class Snow:
    """Tema nostalgia (ausencia, recuerdos, despedidas): nieve suave cayendo y destellos tenues.
    En coros: un poco más de nieve y luces cálidas (bokeh) subiendo despacio. Sin confeti ni corazones."""
    def __init__(self, seed=5):
        r = random.Random(seed)
        self.flakes = [dict(x=r.uniform(0, W), y0=r.uniform(0, H), v=r.uniform(35, 95), sw=r.uniform(10, 40),
                            f=r.uniform(0.2, 0.7), ph=r.uniform(0, 6.28), s=r.uniform(1.8, 4.5),
                            a=r.randint(130, 220), chorus=i % 3 == 0) for i in range(55)]
        self.bokeh = [dict(x=r.uniform(0, W), y0=r.uniform(0, H + 300), v=r.uniform(18, 40), s=r.uniform(18, 42),
                           ph=r.uniform(0, 6.28), f=r.uniform(0.4, 0.9),
                           c=r.choice([(255, 214, 150), (255, 190, 170), (255, 240, 210)])) for _ in range(12)]

    def draw(self, img, t, hearts):
        # capa aparte: dibujar RGBA directo sobre img reemplaza píxeles (sin mezclar) y todo sale opaco
        layer = Image.new("RGBA", (W, H), (255, 255, 255, 0))
        d = ImageDraw.Draw(layer)
        if hearts:
            for b in self.bokeh:
                y = H + 150 - (b["y0"] + b["v"] * t) % (H + 300)
                x = b["x"] + 20 * math.sin(0.3 * t + b["ph"]); s = b["s"]
                tw = 0.5 + 0.5 * math.sin(b["f"] * t + b["ph"])
                d.ellipse((x - s, y - s, x + s, y + s), fill=b["c"] + (int(22 + 30 * tw),))
                d.ellipse((x - s * 0.5, y - s * 0.5, x + s * 0.5, y + s * 0.5), fill=b["c"] + (int(25 + 35 * tw),))
        for q in self.flakes:
            if q["chorus"] and not hearts:
                continue
            y = (q["y0"] + q["v"] * t) % (H + 40) - 20
            x = q["x"] + q["sw"] * math.sin(q["f"] * t + q["ph"]); s = q["s"]
            d.ellipse((x - s * 2.6, y - s * 2.6, x + s * 2.6, y + s * 2.6), fill=(255, 255, 255, q["a"] // 8))
            d.ellipse((x - s * 1.6, y - s * 1.6, x + s * 1.6, y + s * 1.6), fill=(255, 255, 255, q["a"] // 4))
            d.ellipse((x - s, y - s, x + s, y + s), fill=(255, 255, 255, q["a"]))
        img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(1.6)))

class Sparks:
    """Tema epico (rock, himnos, historias de vida): chispas doradas subiendo con estela, sin confeti ni corazones.
    En coros: el doble de chispas y resplandores cálidos en los bordes."""
    def __init__(self, seed=9):
        r = random.Random(seed)
        self.sp = [dict(x=r.uniform(0, W), y0=r.uniform(0, H + 200), v=r.uniform(70, 210), sw=r.uniform(8, 46),
                        f=r.uniform(0.5, 1.6), ph=r.uniform(0, 6.28), s=r.uniform(1.6, 4.2),
                        c=r.choice([(255, 196, 92), (255, 150, 50), (255, 228, 160)]),
                        chorus=i % 2 == 0) for i in range(70)]
        self.glow = [dict(x=r.choice([r.uniform(-40, 170), r.uniform(910, W + 40)]), y0=r.uniform(0, H + 300),
                          v=r.uniform(30, 60), s=r.uniform(28, 60), ph=r.uniform(0, 6.28), f=r.uniform(0.5, 1.1))
                     for _ in range(9)]

    def draw(self, img, t, hearts):
        layer = Image.new("RGBA", (W, H), (255, 255, 255, 0))
        d = ImageDraw.Draw(layer)
        if hearts:
            for g in self.glow:
                y = H + 150 - (g["y0"] + g["v"] * t) % (H + 300); s = g["s"]
                tw = 0.5 + 0.5 * math.sin(g["f"] * t + g["ph"])
                d.ellipse((g["x"] - s, y - s, g["x"] + s, y + s), fill=(255, 170, 70, int(16 + 26 * tw)))
        for q in self.sp:
            if q["chorus"] and not hearts:
                continue
            y = H + 100 - (q["y0"] + q["v"] * t) % (H + 200)
            x = q["x"] + q["sw"] * math.sin(q["f"] * t + q["ph"]); s = q["s"]
            tw = 0.55 + 0.45 * math.sin(3.1 * q["f"] * t + q["ph"])
            d.line((x, y, x - q["sw"] * 0.05, y + s * 5), fill=q["c"] + (int(70 * tw),), width=max(1, int(s * 0.7)))
            d.ellipse((x - s * 2.2, y - s * 2.2, x + s * 2.2, y + s * 2.2), fill=q["c"] + (int(45 * tw),))
            d.ellipse((x - s, y - s, x + s, y + s), fill=q["c"] + (int(235 * tw),))
        img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(0.9)))

def star(d, x, y, s, a, c):
    pts = []
    for k in range(10):
        r = s if k % 2 == 0 else s * 0.45
        ang = a + k * math.pi / 5 - math.pi / 2
        pts.append((x + r * math.cos(ang), y + r * math.sin(ang)))
    d.polygon(pts, fill=c)

def heart(d, x, y, s, c):
    r = s / 4
    d.ellipse((x - 2 * r, y - r, x, y + r), fill=c)
    d.ellipse((x, y - r, x + 2 * r, y + r), fill=c)
    d.polygon([(x - 2 * r + 1, y + r * 0.3), (x + 2 * r - 1, y + r * 0.3), (x, y + 2.6 * r)], fill=c)

def main():
    tl = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    fps, dur = tl["fps"], tl["duration"]
    rng = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 and sys.argv[3] == "--range" else None
    focus = {(int(k) if k.isdigit() else k): v for k, v in tl.get("focus", {}).items()}
    beats = np.array(tl["beats"])
    pulso = tl.get("pulso", True)  # zoom en cada beat; algunos clientes lo sienten mareador
    segs = tl["segments"]
    cache = {}
    def photo(n):
        if n not in cache:
            if n == "clip":
                cache[n] = Clip(tl["clip"], tl.get("clip_inicio", 0.0), fps)
            else:
                cache[n] = Photo(tl["files"][n - 1])
            if len(cache) > 6:
                cache.pop(next(k for k in cache if k != "clip"))
        return cache[n]
    overlay = make_overlay()
    tema = tl.get("tema")
    conf = Kids() if tema == "infantil" else Snow() if tema == "nostalgia" else Sparks() if tema == "epico" else Confetti()
    hearts = tl.get("hearts", [])
    XF = tl.get("crossfade") or 0.35  # segundos; nostalgia: ~1.0 (fundidos lentos)
    frames = range(int(dur * fps))
    if rng:
        frames = range(round(rng[0] * fps), round(min(rng[1], dur) * fps))
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                           "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    si = 0
    for fi in frames:
        t = fi / fps
        while si < len(segs) - 1 and t >= segs[si]["end"]:
            si += 1
        while si > 0 and t < segs[si]["start"]:
            si -= 1
        s = segs[si]
        # pulso: True = en cada beat (decay rápido); "suave" = solo en los coros, un respiro lento
        # cada compás (4 beats); False = nada
        k = np.searchsorted(beats, t) - 1
        pulse = 0.0
        if pulso == "suave":
            if k >= 0 and any(a <= t < b for a, b in hearts):
                k4 = k - k % 4
                dt = t - beats[k4]
                if dt < 1.2:
                    pulse = 0.008 * math.sin(math.pi * dt / 1.2)
        elif pulso and k >= 0:
            dt = t - beats[k]
            pulse = 0.018 * math.exp(-dt * 9) * (1.6 if k % 2 == 0 else 1.0)
        p = (t - s["start"]) / (s["end"] - s["start"])
        img = photo(s["photo"]).frame(p, s.get("pan", -1), pulse, focus.get(s["photo"], 0.5),
                                         s["end"] - s["start"])
        # crossfade hacia el siguiente
        if si < len(segs) - 1 and t > s["end"] - XF:
            n = segs[si + 1]
            a = (t - (s["end"] - XF)) / XF
            pn = (t - n["start"]) / (n["end"] - n["start"])
            nxt = photo(n["photo"]).frame(max(pn, 0), n.get("pan", -1), pulse, focus.get(n["photo"], 0.5),
                                          n["end"] - n["start"])
            img = Image.blend(img, nxt, ease(a))
        img = img.convert("RGBA")
        img.alpha_composite(overlay)
        in_hearts = any(a <= t < b for a, b in hearts)
        conf.draw(img, t, in_hearts)
        # flash blanco al inicio de segmentos marcados
        if s.get("flash") and t - s["start"] < 0.25:
            fa = int(200 * (1 - (t - s["start"]) / 0.25))
            img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, fa)))
        ff.stdin.write(img.convert("RGB").tobytes())
        if fi % (fps * 10) == 0:
            print(f"{t:6.1f}s / {dur:.0f}s", flush=True)
    ff.stdin.close(); ff.wait()

if __name__ == "__main__":
    main()
