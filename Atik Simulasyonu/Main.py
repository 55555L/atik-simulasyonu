"""Akıllı Yeraltı Atık Transfer Simülasyonu (tkinter)
Sadece Python standart kütüphanesi kullanır. Model katsayıları örnek değerlerdir."""
import math
import random
import tkinter as tk
from tkinter import ttk

W, H = 1000, 520
HUB = 46
MY = H / 2
BL = min(105, H * 0.3)
SPD = 45          # birim/dakika: vagon hızı
K = 0.012         # kWh/birim: model katsayısı
MON = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara']
T_AMB = [0.3, 1.7, 5.8, 11, 15.8, 19.8, 23.2, 23, 18.5, 12.7, 6.8, 2.4]
GHI = [350, 480, 640, 790, 900, 990, 1010, 960, 830, 640, 450, 320]
SUN_H = [1.9, 2.8, 4, 5.2, 6.4, 7.2, 7.5, 6.8, 5.4, 3.6, 2.2, 1.6]
DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

BG, PANEL, INK, MUTED = "#0f1a1e", "#172429", "#e2ecee", "#91a7ae"
ACC, OK, TUNNEL, SUN = "#ff7a50", "#4cc79a", "#466068", "#f0bf3f"


class App:
    def __init__(self, root):
        self.root = root
        root.title("Akıllı Yeraltı Atık Transfer Simülasyonu")
        root.configure(bg=BG)
        self.p = dict(n=14, th=70, v=2, sp=30, rt=60, cr=1.3, ov=18, ar=1000, dm=1100)
        self.t = self.D = self.st = self.over = 0.0
        self.pause = False

        self.canvas = tk.Canvas(root, width=W, height=H, bg=BG, highlightthickness=0)
        self.canvas.pack(side="left")

        side = tk.Frame(root, bg=PANEL, padx=10, pady=10)
        side.pack(side="right", fill="y")
        tk.Label(side, text="Tünel ağı", bg=PANEL, fg=INK, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.make_slider(side, "n", "Bina sayısı", 4, 24, 1, self.reset)
        self.make_slider(side, "th", "Çağrı eşiği (%)", 30, 95, 5)
        self.make_slider(side, "v", "Vagon sayısı", 1, 4, 1, self.reset)
        self.make_slider(side, "sp", "Simülasyon hızı (dk/sn)", 5, 120, 5)
        self.make_slider(side, "rt", "Sabit tur aralığı (dk)", 30, 180, 10)

        btns = tk.Frame(side, bg=PANEL)
        btns.pack(anchor="w", pady=6)
        self.pause_btn = tk.Button(btns, text="Duraklat", command=self.toggle_pause)
        self.pause_btn.pack(side="left", padx=(0, 6))
        tk.Button(btns, text="Yeniden başlat", command=self.reset).pack(side="left")

        tk.Label(side, text="Koni boru", bg=PANEL, fg=INK, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 0))
        self.make_slider(side, "cr", "Koni açılma oranı", 1.0, 1.8, 0.05, self.update_pipe)
        self.damp = tk.BooleanVar(value=True)
        self.nonstick = tk.BooleanVar(value=True)
        tk.Checkbutton(side, text="Titreşim sönümleyici", variable=self.damp, command=self.update_pipe,
                       bg=PANEL, fg=INK, selectcolor=BG, activebackground=PANEL).pack(anchor="w")
        tk.Checkbutton(side, text="Yapışmaz iç yüzey", variable=self.nonstick, command=self.update_pipe,
                       bg=PANEL, fg=INK, selectcolor=BG, activebackground=PANEL).pack(anchor="w")
        self.pipe_label = tk.Label(side, bg=PANEL, fg=INK, justify="left")
        self.pipe_label.pack(anchor="w")

        tk.Label(side, text="Güneş enerjisi (Ankara ortalaması)", bg=PANEL, fg=INK,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 0))
        self.make_slider(side, "ov", "Panel artırımı (%)", 0, 40, 2, self.draw_solar)
        self.make_slider(side, "ar", "Taban panel alanı (m²)", 500, 2000, 100, self.draw_solar)
        self.make_slider(side, "dm", "Günlük tüketim (kWh)", 500, 2500, 50, self.draw_solar)
        self.solar_canvas = tk.Canvas(side, width=260, height=130, bg=BG, highlightthickness=0)
        self.solar_canvas.pack(anchor="w", pady=4)
        self.solar_label = tk.Label(side, bg=PANEL, fg=INK, justify="left")
        self.solar_label.pack(anchor="w")

        self.stats_label = tk.Label(root, bg=BG, fg=INK, font=("Segoe UI", 10), justify="left", anchor="w")
        self.stats_label.place(x=10, y=H - 10, anchor="sw")

        self.reset()
        self.update_pipe()
        self.draw_solar()
        self.last_stats = 0
        self.tick()

    # ---------- arayüz yardımcıları ----------
    def make_slider(self, parent, key, name, a, b, step, callback=None):
        lbl = tk.Label(parent, bg=PANEL, fg=MUTED, text=f"{name}: {self.p[key]:g}")
        lbl.pack(anchor="w")

        def on_change(value, k=key, st=step, L=lbl, nm=name, cb=callback):
            val = round(round(float(value) / st) * st, 2)
            self.p[k] = val
            L.config(text=f"{nm}: {val:g}")
            if cb:
                cb()

        ttk.Scale(parent, from_=a, to=b, value=self.p[key], length=240, command=on_change).pack(anchor="w")

    def toggle_pause(self):
        self.pause = not self.pause
        self.pause_btn.config(text="Devam et" if self.pause else "Duraklat")

    # ---------- tünel simülasyonu ----------
    def reset(self):
        n = int(self.p['n'])
        cols = max(1, math.ceil(n / 2) - 1)
        self.B = []
        for i in range(n):
            self.B.append(dict(fx=(i // 2) / cols, up=(i % 2 == 0), f=random.random() * 45,
                               r=0.08 + random.random() * 0.16, tg=False, o=False))
        self.V = [dict(x=HUB, y=MY, s='idle', b=None, w=0.0, ld=False) for _ in range(int(self.p['v']))]
        self.t = self.D = self.st = self.over = 0.0

    def bx(self, b):
        return HUB + 40 + b['fx'] * (W - HUB - 120)

    def move(self, v, tx, ty, m):
        dx, dy = tx - v['x'], ty - v['y']
        d = math.hypot(dx, dy)
        s = min(d, m)
        if d > 0:
            v['x'] += dx / d * s
            v['y'] += dy / d * s
        self.D += s * (1.25 if v['ld'] else 1.0)
        return d <= m

    def step(self, dm):
        self.t += dm
        for b in self.B:
            b['f'] = min(100.0, b['f'] + b['r'] * dm)
            if b['f'] >= 100:
                if not b['o']:
                    self.over += 1
                b['o'] = True
            else:
                b['o'] = False

        for v in self.V:
            m = SPD * dm
            if v['s'] == 'idle':
                c = sorted([b for b in self.B if not b['tg'] and b['f'] >= self.p['th']], key=lambda b: b['fx'])
                if c:
                    v['b'] = c[0]
                    c[0]['tg'] = True
                    v['s'] = 'out'
            b = v['b']
            if b is None:
                continue
            by = MY - BL if b['up'] else MY + BL
            s = v['s']
            if s == 'out' and self.move(v, self.bx(b), MY, m):
                v['s'] = 'in'
            elif s == 'in' and self.move(v, self.bx(b), by, m):
                v['s'] = 'load'
                v['w'] = 20
            elif s == 'load':
                v['w'] -= dm
                b['f'] = max(0.0, b['f'] - dm * 5)
                if v['w'] <= 0:
                    b['f'], b['tg'], b['o'] = 0.0, False, False
                    v['ld'] = True
                    self.st += 1
                    v['s'] = 'outb'
            elif s == 'outb' and self.move(v, self.bx(b), MY, m):
                v['s'] = 'back'
            elif s == 'back' and self.move(v, HUB, MY, m):
                v['s'] = 'unl'
                v['w'] = 10
            elif s == 'unl':
                v['w'] -= dm
                if v['w'] <= 0:
                    v['ld'] = False
                    v['s'] = 'idle'
                    v['b'] = None

    def draw(self):
        c = self.canvas
        c.delete("all")
        c.create_line(HUB, MY, W - 30, MY, fill=TUNNEL, width=8, capstyle="round")
        c.create_text(14, 14, anchor="nw", fill=MUTED, text="Yer üstü: bina sırası   Yer altı: depo ve tünel")
        for b in self.B:
            x = self.bx(b)
            y = MY - BL if b['up'] else MY + BL
            c.create_line(x, MY, x, y, fill=TUNNEL, width=2)
            hot = b['f'] >= self.p['th']
            w, h = 26, 34
            c.create_rectangle(x - w / 2, y - h / 2, x + w / 2, y + h / 2, fill=PANEL,
                               outline=ACC if hot else INK, width=2)
            fh = (h - 4) * b['f'] / 100
            c.create_rectangle(x - w / 2 + 2, y + h / 2 - 2 - fh, x + w / 2 - 2, y + h / 2 - 2,
                               fill=ACC if hot else OK, outline="")
        c.create_rectangle(HUB - 26, MY - 22, HUB + 6, MY + 22, fill=INK, outline="")
        c.create_text(HUB - 10, MY, text="Merkez", fill=PANEL, font=("Segoe UI", 7))
        for v in self.V:
            c.create_rectangle(v['x'] - 11, v['y'] - 6, v['x'] + 11, v['y'] + 6,
                               fill=INK if v['ld'] else ACC, outline="")

    def update_stats(self):
        n = len(self.B)
        bl = BL
        bd = self.D * K
        rd = 2 * (W - HUB - 60) + n * 2 * bl
        rounds = self.t / self.p['rt']
        bs = rounds * rd * 1.25 * K
        sv = max(0.0, 100 * (1 - bd / bs)) if bs > 1 else 0.0
        avg = sum(b['f'] for b in self.B) / n
        days, hours = int(self.t // 1440), int(self.t % 1440 // 60)
        self.stats_label.config(text=(
            f"Süre: {days} g {hours} sa   |   Dinamik rota enerjisi: {bd:.0f} kWh   |   "
            f"Sabit tur enerjisi: {bs:.0f} kWh   |   Tasarruf: %{sv:.0f}\n"
            f"Uğrama (dinamik / sabit): {self.st} / {round(rounds * n)}   |   "
            f"Ortalama doluluk: %{avg:.0f}   |   Taşma olayı: {int(self.over)}"))

    # ---------- boru ----------
    def update_pipe(self):
        r = self.p['cr']
        x = 0.42 * math.exp(-3.2 * (r - 1))
        if self.damp.get():
            x *= 0.5
        if self.nonstick.get():
            x *= 0.6
        self.pipe_label.config(text=f"1000 atımda tahmini köprülenme: %{x * 100:.1f} "
                                    f"({round(x * 1000)} olay)\nBasit sezgisel model, gerçek değer için akış testi gerekir.")

    # ---------- güneş ----------
    def solar_data(self):
        rows = []
        for i in range(12):
            tc = T_AMB[i] + 20 / 800 * GHI[i]
            loss = max(0.0, 0.004 * (tc - 25))
            ideal = self.p['ar'] * 0.2 * SUN_H[i] * 0.8 * DAYS[i]
            act = ideal * (1 - loss) * (1 + self.p['ov'] / 100)
            need = self.p['dm'] * DAYS[i]
            rows.append((loss, act, need))
        return rows

    def draw_solar(self):
        rows = self.solar_data()
        c = self.solar_canvas
        c.delete("all")
        w, h = 260, 130
        mx = max(max(a, n) for _, a, n in rows) * 1.1
        bw = w / 12
        for i, (_, act, need) in enumerate(rows):
            x = i * bw + bw * 0.15
            bh = (h - 20) * act / mx
            c.create_rectangle(x, h - 14 - bh, x + bw * 0.7, h - 14, fill=OK, outline="")
            c.create_text(x + 2, h - 4, anchor="sw", fill=MUTED, text=MON[i][:1], font=("Segoe UI", 7))
        pts = []
        for i, (_, _, need) in enumerate(rows):
            pts += [i * bw + bw / 2, h - 14 - (h - 20) * need / mx]
        c.create_line(*pts, fill=ACC, width=2)

        prod = sum(a for _, a, _ in rows)
        need_sum = sum(n for _, _, n in rows)
        worst = min(a / n for _, a, n in rows) * 100
        jul_loss = rows[6][0] * 100
        self.solar_label.config(text=(
            f"Temmuz ısıl kaybı: %{jul_loss:.1f}   Yıllık üretim: {prod / 1000:.0f} MWh\n"
            f"Yıllık karşılama: %{min(100, prod / need_sum * 100):.0f}   En zayıf ay: %{worst:.0f}"))

    # ---------- döngü ----------
    def tick(self):
        if not self.pause:
            self.step(0.05 * self.p['sp'])
        self.draw()
        self.last_stats += 1
        if self.last_stats >= 4:
            self.update_stats()
            self.last_stats = 0
        self.root.after(50, self.tick)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()