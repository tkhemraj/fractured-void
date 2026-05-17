"""
Procedural art library for Fractured Void.
Ships drawn with layered polygon shading, specular highlights, panel detail.
Light source: upper-left. All sizes in half-height pixels.
"""
import math
import pygame

# ── Palette ───────────────────────────────────────────────────────────────
BLACK        = (0,   0,   0)
SPACE_BG     = (2,   3,   10)
METAL_DARK   = (15,  20,  18)
METAL_MID    = (38,  50,  44)
METAL_LIGHT  = (68,  90,  76)
METAL_SHINE  = (130, 160, 140)
HUD_GREEN    = (60,  220, 80)
HUD_GREEN_D  = (25,  90,  35)
HUD_AMBER    = (220, 160, 40)
HUD_RED      = (220, 55,  40)
HUD_CYAN     = (60,  220, 220)
HUD_BLUE     = (60,  140, 255)
HUD_DIM      = (28,  55,  32)
HUD_WHITE    = (195, 210, 200)
COCKPIT_GLASS = (40, 80, 120, 180)
RIVET_COLOR  = (50,  65,  55)

FACTION_COLORS = {
    "apex_syndicate":   (220, 60,  40),
    "helix_commerce":   (60,  180, 100),
    "ironveil_trading": (160, 130, 70),
    "drift_cartel":     (180, 80,  220),
    "the_remnant":      (80,  160, 220),
    "ghost_fleet":      (100, 220, 220),
}


# ── Color math ────────────────────────────────────────────────────────────
def _shade(color: tuple, factor: float) -> tuple:
    return tuple(max(0, min(255, int(c * factor))) for c in color[:3])

def _add(color: tuple, delta: int) -> tuple:
    return tuple(max(0, min(255, c + delta)) for c in color[:3])

def _blend(c1: tuple, c2: tuple, t: float) -> tuple:
    return tuple(int(a + (b - a) * t) for a, b in zip(c1[:3], c2[:3]))

def _tint(color: tuple, factor: float) -> tuple:
    return _shade(color, factor)


# ── Rotation helper ───────────────────────────────────────────────────────
def _pt(cx: float, cy: float, angle_deg: float, dx: float, dy: float) -> tuple:
    a = math.radians(angle_deg)
    cos_a, sin_a = math.cos(a), math.sin(a)
    return (dx * cos_a - dy * sin_a + cx, dx * sin_a + dy * cos_a + cy)

def _poly(cx, cy, angle, pts_local, s):
    return [_pt(cx, cy, angle, dx * s, dy * s) for dx, dy in pts_local]

def _ipt(p):
    return (int(p[0]), int(p[1]))

def _ipoly(pts):
    return [_ipt(p) for p in pts]


# ── Glow helpers ──────────────────────────────────────────────────────────
def draw_glow_circle(surf: pygame.Surface, color: tuple, cx: int, cy: int,
                     r: int, layers: int = 5) -> None:
    for i in range(layers, 0, -1):
        alpha = int(55 * i / layers)
        radius = r + (layers - i) * 4
        glow = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, color + (alpha,), (radius + 2, radius + 2), radius)
        surf.blit(glow, (cx - radius - 2, cy - radius - 2))
    # Core
    pygame.draw.circle(surf, _add(color, 80), (cx, cy), max(1, r // 2))
    pygame.draw.circle(surf, color, (cx, cy), r)


def _engine_exhaust(surf, cx, cy, r, color, layers=5):
    """Realistic engine glow: outer cool halo → hot core."""
    halo = _blend(color, (20, 30, 80), 0.55)
    mid  = _blend(color, (255, 255, 255), 0.25)
    for i in range(layers, 0, -1):
        alpha = int(45 * i / layers)
        radius = r + (layers - i) * 5
        g = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(g, halo + (alpha,), (radius + 2, radius + 2), radius)
        surf.blit(g, (cx - radius - 2, cy - radius - 2))
    pygame.draw.circle(surf, mid, (cx, cy), r)
    pygame.draw.circle(surf, (240, 250, 255), (cx, cy), max(1, r // 3))


def draw_glow_line(surf: pygame.Surface, color: tuple, p1: tuple, p2: tuple,
                   width: int = 1, glow: int = 3) -> None:
    for i in range(glow, 0, -1):
        alpha = int(70 * i / glow)
        gl = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.line(gl, color + (alpha,), p1, p2, width + i * 2)
        surf.blit(gl)
    pygame.draw.line(surf, color, p1, p2, width)


def glow_text(surf: pygame.Surface, font: pygame.font.Font, text: str,
              color: tuple, pos: tuple, glow_color: tuple | None = None, passes: int = 4) -> None:
    gcolor = glow_color or tuple(min(255, c // 3) for c in color)
    for i in range(passes, 0, -1):
        alpha = int(150 * i / passes)
        rendered = font.render(text, True, gcolor)
        rendered.set_alpha(alpha)
        for dx, dy in [(-i, 0), (i, 0), (0, -i), (0, i), (-i, -i), (i, i)]:
            surf.blit(rendered, (pos[0] + dx, pos[1] + dy))
    surf.blit(font.render(text, True, color), pos)


def draw_panel(surf: pygame.Surface, x: int, y: int, w: int, h: int,
               title: str = "", font: pygame.font.Font | None = None,
               border_color: tuple = HUD_GREEN, bg: tuple = (4, 10, 6)) -> None:
    pygame.draw.rect(surf, bg, (x, y, w, h))
    # Inner bevel
    pygame.draw.rect(surf, _shade(bg, 0.6), (x + 1, y + 1, w - 2, h - 2), 1)
    pygame.draw.rect(surf, border_color, (x, y, w, h), 1)
    corner = 10
    c = border_color
    for cx2, cy2, dx, dy in [(x, y, 1, 1), (x+w, y, -1, 1), (x, y+h, 1, -1), (x+w, y+h, -1, -1)]:
        pygame.draw.line(surf, c, (cx2, cy2), (cx2 + dx * corner, cy2), 2)
        pygame.draw.line(surf, c, (cx2, cy2), (cx2, cy2 + dy * corner), 2)
    if title and font:
        bg2 = pygame.Surface((font.size(title)[0] + 8, font.get_height()), pygame.SRCALPHA)
        bg2.fill(bg + (255,))
        surf.blit(bg2, (x + 6, y - font.get_height() // 2))
        surf.blit(font.render(title, True, border_color), (x + 8, y - font.get_height() // 2))


def bar(surf: pygame.Surface, x: int, y: int, w: int, h: int, pct: float,
        fill_color: tuple, bg: tuple = (6, 14, 8), border: bool = True) -> None:
    pct = max(0.0, min(1.0, pct))
    pygame.draw.rect(surf, bg, (x, y, w, h))
    fw = int(w * pct)
    if fw > 0:
        pygame.draw.rect(surf, fill_color, (x, y, fw, h))
        # Bright highlight top strip
        pygame.draw.rect(surf, _add(fill_color, 60), (x, y, fw, max(1, h // 3)))
        # Dim bottom strip (shadow)
        pygame.draw.rect(surf, _shade(fill_color, 0.6), (x, y + h - max(1, h // 4), fw, max(1, h // 4)))
    if border:
        pygame.draw.rect(surf, _shade(fill_color, 0.5), (x, y, w, h), 1)


def health_color(pct: float) -> tuple:
    if pct > 0.55:
        return HUD_GREEN
    elif pct > 0.28:
        return HUD_AMBER
    return HUD_RED


def draw_rivet_strip(surf: pygame.Surface, x: int, y: int, length: int,
                     horizontal: bool = True, spacing: int = 16) -> None:
    n = max(0, length // spacing)
    for i in range(n):
        rx = x + i * spacing if horizontal else x
        ry = y if horizontal else y + i * spacing
        pygame.draw.circle(surf, RIVET_COLOR, (rx, ry), 2)
        pygame.draw.circle(surf, METAL_SHINE, (rx - 1, ry - 1), 1)


# ── Panel line drawing ────────────────────────────────────────────────────
def _panel_line(surf, cx, cy, angle, ax, ay, bx, by, s, color):
    p1 = _pt(cx, cy, angle, ax * s, ay * s)
    p2 = _pt(cx, cy, angle, bx * s, by * s)
    pygame.draw.line(surf, color, _ipt(p1), _ipt(p2), 1)


def _fill_poly(surf, pts, color):
    if len(pts) >= 3:
        pygame.draw.polygon(surf, color, _ipoly(pts))


def _outline_poly(surf, pts, color, width=1):
    if len(pts) >= 3:
        pygame.draw.polygon(surf, color, _ipoly(pts), width)


# ── SHIP DRAW FUNCTIONS ───────────────────────────────────────────────────

def draw_ship(surf: pygame.Surface, ship_id: str, cx: float, cy: float,
              size: float, base_color: tuple, angle_deg: float = 0,
              engine_glow: bool = True) -> None:
    fn = _SHIP_DRAW.get(ship_id, _draw_generic)
    fn(surf, cx, cy, size, base_color, angle_deg, engine_glow)


def _draw_generic(surf, cx, cy, s, color, angle, glow):
    mid   = _shade(color, 0.75)
    light = _add(color, 40)
    pts = [(-0.55, 0.4), (0, -1.0), (0.55, 0.4), (0.18, 0.1), (-0.18, 0.1)]
    body = [_pt(cx, cy, angle, dx * s, dy * s) for dx, dy in pts]
    _fill_poly(surf, body, mid)
    _outline_poly(surf, body, light, 1)


def _draw_scout_marauder(surf, cx, cy, s, color, angle, glow):
    """Delta-wing interceptor — sharp, fast, with twin engine nacelles."""
    # Lighting: source is upper-left
    lit   = _add(color, 55)
    mid   = _shade(color, 0.80)
    dark  = _shade(color, 0.42)
    shadow= _shade(color, 0.28)
    spec  = _add(color, 120)

    # ── Main delta wing body ──
    wing = [(-0.88, 0.62), (0, -1.10), (0.88, 0.62),
            (0.38, 0.30), (0.10, 0.60), (-0.10, 0.60), (-0.38, 0.30)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in wing], mid)

    # Left wing top-lit face
    left_wing = [(-0.88, 0.62), (0, -1.10), (-0.10, 0.60), (-0.38, 0.30)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in left_wing], lit)

    # Right wing shadow face
    right_wing = [(0, -1.10), (0.88, 0.62), (0.38, 0.30), (0.10, 0.60)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in right_wing], dark)

    # ── Central spine ──
    spine = [(-0.12, -0.55), (0.12, -0.55), (0.09, 0.55), (-0.09, 0.55)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in spine], _shade(color, 0.35))

    # Spine ridge highlight
    p1 = _pt(cx, cy, angle, -0.02*s, -1.0*s)
    p2 = _pt(cx, cy, angle, -0.02*s,  0.55*s)
    pygame.draw.line(surf, spec, _ipt(p1), _ipt(p2), 1)

    # ── Panel detail lines ──
    panel_dark = _shade(color, 0.45)
    for dy_frac in [-0.40, -0.10, 0.20]:
        _panel_line(surf, cx, cy, angle, -0.75, dy_frac, -0.14, dy_frac, s, panel_dark)
        _panel_line(surf, cx, cy, angle, 0.14, dy_frac, 0.75, dy_frac, s, panel_dark)

    # Wing-to-body join seam
    _panel_line(surf, cx, cy, angle, -0.38, 0.30, -0.10, 0.60, s, panel_dark)
    _panel_line(surf, cx, cy, angle,  0.38, 0.30,  0.10, 0.60, s, panel_dark)

    # ── Weapon pylons under wings ──
    for side in [-1, 1]:
        pylon = [(0.55*side, -0.05), (0.68*side, -0.05),
                 (0.72*side,  0.32), (0.50*side,  0.35)]
        _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in pylon], shadow)
        # Gun barrel
        p1 = _pt(cx, cy, angle, 0.65*side*s, -0.05*s)
        p2 = _pt(cx, cy, angle, 0.65*side*s, -0.42*s)
        pygame.draw.line(surf, _shade(color, 0.65), _ipt(p1), _ipt(p2), 2)
        # Gun tip flash
        tip = _pt(cx, cy, angle, 0.65*side*s, -0.42*s)
        pygame.draw.circle(surf, _add(color, 80), _ipt(tip), max(1, int(s*0.04)))

    # ── Cockpit canopy ──
    cockpit = [(0, -1.05), (0.11, -0.75), (0.09, -0.35), (-0.09, -0.35), (-0.11, -0.75)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in cockpit], (30, 70, 130))
    # Glass highlight
    gl = [(0, -1.02), (0.08, -0.78), (0.05, -0.55)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in gl], (120, 180, 255))
    _outline_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in cockpit],
                  (100, 160, 255), 1)

    # ── Outer wing silhouette highlight ──
    outer = [(-0.88, 0.62), (0, -1.10), (0.88, 0.62)]
    _outline_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in outer],
                  _add(color, 35), 1)

    # ── Engines ──
    if glow:
        for ex_dx in [-0.24, 0.24]:
            ep = _pt(cx, cy, angle, ex_dx*s, 0.62*s)
            r = max(2, int(s * 0.11))
            _engine_exhaust(surf, int(ep[0]), int(ep[1]), r, (90, 150, 255), 4)


def _draw_cinder_pact(surf, cx, cy, s, color, angle, glow):
    """Battered freighter — asymmetric panels, cargo pods, heavy patching."""
    lit   = _add(color, 45)
    mid   = _shade(color, 0.72)
    dark  = _shade(color, 0.45)
    vdark = _shade(color, 0.28)

    # ── Main hull block ──
    hull_pts = [(-0.40, -0.80), (0.40, -0.80), (0.50, -0.50),
                (0.52, 0.30), (0.42, 0.78), (-0.42, 0.78),
                (-0.52, 0.30), (-0.50, -0.50)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in hull_pts], mid)

    # Top-lit face (upper portion of hull)
    top_face = [(-0.40, -0.80), (0.40, -0.80), (0.50, -0.50), (-0.50, -0.50)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in top_face], lit)

    # Left shadow face
    left_face = [(-0.52, 0.30), (-0.50, -0.50), (-0.40, -0.80),
                 (-0.42, -0.60), (-0.44, 0.20)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in left_face], dark)

    # ── Hull panel lines (wear and modular plating) ──
    panel_c = _shade(color, 0.38)
    for dy_f in [-0.50, -0.15, 0.22, 0.58]:
        _panel_line(surf, cx, cy, angle, -0.50, dy_f, 0.50, dy_f, s, panel_c)
    _panel_line(surf, cx, cy, angle, -0.18, -0.80, -0.18, 0.78, s, panel_c)
    _panel_line(surf, cx, cy, angle,  0.18, -0.80,  0.18, 0.78, s, panel_c)

    # ── Port-side cargo pod (left) ──
    lpod = [(-0.52, -0.12), (-0.74, -0.05), (-0.78, 0.46), (-0.55, 0.52), (-0.42, 0.48)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in lpod], vdark)
    _outline_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in lpod], dark, 1)
    # Pod panel
    _panel_line(surf, cx, cy, angle, -0.74, 0.10, -0.74, 0.42, s, _shade(color, 0.22))
    _panel_line(surf, cx, cy, angle, -0.60, 0.10, -0.60, 0.42, s, _shade(color, 0.22))

    # ── Starboard cargo pod (right, larger — asymmetric) ──
    rpod = [(0.52, -0.20), (0.76, -0.12), (0.82, 0.40), (0.60, 0.55), (0.42, 0.48)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in rpod], dark)
    _outline_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in rpod], mid, 1)
    _panel_line(surf, cx, cy, angle, 0.76, 0.05, 0.76, 0.38, s, _shade(color, 0.30))

    # ── Bridge tower ──
    bridge = [(-0.20, -0.80), (0.20, -0.80), (0.16, -1.10), (-0.16, -1.10)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in bridge], _add(mid, 15))
    # Bridge windows
    for wx in [-0.10, 0, 0.10]:
        wp = _pt(cx, cy, angle, wx*s, -0.95*s)
        pygame.draw.rect(surf, (30, 80, 140),
                         (int(wp[0])-2, int(wp[1])-2, 4, 6))
        pygame.draw.rect(surf, (80, 160, 220),
                         (int(wp[0])-1, int(wp[1])-2, 2, 2))

    # ── Sensor mast ──
    sm1 = _pt(cx, cy, angle, 0, -1.10*s)
    sm2 = _pt(cx, cy, angle, 0, -1.30*s)
    pygame.draw.line(surf, _shade(color, 0.6), _ipt(sm1), _ipt(sm2), 1)
    dish_c = _pt(cx, cy, angle, 0, -1.28*s)
    pygame.draw.circle(surf, _add(color, 30), _ipt(dish_c), max(1, int(s*0.06)))

    # ── Hull outline and specular edge ──
    _outline_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in hull_pts],
                  _add(color, 25), 1)
    # Top edge specular
    tl = _pt(cx, cy, angle, -0.40*s, -0.80*s)
    tr = _pt(cx, cy, angle,  0.40*s, -0.80*s)
    pygame.draw.line(surf, _add(color, 80), _ipt(tl), _ipt(tr), 2)

    # ── Engines ──
    if glow:
        for ex_dx, ex_r in [(-0.28, 0.14), (0.28, 0.14), (0.0, 0.10)]:
            ep = _pt(cx, cy, angle, ex_dx*s, 0.76*s)
            r = max(2, int(s * ex_r))
            _engine_exhaust(surf, int(ep[0]), int(ep[1]), r, (70, 130, 255), 5)


def _draw_merchant_hauler(surf, cx, cy, s, color, angle, glow):
    """Massive container hauler — modular cargo sections, brutally functional."""
    lit  = _add(color, 40)
    mid  = _shade(color, 0.65)
    dark = _shade(color, 0.38)

    # ── Outer hull ──
    hull = [(-0.10, -0.95), (0.10, -0.95), (0.60, -0.65),
            (0.68, 0.38), (0.55, 0.90), (-0.55, 0.90),
            (-0.68, 0.38), (-0.60, -0.65)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in hull], mid)

    # Top lit face
    top = [(-0.10, -0.95), (0.10, -0.95), (0.60, -0.65), (-0.60, -0.65)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in top], lit)

    # Left shadow
    left = [(-0.68, 0.38), (-0.60, -0.65), (-0.10, -0.95), (-0.12, -0.70), (-0.65, 0.30)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in left], dark)

    # ── Cargo container grid ──
    cg = _shade(color, 0.42)
    cg_light = _shade(color, 0.55)
    rows = [(-0.35, 0.25), (-0.02, 0.25), (-0.35, 0.55), (-0.02, 0.55)]
    col_w, row_h = 0.30, 0.26
    for col_dx, row_dy in rows:
        cpts = [(col_dx, row_dy), (col_dx + col_w, row_dy),
                (col_dx + col_w, row_dy + row_h), (col_dx, row_dy + row_h)]
        _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in cpts], cg)
        _outline_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in cpts], cg_light, 1)
        # Container label stripe
        stripe_pts = [(col_dx + 0.02, row_dy + 0.04), (col_dx + col_w - 0.02, row_dy + 0.04),
                      (col_dx + col_w - 0.02, row_dy + 0.10), (col_dx + 0.02, row_dy + 0.10)]
        _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in stripe_pts],
                   _blend(color, (220, 180, 50), 0.4))

    # Additional container row at top
    top_cont = [(-0.35, -0.62), (0.35, -0.62), (0.35, -0.38), (-0.35, -0.38)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in top_cont], _shade(color, 0.50))
    _outline_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in top_cont], cg_light, 1)

    # ── Bridge / command module (top) ──
    bridge = [(-0.15, -0.95), (0.15, -0.95), (0.12, -1.20), (-0.12, -1.20)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in bridge], _add(mid, 20))
    for wx in [-0.06, 0.06]:
        wp = _pt(cx, cy, angle, wx*s, -1.06*s)
        pygame.draw.rect(surf, (25, 70, 130), (int(wp[0])-2, int(wp[1])-2, 5, 7))
        pygame.draw.rect(surf, (70, 150, 220), (int(wp[0])-1, int(wp[1])-2, 2, 3))

    # ── Side thrusters ──
    for side, flip in [(-1, 1), (1, 1)]:
        thr = [(0.62*side, 0.0), (0.80*side, 0.05),
               (0.82*side, 0.25), (0.65*side, 0.30)]
        _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in thr], dark)
        _outline_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in thr], mid, 1)

    _outline_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in hull], _add(color, 20), 1)

    if glow:
        for ex_dx in [-0.35, 0, 0.35]:
            ep = _pt(cx, cy, angle, ex_dx*s, 0.88*s)
            _engine_exhaust(surf, int(ep[0]), int(ep[1]), max(2, int(s*0.12)), (80, 130, 230), 4)


def _draw_ironveil_corvette(surf, cx, cy, s, color, angle, glow):
    """Angular corporate corvette — hard geometry, weapon rails, corporate precision."""
    lit   = _add(color, 50)
    mid   = _shade(color, 0.72)
    dark  = _shade(color, 0.42)
    accent = _blend(color, (200, 170, 60), 0.35)

    # ── Main angular hull ──
    hull = [(0, -1.05), (0.28, -0.72), (0.58, -0.05),
            (0.54, 0.62), (0.22, 0.88), (-0.22, 0.88),
            (-0.54, 0.62), (-0.58, -0.05), (-0.28, -0.72)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in hull], mid)

    # Top-lit face
    top_face = [(0, -1.05), (0.28, -0.72), (0, -0.40), (-0.28, -0.72)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in top_face], lit)

    # Right shadow
    right_face = [(0.28, -0.72), (0.58, -0.05), (0.54, 0.62), (0.22, 0.88),
                  (0.16, 0.60), (0.48, 0.50), (0.50, -0.05)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in right_face], dark)

    # ── Central dorsal ridge ──
    ridge = [(-0.06, -1.0), (0.06, -1.0), (0.05, 0.80), (-0.05, 0.80)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in ridge], _shade(color, 0.32))
    # Ridge highlight
    rp1 = _pt(cx, cy, angle, -0.01*s, -0.98*s)
    rp2 = _pt(cx, cy, angle, -0.01*s,  0.78*s)
    pygame.draw.line(surf, _add(color, 60), _ipt(rp1), _ipt(rp2), 1)

    # ── Wing fins (swept, with weapon rails) ──
    for side in [-1, 1]:
        fin = [(0.58*side, -0.05), (0.92*side, 0.08), (0.88*side, 0.55), (0.54*side, 0.62)]
        _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in fin], dark)
        _outline_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in fin], lit, 1)

        # Rail stripe on fin
        rail_pts = [(0.62*side, 0.0), (0.88*side, 0.1), (0.86*side, 0.18), (0.62*side, 0.08)]
        _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in rail_pts], accent)

        # Weapon mount at wingtip
        wp = _pt(cx, cy, angle, 0.88*side*s, 0.30*s)
        pygame.draw.circle(surf, _shade(color, 0.50), _ipt(wp), max(2, int(s*0.06)))
        pygame.draw.circle(surf, accent, _ipt(wp), max(1, int(s*0.04)))

    # ── Panel detail ──
    panel_c = _shade(color, 0.40)
    for dy_f in [-0.60, -0.20, 0.20, 0.60]:
        _panel_line(surf, cx, cy, angle, -0.50, dy_f, 0.50, dy_f, s, panel_c)
    _panel_line(surf, cx, cy, angle, -0.22, -0.72, -0.22, 0.88, s, panel_c)
    _panel_line(surf, cx, cy, angle,  0.22, -0.72,  0.22, 0.88, s, panel_c)

    # ── IronVeil corporate stripe ──
    stripe_pts = [(-0.50, 0.05), (0.50, 0.05), (0.50, 0.14), (-0.50, 0.14)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in stripe_pts], accent)

    _outline_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in hull], _add(color, 30), 1)
    # Specular edge
    tl = _pt(cx, cy, angle, -0.28*s, -0.72*s)
    tr = _pt(cx, cy, angle, 0*s, -1.05*s)
    pygame.draw.line(surf, _add(color, 90), _ipt(tl), _ipt(tr), 2)

    if glow:
        for ex_dx in [-0.22, 0.22]:
            ep = _pt(cx, cy, angle, ex_dx*s, 0.86*s)
            _engine_exhaust(surf, int(ep[0]), int(ep[1]), max(2, int(s*0.13)), (130, 180, 255), 4)


def _draw_apex_enforcer(surf, cx, cy, s, color, angle, glow):
    """Apex Syndicate attack craft — predatory, aggressive, weapon-heavy."""
    lit   = _add(color, 45)
    mid   = _shade(color, 0.65)
    dark  = _shade(color, 0.38)
    red   = (220, 60, 40)
    red_dim = (140, 30, 20)

    # ── Main predatory hull ──
    hull = [(0, -1.20), (0.20, -0.85), (0.65, -0.18),
            (0.68, 0.44), (0.32, 0.82), (0, 0.62),
            (-0.32, 0.82), (-0.68, 0.44), (-0.65, -0.18), (-0.20, -0.85)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in hull], mid)

    # Top lit face — swept nose
    nose = [(0, -1.20), (0.20, -0.85), (0, -0.42), (-0.20, -0.85)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in nose], lit)

    # Shadow right
    right_sh = [(0.20, -0.85), (0.65, -0.18), (0.68, 0.44), (0.32, 0.82),
                (0.28, 0.68), (0.62, 0.38), (0.60, -0.15)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in right_sh], dark)

    # ── Armored cheek panels ──
    for side in [-1, 1]:
        cheek = [(0.38*side, -0.40), (0.65*side, -0.18),
                 (0.68*side, 0.30), (0.40*side, 0.40)]
        _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in cheek], _shade(color, 0.50))
        _outline_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in cheek], red_dim, 1)

    # ── Weapon sponsons ──
    for side in [-1, 1]:
        spons = [(0.62*side, -0.25), (0.84*side, -0.18),
                 (0.88*side, 0.20), (0.66*side, 0.32)]
        _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in spons], dark)
        _outline_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in spons], red_dim, 1)
        # Twin gun barrels
        for barrel_offset in [-0.03, 0.03]:
            b_x = (0.80 + barrel_offset) * side
            b1 = _pt(cx, cy, angle, b_x*s, -0.20*s)
            b2 = _pt(cx, cy, angle, b_x*s, -0.62*s)
            pygame.draw.line(surf, _shade(red, 0.6), _ipt(b1), _ipt(b2), 1)
        # Muzzle glow
        mg = _pt(cx, cy, angle, 0.80*side*s, -0.62*s)
        pygame.draw.circle(surf, (255, 140, 80), _ipt(mg), max(1, int(s*0.04)))

    # ── Apex Syndicate red stripe ──
    stripe = [(-0.62, 0.10), (0.62, 0.10), (0.60, 0.20), (-0.60, 0.20)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in stripe], red_dim)
    # Red accent line
    ra1 = _pt(cx, cy, angle, -0.60*s, 0.10*s)
    ra2 = _pt(cx, cy, angle,  0.60*s, 0.10*s)
    pygame.draw.line(surf, red, _ipt(ra1), _ipt(ra2), 1)

    # ── Narrow armored cockpit ──
    cpit = [(0, -1.15), (0.10, -0.88), (0.08, -0.48), (-0.08, -0.48), (-0.10, -0.88)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in cpit], (60, 12, 12))
    _outline_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in cpit], red, 1)
    # Red glass glint
    gl = [(0, -1.12), (0.06, -0.92), (0.04, -0.72)]
    _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in gl], (200, 80, 60))

    # Panel lines
    panel_c = _shade(color, 0.38)
    for dy_f in [-0.65, -0.30, 0.10, 0.45]:
        _panel_line(surf, cx, cy, angle, -0.55, dy_f, 0.55, dy_f, s, panel_c)

    _outline_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in hull], lit, 1)
    # Specular nose edge
    n1 = _pt(cx, cy, angle, 0*s, -1.20*s)
    n2 = _pt(cx, cy, angle, -0.20*s, -0.85*s)
    pygame.draw.line(surf, _add(color, 100), _ipt(n1), _ipt(n2), 2)

    if glow:
        for ex_dx in [-0.20, 0, 0.20]:
            ep = _pt(cx, cy, angle, ex_dx*s, 0.80*s)
            _engine_exhaust(surf, int(ep[0]), int(ep[1]), max(2, int(s*0.12)), (255, 100, 50), 5)


def _draw_ghost_wraith(surf, cx, cy, s, color, angle, glow):
    """Ghost Fleet alien vessel — organic, bio-mechanical, bioluminescent."""
    c     = color
    dark_c = _shade(c, 0.32)
    mid_c  = _shade(c, 0.58)
    glow_c = _add(c, 60)

    # ── Primary bio-hull form (asymmetric swept) ──
    form1 = [(0, -1.25), (0.72, 0.05), (0.92, 0.58), (0.28, 0.92), (-0.08, 0.62)]
    form2 = [(0, -1.25), (-0.72, 0.05), (-0.92, 0.58), (-0.28, 0.92), (0.08, 0.62)]

    # Shadow underlayer
    for form in [form1, form2]:
        _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in form], dark_c)

    # Inner organic surface with translucency simulation
    inner1 = [(0, -1.25), (0.48, 0.02), (0.60, 0.48), (0.18, 0.80), (0, 0.55)]
    inner2 = [(0, -1.25), (-0.48, 0.02), (-0.60, 0.48), (-0.18, 0.80), (0, 0.55)]
    for inner in [inner1, inner2]:
        _fill_poly(surf, [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in inner], mid_c)

    # ── Bioluminescent vein network ──
    vein_c_a = c + (120,)
    vein_c_b = _add(c, 80) + (80,)
    vein_data = [
        # (x1,y1) → (x2,y2)
        (0, -1.0,  0.45, -0.05),
        (0, -1.0, -0.45, -0.05),
        (0.45, -0.05, 0.72, 0.40),
        (-0.45, -0.05, -0.72, 0.40),
        (0.45, -0.05, 0.10, 0.55),
        (-0.45, -0.05, -0.10, 0.55),
        (0, -0.60, 0.30, 0.10),
        (0, -0.60, -0.30, 0.10),
    ]
    vein_surf = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for x1, y1, x2, y2 in vein_data:
        p1 = _pt(cx, cy, angle, x1*s, y1*s)
        p2 = _pt(cx, cy, angle, x2*s, y2*s)
        pygame.draw.line(vein_surf, vein_c_a, _ipt(p1), _ipt(p2), 2)
    surf.blit(vein_surf, (0, 0))

    # Thinner inner veins
    vein_surf2 = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for x1, y1, x2, y2 in vein_data[2:]:
        p1 = _pt(cx, cy, angle, x1*s*0.6, y1*s*0.6)
        p2 = _pt(cx, cy, angle, x2*s*0.6, y2*s*0.6)
        pygame.draw.line(vein_surf2, vein_c_b, _ipt(p1), _ipt(p2), 1)
    surf.blit(vein_surf2, (0, 0))

    # ── Glowing sensor orbs ──
    orb_positions = [(0, -0.85), (0.55, 0.18), (-0.55, 0.18), (0.28, 0.62), (-0.28, 0.62)]
    for dx, dy in orb_positions:
        op = _pt(cx, cy, angle, dx*s, dy*s)
        r = max(2, int(s * 0.08))
        draw_glow_circle(surf, c, int(op[0]), int(op[1]), r, layers=3)

    # ── Central bioluminescent core ──
    if glow:
        core = _pt(cx, cy, angle, 0, -0.10*s)
        core_r = max(4, int(s * 0.22))
        for i in range(5, 0, -1):
            alpha = int(35 * i / 5)
            r = core_r + i * 4
            g_surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(g_surf, c + (alpha,), (r + 2, r + 2), r)
            surf.blit(g_surf, (int(core[0]) - r - 2, int(core[1]) - r - 2))
        pygame.draw.circle(surf, glow_c, _ipt(core), core_r)
        pygame.draw.circle(surf, (255, 255, 255), _ipt(core), max(1, core_r // 3))

    # ── Glowing outer edges ──
    edge_surf = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for form, alpha in [(form1, 140), (form2, 100)]:
        pts_rot = [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in form]
        for i in range(len(pts_rot)):
            p1 = pts_rot[i]
            p2 = pts_rot[(i + 1) % len(pts_rot)]
            pygame.draw.line(edge_surf, c + (alpha,), _ipt(p1), _ipt(p2), 2)
    surf.blit(edge_surf, (0, 0))

    # Secondary engine glow nodes at rear
    if glow:
        for ex_dx in [(0.60, 0.55), (-0.60, 0.55), (0, 0.85)]:
            ep = _pt(cx, cy, angle, ex_dx[0]*s, ex_dx[1]*s)
            _engine_exhaust(surf, int(ep[0]), int(ep[1]), max(2, int(s*0.10)), c, 3)


_SHIP_DRAW = {
    "scout_marauder":    _draw_scout_marauder,
    "cinder_pact":       _draw_cinder_pact,
    "merchant_hauler":   _draw_merchant_hauler,
    "ironveil_corvette": _draw_ironveil_corvette,
    "apex_enforcer":     _draw_apex_enforcer,
    "ghost_wraith":      _draw_ghost_wraith,
}


# ── Faction logos ─────────────────────────────────────────────────────────
def draw_faction_logo(surf: pygame.Surface, faction_id: str,
                      cx: int, cy: int, size: int) -> None:
    color = FACTION_COLORS.get(faction_id, METAL_MID)
    s = size
    dark = _shade(color, 0.3)

    if faction_id == "apex_syndicate":
        # Hawk/triangle with targeting reticule
        pts = [(cx, cy - s), (cx + s, cy + s // 2), (cx - s, cy + s // 2)]
        pygame.draw.polygon(surf, dark, pts)
        pygame.draw.polygon(surf, color, pts, 2)
        pygame.draw.line(surf, color, (cx, cy - s // 2), (cx, cy + s // 2), 1)
        pygame.draw.line(surf, color, (cx - s // 2, cy + s // 4), (cx + s // 2, cy + s // 4), 1)
        pygame.draw.circle(surf, _add(color, 60), (cx, cy - s // 4), s // 6)

    elif faction_id == "helix_commerce":
        # Double-ring with nodes
        pygame.draw.circle(surf, dark, (cx, cy), s, 0)
        pygame.draw.circle(surf, color, (cx, cy), s, 2)
        pygame.draw.circle(surf, _shade(color, 0.5), (cx, cy), s // 2, 1)
        for i in range(6):
            a = i * math.pi / 3
            px = int(cx + s * 0.72 * math.cos(a))
            py = int(cy + s * 0.72 * math.sin(a))
            pygame.draw.circle(surf, color, (px, py), max(2, s // 5))
            pygame.draw.circle(surf, _add(color, 60), (px, py), max(1, s // 8))

    elif faction_id == "ironveil_trading":
        # Cog / gear
        n_teeth = 8
        for i in range(n_teeth):
            a1 = i * 2 * math.pi / n_teeth
            a2 = (i + 0.45) * 2 * math.pi / n_teeth
            for inner_r, outer_r in [(s * 0.65, s)]:
                p = [(cx + int(outer_r * math.cos(a1)), cy + int(outer_r * math.sin(a1))),
                     (cx + int(outer_r * math.cos(a2)), cy + int(outer_r * math.sin(a2))),
                     (cx + int(inner_r * math.cos(a2)), cy + int(inner_r * math.sin(a2))),
                     (cx + int(inner_r * math.cos(a1)), cy + int(inner_r * math.sin(a1)))]
                pygame.draw.polygon(surf, dark, p)
                pygame.draw.polygon(surf, color, p, 1)
        pygame.draw.circle(surf, dark, (cx, cy), s // 3)
        pygame.draw.circle(surf, color, (cx, cy), s // 3, 2)
        pygame.draw.circle(surf, _add(color, 40), (cx, cy), s // 6)

    elif faction_id == "drift_cartel":
        # Comet / blazing star
        for i in range(5):
            a = i * 2 * math.pi / 5 - math.pi / 2
            ox = int(cx + s * math.cos(a))
            oy = int(cy + s * math.sin(a))
            pygame.draw.line(surf, color, (cx, cy), (ox, oy), 2)
            pygame.draw.circle(surf, _add(color, 80), (ox, oy), max(1, s // 6))
        pygame.draw.circle(surf, dark, (cx, cy), s // 3)
        pygame.draw.circle(surf, _add(color, 60), (cx, cy), s // 3, 0)

    elif faction_id == "the_remnant":
        # Broken ring / uprising fist
        pygame.draw.circle(surf, dark, (cx, cy), s, 0)
        pygame.draw.circle(surf, color, (cx, cy), s, 2)
        # Break in the ring (top)
        pygame.draw.rect(surf, (2, 3, 10), (cx - s // 4, cy - s - 2, s // 2, s // 3 + 2))
        # Inner symbol
        for a in [math.pi * 0.5, math.pi * 1.5]:
            px = int(cx + s * 0.5 * math.cos(a))
            py = int(cy + s * 0.5 * math.sin(a))
            pygame.draw.circle(surf, color, (px, py), max(2, s // 5), 2)
        pygame.draw.line(surf, color, (cx, cy - s // 2), (cx, cy + s // 2), 2)

    elif faction_id == "ghost_fleet":
        # Pulsing eye
        for r_add in range(5, 0, -1):
            alpha = 30 * r_add // 5
            g = pygame.Surface(((s + r_add * 4) * 2, (s + r_add * 4) * 2), pygame.SRCALPHA)
            pygame.draw.circle(g, color + (alpha,),
                               (s + r_add * 4, s + r_add * 4), s + r_add * 3)
            surf.blit(g, (cx - s - r_add * 4, cy - s - r_add * 4))
        pygame.draw.circle(surf, dark, (cx, cy), s, 0)
        pygame.draw.circle(surf, color, (cx, cy), s, 1)
        pygame.draw.circle(surf, _add(color, 80), (cx, cy), s // 3)
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy), max(1, s // 6))


# ── Scanline overlay ──────────────────────────────────────────────────────
_scanline_cache: dict = {}

def get_scanline_overlay(width: int, height: int, alpha: int = 18) -> pygame.Surface:
    key = (width, height, alpha)
    if key not in _scanline_cache:
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        for y in range(0, height, 2):
            pygame.draw.line(surf, (0, 0, 0, alpha), (0, y), (width, y), 1)
        _scanline_cache[key] = surf
    return _scanline_cache[key]


# ── Vignette overlay ──────────────────────────────────────────────────────
_vignette_cache: dict = {}

def get_vignette(width: int, height: int) -> pygame.Surface:
    key = (width, height)
    if key not in _vignette_cache:
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        cx2, cy2 = width // 2, height // 2
        max_r = math.sqrt(cx2**2 + cy2**2)
        for y in range(0, height, 2):
            for x in range(0, width, 4):
                d = math.sqrt((x - cx2)**2 + (y - cy2)**2)
                alpha = int(200 * (d / max_r) ** 2.2)
                if alpha > 0:
                    pygame.draw.rect(surf, (0, 0, 0, min(200, alpha)), (x, y, 4, 2))
        _vignette_cache[key] = surf
    return _vignette_cache[key]
