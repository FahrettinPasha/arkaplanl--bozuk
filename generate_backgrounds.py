"""
generate_backgrounds.py
========================
Fragmentia oyunu için 7 tema × 3 parallax katman = 21 PNG üretir.
Çıktı klasörü: assets/backgrounds/

Kullanım:
    python3 generate_backgrounds.py

Üretilen dosyalar (settings.py THEMES sırası):
    0: neon_far/mid/near.png       — NEON PAZARI
    1: nexus_far/mid/near.png      — NEXUS ÇEKİRDEĞİ
    2: gutter_far/mid/near.png     — MİDE (THE GUTTER)
    3: industrial_far/mid/near.png — DÖKÜMHANE
    4: safe_far/mid/near.png       — GÜVENLİ BÖLGE
    5: factory_far/mid/near.png    — FABRİKA İÇİ
    6: manor_far/mid/near.png      — MALİKANE

Her PNG: 3840 × 1080 px (2 × ekran genişliği → sorunsuz döngü)
"""

import os
import math
import random
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

# ─── AYARLAR ───────────────────────────────────────────────────────────────────
W  = 3840   # 2 × LOGICAL_WIDTH — sorunsuz yatay döngü için
H  = 1080   # LOGICAL_HEIGHT
OUT = "assets/backgrounds"
os.makedirs(OUT, exist_ok=True)

RNG = random.Random(42)   # Deterministik — her çalıştırmada aynı görüntü

# ─── YARDIMCI FONKSİYONLAR ─────────────────────────────────────────────────────

def img(color=(0,0,0)):
    if len(color) == 4:
        return Image.new("RGBA", (W, H), color)
    return Image.new("RGBA", (W, H), color + (255,))

def draw(im):
    return ImageDraw.Draw(im, "RGBA")

def clamp(v, lo=0, hi=255):
    return max(lo, min(hi, int(v)))

def col(r, g, b, a=255):
    return (clamp(r), clamp(g), clamp(b), clamp(a))

def lerp_col(c1, c2, t):
    return col(c1[0]+(c2[0]-c1[0])*t, c1[1]+(c2[1]-c1[1])*t, c1[2]+(c2[2]-c1[2])*t)

def gradient_rect(d, x0, y0, x1, y1, c_top, c_bot, steps=40):
    """Dikey gradyan dikdörtgen çizer."""
    h = y1 - y0
    if h <= 0:
        return
    step = max(1, h // steps)
    for y in range(y0, y1, step):
        t = (y - y0) / max(1, h)
        c = lerp_col(c_top, c_bot, t)
        d.rectangle([(x0, y), (x1, min(y + step, y1))], fill=c)

def vgrad_bg(im, c_top, c_bot):
    """Tüm arka planı dikey gradyanla doldurur."""
    d = draw(im)
    gradient_rect(d, 0, 0, W, H, c_top, c_bot, steps=80)

def glow_circle(im, cx, cy, radius, color, alpha_center=180, alpha_edge=0):
    """Radyal parıltı efekti (arka plana blit edilir)."""
    glow = Image.new("RGBA", (W, H), (0,0,0,0))
    gd = ImageDraw.Draw(glow, "RGBA")
    steps = 20
    for i in range(steps, 0, -1):
        r = int(radius * i / steps)
        a = int(alpha_center * (1 - i/steps) + alpha_edge * (i/steps))
        a = clamp(a)
        gd.ellipse([(cx-r, cy-r),(cx+r, cy+r)],
                   fill=(color[0], color[1], color[2], a))
    im.alpha_composite(glow)

def save(im, name):
    path = os.path.join(OUT, name)
    im.save(path, "PNG")
    print(f"  ✓  {path}")

def neon_line(d, x0, y0, x1, y1, color, width=1, glow_width=4):
    """Neon çizgi: önce geniş yarı saydam, sonra ince parlak."""
    r, g, b = color[:3]
    d.line([(x0,y0),(x1,y1)], fill=(r,g,b,40), width=glow_width*3)
    d.line([(x0,y0),(x1,y1)], fill=(r,g,b,100), width=glow_width)
    d.line([(x0,y0),(x1,y1)], fill=(r,g,b,220), width=width)

def repeat_motif(draw_fn, count, rng=None):
    """Bir çizim fonksiyonunu yatayda count kez tekrar eder."""
    if rng is None:
        rng = RNG
    for i in range(count):
        x_offset = i * (W // count)
        draw_fn(x_offset, rng)

def stars(d, count, rng, y_max=H, alpha_range=(60,200)):
    for _ in range(count):
        x = rng.randint(0, W)
        y = rng.randint(0, y_max)
        a = rng.randint(*alpha_range)
        r = rng.choice([1,1,1,2])
        d.ellipse([(x-r,y-r),(x+r,y+r)], fill=(255,255,255,a))

def scanlines(im, alpha=15):
    """Hafif CRT tarama çizgileri efekti."""
    sl = Image.new("RGBA", (W, H), (0,0,0,0))
    sld = ImageDraw.Draw(sl, "RGBA")
    for y in range(0, H, 3):
        sld.line([(0,y),(W,y)], fill=(0,0,0,alpha))
    im.alpha_composite(sl)

# ══════════════════════════════════════════════════════════════════════════════
#  TEMA 0: NEON PAZARI
#  Renk paleti: bg (15,15,25) | cyan (0,200,255) | magenta (220,0,200)
# ══════════════════════════════════════════════════════════════════════════════

def make_neon_far():
    """Uzak ufuk: siber gece gökyüzü + uzak gökdelen siluetleri + yıldızlar."""
    im = img()
    d  = draw(im)

    # Gökyüzü gradyanı — tepeden tabana
    gradient_rect(d, 0, 0, W, H, (5,5,18), (20,10,35), 100)

    # Ufuk parıltısı — neon pembe/mor
    glow_circle(im, W//4,   H-80, 600, (180,0,200), 60, 0)
    glow_circle(im, W*3//4, H-80, 500, (0,180,220), 50, 0)

    # Uzak gökdelen siluetleri
    buildings = [
        (0, 200, 250, 560), (300, 320, 180, 400), (550, 150, 220, 580),
        (820, 280, 200, 450), (1100, 100, 250, 620), (1420, 350, 180, 390),
        (1660, 200, 270, 530), (1980, 120, 190, 610), (2250, 300, 220, 440),
        (2540, 180, 260, 560), (2860, 250, 150, 490), (3100, 310, 200, 430),
        (3350, 140, 280, 600), (3650, 270, 160, 480),
    ]
    for (x, y, w, h_b) in buildings:
        # Bina gövdesi — çok koyu mavi-mor
        d.rectangle([(x, H-h_b), (x+w, H)], fill=(12,8,25,220))
        # Pencereler — sarımsı veya neon
        for wy in range(H-h_b+20, H-20, 35):
            for wx in range(x+10, x+w-10, 25):
                if RNG.random() < 0.45:
                    wc = RNG.choice([(0,200,255,160),(200,0,255,140),(255,200,0,120)])
                    d.rectangle([(wx,wy),(wx+10,wy+14)], fill=wc)
        # Çatı anteni
        ax = x + w//2
        d.line([(ax, H-h_b),(ax, H-h_b-40)], fill=(0,200,255,180), width=2)
        d.ellipse([(ax-4,H-h_b-46),(ax+4,H-h_b-38)], fill=(0,255,255,200))

    # Uzak neon ızgara çizgileri (perspektif)
    for i in range(10):
        vx = i * (W // 10)
        d.line([(vx, H*2//3),(W//2, H)], fill=(0,180,220,20), width=1)

    stars(d, 250, RNG, y_max=H*2//3)
    scanlines(im, 12)
    return im

def make_neon_mid():
    """Orta kat: cyberpunk binalar, neon tabelalar, hologramlar."""
    im = img((0,0,0,0))  # Şeffaf — üste gelir
    d  = draw(im)

    # Orta plan bina blokları
    blocks = [
        (0, H-420, 280, 420), (350, H-340, 200, 340), (620, H-480, 240, 480),
        (940, H-360, 220, 360), (1240, H-520, 260, 520), (1580, H-380, 200, 380),
        (1850, H-440, 280, 440), (2210, H-350, 230, 350), (2530, H-490, 250, 490),
        (2860, H-370, 210, 370), (3140, H-430, 270, 430), (3480, H-360, 200, 360),
        (3740, H-410, 260, 410),
    ]
    for (x, y, w, h_b) in blocks:
        # Ana gövde
        d.rectangle([(x,y),(x+w,H)], fill=(18,12,30,230))
        # Yan kenar çizgisi (neon outline)
        d.line([(x,y),(x,H)], fill=(0,180,255,80), width=2)
        d.line([(x+w,y),(x+w,H)], fill=(0,180,255,60), width=1)
        # Teras/çatı detayı
        d.rectangle([(x+10,y),(x+w-10,y+12)], fill=(0,140,200,120))
        # Pencereler
        for wy in range(y+30, H-20, 32):
            for wx in range(x+12, x+w-12, 22):
                if RNG.random() < 0.5:
                    intensity = RNG.randint(80, 200)
                    wc = RNG.choice([
                        (0,intensity,255,180),
                        (intensity,0,255,150),
                        (intensity,intensity,40,130)
                    ])
                    d.rectangle([(wx,wy),(wx+12,wy+18)], fill=wc)

    # Neon tabelalar
    signs = [
        (180, H-300, "═══════", (0,220,255)),
        (700, H-260, "▓▓▓▓▓▓▓", (220,0,180)),
        (1300, H-350, "═══════", (0,255,150)),
        (1900, H-290, "▓▓▓▓▓▓▓", (255,150,0)),
        (2600, H-380, "═══════", (0,220,255)),
        (3200, H-300, "▓▓▓▓▓▓▓", (220,0,180)),
    ]
    for (sx, sy, text, color) in signs:
        r,g,b = color
        # Parıltı arkaplanı
        d.rectangle([(sx-5,sy-8),(sx+100,sy+22)], fill=(r,g,b,30))
        d.rectangle([(sx-2,sy-4),(sx+98,sy+18)], fill=(r,g,b,80))
        # Tabela çizgisi
        d.line([(sx,sy+7),(sx+95,sy+7)], fill=(r,g,b,220), width=3)
        d.line([(sx,sy+9),(sx+95,sy+9)], fill=(r,g,b,100), width=2)

    # Dikey neon borular/hatlar
    for px in range(0, W, 280):
        px += RNG.randint(-30,30)
        c = RNG.choice([(0,180,255),(180,0,255),(0,255,150)])
        alpha = RNG.randint(30,100)
        d.line([(px,H-500),(px,H)], fill=(*c,alpha), width=1)

    return im

def make_neon_near():
    """Ön plan: zemin boruları, yangın merdivenleri, ızgaralar."""
    im = img((0,0,0,0))
    d  = draw(im)

    # Zemin şeridi
    gradient_rect(d, 0, H-60, W, H, (10,8,22), (5,5,15), 10)
    d.line([(0,H-60),(W,H-60)], fill=(0,180,255,120), width=2)

    # Ön zemin silüetleri / barikatlar
    for i in range(0, W, 400):
        x = i + RNG.randint(0,80)
        btype = RNG.randint(0,2)
        if btype == 0:
            # Metal konteyner
            d.rectangle([(x, H-110),(x+120, H-62)], fill=(8,6,18,240))
            d.rectangle([(x+2, H-108),(x+118, H-64)], fill=(0,0,0,0))  # içi boş
            d.line([(x,H-110),(x+120,H-110)], fill=(0,150,200,150), width=2)
        elif btype == 1:
            # Boru demeti
            for pi in range(3):
                px2 = x + pi*18
                d.rectangle([(px2, H-160),(px2+12, H-60)], fill=(15,15,30,220))
                d.line([(px2+6,H-170),(px2+6,H-155)], fill=(0,200,255,180), width=2)
        else:
            # Çöp kutusu
            d.rectangle([(x, H-100),(x+60, H-62)], fill=(20,10,30,230))

    # Yukarıdaki yangın merdiveni yapıları
    for mx in range(100, W, 700):
        mh = RNG.randint(200, 400)
        # Dikey kolon
        d.rectangle([(mx, H-mh),(mx+8, H-60)], fill=(15,10,28,200))
        # Yatay basamaklar
        for fy in range(H-mh+30, H-60, 40):
            d.line([(mx-30, fy),(mx+38, fy)], fill=(0,150,200,120), width=2)
        # Parlak bağlantı noktaları
        for fy in range(H-mh, H-60, 80):
            d.ellipse([(mx-3,fy-3),(mx+11,fy+3)], fill=(0,220,255,200))

    # Zemin neon çizgisi parıltısı
    neon_line(d, 0, H-62, W, H-62, (0,200,255), width=2, glow_width=6)

    return im


# ══════════════════════════════════════════════════════════════════════════════
#  TEMA 1: NEXUS ÇEKİRDEĞİ
#  Renk paleti: bg (20,20,20) | kırmızı (255,0,0) | altın (255,215,0)
# ══════════════════════════════════════════════════════════════════════════════

def make_nexus_far():
    """Uzak arka plan: veri ızgarası, sistem sunucu kuleleri silueti."""
    im = img()
    d  = draw(im)

    # Karanlık gradyan — çok koyu, neredeyse siyah
    gradient_rect(d, 0, 0, W, H, (8,5,5), (25,8,8), 80)

    # Uzak perspektif ızgara (veri matrisi hissi)
    horizon = H * 3 // 5
    for i in range(0, W, 120):
        d.line([(i, horizon),(W//2 + (i-W//2)*2, H)], fill=(180,0,0,25), width=1)
    for step in range(0, 20):
        y = horizon + step * (H-horizon)//20
        alpha = int(20 + step * 4)
        d.line([(0,y),(W,y)], fill=(180,0,0,min(alpha,80)), width=1)

    # Uzak silindir/kule yapıları (Nexus sunucu kuleleri)
    for tx in range(0, W, 320):
        tx += RNG.randint(0,50)
        th = RNG.randint(200, 500)
        tw = RNG.randint(40, 80)
        d.rectangle([(tx, H-th),(tx+tw, H)], fill=(15,8,8,200))
        # Kule ışık halkası
        ring_y = H - th
        d.ellipse([(tx-5,ring_y-4),(tx+tw+5,ring_y+4)], fill=(200,0,0,80))
        # Kule tepesi ışık
        d.ellipse([(tx+tw//2-6,ring_y-14),(tx+tw//2+6,ring_y-2)],
                  fill=(255,60,60,200))

    # Uzak kırmızı enerji çizgileri
    for _ in range(15):
        lx = RNG.randint(0, W)
        ly = RNG.randint(H//3, H*2//3)
        lw = RNG.randint(200, 800)
        d.line([(lx,ly),(lx+lw,ly+RNG.randint(-20,20))],
               fill=(200,0,0,RNG.randint(15,40)), width=1)

    stars(d, 150, RNG, y_max=H//2, alpha_range=(40,120))
    return im

def make_nexus_mid():
    """Orta: dev veri kuleleri, kırmızı enerji halkalar, sistem ağ geçitleri."""
    im = img((0,0,0,0))
    d  = draw(im)

    # Ana kule blokları
    towers = [
        (50, H-600, 100, 20, True),
        (400, H-450, 80, 18, False),
        (750, H-700, 120, 22, True),
        (1150, H-500, 90, 18, False),
        (1550, H-650, 110, 20, True),
        (1950, H-480, 85, 18, False),
        (2300, H-720, 130, 24, True),
        (2750, H-540, 95, 19, False),
        (3100, H-680, 115, 21, True),
        (3500, H-460, 88, 17, False),
        (3750, H-580, 105, 20, True),
    ]

    for (x, y, w, segment_h, is_main) in towers:
        h_t = H - y
        # Kule gövdesi — bölümlü
        seg_count = h_t // segment_h
        for si in range(seg_count):
            sy = y + si * segment_h
            brightness = 8 + si * 2
            d.rectangle([(x, sy),(x+w, sy+segment_h-2)],
                        fill=(brightness, brightness//2, brightness//2, 230))
            if si % 3 == 0:
                # Enerji halkası
                d.line([(x-8,sy+segment_h//2),(x+w+8,sy+segment_h//2)],
                       fill=(200,0,0,60), width=3)

        # Kule ana hat çizgisi
        d.line([(x,y),(x,H)], fill=(200,20,20,100), width=2)
        d.line([(x+w,y),(x+w,H)], fill=(180,0,0,80), width=1)

        # Tepedeki anten/enerji küre
        if is_main:
            ax = x + w//2
            # Anten
            d.line([(ax, y),(ax, y-60)], fill=(255,80,80,180), width=3)
            # Enerji küresi
            d.ellipse([(ax-18,y-82),(ax+18,y-44)], fill=(200,0,0,200))
            d.ellipse([(ax-10,y-74),(ax+10,y-52)], fill=(255,100,100,255))

        # Veri akış çizgileri (dikey parlak çizgiler)
        for di in range(3):
            dx = x + 10 + di * (w//4)
            # Aşağı akan veri
            for gy in range(y+20, H, 30):
                if RNG.random() < 0.3:
                    d.rectangle([(dx,gy),(dx+3,gy+15)], fill=(255,0,0,RNG.randint(20,80)))

    # Arka plan kırmızı ağ geçidi kemerleri
    for ax in range(200, W, 800):
        aw = 300
        ah = 220
        d.arc([(ax,H-ah),(ax+aw,H+40)], 180, 0, fill=(180,0,0,60), width=3)
        d.arc([(ax+10,H-ah+10),(ax+aw-10,H+30)], 180, 0, fill=(255,60,60,40), width=1)

    return im

def make_nexus_near():
    """Ön plan: metal zemin ızgara, kırmızı lazer hatlar, veri terminalleri."""
    im = img((0,0,0,0))
    d  = draw(im)

    # Metal zemin
    gradient_rect(d, 0, H-70, W, H, (18,8,8), (8,4,4), 20)

    # Zemin ızgara
    for gx in range(0, W, 80):
        d.line([(gx, H-70),(gx, H)], fill=(180,0,0,40), width=1)
    d.line([(0, H-70),(W, H-70)], fill=(220,0,0,140), width=2)
    d.line([(0, H-68),(W, H-68)], fill=(255,60,60,60), width=1)

    # Kırmızı lazer çit/barikatlar
    for lx in range(0, W, 350):
        lx += RNG.randint(0,80)
        lh = RNG.randint(80,160)
        # Dikey direk
        d.rectangle([(lx-4, H-lh-70),(lx+4, H-70)], fill=(30,10,10,220))
        # Lazer ışını
        d.line([(lx,H-lh-70),(lx,H-70)], fill=(255,0,0,200), width=2)
        d.line([(lx,H-lh-70),(lx,H-70)], fill=(255,100,100,80), width=6)
        # Tepe ışıkçık
        d.ellipse([(lx-5,H-lh-76),(lx+5,H-lh-66)], fill=(255,50,50,240))

    # Veri terminalleri
    for tx in range(150, W, 600):
        tx += RNG.randint(0,100)
        # Terminal gövdesi
        d.rectangle([(tx, H-150),(tx+60, H-70)], fill=(20,10,10,230))
        d.rectangle([(tx+5, H-145),(tx+55, H-90)], fill=(40,0,0,200))
        # Ekran parıltısı
        d.rectangle([(tx+8, H-142),(tx+52, H-93)], fill=(180,0,0,100))
        d.rectangle([(tx+12,H-138),(tx+48,H-97)], fill=(220,30,30,60))
        # Ekran çizgileri (veri akışı)
        for ey in range(H-135, H-98, 8):
            d.line([(tx+12,ey),(tx+48,ey)], fill=(255,60,60,80), width=1)

    # Zemin kırmızı enerji hattı
    neon_line(d, 0, H-71, W, H-71, (255,0,0), width=2, glow_width=8)

    return im


# ══════════════════════════════════════════════════════════════════════════════
#  TEMA 2: MİDE / THE GUTTER
#  Renk paleti: bg (10,20,10) | yeşil (50,200,50) | çürük sarı (150,180,30)
# ══════════════════════════════════════════════════════════════════════════════

def make_gutter_far():
    """Uzak: kirli yeraltı tavanı, uzak boru ağları, loş yeşil parıltı."""
    im = img()
    d  = draw(im)

    # Kirli yeraltı hava gradyanı
    gradient_rect(d, 0, 0, W, H, (5,12,5), (12,22,8), 80)

    # Tavan yapısı — üstte beton/taş izlenimi
    gradient_rect(d, 0, 0, W, 120, (8,18,8), (5,12,5), 30)
    for cx in range(0, W, 180):
        # Tavan çatlakları
        for _ in range(3):
            x1 = cx + RNG.randint(0, 160)
            y1 = RNG.randint(0, 80)
            d.line([(x1,y1),(x1+RNG.randint(-40,40),y1+RNG.randint(30,80))],
                   fill=(3,8,3,120), width=1)

    # Uzak dev boru silüetleri
    for px in range(0, W, 220):
        px += RNG.randint(0,40)
        pr = RNG.randint(15,35)
        py = RNG.randint(50, 200)
        plen = RNG.randint(200, 600)
        # Yatay boru
        d.rectangle([(px, py-pr),(px+plen, py+pr)], fill=(8,16,8,180))
        d.line([(px,py),(px+plen,py)], fill=(20,80,20,80), width=2)
        # Boru flanşları
        for fx in range(px, px+plen, 100):
            d.ellipse([(fx-pr-5,py-pr-5),(fx+pr+5,py+pr+5)], fill=(10,20,10,160))
            d.ellipse([(fx-pr,py-pr),(fx+pr,py+pr)], fill=(8,16,8,180))

    # Uzak zayıf biyoışık nokta parıltıları
    for _ in range(30):
        gx = RNG.randint(0, W)
        gy = RNG.randint(100, H*2//3)
        r  = RNG.randint(3, 12)
        a  = RNG.randint(30, 90)
        d.ellipse([(gx-r,gy-r),(gx+r,gy+r)], fill=(30,180,30,a))

    # Kirli su birikintisi yansıması (altta)
    gradient_rect(d, 0, H-120, W, H, (6,16,6), (4,10,4), 20)
    for wx in range(0, W, 80):
        wy = H - RNG.randint(5,25)
        d.ellipse([(wx,wy-4),(wx+60,wy+3)], fill=(15,50,15,60))

    return im

def make_gutter_mid():
    """Orta: atık tünel duvarları, çürümüş binalar, eski reklam levhaları."""
    im = img((0,0,0,0))
    d  = draw(im)

    # Tünel duvar yapıları
    walls = [
        (0, H-500, 180, 500),
        (250, H-350, 140, 350),
        (480, H-440, 160, 440),
        (740, H-380, 120, 380),
        (980, H-480, 170, 480),
        (1240, H-330, 130, 330),
        (1480, H-460, 155, 460),
        (1740, H-390, 145, 390),
        (2000, H-500, 175, 500),
        (2280, H-360, 135, 360),
        (2530, H-440, 165, 440),
        (2810, H-410, 150, 410),
        (3060, H-470, 160, 470),
        (3330, H-350, 140, 350),
        (3580, H-430, 155, 430),
        (3800, H-380, 140, 380),
    ]
    for (x, y, w, h_w) in walls:
        # Beton/moloz duvar
        base_c = (10+RNG.randint(0,8), 20+RNG.randint(0,10), 10+RNG.randint(0,8))
        d.rectangle([(x,y),(x+w,H)], fill=(*base_c, 210))
        # Tuğla/beton blok çizgileri
        for by in range(y, H, 25):
            d.line([(x,by),(x+w,by)], fill=(5,10,5,60), width=1)
        for bx in range(x, x+w, 40):
            d.line([(bx,y),(bx,H)], fill=(5,10,5,40), width=1)
        # Yosun/biyoışık çatlaklar
        for _ in range(4):
            cy = y + RNG.randint(20, h_w-40)
            d.line([(x+RNG.randint(5,w-5), cy),(x+RNG.randint(5,w-5), cy+RNG.randint(20,60))],
                   fill=(20,120,20,100), width=2)

    # Çürümüş reklam panoları
    billboards = [
        (300, H-360, 180, 80),
        (900, H-420, 200, 90),
        (1600, H-380, 190, 85),
        (2400, H-400, 175, 80),
        (3100, H-360, 185, 80),
    ]
    for (bx, by, bw, bh) in billboards:
        d.rectangle([(bx,by),(bx+bw,by+bh)], fill=(8,16,8,200))
        d.rectangle([(bx+3,by+3),(bx+bw-3,by+bh-3)], fill=(12,25,10,160))
        # Bozuk piksel satırları
        for ry in range(by+6, by+bh-6, 10):
            for rx in range(bx+6, bx+bw-6, 12):
                if RNG.random() < 0.35:
                    c = RNG.choice([(50,200,50,180),(30,120,30,120),(200,180,0,100)])
                    d.rectangle([(rx,ry),(rx+8,ry+7)], fill=c)
        # Direk
        mx = bx + bw//2
        d.line([(mx,by+bh),(mx,H)], fill=(15,30,15,160), width=4)

    # Sarkan borular
    for px in range(0, W, 300):
        px += RNG.randint(0,80)
        pd = RNG.randint(6,14)
        py_top = RNG.randint(80, 200)
        py_bot = RNG.randint(250, 450)
        d.rectangle([(px-pd, py_top),(px+pd, py_bot)], fill=(12,28,12,180))
        # Boru kirliliği/paslı
        d.line([(px,py_top),(px,py_bot)], fill=(40,100,40,100), width=2)
        # Damlatma izi
        for dy in range(py_bot, py_bot+60, 15):
            da = max(20, 100 - (dy-py_bot)*2)
            d.line([(px,dy),(px,dy+10)], fill=(20,80,20,da), width=1)

    return im

def make_gutter_near():
    """Ön plan: çürük platform zemin, boru ağızları, atık konteynerleri."""
    im = img((0,0,0,0))
    d  = draw(im)

    # Zemin seviyesi
    gradient_rect(d, 0, H-65, W, H, (8,18,8), (4,10,4), 15)
    # Zemin kirlilik çizgileri
    for gx in range(0, W, 60):
        d.line([(gx, H-65),(gx, H)], fill=(10,25,10,50), width=1)
    # Zemin çatlakları
    for _ in range(40):
        cx = RNG.randint(0, W)
        cy = H - RNG.randint(10,50)
        d.line([(cx, cy),(cx+RNG.randint(-60,60), cy+RNG.randint(10,40))],
               fill=(5,12,5,100), width=1)

    # Boru ağızları
    for bx in range(80, W, 500):
        bx += RNG.randint(0,100)
        # Dikey boru
        d.rectangle([(bx-12, H-180),(bx+12, H-65)], fill=(10,25,10,200))
        d.line([(bx, H-180),(bx, H-65)], fill=(30,100,30,100), width=4)
        # Açık ağız
        d.ellipse([(bx-16, H-194),(bx+16, H-168)], fill=(6,18,6,220))
        d.ellipse([(bx-10, H-188),(bx+10, H-174)], fill=(0,0,0,200))
        # Duman efekti simülasyonu
        for si in range(4):
            ssize = 8 + si*10
            sa = 30 - si*6
            d.ellipse([(bx-ssize, H-200-si*20),(bx+ssize, H-195-si*20)],
                      fill=(15,40,15,sa))

    # Atık konteynerleri
    for cx2 in range(0, W, 620):
        cx2 += RNG.randint(0,150)
        ctype = RNG.randint(0,2)
        if ctype == 0:
            # Büyük konteyner
            d.rectangle([(cx2, H-140),(cx2+160, H-65)], fill=(6,16,6,230))
            d.rectangle([(cx2+5,H-135),(cx2+155,H-70)], fill=(10,22,10,200))
            for sy in range(H-130, H-70, 20):
                d.line([(cx2+5,sy),(cx2+155,sy)], fill=(15,35,15,80), width=1)
        elif ctype == 1:
            # Küçük variller
            for vi in range(3):
                vx = cx2 + vi*35
                d.ellipse([(vx,H-110),(vx+28,H-65)], fill=(8,20,8,210))
                d.line([(vx,H-90),(vx+28,H-90)], fill=(20,60,20,100), width=2)

    # Ön zemin neon çizgisi
    neon_line(d, 0, H-66, W, H-66, (50,200,50), width=2, glow_width=6)

    return im


# ══════════════════════════════════════════════════════════════════════════════
#  TEMA 3: DÖKÜMHANE (INDUSTRIAL)
#  Renk paleti: bg (20,10,5) | turuncu (255,100,0) | sarı (255,200,0)
# ══════════════════════════════════════════════════════════════════════════════

def make_industrial_far():
    """Uzak: endüstriyel gece gökyüzü, baca dumanı, uzak fırın ışıkları."""
    im = img()
    d  = draw(im)

    # Koyu kahve-turuncu gökyüzü
    gradient_rect(d, 0, 0, W, H, (12,5,2), (30,12,4), 80)

    # Ufuk alev parıltısı
    glow_circle(im, W//3,   H, 700, (220,60,0),  70, 0)
    glow_circle(im, W*2//3, H, 550, (180,40,0), 55, 0)

    # Uzak baca siluetleri
    chimneys = [(i*200+RNG.randint(0,80), RNG.randint(60,180)) for i in range(20)]
    for (cx, ch) in chimneys:
        cw = RNG.randint(18,35)
        d.rectangle([(cx, H-ch),(cx+cw, H)], fill=(15,6,2,200))
        # Baca ağzı
        d.rectangle([(cx-4, H-ch-10),(cx+cw+4, H-ch+6)], fill=(20,8,3,200))
        # Duman bulutları
        for si in range(5):
            soffset = si * 25
            sr = 20 + si*8
            sa = max(10, 50 - si*10)
            sx = cx + cw//2 + RNG.randint(-15,15)
            sy = H - ch - 30 - soffset
            d.ellipse([(sx-sr,sy-sr//2),(sx+sr,sy+sr//2)],
                      fill=(40,20,10,sa))

    # Uzak sanayi binaları
    for bx in range(0, W, 380):
        bx += RNG.randint(0,60)
        bh = RNG.randint(150, 350)
        bw = RNG.randint(120, 250)
        d.rectangle([(bx, H-bh),(bx+bw, H)], fill=(18,7,2,210))
        # Küçük turuncu pencereler
        for wy in range(H-bh+20, H-20, 40):
            for wx in range(bx+10, bx+bw-10, 30):
                if RNG.random() < 0.35:
                    a = RNG.randint(100,200)
                    d.rectangle([(wx,wy),(wx+15,wy+20)],
                                fill=(200+RNG.randint(0,55), 60+RNG.randint(0,40), 0, a))

    stars(d, 100, RNG, y_max=H//2, alpha_range=(30,80))
    return im

def make_industrial_mid():
    """Orta: fırınlar, konveyör destekleri, dev preslerin iskelet görüntüsü."""
    im = img((0,0,0,0))
    d  = draw(im)

    # Fırın/yüksek fırın yapıları
    furnaces = [
        (0,   H-520, 140),
        (280, H-380, 110),
        (560, H-600, 160),
        (890, H-420, 120),
        (1180,H-560, 150),
        (1520,H-400, 115),
        (1820,H-580, 155),
        (2180,H-440, 125),
        (2490,H-610, 170),
        (2870,H-390, 112),
        (3160,H-550, 148),
        (3500,H-420, 118),
        (3760,H-500, 140),
    ]

    for (x, y, w) in furnaces:
        h_f = H - y
        # Ana gövde — siyah metal
        d.rectangle([(x,y),(x+w,H)], fill=(18,7,2,220))
        # Yana yanal dikmeler
        d.rectangle([(x-8,y+30),(x+8,H)], fill=(25,10,3,200))
        d.rectangle([(x+w-8,y+30),(x+w+8,H)], fill=(25,10,3,200))
        # Fırın gözleri (erimiş metal parıltısı)
        eye_y = y + h_f//3
        eye_w = w * 2//3
        ex = x + (w-eye_w)//2
        # Alev parıltısı
        d.ellipse([(ex,eye_y-20),(ex+eye_w,eye_y+40)],
                  fill=(180,50,0,100))
        d.ellipse([(ex+5,eye_y-12),(ex+eye_w-5,eye_y+30)],
                  fill=(220,90,0,160))
        d.ellipse([(ex+10,eye_y-4),(ex+eye_w-10,eye_y+20)],
                  fill=(255,160,0,200))
        # Baca borusu
        pipe_x = x + w//2
        d.rectangle([(pipe_x-8,y-80),(pipe_x+8,y+10)], fill=(22,9,2,210))
        # Duman
        for si in range(4):
            ssize = 15 + si*12
            sa = max(8, 40 - si*9)
            sx = pipe_x + RNG.randint(-20,20)
            sy = y - 80 - si*30
            d.ellipse([(sx-ssize,sy-ssize//2),(sx+ssize,sy+ssize//2)],
                      fill=(35,15,5,sa))

    # Yatay konveyör yapı kirişleri
    for kx in range(0, W, 400):
        kh = RNG.randint(H-500, H-300)
        klen = RNG.randint(300, 500)
        # Ana kiriş
        d.rectangle([(kx, kh),(kx+klen, kh+16)], fill=(28,12,3,200))
        # Kirişe bağlı destekler
        for sx2 in range(kx, kx+klen, 60):
            d.line([(sx2+30, kh),(sx2+30, kh+80)], fill=(22,9,2,160), width=6)

    # Turuncu enerji/alev efektleri
    for fx in range(0, W, 500):
        fx += RNG.randint(0,100)
        fh = RNG.randint(40,100)
        fy = H - fh - RNG.randint(60, 200)
        # Alev şekli
        for fli in range(8):
            fat = int(80 * (1 - fli/8))
            fw = max(2, int(fh * (1 - fli/8) * 0.5))
            eh = max(2, fh - fli*8)
            ey0 = fy - fli*10
            d.ellipse([(fx-fw, ey0),(fx+fw, ey0+eh)],
                      fill=(255, int(100+fli*15), 0, fat))

    return im

def make_industrial_near():
    """Ön plan: metal kafes zemin, buhar boruları, döküm kalıp parçaları."""
    im = img((0,0,0,0))
    d  = draw(im)

    # Endüstriyel metal zemin
    gradient_rect(d, 0, H-65, W, H, (22,9,2), (12,5,1), 15)
    # Metalik ızgara çizgileri
    for gx in range(0, W, 50):
        d.line([(gx,H-65),(gx,H)], fill=(40,15,3,60), width=1)
    d.line([(0,H-65),(W,H-65)], fill=(180,70,0,150), width=3)

    # Buhar/alev boruları
    for bx in range(0, W, 300):
        bx += RNG.randint(0,100)
        bd = RNG.randint(10,20)
        bh = RNG.randint(100, 250)
        # Dikey boru
        d.rectangle([(bx-bd, H-bh-65),(bx+bd, H-65)], fill=(28,11,2,210))
        # Boru halkası
        d.rectangle([(bx-bd-4,H-bh//2-65-8),(bx+bd+4,H-bh//2-65+8)],
                    fill=(35,14,3,190))
        # Valf
        d.ellipse([(bx-8, H-bh-65-12),(bx+8, H-bh-65+4)],
                  fill=(40,16,3,220))
        # Buhar püskürtmesi
        if RNG.random() < 0.6:
            for si in range(5):
                ssize = 6 + si*8
                sa = max(5, 35 - si*7)
                sx = bx + RNG.randint(-ssize,ssize)
                sy = H - bh - 65 - 20 - si*18
                d.ellipse([(sx-ssize,sy-ssize//2),(sx+ssize,sy+ssize//2)],
                          fill=(200,100,30,sa))

    # Döküm parça yığınları
    for px in range(0, W, 500):
        px += RNG.randint(0, 150)
        for pi in range(RNG.randint(2,5)):
            pw = RNG.randint(30,70)
            ph = RNG.randint(15,35)
            py = H - 65 - ph - pi*20
            d.rectangle([(px+pi*15, py),(px+pi*15+pw, py+ph)],
                        fill=(25,10,2,220))

    # Turuncu ön zemin enerji hattı
    neon_line(d, 0, H-66, W, H-66, (255,100,0), width=2, glow_width=8)

    return im


# ══════════════════════════════════════════════════════════════════════════════
#  TEMA 4: GÜVENLİ BÖLGE (REST AREA)
#  Renk paleti: bg (10,10,25) | mavi (100,200,255) | beyaz (220,240,255)
# ══════════════════════════════════════════════════════════════════════════════

def make_safe_far():
    """Uzak: yeraltı metro istasyonu tonozları, uzak tünel ışıkları."""
    im = img()
    d  = draw(im)

    # Sakin koyu mavi gradyan
    gradient_rect(d, 0, 0, W, H, (5,5,18), (15,15,35), 80)

    # Büyük tonoz kemerleri
    arch_count = 8
    arch_w = W // arch_count
    for i in range(arch_count):
        ax = i * arch_w
        aw = arch_w
        ah = 250
        # Kemer dolgusunu çiz
        d.ellipse([(ax-20, H-ah-80),(ax+aw+20, H-50)],
                  fill=(10,10,28,120))
        d.arc([(ax, H-ah-80),(ax+aw, H-50)],
              180, 0, fill=(40,80,140,100), width=4)
        # İç kemer
        d.arc([(ax+15, H-ah-60),(ax+aw-15, H-60)],
              180, 0, fill=(60,120,200,60), width=2)
        # Kemer köşe taşları
        kcx = ax + aw//2
        kcy = H - ah - 80
        d.rectangle([(kcx-15,kcy-8),(kcx+15,kcy+8)],
                    fill=(20,30,60,160))

    # Tünel derinliği — uzaktan gelen ışık
    for i in range(5):
        r = 40 + i*60
        a = max(10, 60 - i*12)
        tunnel_x = W // 2
        tunnel_y = H // 2
        d.ellipse([(tunnel_x-r,tunnel_y-r),(tunnel_x+r,tunnel_y+r)],
                  fill=(60,120,200,a))

    # Duvardaki loş aydınlatma aplikleri
    for lx in range(0, W, 200):
        ly = RNG.randint(200, 400)
        d.ellipse([(lx-15,ly-20),(lx+15,ly+5)], fill=(40,60,100,120))
        glow_circle(im, lx, ly, 60, (80,160,255), 30, 0)

    stars(d, 50, RNG, y_max=H//3, alpha_range=(20,60))
    return im

def make_safe_mid():
    """Orta: metro platformu mimarisi, istasyon duvarları, bilgi panoları."""
    im = img((0,0,0,0))
    d  = draw(im)

    # Platform kolonları
    for cx in range(120, W, 360):
        ch = RNG.randint(300, 520)
        cw = 28
        # Kolon gövdesi
        d.rectangle([(cx-cw//2, H-ch),(cx+cw//2, H)], fill=(20,25,50,210))
        # Kolon başlığı
        d.rectangle([(cx-cw-8, H-ch),(cx+cw+8, H-ch+20)],
                    fill=(25,35,65,200))
        # Kolon kenar aydınlatması
        d.line([(cx-cw//2,H-ch),(cx-cw//2,H)], fill=(60,120,200,80), width=2)
        d.line([(cx+cw//2,H-ch),(cx+cw//2,H)], fill=(60,120,200,60), width=1)
        # Tepede parıltı
        d.ellipse([(cx-12,H-ch-14),(cx+12,H-ch+2)], fill=(80,160,255,150))

    # İstasyon duvar panelleri
    panel_h = 200
    for px in range(0, W, 280):
        # Ana panel
        d.rectangle([(px+10, H-panel_h-80),(px+260, H-80)],
                    fill=(12,15,35,180))
        d.rectangle([(px+14, H-panel_h-76),(px+256, H-84)],
                    fill=(16,20,45,160))
        # Panel yatay şerit
        d.rectangle([(px+10, H-panel_h-80),(px+260, H-panel_h-68)],
                    fill=(30,60,120,140))
        # Alt şerit
        d.rectangle([(px+10, H-92),(px+260, H-80)],
                    fill=(30,60,120,140))
        # İçerik simülasyonu (piksel satırlar)
        for ry in range(H-panel_h-60, H-95, 14):
            rw = RNG.randint(60, 200)
            d.rectangle([(px+20,ry),(px+20+rw,ry+8)],
                        fill=(50,100,200,RNG.randint(40,120)))

    # Tavan aydınlatma paneli
    gradient_rect(d, 0, 0, W, 30, (15,20,50,200), (8,12,35,100), 10)
    for lx2 in range(0, W, 120):
        d.rectangle([(lx2+10,0),(lx2+100,20)], fill=(60,100,200,100))
        glow_circle(im, lx2+55, 10, 80, (80,160,255), 20, 0)

    # Tabela paneli
    for sx in range(200, W, 800):
        d.rectangle([(sx, H-480),(sx+250, H-420)], fill=(8,12,30,200))
        d.rectangle([(sx+3,H-477),(sx+247,H-423)], fill=(15,25,60,180))
        # "GÜVENLİ BÖLGE" yazısını pixel bloklarla simüle et
        for bi in range(8):
            bx3 = sx + 10 + bi * 28
            d.rectangle([(bx3,H-468),(bx3+20,H-456)],
                        fill=(80,160,255,RNG.randint(80,160)))

    return im

def make_safe_near():
    """Ön plan: platform kenarı, oturma bankları, şarj istasyonları."""
    im = img((0,0,0,0))
    d  = draw(im)

    # Platform zemin yüzeyi
    gradient_rect(d, 0, H-65, W, H, (15,18,40), (8,10,25), 15)
    # Zemin plaka çizgileri
    for gx in range(0, W, 80):
        d.line([(gx,H-65),(gx,H)], fill=(30,50,100,50), width=1)
    d.line([(0,H-65),(W,H-65)], fill=(80,160,255,130), width=2)

    # Platform güvenlik çizgisi (sarı-siyah)
    for sx3 in range(0, W, 80):
        c = (200,200,0,200) if (sx3//40)%2==0 else (0,0,0,200)
        d.rectangle([(sx3,H-68),(sx3+40,H-62)], fill=c)

    # Oturma bankları
    for bx4 in range(150, W, 600):
        bx4 += RNG.randint(0,100)
        # Bant oturma
        d.rectangle([(bx4, H-120),(bx4+180, H-105)], fill=(20,28,58,220))
        d.rectangle([(bx4+5, H-105),(bx4+175, H-100)], fill=(30,40,80,200))
        # Bacaklar
        for leg in [bx4+15, bx4+155]:
            d.rectangle([(leg-4, H-100),(leg+4, H-65)], fill=(22,30,60,210))
        # Arkalık
        d.rectangle([(bx4, H-155),(bx4+180, H-120)], fill=(15,22,48,200))

    # Şarj istasyonları
    for cx3 in range(400, W, 800):
        cx3 += RNG.randint(0,100)
        d.rectangle([(cx3, H-220),(cx3+40, H-65)], fill=(18,22,50,220))
        # Ekran
        d.rectangle([(cx3+3,H-210),(cx3+37,H-155)], fill=(10,15,40,200))
        d.rectangle([(cx3+6,H-207),(cx3+34,H-158)], fill=(20,60,120,150))
        # Hologram parıltı
        for hy in range(H-200, H-160, 8):
            hw = RNG.randint(10,24)
            d.rectangle([(cx3+8,hy),(cx3+8+hw,hy+5)],
                        fill=(60,140,255,RNG.randint(40,100)))

    # Mavi ön zemin enerji hattı
    neon_line(d, 0, H-66, W, H-66, (100,200,255), width=2, glow_width=6)

    return im


# ══════════════════════════════════════════════════════════════════════════════
#  TEMA 5: FABRİKA İÇİ
#  Renk paleti: bg (15,8,5) | turuncu-kırmızı (200,80,0) | sarı (180,120,0)
# ══════════════════════════════════════════════════════════════════════════════

def make_factory_far():
    """Uzak: fabrika tavan yapısı, uzak makinalar, loş sanayi ışıkları."""
    im = img()
    d  = draw(im)

    # Sıcak karanlık sanayi havası
    gradient_rect(d, 0, 0, W, H, (8,4,2), (20,9,3), 80)

    # Fabrika tavan kirişleri
    for bx in range(0, W, 200):
        bh = RNG.randint(40, 80)
        # Kafes kiriş
        d.rectangle([(bx, 0),(bx+180, bh)], fill=(18,8,2,200))
        # Alt çaprazlar
        for ci in range(4):
            cx4 = bx + ci*45
            d.line([(cx4,0),(cx4+45,bh)], fill=(12,5,1,150), width=2)
            d.line([(cx4+45,0),(cx4,bh)], fill=(12,5,1,150), width=2)
        # Tavan ışık aplikleri
        lx3 = bx + 90
        d.rectangle([(lx3-20,bh-5),(lx3+20,bh+8)], fill=(30,12,3,200))
        glow_circle(im, lx3, bh+10, 100, (200,90,10), 40, 0)

    # Uzak makina siluetleri
    for mx in range(0, W, 500):
        mx += RNG.randint(0,150)
        mh = RNG.randint(200, 400)
        mw = RNG.randint(150, 280)
        d.rectangle([(mx, H-mh),(mx+mw, H)], fill=(14,6,1,190))
        # Makina detayları
        # Piston kolları
        for pi in range(3):
            px4 = mx + 20 + pi*(mw//3)
            d.rectangle([(px4-8, H-mh+50),(px4+8, H-mh+150)],
                        fill=(22,10,2,180))
        # Turuncu ışık
        d.rectangle([(mx+10, H-mh+10),(mx+mw-10, H-mh+30)],
                    fill=(180,70,0,120))

    return im

def make_factory_mid():
    """Orta: konveyör bantlar, robotik kollar, kontrol panelleri."""
    im = img((0,0,0,0))
    d  = draw(im)

    # Konveyör bant sistemleri
    conveyor_levels = [H-180, H-320, H-460]
    for cy2 in conveyor_levels:
        # Bant gövdesi
        d.rectangle([(0, cy2),(W, cy2+28)], fill=(22,10,2,200))
        d.rectangle([(0, cy2+28),(W, cy2+40)], fill=(30,14,3,190))
        # Bant desen
        for bx5 in range(0, W, 60):
            d.rectangle([(bx5, cy2),(bx5+50, cy2+28)],
                        fill=(20,9,2,180))
            d.line([(bx5+50,cy2),(bx5+50,cy2+28)],
                   fill=(40,18,4,120), width=2)
        # Bant destekleri
        for sx4 in range(80, W, 240):
            d.rectangle([(sx4-10, cy2+40),(sx4+10, H)],
                        fill=(25,11,2,180))
        # Konveyör üzerindeki ürünler
        for ox in range(30, W, 100):
            if RNG.random() < 0.4:
                ow = RNG.randint(20,45)
                oh = RNG.randint(15,28)
                d.rectangle([(ox, cy2-oh),(ox+ow, cy2)],
                            fill=(30,15,5,200))

    # Robotik kol yapıları
    for rx in range(100, W, 600):
        rx += RNG.randint(0,80)
        # Tavan montaj rayı
        d.rectangle([(rx-10, 80),(rx+10, 200)], fill=(25,11,2,200))
        # Ana kol
        arm_end_y = H - 200 - RNG.randint(0,100)
        d.line([(rx,200),(rx+80,arm_end_y)], fill=(30,14,3,200), width=12)
        d.line([(rx+80,arm_end_y),(rx+140,arm_end_y+60)],
               fill=(30,14,3,200), width=10)
        # Eklem noktaları
        d.ellipse([(rx-12,195),(rx+12,215)], fill=(40,18,4,220))
        d.ellipse([(rx+68,arm_end_y-10),(rx+92,arm_end_y+10)],
                  fill=(40,18,4,220))
        # Tutucu/kavrayıcı
        gx2 = rx+140; gy2 = arm_end_y+60
        d.line([(gx2,gy2),(gx2-20,gy2+40)], fill=(28,12,2,200), width=8)
        d.line([(gx2,gy2),(gx2+20,gy2+40)], fill=(28,12,2,200), width=8)
        # Alarm ışıkları
        d.ellipse([(rx-6,70),(rx+6,82)], fill=(220,80,0,200))

    # Kontrol panelleri (duvara monte)
    for px5 in range(300, W, 900):
        d.rectangle([(px5, H-450),(px5+120, H-300)], fill=(15,7,1,220))
        # Ekran
        d.rectangle([(px5+8,H-440),(px5+112,H-370)], fill=(8,4,0,200))
        d.rectangle([(px5+12,H-436),(px5+108,H-374)], fill=(20,10,2,180))
        # Turuncu göstergeler
        for gi in range(4):
            gx3 = px5 + 15 + gi*22
            gy3 = H - 425
            d.ellipse([(gx3-5,gy3-5),(gx3+5,gy3+5)],
                      fill=(200+RNG.randint(0,55),RNG.randint(40,100),0,200))
        # Kol grafikleri
        for gy4 in range(H-415, H-375, 10):
            gw2 = RNG.randint(20,80)
            d.rectangle([(px5+15,gy4),(px5+15+gw2,gy4+7)],
                        fill=(180,70,0,RNG.randint(60,150)))

    return im

def make_factory_near():
    """Ön plan: endüstriyel döşeme ızgarası, buhar çıkışları, uyarı şeritleri."""
    im = img((0,0,0,0))
    d  = draw(im)

    # Metal ızgara zemin
    gradient_rect(d, 0, H-65, W, H, (20,9,2), (10,5,1), 15)
    for gx4 in range(0, W, 40):
        d.line([(gx4,H-65),(gx4,H)], fill=(35,15,3,60), width=1)
    for gy5 in range(H-65, H, 20):
        d.line([(0,gy5),(W,gy5)], fill=(35,15,3,40), width=1)

    # Uyarı şeridi
    for sx5 in range(0, W, 80):
        c = (200,140,0,200) if (sx5//40)%2==0 else (0,0,0,200)
        d.rectangle([(sx5,H-68),(sx5+40,H-62)], fill=c)
    d.line([(0,H-65),(W,H-65)], fill=(180,70,0,160), width=3)

    # Buhar/egzoz boruları
    for bx6 in range(0, W, 350):
        bx6 += RNG.randint(0,100)
        bd2 = RNG.randint(10,18)
        bh2 = RNG.randint(80,180)
        d.rectangle([(bx6-bd2,H-bh2-65),(bx6+bd2,H-65)], fill=(25,11,2,210))
        d.ellipse([(bx6-bd2-4,H-bh2-65-8),(bx6+bd2+4,H-bh2-65+6)],
                  fill=(30,14,3,200))
        # Buhar animasyonu simülasyonu
        for si2 in range(4):
            ss2 = 8 + si2*10
            sa2 = max(5, 35-si2*8)
            sx6 = bx6 + RNG.randint(-ss2,ss2)
            sy2 = H - bh2 - 65 - 25 - si2*15
            d.ellipse([(sx6-ss2,sy2-ss2//2),(sx6+ss2,sy2+ss2//2)],
                      fill=(100,50,10,sa2))

    # Endüstriyel bariyerler
    for px6 in range(0, W, 550):
        px6 += RNG.randint(0,100)
        # Sarı-siyah güvenlik bariyeri
        for bi2 in range(6):
            bc = (200,140,0,220) if bi2%2==0 else (15,6,1,220)
            d.rectangle([(px6+bi2*16, H-100),(px6+bi2*16+14,H-65)], fill=bc)
        d.line([(px6,H-100),(px6+96,H-100)], fill=(30,14,3,200), width=4)

    # Turuncu zemin enerji hattı
    neon_line(d, 0, H-66, W, H-66, (200,80,0), width=2, glow_width=8)

    return im


# ══════════════════════════════════════════════════════════════════════════════
#  TEMA 6: MALİKANE
#  Renk paleti: bg (8,3,3) | altın (160,90,10) | koyu kırmızı (55,15,15)
# ══════════════════════════════════════════════════════════════════════════════

def make_manor_far():
    """Uzak: manor koridoru perspektifi, uzak mum ışıkları, taş duvarlar."""
    im = img()
    d  = draw(im)

    # Çok koyu gradyan — neredeyse tamamen siyah
    gradient_rect(d, 0, 0, W, H, (4,1,1), (12,4,4), 80)

    # Taş duvar dokusu
    for wy2 in range(0, H, 50):
        for wx2 in range(0, W, 80):
            offset = (wy2//50) * 40
            wx3 = (wx2 + offset) % W
            a = RNG.randint(8,20)
            d.rectangle([(wx3,wy2),(wx3+78,wy2+48)], fill=(10+a//3,3+a//8,3+a//8,a))
            d.line([(wx3,wy2),(wx3+78,wy2)], fill=(3,1,1,30), width=1)

    # Uzak koridor perspektifi
    cx5 = W//2
    for i in range(8):
        r = 50 + i*70
        a = max(5, 35-i*4)
        d.rectangle([(cx5-r,H//2-r//2),(cx5+r,H//2+r//2)],
                    outline=(25,10,10,a), width=1)

    # Uzak mum ışıkları
    for _ in range(20):
        lx4 = RNG.randint(0, W)
        ly2 = RNG.randint(80, H-150)
        glow_circle(im, lx4, ly2, 80, (200,120,20), 40, 0)
        d.ellipse([(lx4-3,ly2-8),(lx4+3,ly2+3)], fill=(255,200,80,220))

    # Uzak aile portreleri/tablo çerçeveleri
    for px7 in range(100, W, 400):
        px7 += RNG.randint(0,80)
        pw2 = 80; ph2 = 100
        py2 = RNG.randint(100, 300)
        # Dış çerçeve — altın
        d.rectangle([(px7-3,py2-3),(px7+pw2+3,py2+ph2+3)], fill=(80,45,5,180))
        # İç tuval
        d.rectangle([(px7,py2),(px7+pw2,py2+ph2)], fill=(6,2,2,200))
        # Siluet figür
        d.ellipse([(px7+30,py2+10),(px7+50,py2+30)], fill=(15,5,5,180))
        d.rectangle([(px7+28,py2+30),(px7+52,py2+80)], fill=(12,4,4,180))

    return im

def make_manor_mid():
    """Orta: gotik kemerler, kitaplıklar, koyu kırmızı perdeler."""
    im = img((0,0,0,0))
    d  = draw(im)

    # Zemin seviyesi koyu kırmızı halı
    gradient_rect(d, 0, H-120, W, H, (35,8,8), (20,5,5), 20)
    # Halı desen
    for hx in range(0, W, 40):
        d.line([(hx,H-120),(hx,H)], fill=(50,12,12,50), width=1)
    d.line([(0,H-120),(W,H-120)], fill=(60,20,5,100), width=2)

    # Taş kolonlar / Gotik pilonlar
    for cx6 in range(80, W, 380):
        ch2 = RNG.randint(400, 650)
        cw2 = 40
        # Kolon gövdesi
        d.rectangle([(cx6-cw2//2,H-ch2),(cx6+cw2//2,H)], fill=(12,4,4,220))
        # Kolon yivleri
        for yi in range(H-ch2, H, 45):
            d.line([(cx6-cw2//2+5,yi),(cx6-cw2//2+5,yi+35)],
                   fill=(20,7,7,100), width=2)
            d.line([(cx6+cw2//2-5,yi),(cx6+cw2//2-5,yi+35)],
                   fill=(20,7,7,100), width=2)
        # Kolon başlığı ve tabanı (kapitel/baz)
        for ky in [H-ch2, H]:
            d.rectangle([(cx6-cw2//2-10,ky-10),(cx6+cw2//2+10,ky+10)],
                        fill=(18,6,6,210))
        # Gotik kemer
        next_col = cx6 + 380
        if next_col < W:
            d.arc([(cx6, H-ch2-100),(next_col, H-ch2+100)],
                  180, 0, fill=(18,6,6,120), width=3)
            # Kemer içi mum ışığı
            lx5 = (cx6+next_col)//2
            glow_circle(im, lx5, H-ch2, 120, (180,100,10), 50, 0)
            d.ellipse([(lx5-4,H-ch2-8),(lx5+4,H-ch2+4)],
                      fill=(255,180,60,240))

    # Kitaplıklar
    for bx7 in range(0, W, 560):
        bx7 += RNG.randint(0,80)
        bh3 = RNG.randint(280, 450)
        bw3 = 200
        # Raf gövdesi
        d.rectangle([(bx7,H-bh3),(bx7+bw3,H)], fill=(10,3,3,210))
        # Raflar
        for ry2 in range(H-bh3+20, H-20, 55):
            d.rectangle([(bx7+5,ry2-4),(bx7+bw3-5,ry2)],
                        fill=(20,8,4,200))
            # Kitap sırtları
            bx_pos = bx7+8
            while bx_pos < bx7+bw3-12:
                bw4 = RNG.randint(8,20)
                bc2 = (RNG.randint(40,100), RNG.randint(5,30),
                       RNG.randint(5,20), 200)
                d.rectangle([(bx_pos,ry2-50),(bx_pos+bw4,ry2-4)], fill=bc2)
                # Kitap altın şerit
                d.line([(bx_pos,ry2-20),(bx_pos+bw4,ry2-20)],
                       fill=(120,70,5,100), width=1)
                bx_pos += bw4+1

    # Koyu kırmızı kadife perdeler
    for px8 in range(0, W, 450):
        px8 += RNG.randint(0,80)
        ph3 = RNG.randint(350, 500)
        pw3 = 80
        # Perde dalgaları
        for di in range(5):
            dx2 = di * 16
            # Her dalga dikey çizgi
            pts = []
            for y in range(H-ph3, H, 15):
                xoff = int(math.sin((y-H+ph3)*0.08 + di*0.6)*10)
                pts.append((px8+dx2+xoff, y))
            if len(pts) > 1:
                d.line(pts, fill=(40+di*4,6,6,160), width=14)
        # Perde üst korniş
        d.rectangle([(px8-5,H-ph3-10),(px8+pw3+5,H-ph3+10)],
                    fill=(80,40,5,200))

    return im

def make_manor_near():
    """Ön plan: mermer taban, altın kaideler, gotik lambader siluetleri."""
    im = img((0,0,0,0))
    d  = draw(im)

    # Mermer/taş zemin
    gradient_rect(d, 0, H-65, W, H, (20,6,6), (10,3,3), 15)
    # Mermer desen çizgileri
    for mx2 in range(0, W, 120):
        d.line([(mx2,H-65),(mx2,H)], fill=(30,8,8,50), width=1)
    for my in range(H-65,H,30):
        d.line([(0,my),(W,my)], fill=(25,7,7,40), width=1)
    # Mermer ince damarları
    for _ in range(20):
        mx3 = RNG.randint(0,W)
        my2 = RNG.randint(H-65,H)
        mlen = RNG.randint(60,200)
        d.line([(mx3,my2),(mx3+mlen,my2+RNG.randint(-5,5))],
               fill=(50,15,15,60), width=1)

    # Zemin kenar altın şeridi
    d.rectangle([(0,H-66),(W,H-62)], fill=(100,60,5,180))
    d.line([(0,H-62),(W,H-62)], fill=(160,90,10,200), width=2)
    d.line([(0,H-68),(W,H-68)], fill=(80,45,3,120), width=1)

    # Gotik lambader/şamdan kaidesi
    for lx6 in range(0, W, 500):
        lx6 += RNG.randint(0,150)
        # Kaide
        d.rectangle([(lx6-15,H-65),(lx6+15,H-65)], fill=(15,5,5,0))
        d.rectangle([(lx6-12,H-100),(lx6+12,H-65)], fill=(12,4,4,220))
        # Orta gövde
        d.rectangle([(lx6-6,H-280),(lx6+6,H-100)], fill=(10,3,3,200))
        # Dal kolları
        for arm_dir in [-1, 1]:
            ax2 = lx6 + arm_dir*60
            # Eğri kol
            for step in range(8):
                t = step/7
                ax3 = int(lx6 + arm_dir*t*60)
                ay2 = int(H - 280 + t*t*60)
                d.ellipse([(ax3-4,ay2-4),(ax3+4,ay2+4)], fill=(10,3,3,200))
            # Mum
            d.rectangle([(ax2-4,H-240),(ax2+4,H-215)],
                        fill=(200,180,140,200))
            # Alev
            d.ellipse([(ax2-5,H-255),(ax2+5,H-238)],
                      fill=(255,180,60,240))
            glow_circle(im, ax2, H-245, 40, (200,120,20), 60, 0)

    # Koyu köşe gölge efektleri
    shadow = Image.new("RGBA", (W, H), (0,0,0,0))
    sd = ImageDraw.Draw(shadow, "RGBA")
    for i in range(60):
        a = int(120 * (1 - i/60))
        sd.rectangle([(i,0),(i+1,H)], fill=(0,0,0,a))
        sd.rectangle([(W-i-1,0),(W-i,H)], fill=(0,0,0,a))
    im.alpha_composite(shadow)

    # Altın zemin çizgisi parıltısı
    neon_line(d, 0, H-66, W, H-66, (160,90,10), width=2, glow_width=6)

    return im


# ══════════════════════════════════════════════════════════════════════════════
#  ANA ÜRETIM DÖNGÜSÜ
# ══════════════════════════════════════════════════════════════════════════════

THEMES = [
    # (prefix, far_fn, mid_fn, near_fn)
    ("neon",       make_neon_far,       make_neon_mid,       make_neon_near),
    ("nexus",      make_nexus_far,      make_nexus_mid,      make_nexus_near),
    ("gutter",     make_gutter_far,     make_gutter_mid,     make_gutter_near),
    ("industrial", make_industrial_far, make_industrial_mid, make_industrial_near),
    ("safe",       make_safe_far,       make_safe_mid,       make_safe_near),
    ("factory",    make_factory_far,    make_factory_mid,    make_factory_near),
    ("manor",      make_manor_far,      make_manor_mid,      make_manor_near),
]

def main():
    print(f"\n{'='*60}")
    print("  Fragmentia Parallax Arkaplan Üretici")
    print(f"  Çözünürlük: {W}×{H}px | Çıktı: {OUT}/")
    print(f"{'='*60}\n")

    for (prefix, far_fn, mid_fn, near_fn) in THEMES:
        print(f"▶ Tema: {prefix.upper()}")

        print("  Katman 1/3 — FAR  (hız: 0.15) ...", end=" ", flush=True)
        save(far_fn(), f"{prefix}_far.png")

        print("  Katman 2/3 — MID  (hız: 0.40) ...", end=" ", flush=True)
        save(mid_fn(), f"{prefix}_mid.png")

        print("  Katman 3/3 — NEAR (hız: 0.75) ...", end=" ", flush=True)
        save(near_fn(), f"{prefix}_near.png")

        print()

    print(f"\n{'='*60}")
    print(f"  Tamamlandı! {len(THEMES)*3} PNG dosyası üretildi.")
    print(f"  Konum: {OUT}/")
    print(f"{'='*60}\n")
    print("  entities.py ParallaxBackground kullanımı:")
    print("  ─────────────────────────────────────────")
    print('  bg_far  = ParallaxBackground("assets/backgrounds/neon_far.png",  0.15)')
    print('  bg_mid  = ParallaxBackground("assets/backgrounds/neon_mid.png",  0.40)')
    print('  bg_near = ParallaxBackground("assets/backgrounds/neon_near.png", 0.75)')
    print()

if __name__ == "__main__":
    main()
