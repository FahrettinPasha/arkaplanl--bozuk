# camera_system.py
# Victorian Mansion projesinden uyarlanan gelişmiş kamera ve fizik sistemleri
# AGENT.MD uyumlu: Pool mimarisi, dt bağımsız, sıfır runtime alloc, draw/update ayrımı
# ─────────────────────────────────────────────────────────────────────────────
#
#  Sınıflar:
#    CameraShake  — Smooth Falloff titreşim (eski screen_shake int'in yerine)
#    ManorCamera  — Aim Lead + Velocity Lookahead + Enemy Pull 2D kamera
#    DynamicZoom  — Nişan alınan düşmana otomatik yakınlaştırma
#    RagdollPool  — Pool tabanlı 5-parçalı fiziksel ölüm animasyonu
#
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations
import math
import random
import pygame

from settings import (
    LOGICAL_WIDTH, LOGICAL_HEIGHT,
    CAM_LERP_X, CAM_LERP_Y,
    CAM_AIM_LEAD_X, CAM_AIM_LEAD_Y,
    CAM_VEL_LOOKAHEAD,
    CAM_ENEMY_PULL_START, CAM_ENEMY_PULL_FULL, CAM_ENEMY_PULL_WEIGHT,
    CAM_ZOOM_AIM_CONE, CAM_ZOOM_AIM_DIST,
    CAM_ZOOM_MIN, CAM_ZOOM_MAX, CAM_ZOOM_LERP, CAM_ZOOM_MARGIN,
    RAGDOLL_POOL_SIZE, RAGDOLL_GRAVITY, RAGDOLL_BOUNCE, RAGDOLL_FRICTION,
)

_LW  = LOGICAL_WIDTH
_LH  = LOGICAL_HEIGHT
_rng = random.Random(1887)    # Sabit seed — deterministik ragdoll dağılımı


# ═════════════════════════════════════════════════════════════════════════════
#  CameraShake — Smooth Falloff Titreşim
# ═════════════════════════════════════════════════════════════════════════════
class CameraShake:
    """
    Eski `screen_shake` int + `random.randint` çiftinin yerini alır.
    Titreşim şiddeti başta güçlü, zamanla yumuşakça sıfıra iner (Smooth Falloff).

    Kullanım:
        camera_shake.trigger(intensity=8.0, duration=0.18)
        ox, oy = camera_shake.get_offset(dt)    # render_offset'e ekle

    Neden daha iyi?
    ─ Saçma rastgele atlamalar yok; sinüs tabanlı organik salınım.
    ─ Daha güçlü talep önceki titreşimi override eder.
    ─ Süre sona erdiğinde abrupt durmaz, yavaşça sönümlenir.
    """
    __slots__ = ('_si', '_st', '_sm', '_ft')

    def __init__(self):
        self._si = 0.0       # Mevcut şiddet (piksel)
        self._st = 0.0       # Kalan süre (sn)
        self._sm = 0.001     # Toplam süre — sıfıra bölme koruması
        self._ft = 0.0       # İç zaman sayacı (salınım frekansı)

    # ── Dış API ──────────────────────────────────────────────────────────────

    def trigger(self, intensity: float, duration: float = 0.18):
        """
        Yeni titreşim başlat.
        Daha güçlü istek — override eder; daha zayıf istek — yoksayılır.
        """
        if intensity > self._si:
            self._si = float(intensity)
            self._st = float(duration)
            self._sm = max(float(duration), 0.001)

    def get_offset(self, dt: float) -> tuple:
        """
        Bu frame'in titreşim ofsetini döndür ve sayacı ilerlet.
        Dönen: (ox, oy) int piksel — render_offset'e eklenir.
        AGENT.MD: Update içinde çağrıl, draw içinde değil.
        """
        self._ft += dt
        if self._st <= 0.0:
            self._si = 0.0
            return (0, 0)
        self._st -= dt
        if self._st <= 0.0:
            self._si = 0.0
            return (0, 0)
        # Smooth falloff: başta maksimum, sonra yumuşakça sıfır
        prog = 1.0 - (self._st / self._sm)   # 0 → 1 arası ilerleme
        mag  = self._si * (1.0 - prog)        # Şiddet giderek azalır
        ox   = math.sin(self._ft * 52.0) * mag
        oy   = math.cos(self._ft * 61.0) * mag * 0.65
        return (int(ox), int(oy))

    def reset(self):
        """Level geçişlerinde titreşimi anında durdur."""
        self._si = self._st = 0.0

    @property
    def is_active(self) -> bool:
        return self._st > 0.0


# ═════════════════════════════════════════════════════════════════════════════
#  ManorCamera — 2D Takip Kamerası (Aim Lead + Enemy Pull + Velocity Lookahead)
# ═════════════════════════════════════════════════════════════════════════════
class ManorCamera:
    """
    Malikane bölümü (manor_stealth) için gelişmiş 2D kamera.
    Mevcut basit lerp kamerasını Aim Lead + Velocity + Enemy Pull ile geliştirir.

    Kullanım:
        mc = ManorCamera()

        # Fizik sonrası, her frame:
        mc.update(player_x, player_y, vx, vy, aim_angle, all_enemies, dt,
                  map_w, map_h)

        # Render'da:
        ox, oy = mc.get_offset()
        # → manor_camera_offset_x = ox, manor_camera_offset_y = oy

    Parametreler (settings.py'den gelir — SSOT):
        CAM_LERP_X / CAM_LERP_Y      : Yatay/dikey yumuşatma faktörü
        CAM_AIM_LEAD_X / Y           : Nişan yönünde ekstra öteleme (px)
        CAM_VEL_LOOKAHEAD            : Hız yönünde ekstra öteleme çarpanı
        CAM_ENEMY_PULL_START / FULL  : Düşman çekimi mesafe eşikleri (px)
        CAM_ENEMY_PULL_WEIGHT        : Maksimum düşman çekimi ağırlığı
    """
    __slots__ = ('x', 'y')

    def __init__(self):
        self.x = 0.0
        self.y = 0.0

    def update(self,
               player_x: float, player_y: float,
               vx: float = 0.0, vy: float = 0.0,
               aim_angle: float = 0.0,
               enemies=None,
               dt: float = 0.016,
               map_w: int = 3300,
               map_h: int = _LH):
        """
        Kamera hedefini hesapla ve LERP ile yaklaş.

        Adım 1 — Oyuncu odağı (hitbox merkezi)
        Adım 2 — Düşman çekimi (en yakın aktif düşmana doğru ağırlıklı kayma)
        Adım 3 — Aim lead + velocity lookahead
        Adım 4 — Harita sınırlama + LERP
        """
        # ── 1. Temel odak: hitbox merkezi ────────────────────────────────────
        PLAYER_W, PLAYER_H = 28, 42   # settings.py'deki PLAYER_W/H ile eşleşmeli
        focus_x = player_x + PLAYER_W * 0.5
        focus_y = player_y + PLAYER_H * 0.5

        # ── 2. Düşman çekimi ─────────────────────────────────────────────────
        if enemies:
            ps = CAM_ENEMY_PULL_START
            pf = CAM_ENEMY_PULL_FULL
            best_d  = ps
            best_ex = None
            best_ey = None

            for e in enemies:
                # Farklı entity tipleri için güvenli koordinat erişimi
                ex = float(getattr(e, 'x',
                      getattr(e, 'wx',
                        getattr(e, 'rect', None) and e.rect.centerx or focus_x)))
                ey = float(getattr(e, 'y',
                      getattr(e, 'wy',
                        getattr(e, 'rect', None) and e.rect.centery or focus_y)))

                d = math.hypot(ex - focus_x, ey - focus_y)
                if d < best_d:
                    best_d  = d
                    best_ex = ex
                    best_ey = ey

            if best_ex is not None:
                t = max(0.0, min(1.0, (ps - best_d) / max(ps - pf, 1.0)))
                w = t * CAM_ENEMY_PULL_WEIGHT
                focus_x = focus_x * (1.0 - w) + best_ex * w
                focus_y = focus_y * (1.0 - w) + best_ey * w

        # ── 3. Aim lead + velocity lookahead ─────────────────────────────────
        al_x = max(-CAM_AIM_LEAD_X, min(CAM_AIM_LEAD_X,
                   math.cos(aim_angle) * CAM_AIM_LEAD_X))
        al_y = max(-CAM_AIM_LEAD_Y, min(CAM_AIM_LEAD_Y,
                   math.sin(aim_angle) * CAM_AIM_LEAD_Y))
        vl_x = max(-28.0, min(28.0, vx * CAM_VEL_LOOKAHEAD))

        # ── 4. Hedef + sınırla + LERP ─────────────────────────────────────────
        cam_max_x = max(0.0, float(map_w - _LW))
        cam_max_y = max(0.0, float(map_h - _LH))
        tx = max(0.0, min(cam_max_x, focus_x - _LW * 0.5 + al_x + vl_x))
        ty = max(0.0, min(cam_max_y, focus_y - _LH * 0.5 + al_y))

        lx = min(1.0, CAM_LERP_X * dt * 60.0)
        ly = min(1.0, CAM_LERP_Y * dt * 60.0)
        self.x += (tx - self.x) * lx
        self.y += (ty - self.y) * ly

    def get_offset(self) -> tuple:
        """Render pipeline için ofset döndür (int, int)."""
        return (int(self.x), int(self.y))

    def reset(self, player_x: float, player_y: float):
        """Level/sahne geçişinde kamerayı anlık konumlandır."""
        self.x = max(0.0, player_x - _LW * 0.5 + 14.0)
        self.y = max(0.0, player_y - _LH * 0.5 + 21.0)


# ═════════════════════════════════════════════════════════════════════════════
#  DynamicZoom — Nişan Alınan Düşmana Otomatik Zoom
# ═════════════════════════════════════════════════════════════════════════════
class DynamicZoom:
    """
    Oyuncu bir düşmana nişan alınca game_canvas yumuşakça yakınlaşır.
    İki karakteri de kadrajda tutan akıllı zoom hesabı yapar.

    Kullanım:
        dz = DynamicZoom()

        # Her frame (update döngüsünde):
        dz.update(player_x, player_y, aim_angle, all_enemies, dt)

        # Final render'da screen.blit() YERINE:
        if not dz.blit(screen, game_canvas):
            screen.blit(final_game_image, (0, 0))   # Fallback: zoom aktif değil

        # Crosshair rengi için:
        if dz.is_targeting:
            crosshair_color = (255, 60, 60)   # Kırmızı — düşman kilitlendi

    Parametreler (settings.py — SSOT):
        CAM_ZOOM_AIM_CONE  : Nişan konisi (radyan)
        CAM_ZOOM_AIM_DIST  : Maksimum etkili mesafe (px)
        CAM_ZOOM_MIN/MAX   : Zoom sınırları
        CAM_ZOOM_LERP      : Yumuşatma hızı (sn⁻¹)
        CAM_ZOOM_MARGIN    : Kenar payı (px)
    """
    __slots__ = ('_zoom', '_zoom_target', '_focus_x', '_focus_y')

    def __init__(self):
        self._zoom        = 1.0
        self._zoom_target = 1.0
        self._focus_x     = float(_LW // 2)
        self._focus_y     = float(_LH // 2)

    def update(self,
               player_x: float, player_y: float,
               aim_angle: float,
               enemies,
               dt: float):
        """
        Düşman tespiti ve zoom hedefi hesapla, sonra LERP ile yaklaş.
        AGENT.MD: Update döngüsünde çağrıl — draw değil.
        """
        px = player_x + 14.0
        py = player_y + 21.0
        self._zoom_target = 1.0
        self._focus_x     = px
        self._focus_y     = py

        for e in enemies:
            # Farklı entity tipleri için güvenli koordinat erişimi
            _r = getattr(e, 'rect', None)
            ex = float(getattr(e, 'x',
                  getattr(e, 'wx', _r.centerx if _r else px)))
            ey = float(getattr(e, 'y',
                  getattr(e, 'wy', _r.centery if _r else py)))

            dx = ex - px;  dy = ey - py
            d  = math.hypot(dx, dy)
            if d < 8.0:
                continue

            ang_to = math.atan2(dy, dx)
            diff   = abs(math.atan2(
                math.sin(aim_angle - ang_to),
                math.cos(aim_angle - ang_to)
            ))

            if diff < CAM_ZOOM_AIM_CONE and d < CAM_ZOOM_AIM_DIST:
                # Odak: oyuncu ve düşman arasının tam ortası
                self._focus_x = (px + ex) * 0.5
                self._focus_y = (py + ey) * 0.5

                # Her ikisini de sığdıracak zoom — mesafeye göre otomatik
                mg = float(CAM_ZOOM_MARGIN)
                needed_w = abs(dx) * 1.5 + mg
                needed_h = abs(dy) * 1.5 + mg
                z_w = _LW / max(needed_w, 1.0)
                z_h = _LH / max(needed_h, 1.0)
                self._zoom_target = max(CAM_ZOOM_MIN,
                                        min(CAM_ZOOM_MAX, min(z_w, z_h)))
                break   # En yakın düşman yeter

        # LERP — ani zıplama yok
        self._zoom += (self._zoom_target - self._zoom) * min(1.0, CAM_ZOOM_LERP * dt)

    def blit(self, screen: pygame.Surface, game_canvas: pygame.Surface) -> bool:
        """
        game_canvas → screen blit.
        Zoom aktifse subsurface al ve ölçekle; aksi halde False döner.
        AGENT.MD: game_canvas sınırını aşmayan güvenli subsurface hesabı.

        Dönen değer:
            True  — zoom aktif, blit yapıldı (caller normal blit'i YAPMAsin)
            False — zoom yok, caller kendi blit'ini yapsın
        """
        if abs(self._zoom - 1.0) < 0.005:
            return False   # Zoom yok, mevcut blit akışı devam eder

        fcx = int(self._focus_x)
        fcy = int(self._focus_y)
        vw  = max(1, int(_LW / self._zoom))
        vh  = max(1, int(_LH / self._zoom))
        # game_canvas sınır güvenliği
        vw  = min(vw, _LW)
        vh  = min(vh, _LH)
        sx  = max(0, min(fcx - vw // 2, _LW - vw))
        sy  = max(0, min(fcy - vh // 2, _LH - vh))

        try:
            sub = game_canvas.subsurface((sx, sy, vw, vh))
            pygame.transform.scale(sub, screen.get_size(), screen)
            return True
        except (pygame.error, ValueError):
            return False   # Fallback: caller normal blit yapsın

    @property
    def is_targeting(self) -> bool:
        """Şu an düşmana nişan alınıyor mu? (crosshair rengi için)"""
        return self._zoom_target > 1.0 + 0.02


# ═════════════════════════════════════════════════════════════════════════════
#  _RagPart — Tek ragdoll parçası (pool slot)
# ═════════════════════════════════════════════════════════════════════════════
class _RagPart:
    __slots__ = ('wx', 'wy', 'vx', 'vy', 'rot', 'rot_vel',
                 'life', 'ml', 'shape', 'col', 'sz', 'floor_y', 'active')

    def __init__(self):
        self.active = False


# ═════════════════════════════════════════════════════════════════════════════
#  RagdollPool — Pool Tabanlı Fiziksel Ölüm Animasyonu
# ═════════════════════════════════════════════════════════════════════════════
class RagdollPool:
    """
    Düşman ölünce 5-parçalı (baş, gövde, 2 bacak, kol) ragdoll fırlatır.
    Pool mimarisi: AGENT.MD kuralına uygun — sıfır runtime alloc.
    Fizik: Yerçekimi + zemin sekme + rotasyon + yatay sönüm + fade-out blink.

    Kullanım:
        rp = RagdollPool()

        # Düşman öldüğünde (event tetiklemeli, update içinde değil!):
        rp.spawn(enemy_x, enemy_y,
                 floor_y  = LOGICAL_HEIGHT - 50,
                 impact_vx = bullet_vx * 0.25)

        # Her frame — update ve draw AYRI çağrıl (AGENT.MD kuralı):
        rp.update(dt)
        rp.draw(game_canvas, render_offset)   # Z-6b: VFX öncesi, oyuncu sonrası

        # Level geçişinde:
        rp.clear()
    """

    def __init__(self):
        self._pool : list[_RagPart] = [_RagPart() for _ in range(RAGDOLL_POOL_SIZE)]
        self._ft   : float = 0.0   # Global zaman (blink senkronizasyonu)

    # ── İç Yardımcı ──────────────────────────────────────────────────────────

    def _spawn_part(self,
                    wx: float, wy: float, floor_y: float,
                    ivx: float, ivy: float,
                    shape: int, col: tuple, sz) -> None:
        """Havuzdan boş slot bul ve doldur. Dolu havuzda sessizce döner."""
        for p in self._pool:
            if not p.active:
                p.wx      = float(wx);       p.wy  = float(wy)
                p.vx      = float(ivx);      p.vy  = float(ivy)
                p.rot     = _rng.uniform(0.0, math.pi * 2.0)
                p.rot_vel = _rng.uniform(-9.0, 9.0)
                p.ml      = _rng.uniform(2.2, 3.8)
                p.life    = p.ml
                p.shape   = shape   # 0=baş(daire), 1=gövde(rect), 2=uzuv(çizgi)
                p.col     = col
                p.sz      = sz
                p.floor_y = float(floor_y)
                p.active  = True
                return

    # ── Dış API ──────────────────────────────────────────────────────────────

    def spawn(self,
              enemy_x: float, enemy_y: float,
              floor_y: float = None,
              impact_vx: float = 0.0,
              body_col: tuple = (130, 130, 140),
              head_col: tuple = (170, 150, 130)) -> None:
        """
        5-parçalı ragdoll fırlat.
        floor_y belirtilmezse LOGICAL_HEIGHT - 50 varsayılır.
        AGENT.MD: Yalnızca event anında çağrıl — update döngüsünde değil.
        """
        if floor_y is None:
            floor_y = float(_LH - 50)

        bx  = enemy_x + 14.0   # Düşman hitbox merkezi X (yaklaşık)
        by  = enemy_y + 6.0    # Üst kısmı
        iv  = impact_vx

        # Baş
        self._spawn_part(bx, enemy_y - 4, floor_y,
                         iv * 0.5 + _rng.uniform(-40, 40),
                         _rng.uniform(-340, -460),
                         0, head_col, 7)
        # Gövde
        self._spawn_part(bx, enemy_y + 14, floor_y,
                         iv * 0.3 + _rng.uniform(-20, 20),
                         _rng.uniform(-200, -310),
                         1, body_col, (22, 30))
        # Sol bacak
        self._spawn_part(enemy_x + 5, enemy_y + 28, floor_y,
                         iv * 0.2 + _rng.uniform(-30, -10),
                         _rng.uniform(-80, -160),
                         2, body_col, 16)
        # Sağ bacak
        self._spawn_part(enemy_x + 22, enemy_y + 28, floor_y,
                         iv * 0.2 + _rng.uniform(10, 30),
                         _rng.uniform(-80, -160),
                         2, body_col, 16)
        # Kol
        self._spawn_part(bx, enemy_y + 10, floor_y,
                         iv * 0.6 + _rng.uniform(-50, 50),
                         _rng.uniform(-260, -380),
                         2, head_col, 12)

    def update(self, dt: float) -> None:
        """
        Tüm aktif parçaların fiziğini güncelle.
        AGENT.MD: draw() çağırma, render pipeline ayrı.
        """
        self._ft += dt
        grav = RAGDOLL_GRAVITY

        for p in self._pool:
            if not p.active:
                continue

            p.life -= dt
            if p.life <= 0.0:
                p.active = False
                continue

            # Yerçekimi + hareket
            p.vy  += grav * dt
            p.wx  += p.vx * dt
            p.wy  += p.vy * dt
            p.rot += p.rot_vel * dt

            # Zemin çarpışması + sekme
            if p.wy >= p.floor_y:
                p.wy       = p.floor_y
                p.vy      *= -RAGDOLL_BOUNCE
                p.vx      *= RAGDOLL_FRICTION
                p.rot_vel *= 0.65
                if abs(p.vy) < 18.0:
                    p.vy = 0.0

            # Yatay hava sürtünmesi
            p.vx *= max(0.0, 1.0 - dt * 1.1)

    def draw(self, surf: pygame.Surface,
             render_offset: tuple = (0, 0)) -> None:
        """
        Tüm aktif parçaları yüzeye çiz.
        AGENT.MD: update() çağırma — bu sadece görseldir.
        render_offset: (ox, oy) — mevcut kamera sarsma ofseti.
        """
        ox, oy = render_offset
        blink_frame = int(self._ft * 18) % 2   # Blink senkronizasyonu

        for p in self._pool:
            if not p.active:
                continue

            sx = int(p.wx) + ox
            sy = int(p.wy) + oy

            # Ekran dışı → çizme
            if sx < -140 or sx > _LW + 140 or sy < -100 or sy > _LH + 100:
                continue

            # Son %35'te yanıp söner (ölüm hissi)
            if (p.life / p.ml) < 0.35 and blink_frame == 0:
                continue

            if p.shape == 0:           # ── Baş (daire)
                r = p.sz
                pygame.draw.circle(surf, p.col, (sx, sy), r)
                # Küçük göz: baş yönünü belirtir
                ex2 = sx + int(math.cos(p.rot) * r * 0.45)
                ey2 = sy + int(math.sin(p.rot) * r * 0.45)
                pygame.draw.circle(surf, (20, 20, 20), (ex2, ey2), 2)

            elif p.shape == 1:         # ── Gövde (dönen dikdörtgen)
                w, h = p.sz
                ca   = math.cos(p.rot)
                sa   = math.sin(p.rot)
                hw   = w * 0.5;  hh = h * 0.5
                pts  = [
                    (int(sx + dx * ca - dy * sa),
                     int(sy + dx * sa + dy * ca))
                    for (dx, dy) in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))
                ]
                pygame.draw.polygon(surf, p.col, pts)

            elif p.shape == 2:         # ── Uzuv (dönen çizgi)
                ln  = p.sz
                hln = ln // 2
                x1  = sx + int(math.cos(p.rot) * hln)
                y1  = sy + int(math.sin(p.rot) * hln)
                x2  = sx - int(math.cos(p.rot) * hln)
                y2  = sy - int(math.sin(p.rot) * hln)
                pygame.draw.line(surf, p.col, (x1, y1), (x2, y2), 3)

    def clear(self) -> None:
        """Level geçişinde tüm parçaları pasifleştir."""
        for p in self._pool:
            p.active = False

    @property
    def active_count(self) -> int:
        """Debug: Aktif parça sayısı."""
        return sum(1 for p in self._pool if p.active)