import pygame
import math

_SCALE = 4
_HB_W = 28 * _SCALE
_HB_H = 42 * _SCALE
_CX   = 14 * _SCALE
_SH_Y = 22 * _SCALE

_ARM_D   = (28, 32, 42)
_ARM_M   = (45, 52, 68)
_ARM_L   = (70, 80, 105)
_ARM_RIM = (100,115,150)
_HELM_D  = (20, 22, 30)
_HELM_M  = (35, 40, 55)
_HELM_L  = (55, 62, 80)
_NEON_C  = (0, 210, 255)
_BOOT_D  = (18, 14, 10)
_BOOT_M  = (35, 28, 20)
_BOOT_L  = (55, 45, 32)
_BLACK   = (5,  5,  8)

def _lc(a, b, t):
    return tuple(int(a[i] + (b[i]-a[i])*t) for i in range(3))

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))

def _capsule(surf, p1, p2, r1, r2, col, bright=True):
    p1 = (int(p1[0]), int(p1[1]))
    p2 = (int(p2[0]), int(p2[1]))
    dx = p2[0]-p1[0]; dy = p2[1]-p1[1]
    d  = math.hypot(dx, dy)
    if d < 1:
        pygame.draw.circle(surf, col, p1, r1)
        return
    nx = -dy/d; ny = dx/d
    shadow = _lc(col, _BLACK, 0.5)
    spts = [(int(p1[0]+nx*r1+1),int(p1[1]+ny*r1+1)),
            (int(p2[0]+nx*r2+1),int(p2[1]+ny*r2+1)),
            (int(p2[0]-nx*r2+1),int(p2[1]-ny*r2+1)),
            (int(p1[0]-nx*r1+1),int(p1[1]-ny*r1+1))]
    pygame.draw.polygon(surf, shadow, spts)
    pts = [(int(p1[0]+nx*r1),int(p1[1]+ny*r1)),
           (int(p2[0]+nx*r2),int(p2[1]+ny*r2)),
           (int(p2[0]-nx*r2),int(p2[1]-ny*r2)),
           (int(p1[0]-nx*r1),int(p1[1]-ny*r1))]
    pygame.draw.polygon(surf, col, pts)
    pygame.draw.polygon(surf, _lc(col,_BLACK,0.35), pts, 1)
    if bright:
        hi = _lc(col,(255,255,255),0.2)
        pygame.draw.line(surf, hi,
            (int(p1[0]+nx*r1*0.45),int(p1[1]+ny*r1*0.45)),
            (int(p2[0]+nx*r2*0.45),int(p2[1]+ny*r2*0.45)), 1)
    pygame.draw.circle(surf, col, p1, r1)
    pygame.draw.circle(surf, col, p2, r2)

def _ik2(ox, oy, tx, ty, l1, l2):
    dx = tx-ox; dy = ty-oy
    d  = _clamp(math.hypot(dx,dy), abs(l1-l2)+0.1, l1+l2-0.1)
    ca = _clamp((d*d+l1*l1-l2*l2)/(2*d*l1), -1.0, 1.0)
    base = math.atan2(dy, dx)
    ang  = base - math.acos(ca)
    return int(ox+math.cos(ang)*l1), int(oy+math.sin(ang)*l1)

def _draw_helmet(surf, hx, hy, r, f):
    hx = int(hx); hy = int(hy); r = int(r)
    pygame.draw.circle(surf, _BLACK, (hx+2, hy+2), r+1)
    helm_rect = pygame.Rect(hx-r, hy-int(r*1.05), r*2, int(r*2.05))
    pygame.draw.ellipse(surf, _HELM_M, helm_rect)
    hi = pygame.Rect(hx-int(r*0.5), hy-int(r*0.95), int(r*0.7), int(r*0.5))
    pygame.draw.ellipse(surf, _HELM_L, hi)
    pygame.draw.ellipse(surf, _HELM_D, helm_rect, 1)
    cheek = [
        (hx+f*int(r*0.25), hy+int(r*0.05)),
        (hx+f*int(r*0.88), hy+int(r*0.05)),
        (hx+f*int(r*0.80), hy+int(r*0.82)),
        (hx+f*int(r*0.15), hy+int(r*0.88)),
    ]
    pygame.draw.polygon(surf, _ARM_D, cheek)
    pygame.draw.polygon(surf, _ARM_L, cheek, 1)
    vx1 = hx + f*int(r*0.22); vx2 = hx + f*int(r*0.76)
    vy1 = hy - int(r*0.35);   vy2 = hy + int(r*0.25)
    vpts = [(vx1,vy1),(vx2,vy1+int(r*0.08)),(vx2,vy2-int(r*0.06)),(vx1,vy2)]
    gs = pygame.Surface((abs(vx2-vx1)+8, abs(vy2-vy1)+8), pygame.SRCALPHA)
    pygame.draw.rect(gs, (*_NEON_C,60), gs.get_rect(), border_radius=2)
    surf.blit(gs, (min(vx1,vx2)-4, vy1-4))
    pygame.draw.polygon(surf, _lc(_NEON_C,_BLACK,0.65), vpts)
    pygame.draw.polygon(surf, _NEON_C, vpts, 2)
    for sy in range(vy1+3, vy2, max(1,int(r*0.12))):
        pygame.draw.line(surf, _lc(_NEON_C,_BLACK,0.4), (vx1,sy),(vx2,sy),1)
    ax = hx - f*int(r*0.2)
    ay = hy - int(r*1.05)
    pygame.draw.line(surf, _ARM_M, (ax,ay), (ax+f*int(r*0.5), ay-int(r*0.6)), 1)
    pygame.draw.circle(surf, _NEON_C, (ax+f*int(r*0.5), ay-int(r*0.6)), max(1,int(r*0.08)))

def _draw_torso(surf, cx, sh_y, hip_y, f, S, state):
    h = hip_y - sh_y
    front_t = cx + f*int(3.5*S)
    back_t  = cx - f*int(2.5*S)
    front_h = cx + f*int(2.8*S)
    back_h  = cx - f*int(2.0*S)
    back_pts = [(back_t,sh_y+int(h*0.05)),(cx,sh_y),(cx,hip_y),(back_h,hip_y)]
    pygame.draw.polygon(surf, _lc(_ARM_M,_BLACK,0.45), back_pts)
    body_pts = [(back_t,sh_y+int(h*0.05)),
                (front_t,sh_y+int(h*0.02)),
                (front_h,hip_y),
                (back_h,hip_y)]
    pygame.draw.polygon(surf, _ARM_M, body_pts)
    pygame.draw.polygon(surf, _lc(_ARM_M,_BLACK,0.4), body_pts, 1)
    chest = [(back_t+f*int(S*0.3), sh_y+int(h*0.04)),
             (front_t-f*int(S*0.3),sh_y+int(h*0.04)),
             (front_h-f*int(S*0.5),sh_y+int(h*0.58)),
             (back_h +f*int(S*0.5),sh_y+int(h*0.58))]
    pygame.draw.polygon(surf, _ARM_D, chest)
    pygame.draw.polygon(surf, _ARM_L, chest, 1)
    pygame.draw.line(surf, _ARM_L,
        (front_t,sh_y+int(h*0.02)),(front_h,hip_y),max(1,int(S*0.5)))
    ex = cx + f*int(S*0.4)
    sw = max(1,int(S*0.5))
    pygame.draw.line(surf, _lc(_NEON_C,(255,255,255),0.3),
        (ex, sh_y+int(h*0.06)),(ex, sh_y+int(h*0.54)), sw+1)
    gs2 = pygame.Surface((sw*3,int(h*0.5)), pygame.SRCALPHA)
    gs2.fill((*_NEON_C,35))
    surf.blit(gs2,(ex-sw, sh_y+int(h*0.06)))
    bh2 = max(2,int(S*1.2))
    pygame.draw.rect(surf, _ARM_D,
        (min(back_h,front_h), hip_y-int(S*0.5),
         abs(front_h-back_h)+1, bh2))
    pygame.draw.rect(surf, _ARM_RIM,
        (min(back_h,front_h), hip_y-int(S*0.5),
         abs(front_h-back_h)+1, bh2), 1)

def _draw_leg(surf, hip, knee, ankle, f, S, front=True, state='idle', phase=0.0):
    hip   = (int(hip[0]),   int(hip[1]))
    knee  = (int(knee[0]),  int(knee[1]))
    ankle = (int(ankle[0]), int(ankle[1]))
    if front:
        col = _ARM_M; col2 = _ARM_D
        rU = max(2,int(0.95*S)); rL = max(2,int(0.80*S)); rA = max(2,int(0.70*S))
    else:
        col = _lc(_ARM_D,_BLACK,0.3); col2 = _lc(_ARM_D,_BLACK,0.5)
        rU = max(2,int(0.75*S)); rL = max(2,int(0.65*S)); rA = max(2,int(0.58*S))
    _capsule(surf, hip, knee, rU, rL, col, bright=front)
    if front:
        pygame.draw.circle(surf, _ARM_L, knee, rL)
        pygame.draw.circle(surf, _ARM_RIM, knee, rL, 1)
    _capsule(surf, knee, ankle, rL, rA, col2, bright=front)
    bh = int(2.5*S)
    sy = ankle[1] + bh
    tx = ankle[0] + f*int(4.5*S)
    hx = ankle[0] - f*int(1.5*S)
    pygame.draw.ellipse(surf,_lc(_BOOT_M,_BLACK,0.3),
        (min(hx,ankle[0])-rA, ankle[1]-int(0.5*S),
         abs(hx-ankle[0])+rA*2, int(2.0*S)))
    boot = [(hx-f*int(0.3*S), ankle[1]+int(0.5*S)),
            (tx+f*int(1.2*S), ankle[1]+int(0.1*S)),
            (tx+f*int(1.5*S), sy-int(0.8*S)),
            (hx-f*int(0.3*S), sy-int(0.4*S))]
    pygame.draw.polygon(surf, _BOOT_M, boot)
    pygame.draw.polygon(surf, _lc(_BOOT_M,_BLACK,0.4), boot, 1)
    pygame.draw.ellipse(surf, _BOOT_M,
        (tx-int(1.2*S), ankle[1]-int(0.2*S), int(3.0*S), int(2.0*S)))
    pygame.draw.ellipse(surf, _lc(_BOOT_M,_BLACK,0.6),
        (hx-f*int(0.6*S), sy-int(0.6*S),
         abs(tx-hx)+int(2.5*S), int(1.5*S)))
    if front:
        pygame.draw.ellipse(surf, _BOOT_L,
            (tx-int(0.8*S), ankle[1], int(2.0*S), int(0.9*S)))
        pygame.draw.line(surf, _NEON_C,
            (hx, ankle[1]+int(0.8*S)),
            (hx, ankle[1]+bh-int(0.5*S)), 1)
        if state=='running' and abs(math.sin(phase)) > 0.72:
            da = int((abs(math.sin(phase))-0.72)*3.5*100)
            gs3 = pygame.Surface((int(6*S),int(3*S)),pygame.SRCALPHA)
            pygame.draw.ellipse(gs3,(*_ARM_RIM,da),gs3.get_rect())
            surf.blit(gs3,(ankle[0]-int(3*S), sy))

def _draw_arm(surf, sh, elbow, wrist, S, front=True):
    sh    = (int(sh[0]),    int(sh[1]))
    elbow = (int(elbow[0]), int(elbow[1]))
    wrist = (int(wrist[0]), int(wrist[1]))
    if front:
        col = _ARM_L; col2 = _ARM_M
        rU = max(2,int(0.85*S)); rL = max(2,int(0.72*S))
    else:
        col = _ARM_D; col2 = _lc(_ARM_D,_BLACK,0.3)
        rU = max(2,int(0.70*S)); rL = max(2,int(0.58*S))
    _capsule(surf, sh, elbow, rU, rL, col, bright=front)
    _capsule(surf, elbow, wrist, rL, max(2,int(0.60*S)), col2, bright=front)
    if front:
        pygame.draw.circle(surf, _ARM_RIM, elbow, rL)
        pygame.draw.circle(surf, _lc(_ARM_RIM,_BLACK,0.3), elbow, rL, 1)
        pygame.draw.circle(surf, _ARM_M,  wrist, max(2,int(0.62*S)))
        pygame.draw.circle(surf, _NEON_C, wrist, max(2,int(0.62*S)), 1)

# =========================================================
# KOSU KOL YARDIMCISI
# Gercek kosu mekánigi:
#   - Ust kol one-arkaya sallaniyor (sagittal)
#   - Dirsek yaklasik 90 derece kirili kaliyor
#   - El: one fazda omuz hizasina yukseliyor, arkaya gidince kalca hizasina iniyor
#   - phase: bacakla TERS faz (sag bacak ondeyken sol kol onde)
# =========================================================
def _running_arm_pts(sh_x, sh_y, phase, S, f):
    swing = math.sin(phase)          # -1=one, +1=arkaya
    # Ust kol: omuzdan dirseğe, one-arkaya +-30 derece
    upper_ang = math.radians(swing * 32)
    u_len = int(5.0 * S)
    ex = sh_x + int(math.sin(upper_ang) * u_len * f)
    ey = sh_y + int(math.cos(upper_ang) * u_len)
    # On kol: dirsekten bileğe, ~90 derece kirili
    # one gidince bilek yukari-one, arkaya gidince asagi-arka
    fore_ang = upper_ang + math.radians(88 + swing * 18)
    w_len = int(4.5 * S)
    wx = ex + int(math.sin(fore_ang) * w_len * f)
    wy = ey + int(math.cos(fore_ang) * w_len)
    return (int(ex), int(ey)), (int(wx), int(wy))

def draw_player_solid(
    surf, px, py,
    direction, state, draw_params,
    theme_color,
    aim_angle=0, shoot_timer=0,
    is_dashing=False, is_slamming=False
):
    f  = direction
    S  = _SCALE
    ft = pygame.time.get_ticks() * 0.001

    px = px - (S-1)*14
    py = py - (S-1)*42

    cx    = px + _CX
    sh_y  = py + _SH_Y

    head_r  = int(4.5*S)
    neck_h  = int(2*S)
    torso_h = int(11*S)
    leg_h   = int(14*S)
    thl     = int(7*S)
    shl     = int(7*S)

    head_y     = py + int(2*S) + head_r
    neck_bot   = head_y + head_r + int(1*S)
    sh_y2      = neck_bot + neck_h
    hip_y      = sh_y2 + torso_h
    feet_y     = hip_y + leg_h

    breath = math.sin(ft*2.2) * (0.7 if state=='idle' else 0.1)

    if   state=='running': cx += f*int(1.2*S)
    elif state=='dashing':  cx += f*int(3*S)

    FREQ  = 9.0
    SWING = int(6*S)
    LIFT  = int(5*S)
    pf = ft * FREQ
    pb = ft * FREQ + math.pi

    def _leg_tgt(phase):
        if state == 'running':
            ax = cx + int(math.sin(phase)*SWING)
            lift = max(0.0, -math.sin(phase))
            ay   = feet_y - int(lift*LIFT)
        elif state == 'jumping':
            ax = cx + f*int(1.5*S); ay = hip_y + thl + shl - int(3*S)
        elif state == 'falling':
            ax = cx; ay = hip_y + thl + shl + int(2*S)
        elif state == 'dashing':
            ax = cx - f*int(3*S); ay = feet_y
        else:
            idle_off = int(math.sin(ft*1.8)*S*0.5)
            ax = cx + idle_off; ay = feet_y
        return ax, ay

    hip_pt = (cx, hip_y)

    ax_fr, ay_fr = _leg_tgt(pf)
    ax_bk, ay_bk = _leg_tgt(pb)
    kx_fr, ky_fr = _ik2(cx, hip_y, ax_fr, ay_fr, thl, shl)
    kx_bk, ky_bk = _ik2(cx, hip_y, ax_bk, ay_bk, thl, shl)
    knee_fr = (kx_fr, ky_fr); ank_fr = (ax_fr, ay_fr)
    knee_bk = (kx_bk, ky_bk); ank_bk = (ax_bk, ay_bk)

    # ── Kol noktaları ────────────────────────────────────────────
    bsh_x = cx - f*int(3.0*S)
    bsh   = (bsh_x, sh_y2)

    if state == 'running':
        # Arka kol: on bacakla TERS faz (pb = ön bacak tersi = arka bacakla ayni)
        belb, bwri = _running_arm_pts(bsh_x, sh_y2, pb + math.pi, S, f)
        # On kol: arka bacakla TERS faz
        fsh_x = cx + f*int(2.8*S)
        felb, fwri = _running_arm_pts(fsh_x, sh_y2, pf + math.pi, S, f)
        fsh = (fsh_x, sh_y2)
    elif state == 'jumping':
        belb = (bsh_x - f*int(2*S), sh_y2 + int(3*S))
        bwri = (bsh_x - f*int(3*S), sh_y2 + int(8*S))
        fsh  = (cx + f*int(2.8*S), sh_y2)
        felb = (fsh[0]+f*int(S),   fsh[1]+int(2*S))
        fwri = (fsh[0]+f*int(2*S), fsh[1]+int(7*S))
    elif state == 'falling':
        belb = (bsh_x - f*int(S),   sh_y2 + int(8*S))
        bwri = (bsh_x + f*int(S),   sh_y2 + int(14*S))
        fsh  = (cx + f*int(2.8*S), sh_y2)
        felb = (fsh[0]+f*int(S*0.5), fsh[1]+int(6*S))
        fwri = (fsh[0]-f*int(S),     fsh[1]+int(12*S))
    else:
        belb = (bsh_x - f*int(S),    sh_y2 + int(5*S) + int(breath))
        bwri = (bsh_x - f*int(0.5*S),sh_y2 + int(11*S))
        fsh  = (cx + f*int(2.8*S), sh_y2)
        felb = (fsh[0]+f*int(S*0.3), fsh[1]+int(4*S)+int(breath))
        fwri = (fsh[0]+f*int(S*0.2), fsh[1]+int(9*S))

    aim_sh = (cx + f*int(3*S), sh_y)

    # Z SIRASI
    _draw_arm(surf, bsh, belb, bwri, S, front=False)
    _draw_leg(surf, hip_pt, knee_bk, ank_bk, f, S, front=False, state=state, phase=pb)
    _draw_torso(surf, cx, sh_y2, hip_y, f, S, state)
    _draw_leg(surf, hip_pt, knee_fr, ank_fr, f, S, front=True, state=state, phase=pf)

    neck_top    = (cx + f*int(S*0.3), head_y + head_r + int(0.5*S))
    neck_bot_pt = (cx + f*int(S*0.2), sh_y2 - int(0.5*S))
    _capsule(surf, neck_bot_pt, neck_top,
             max(2,int(0.7*S)), max(2,int(0.65*S)), _ARM_M, bright=False)

    _draw_helmet(surf,
                 cx + f*int(S*0.4) + int(breath*0.5),
                 head_y + int(breath*1.2),
                 head_r, f)

    pygame.draw.circle(surf, _ARM_L,   aim_sh, max(2,int(1.8*S)))
    pygame.draw.circle(surf, _ARM_RIM, aim_sh, max(2,int(1.8*S)), 1)

    if shoot_timer <= 0 and not is_dashing:
        _draw_arm(surf, fsh, felb, fwri, S, front=True)

    if is_dashing:
        for i in range(3):
            lx = cx - f*int((4+i*4)*S); ly = sh_y2 + i*int(3*S)
            gs4 = pygame.Surface((int((5+i*3)*S),2),pygame.SRCALPHA)
            gs4.fill((*_NEON_C, 55-i*15))
            surf.blit(gs4,(lx,ly))

    if 0 < shoot_timer < 0.12:
        t = 1.0 - shoot_timer/0.12
        gs5 = pygame.Surface((int(20*S),int(20*S)),pygame.SRCALPHA)
        pygame.draw.circle(gs5,(*_NEON_C,int(50*t)),(int(10*S),int(10*S)),int(9*S*t))
        surf.blit(gs5,(aim_sh[0]-int(10*S), aim_sh[1]-int(10*S)))

def draw_weapon_arm(surf, cx, cy, pivot_x, pivot_y, facing_right=True):
    S  = _SCALE
    ex = int(cx+(pivot_x-cx)*0.55)
    ey = int(cy+(pivot_y-cy)*0.55+int(S))
    _capsule(surf,(int(cx),int(cy)),(ex,ey),
             max(2,int(0.85*S)),max(2,int(0.72*S)),_ARM_L)
    _capsule(surf,(ex,ey),(int(pivot_x),int(pivot_y)),
             max(2,int(0.72*S)),max(2,int(0.60*S)),_ARM_M)
    pygame.draw.circle(surf,_ARM_RIM,(ex,ey),max(2,int(0.72*S)))
    pygame.draw.circle(surf,_NEON_C,(int(pivot_x),int(pivot_y)),max(2,int(0.60*S)),1)