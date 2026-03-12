# level_16_manor.py
# BÖLÜM 16: EGEMENLERİN MALİKANESİ
# Fragmentia Engine — Gizlilik Bölümü Platform Haritası + Victorian Görsel Sistemi
# =============================================================================
#
# AGENT.MD UYUMLULUĞU:
#   RULE 1 (Zero Alloc)  : Surface/Font build_/draw_ dışında init edilir.
#   RULE 2 (frame_mul)   : Fizik sabiti yok; hepsi settings.py'de.
#   RULE 3 (Model-View)  : Platform verisi (build_) render'dan (draw_) ayrı.
#   RULE 4 (SSOT)        : Tüm koordinat/renk sabitleri dosya tepesinde.
#
# ODA ORANLARI:
#   Oyuncu yüksekliği  : 42 px
#   Kat aralığı        : 400 px  → oran %10.5  (sağlıklı oran)
#   Önceki oran        : ~%22    (çok büyük görünüyordu)
#
# DİKEY KAMERA:
#   Harita yüksekliği 2100 px → ManorCamera dikey kaydırma yapar.
#   Oyuncu zemin katta başlar (Y_G=2000), en üste (Y_GS=220) tırmanır.
# =============================================================================

from __future__ import annotations
import pygame
import math
import random as _random

# ─── SSOT: Kat Y Koordinatları  (platform.rect.top değerleri) ────────────────
#
#   Her kat arası 400 px — oyuncu (42 px) odanın ~%10'unu kaplar.
#   Harita: 4000 x 2100 px, ManorCamera dikey kaydırır.
#
Y_G   = 2000   # Zemin kat
Y_F1  = 1600   # 1. Kat   (400 px aralik)
Y_F2  = 1200   # 2. Kat   (400 px aralik)
Y_RF  =  800   # Cati kati(400 px aralik)
Y_GS  =  220   # Gizli kat — KASA ODASI (580 px aralik)

# Platform geometri sabitleri
_T  = 22   # Platform kalinligi
_W  = 20   # Duvar kalinligi

# ─── Merdiven sabitleri ───────────────────────────────────────────────────────
#   Her basamak: 72 px genis x 36 px yuksek.
#   400 px kat farki → ~11 basamak x 72 px = 792 px yatay alan.
#   Sahanlık (landing): 120 px duz bolum, alt ve ustte.
_STEP_W  = 72    # Basamak genisligi
_STEP_H  = 36    # Basamak yuksekligi (riseri)
_LANDING = 120   # Sahanlık uzunlugu

# ─── Harita Sabitleri ─────────────────────────────────────────────────────────
MANOR_16_MAP_WIDTH  : int   = 4000
MANOR_16_MAP_HEIGHT : int   = 2100
MANOR_16_SPAWN_X    : float = 160.0
MANOR_16_SPAWN_Y    : float = float(Y_G - 44)

MANOR_16_SAFE_X : int   = 3650
MANOR_16_SAFE_Y : float = float(Y_GS - 44)
MANOR_16_SAFE_R : int   = 90

LEVEL_16_CONFIG: dict = {
    "name"               : "EGEMENLERIN MALIKANESI",
    "goal_score"         : 0,
    "speed_mult"         : 0.0,
    "theme_index"        : 6,
    "type"               : "manor_stealth",
    "music_file"         : "dark_ambient.mp3",
    "no_enemies"         : True,
    "map_width"          : MANOR_16_MAP_WIDTH,
    "map_height"         : MANOR_16_MAP_HEIGHT,
    "secret_safe_x"      : MANOR_16_SAFE_X,
    "secret_safe_y"      : MANOR_16_SAFE_Y,
    "secret_safe_radius" : MANOR_16_SAFE_R,
    "desc"               : "Egemenlerin malikanesine siz. Gizli kasayi bul. Algilanma.",
}

# ─── Victorian Renk Paleti ────────────────────────────────────────────────────
_S2      = (48,  40, 32)
_S3      = (68,  56, 44)
_W2      = (65,  43, 18)
_W3      = (92,  62, 26)
_W4      = (128, 90, 38)
_BOR     = (80,  10, 10)
_BRL     = (120, 20, 20)
_ZUM     = (12,  55, 35)
_ZUL     = (22,  90, 55)
_LAC     = (12,  18, 60)
_LAL     = (22,  35,100)
_MRB     = (160,155,145)
_MRG     = (110,105, 98)
_IRN     = (45,  45, 50)
_AMB     = (140,  80, 10)
_GLD     = (200, 155, 20)
_KARO_W  = (190,185,175)
_KARO_B  = (22,  18, 14)
_VAULT   = (30,  25, 10)
_VAULT_G = (90,  70,  5)

# ─── RULE 1B: Surface/Font onbellekleri ───────────────────────────────────────
_CACHE_READY      : bool                    = False
_glow_window_surf : pygame.Surface | None   = None
_glow_fire_surf   : pygame.Surface | None   = None
_glow_vault_surf  : pygame.Surface | None   = None
_label_font       : pygame.font.Font | None = None
_star_rng_z       = _random.Random(42)
_star_rng_rf      = _random.Random(77)


def _ensure_caches() -> None:
    global _CACHE_READY, _glow_window_surf, _glow_fire_surf, _glow_vault_surf, _label_font
    if _CACHE_READY:
        return
    _glow_window_surf = pygame.Surface((120, 140), pygame.SRCALPHA)
    _glow_fire_surf   = pygame.Surface((160,  80), pygame.SRCALPHA)
    _glow_vault_surf  = pygame.Surface((300, 300), pygame.SRCALPHA)
    try:
        _label_font = pygame.font.SysFont("georgia", 14, italic=True)
    except Exception:
        _label_font = pygame.font.SysFont(None, 14)
    _CACHE_READY = True


# ─── Yardimci Render Fonksiyonlari ───────────────────────────────────────────

def _lc(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _grad_rect(surf, rect, top_col, bot_col):
    if rect.h <= 0 or rect.w <= 0:
        return
    x, w = rect.x, rect.w
    for row in range(rect.h):
        t = row / max(rect.h - 1, 1)
        pygame.draw.line(surf, _lc(top_col, bot_col, t),
                         (x, rect.y + row), (x + w, rect.y + row))


def _karo_floor(surf, rect, ox, oy, size=40):
    clip = surf.get_clip()
    surf.set_clip(rect)
    x0 = rect.x - ((rect.x - ox) % (size * 2))
    y0 = rect.y - ((rect.y - oy) % (size * 2))
    r  = pygame.Rect(0, 0, size, size)
    xi = x0
    while xi < rect.right:
        yi, row = y0, 0
        while yi < rect.bottom:
            col = _KARO_W if (int((xi - ox) // size) + row) % 2 == 0 else _KARO_B
            r.x, r.y = xi, yi
            pygame.draw.rect(surf, col, r)
            yi += size
            row += 1
        xi += size
    surf.set_clip(clip)


def _wood_planks(surf, rect, col_dark, col_light, plank_h=18):
    clip = surf.get_clip()
    surf.set_clip(rect)
    y, toggle = rect.y, False
    while y < rect.bottom:
        c = col_light if toggle else col_dark
        h = min(plank_h, rect.bottom - y)
        pygame.draw.rect(surf, c, (rect.x, y, rect.w, h))
        toggle = not toggle
        y += plank_h
    surf.set_clip(clip)


def _stone_wall(surf, rect, col_dark, col_light, block_h=32, block_w=80):
    clip = surf.get_clip()
    surf.set_clip(rect)
    row, y = 0, rect.y
    while y < rect.bottom:
        offset = (block_w // 2) if row % 2 else 0
        x = rect.x - offset
        while x < rect.right:
            bw = min(block_w - 2, rect.right - x - 1)
            bh = min(block_h - 2, rect.bottom - y - 1)
            if bw > 0 and bh > 0:
                c = _lc(col_dark, col_light,
                        0.3 + 0.4 * ((row + int(x // block_w)) % 3 / 2))
                pygame.draw.rect(surf, c, (max(rect.x, x + 1), y + 1, bw, bh))
            x += block_w   # ic dongude olmali — disarida sonsuz dongu!
        y += block_h
        row += 1
    surf.set_clip(clip)


def _window(surf, x, y, w, h, ox, oy, tick):
    _ensure_caches()
    sx, sy = x + ox, y + oy
    if sx + w < 0 or sx > surf.get_width():
        return
    glow_t = max(0.0, min(1.0, 0.55 + 0.15 * math.sin(tick * 0.8)))
    pygame.draw.rect(surf, _W3, (sx, sy, w, h), 3)
    inner = pygame.Rect(sx + 4, sy + 4, w - 8, h - 8)
    if inner.w > 0 and inner.h > 0:
        _grad_rect(surf, inner,
                   _lc((60, 50, 20), (100, 80, 30), glow_t),
                   _lc((20, 15,  5), ( 40, 30, 10), glow_t))
    pygame.draw.line(surf, _W4, (sx, sy + h // 2), (sx + w, sy + h // 2), 2)
    pygame.draw.line(surf, _W4, (sx + w // 2, sy), (sx + w // 2, sy + h), 2)
    glow_col = _lc((80, 60, 10), (120, 90, 20), glow_t)
    _glow_window_surf.fill((0, 0, 0, 0))
    pygame.draw.rect(_glow_window_surf, (*glow_col, 18),
                     (0, 0, w + 20, h + 20), border_radius=4)
    surf.blit(_glow_window_surf, (sx - 10, sy - 10))


def _fireplace(surf, x, y, ox, oy, tick):
    _ensure_caches()
    sx, sy = x + ox, y + oy
    if sx + 80 < 0 or sx > surf.get_width():
        return
    f = max(0.0, min(1.0, 0.5 + 0.5 * math.sin(tick * 4.2 + x * 0.01)))
    pygame.draw.rect(surf, _S2, (sx, sy, 80, 60))
    pygame.draw.arc(surf, _S3, (sx - 5, sy - 20, 90, 50), 0, math.pi, 4)
    inner = pygame.Rect(sx + 8, sy + 8, 64, 48)
    if inner.w > 0 and inner.h > 0:
        _grad_rect(surf, inner,
                   _lc((200, 100, 20), (255, 160, 30), f), (60, 10, 5))
    _glow_fire_surf.fill((0, 0, 0, 0))
    pygame.draw.ellipse(_glow_fire_surf, (180, 80, 10, int(35 * f)), (0, 0, 160, 80))
    surf.blit(_glow_fire_surf, (sx - 40, sy + 55))


def _vault_glow(surf, ox, oy, tick):
    _ensure_caches()
    sx = MANOR_16_SAFE_X + ox
    sy = int(MANOR_16_SAFE_Y) + oy
    if sx + 200 < 0 or sx > surf.get_width():
        return
    pulse = max(0.0, min(1.0, 0.6 + 0.4 * math.sin(tick * 2.0)))
    _glow_vault_surf.fill((0, 0, 0, 0))
    pygame.draw.circle(_glow_vault_surf, (180, 140, 10, int(60 * pulse)), (150, 150), 120)
    pygame.draw.circle(_glow_vault_surf, (220, 180, 30, int(30 * pulse)), (150, 150),  90)
    surf.blit(_glow_vault_surf, (sx - 150, sy - 100))
    pygame.draw.circle(surf, _GLD, (sx, sy + 20), 36, 3)
    pygame.draw.circle(surf, _AMB, (sx, sy + 20), 24, 2)
    for ang in range(0, 360, 45):
        rad = math.radians(ang + tick * 20)
        pygame.draw.circle(surf, _GLD,
                           (int(sx + math.cos(rad) * 28),
                            int(sy + 20 + math.sin(rad) * 28)), 3)


# =============================================================================
#  ANA GORSEL FONKSIYON
# =============================================================================
def draw_level_16_bg(surf: pygame.Surface, ox: int, oy: int, tick: float) -> None:
    """
    Bolum 16 Victorian atmosferini cizer.
    Harita 4000 x 2100 px. ManorCamera dikey kaydirir.
    ox/oy kamera ofseti (negatif = sola/yukari kaydir).
    """
    sw = surf.get_width()
    surf.fill((8, 3, 3))

    # Her kat icin arka plan yuksekligi
    _RH = 380   # oda ic yuksekligi (gorsel)
    _FH = 60    # zemin seridi (karo/tahta)

    # ── ZEMIN KAT (Y_G = 2000) ────────────────────────────────────────────────

    _r = pygame.Rect(20 + ox, Y_G - _RH + oy, 900, _RH)
    if _r.right > 0 and _r.x < sw:
        _stone_wall(surf, _r, _S2, _S3)
        _karo_floor(surf, pygame.Rect(_r.x, Y_G - _FH + oy, _r.w, _FH), ox, oy, 44)
        _window(surf,  80, Y_G - 340, 90, 130, ox, oy, tick)
        _window(surf, 380, Y_G - 340, 90, 130, ox, oy, tick)
        _window(surf, 620, Y_G - 340, 90, 130, ox, oy, tick)
        _fireplace(surf, 200, Y_G - 90, ox, oy, tick)

    _r = pygame.Rect(920 + ox, Y_G - _RH + oy, 980, _RH)
    if _r.right > 0 and _r.x < sw:
        _grad_rect(surf, _r, _BOR, _lc(_BOR, (15, 5, 5), 0.5))
        for yy in range(_r.y, _r.bottom, 28):
            pygame.draw.line(surf, _BRL, (_r.x, yy), (_r.right, yy), 1)
        _wood_planks(surf, pygame.Rect(_r.x, Y_G - _FH + oy, _r.w, _FH), _W2, _W3, 22)
        _window(surf, 1020, Y_G - 340, 90, 130, ox, oy, tick)
        _window(surf, 1400, Y_G - 340, 90, 130, ox, oy, tick)
        _window(surf, 1700, Y_G - 340, 90, 130, ox, oy, tick)
        _fireplace(surf, 1300, Y_G - 90, ox, oy, tick)

    _r = pygame.Rect(1900 + ox, Y_G - _RH + oy, 1000, _RH)
    if _r.right > 0 and _r.x < sw:
        _wood_planks(surf, _r, _W2, _W3, 24)
        _karo_floor(surf, pygame.Rect(_r.x, Y_G - _FH + oy, _r.w, _FH), ox, oy, 38)
        _window(surf, 2050, Y_G - 340, 90, 130, ox, oy, tick)
        _window(surf, 2500, Y_G - 340, 90, 130, ox, oy, tick)
        _window(surf, 2780, Y_G - 340, 90, 130, ox, oy, tick)

    _r = pygame.Rect(2900 + ox, Y_G - _RH + oy, 1082, _RH)
    if _r.right > 0 and _r.x < sw:
        _stone_wall(surf, _r, (30, 30, 35), (50, 50, 58))
        _window(surf, 3050, Y_G - 340, 80, 110, ox, oy, tick)
        _window(surf, 3500, Y_G - 340, 80, 110, ox, oy, tick)
        _window(surf, 3800, Y_G - 340, 80, 110, ox, oy, tick)

    # ── 1. KAT (Y_F1 = 1600) ──────────────────────────────────────────────────

    _r = pygame.Rect(20 + ox, Y_F1 - _RH + oy, 1080, _RH)
    if _r.right > 0 and _r.x < sw:
        _grad_rect(surf, _r, (14, 8, 3), _W2)
        _wood_planks(surf, pygame.Rect(_r.x, _r.y, _r.w, _r.h // 2), _W2, _W3, 22)
        for xb in range(_r.x + 90, _r.right, 100):
            pygame.draw.line(surf, _W4, (xb, _r.y + 10), (xb, _r.bottom - 10), 2)
        pygame.draw.line(surf, _W3, (_r.x, _r.y + _r.h // 2), (_r.right, _r.y + _r.h // 2), 2)
        _window(surf, 180, Y_F1 - 340, 80, 120, ox, oy, tick)
        _window(surf, 600, Y_F1 - 340, 80, 120, ox, oy, tick)
        _window(surf, 900, Y_F1 - 340, 80, 120, ox, oy, tick)

    _r = pygame.Rect(1100 + ox, Y_F1 - _RH + oy, 1060, _RH)
    if _r.right > 0 and _r.x < sw:
        _grad_rect(surf, _r, _LAC, _LAL)
        for yy in range(_r.y, _r.bottom, 32):
            pygame.draw.line(surf, _lc(_LAC, _LAL, 0.4), (_r.x, yy), (_r.right, yy), 1)
        _window(surf, 1250, Y_F1 - 340, 80, 120, ox, oy, tick)
        _window(surf, 1700, Y_F1 - 340, 80, 120, ox, oy, tick)
        _fireplace(surf, 1450, Y_F1 - 90, ox, oy, tick)

    _r = pygame.Rect(2160 + ox, Y_F1 - _RH + oy, 1100, _RH)
    if _r.right > 0 and _r.x < sw:
        _grad_rect(surf, _r, _IRN, (28, 28, 32))
        for xm in range(_r.x, _r.right, 45):
            pygame.draw.line(surf, (60, 60, 68), (xm, _r.y), (xm, _r.bottom), 1)

    _r = pygame.Rect(3260 + ox, Y_F1 - _RH + oy, 722, _RH)
    if _r.right > 0 and _r.x < sw:
        _stone_wall(surf, _r, (22, 18, 14), (38, 32, 25))

    # ── 2. KAT (Y_F2 = 1200) ──────────────────────────────────────────────────

    _r = pygame.Rect(20 + ox, Y_F2 - _RH + oy, 940, _RH)
    if _r.right > 0 and _r.x < sw:
        _grad_rect(surf, _r, (50, 5, 5), _BOR)
        pygame.draw.line(surf, _GLD, (_r.x, _r.y + 14), (_r.right, _r.y + 14), 2)
        pygame.draw.line(surf, _GLD, (_r.x, _r.bottom - 14), (_r.right, _r.bottom - 14), 2)
        _window(surf, 120, Y_F2 - 340, 90, 130, ox, oy, tick)
        _window(surf, 550, Y_F2 - 340, 90, 130, ox, oy, tick)
        _fireplace(surf, 320, Y_F2 - 90, ox, oy, tick)

    _r = pygame.Rect(960 + ox, Y_F2 - _RH + oy, 1090, _RH)
    if _r.right > 0 and _r.x < sw:
        _grad_rect(surf, _r, _MRG, _MRB)
        _karo_floor(surf, pygame.Rect(_r.x, Y_F2 - _FH + oy, _r.w, _FH), ox, oy, 32)
        _window(surf, 1060, Y_F2 - 340, 80, 120, ox, oy, tick)
        _window(surf, 1650, Y_F2 - 340, 80, 120, ox, oy, tick)

    _r = pygame.Rect(2050 + ox, Y_F2 - _RH + oy, 1100, _RH)
    if _r.right > 0 and _r.x < sw:
        _grad_rect(surf, _r, _ZUM, _ZUL)
        for yy in range(_r.y, _r.bottom, 30):
            pygame.draw.line(surf, _lc(_ZUM, _ZUL, 0.35), (_r.x, yy), (_r.right, yy), 1)
        _window(surf, 2200, Y_F2 - 340, 80, 120, ox, oy, tick)
        _window(surf, 2750, Y_F2 - 340, 80, 120, ox, oy, tick)
        _fireplace(surf, 2450, Y_F2 - 90, ox, oy, tick)

    _r = pygame.Rect(3150 + ox, Y_F2 - _RH + oy, 832, _RH)
    if _r.right > 0 and _r.x < sw:
        _grad_rect(surf, _r, (8, 10, 16), (18, 20, 30))
        _star_rng_z.seed(42)
        for _ in range(22):
            sx2 = _r.x + _star_rng_z.randint(0, max(1, _r.w))
            sy2 = _r.y + _star_rng_z.randint(0, max(1, _r.h // 2))
            br = max(0, min(255, int(80 + 60 * math.sin(tick * 1.5 + sx2 * 0.05))))
            if 0 <= sx2 < surf.get_width() and 0 <= sy2 < surf.get_height():
                pygame.draw.circle(surf, (br, br, br), (sx2, sy2), 1)

    # ── CATI KATI (Y_RF = 800) ────────────────────────────────────────────────

    _r = pygame.Rect(20 + ox, Y_RF - _RH + oy, 1570, _RH)
    if _r.right > 0 and _r.x < sw:
        _grad_rect(surf, _r, (4, 6, 14), (10, 14, 26))
        _star_rng_rf.seed(77)
        for _ in range(35):
            sx3 = _r.x + _star_rng_rf.randint(0, max(1, _r.w))
            sy3 = _r.y + _star_rng_rf.randint(0, max(1, _r.h))
            br2 = max(0, min(255, int(60 + 80 * math.sin(tick * 0.7 + sx3 * 0.03))))
            if 0 <= sx3 < surf.get_width() and 0 <= sy3 < surf.get_height():
                pygame.draw.circle(surf, (br2, br2, br2), (sx3, sy3), 1)

    _r = pygame.Rect(1700 + ox, Y_RF - _RH + oy, 1250, _RH)
    if _r.right > 0 and _r.x < sw:
        _stone_wall(surf, _r, (26, 22, 28), (42, 38, 46))

    _r = pygame.Rect(2950 + ox, Y_RF - _RH + oy, 1032, _RH)
    if _r.right > 0 and _r.x < sw:
        _grad_rect(surf, _r, _VAULT, _lc(_VAULT, _VAULT_G, 0.3))
        for xp in range(_r.x, _r.right, 65):
            pygame.draw.line(surf, _lc(_VAULT, _VAULT_G, 0.5), (xp, _r.y), (xp, _r.bottom), 1)
        for yp in range(_r.y, _r.bottom, 45):
            pygame.draw.line(surf, _lc(_VAULT, _VAULT_G, 0.5), (_r.x, yp), (_r.right, yp), 1)

    # ── GIZLI KAT (Y_GS = 220) ────────────────────────────────────────────────
    _r = pygame.Rect(3300 + ox, Y_GS - 280 + oy, 682, 280)
    if _r.right > 0 and _r.x < sw:
        _grad_rect(surf, _r, (4, 3, 1), _VAULT)
        for xv in range(_r.x, _r.right, 55):
            pygame.draw.line(surf, _lc(_VAULT, _VAULT_G, 0.4), (xv, _r.y), (xv, _r.bottom), 1)
    _vault_glow(surf, ox, oy, tick)

    # ── ODA ETIKETLERI ────────────────────────────────────────────────────────
    _LABELS = [
        ( 450, Y_G  - 360, "GIRIS HOLU"),
        (1380, Y_G  - 360, "CEKILIS SALONU"),
        (2350, Y_G  - 360, "YEMEK ODASI"),
        (3400, Y_G  - 360, "GUVENLIK"),
        ( 480, Y_F1 - 360, "KUTUPHANE"),
        (1570, Y_F1 - 360, "MISAFIR ODALARI"),
        (2600, Y_F1 - 360, "GUVENLIK KORIDORU"),
        ( 430, Y_F2 - 360, "EFENDI DAIRESI"),
        (1440, Y_F2 - 360, "MERMER BANYO"),
        (2500, Y_F2 - 360, "MISAFIR SUITI"),
        ( 760, Y_RF - 360, "CATI TERASI"),
        (2150, Y_RF - 360, "CATI"),
        (3300, Y_RF - 360, "KASA BOLUMU"),
        (3560, Y_GS - 210, "* GIZLI KASA *"),
    ]
    _ensure_caches()
    for lx, ly, ltxt in _LABELS:
        sx4, sy4 = lx + ox, ly + oy
        if -200 < sx4 < surf.get_width() + 200 and -50 < sy4 < surf.get_height() + 50:
            surf.blit(_label_font.render(ltxt, True, (160, 130, 80)), (sx4, sy4))


# =============================================================================
#  MERDIVEN INSAAT FONKSIYONU — Sahanlikli tasarim
# =============================================================================
def _staircase(buf: list, x_base: int, y_bottom: int, y_top: int,
               ti: int, go_right: bool = True) -> None:
    """
    Sahanlikli merdiven insaa eder.

    Yapi (go_right=True):
        [ALT SAHANLIK 120px] → [BASAMAKLAR →] → [UST SAHANLIK 120px]

    Basamak olculeri: _STEP_W x _STEP_H (72 x 36 px)
    400 px yukseklik → ~11 basamak x 72 px = 792 px + 2x120 px sahanlık = ~1032 px toplam.
    """
    from entities import Platform

    gap         = y_bottom - y_top
    n_steps     = max(2, round(gap / _STEP_H))
    actual_rise = gap / n_steps
    direction   = 1 if go_right else -1

    # Alt sahanlık — baslangic noktasi
    buf.append(Platform(x_base, y_bottom - _T, _LANDING, _T, theme_index=ti))

    # Basamaklar
    for i in range(n_steps):
        step_x = x_base + _LANDING + i * _STEP_W * direction
        step_y = int(y_bottom - (i + 1) * actual_rise) - _T
        buf.append(Platform(step_x, step_y, _STEP_W, _T, theme_index=ti))

    # Ust sahanlık — bitis noktasi
    top_x = x_base + _LANDING + n_steps * _STEP_W * direction
    buf.append(Platform(top_x, y_top - _T, _LANDING, _T, theme_index=ti))


# =============================================================================
#  ANA PLATFORM INSAAT FONKSIYONU
# =============================================================================
def build_level_16_platforms(all_platforms: pygame.sprite.Group,
                              theme_idx: int) -> None:
    """
    Bolum 16 platform haritasini insaa eder.
    Cagri yeri: main.py -> init_game() -> manor_stealth -> if current_level_idx == 16
    On kosul  : all_platforms.empty() zaten cagrilmis olmali.

    Harita Ozeti (4000 x 2100 px, 5 kat):
        Y_G  = 2000 — Zemin kat
        Y_F1 = 1600 — 1. Kat
        Y_F2 = 1200 — 2. Kat
        Y_RF =  800 — Cati kati
        Y_GS =  220 — Gizli kat (kasa)
    """
    from entities import Platform
    _ti = theme_idx
    buf: list = []

    # ── Dis Duvarlar ──────────────────────────────────────────────────────────
    buf.append(Platform(0,    Y_GS, _W, MANOR_16_MAP_HEIGHT - Y_GS, theme_index=_ti))
    buf.append(Platform(3980, Y_GS, _W, MANOR_16_MAP_HEIGHT - Y_GS, theme_index=_ti))

    # ── ZEMIN KAT ─────────────────────────────────────────────────────────────
    buf.append(Platform(20,   Y_G, 3960, _T, theme_index=_ti))
    buf.append(Platform( 920, Y_F1 + _T, _W, Y_G - Y_F1 - _T, theme_index=_ti))
    buf.append(Platform(1900, Y_F1 + _T, _W, Y_G - Y_F1 - _T, theme_index=_ti))
    buf.append(Platform(2900, Y_F1 + _T, _W, Y_G - Y_F1 - _T, theme_index=_ti))

    # ── MERDIVEN: Zemin → 1. Kat ──────────────────────────────────────────────
    #   3 merdiven — sol saga, orta sola, sag sola gider (zikzak etki)
    _staircase(buf, x_base=200,  y_bottom=Y_G,  y_top=Y_F1, ti=_ti, go_right=True)
    _staircase(buf, x_base=2050, y_bottom=Y_G,  y_top=Y_F1, ti=_ti, go_right=False)
    _staircase(buf, x_base=3550, y_bottom=Y_G,  y_top=Y_F1, ti=_ti, go_right=False)

    # ── 1. KAT ────────────────────────────────────────────────────────────────
    buf.append(Platform(  20, Y_F1,  880, _T, theme_index=_ti))
    buf.append(Platform(1100, Y_F1,  920, _T, theme_index=_ti))
    buf.append(Platform(2160, Y_F1,  960, _T, theme_index=_ti))
    buf.append(Platform(3260, Y_F1,  720, _T, theme_index=_ti))
    buf.append(Platform(1300, Y_F2 + _T, _W, Y_F1 - Y_F2 - _T, theme_index=_ti))
    buf.append(Platform(2350, Y_F2 + _T, _W, Y_F1 - Y_F2 - _T, theme_index=_ti))

    # Havalandirma raflari (kacis / platform atlama yolu)
    for _hx, _hy in [
        (420, 1480), (720, 1430), (1050, 1480),
        (1550, 1430), (2050, 1480), (2650, 1430), (3150, 1480),
    ]:
        buf.append(Platform(_hx, _hy, 180, _T, theme_index=_ti))

    # ── MERDIVEN: 1. Kat → 2. Kat ─────────────────────────────────────────────
    _staircase(buf, x_base=850,  y_bottom=Y_F1, y_top=Y_F2, ti=_ti, go_right=True)
    _staircase(buf, x_base=2250, y_bottom=Y_F1, y_top=Y_F2, ti=_ti, go_right=False)
    _staircase(buf, x_base=3450, y_bottom=Y_F1, y_top=Y_F2, ti=_ti, go_right=False)

    # ── 2. KAT ────────────────────────────────────────────────────────────────
    buf.append(Platform(  20, Y_F2,  800, _T, theme_index=_ti))
    buf.append(Platform( 960, Y_F2, 1010, _T, theme_index=_ti))
    buf.append(Platform(2050, Y_F2, 1020, _T, theme_index=_ti))
    buf.append(Platform(3150, Y_F2,  830, _T, theme_index=_ti))
    buf.append(Platform(2280, Y_RF + _T, _W, Y_F2 - Y_RF - _T, theme_index=_ti))

    # Havalandirma raflari
    for _hx, _hy in [
        (350, 1080), (780, 1030), (1250, 1080),
        (1850, 1030), (2450, 1080), (3050, 1030),
    ]:
        buf.append(Platform(_hx, _hy, 180, _T, theme_index=_ti))

    # ── MERDIVEN: 2. Kat → Cati ───────────────────────────────────────────────
    _staircase(buf, x_base=1900, y_bottom=Y_F2, y_top=Y_RF, ti=_ti, go_right=True)
    _staircase(buf, x_base=3380, y_bottom=Y_F2, y_top=Y_RF, ti=_ti, go_right=False)

    # ── CATI KATI ─────────────────────────────────────────────────────────────
    buf.append(Platform(  20, Y_RF, 1570, _T, theme_index=_ti))
    buf.append(Platform(1700, Y_RF, 1120, _T, theme_index=_ti))
    buf.append(Platform(2950, Y_RF, 1030, _T, theme_index=_ti))

    # ── MERDIVEN: Cati → Gizli Kat ────────────────────────────────────────────
    #   580 px yukseklik → ~16 basamak (en zorlu tirmanis)
    _staircase(buf, x_base=3350, y_bottom=Y_RF, y_top=Y_GS, ti=_ti, go_right=False)

    # Uzun merdivende ara nefes platformu
    mid_y = (Y_RF + Y_GS) // 2
    buf.append(Platform(2900, mid_y, 300, _T, theme_index=_ti))

    # ── GIZLI KAT — KASA ODASI ────────────────────────────────────────────────
    buf.append(Platform(3300, Y_GS, 682, _T + 8, theme_index=_ti))

    all_platforms.add(*buf)