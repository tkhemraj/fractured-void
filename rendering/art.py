"""
Procedural art library for Fractured Void.
All graphics are drawn with pygame primitives — no external assets.
Central palette, ship silhouettes, UI components, glow effects.
"""
import math
import pygame

# ── Palette ──────────────────────────────────────────────────────────────────
BLACK       = (0,   0,   0)
SPACE_BG    = (2,   3,   10)
METAL_DARK  = (18,  22,  20)
METAL_MID   = (38,  50,  44)
METAL_LIGHT = (65,  85,  72)
METAL_SHINE = (120, 150, 130)
HUD_GREEN   = (60,  220, 80)
HUD_GREEN_D = (30,  100, 40)
HUD_AMBER   = (220, 160, 40)
HUD_RED     = (220, 55,  40)
HUD_CYAN    = (60,  220, 220)
HUD_BLUE    = (60,  140, 255)
HUD_DIM     = (28,  55,  32)
HUD_WHITE   = (195, 210, 200)
COCKPIT_GLASS = (40, 80, 120, 180)
RIVET_COLOR = (50,  65,  55)

FACTION_COLORS = {
    "apex_syndicate":   (220, 60,  40),
    "helix_commerce":   (60,  180, 100),
    "ironveil_trading": (160, 130, 70),
    "drift_cartel":     (180, 80,  220),
    "the_remnant":      (80,  160, 220),
    "ghost_fleet":      (100, 220, 220),
}


# ── Glow helper ──────────────────────────────────────────────────────────────
def draw_glow_circle(surf: pygame.Surface, color: tuple, cx: int, cy: int,
                     r: int, layers: int = 5) -> None:
    for i in range(layers, 0, -1):
        alpha = int(60 * i / layers)
        radius = r + (layers - i) * 3
        glow = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, color + (alpha,), (radius + 1, radius + 1), radius)
        surf.blit(glow, (cx - radius - 1, cy - radius - 1))
    pygame.draw.circle(surf, color, (cx, cy), r)


def draw_glow_line(surf: pygame.Surface, color: tuple, p1: tuple, p2: tuple,
                   width: int = 1, glow: int = 3) -> None:
    for i in range(glow, 0, -1):
        alpha = int(80 * i / glow)
        gl = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.line(gl, color + (alpha,), p1, p2, width + i * 2)
        surf.blit(gl)
    pygame.draw.line(surf, color, p1, p2, width)


def glow_text(surf: pygame.Surface, font: pygame.font.Font, text: str,
              color: tuple, pos: tuple, glow_color: tuple | None = None, passes: int = 3) -> None:
    gcolor = glow_color or tuple(min(255, c + 40) for c in color)
    for i in range(passes, 0, -1):
        alpha = int(120 * i / passes)
        rendered = font.render(text, True, gcolor)
        rendered.set_alpha(alpha)
        for dx, dy in [(-i, 0), (i, 0), (0, -i), (0, i), (-i, -i), (i, i)]:
            surf.blit(rendered, (pos[0] + dx, pos[1] + dy))
    surf.blit(font.render(text, True, color), pos)


def draw_panel(surf: pygame.Surface, x: int, y: int, w: int, h: int,
               title: str = "", font: pygame.font.Font | None = None,
               border_color: tuple = HUD_GREEN, bg: tuple = (4, 10, 6)) -> None:
    pygame.draw.rect(surf, bg, (x, y, w, h))
    pygame.draw.rect(surf, border_color, (x, y, w, h), 1)
    # Corner accents
    corner = 8
    c = border_color
    for cx2, cy2, dx, dy in [(x, y, 1, 1), (x+w, y, -1, 1), (x, y+h, 1, -1), (x+w, y+h, -1, -1)]:
        pygame.draw.line(surf, c, (cx2, cy2), (cx2 + dx * corner, cy2), 2)
        pygame.draw.line(surf, c, (cx2, cy2), (cx2, cy2 + dy * corner), 2)
    if title and font:
        lbl = font.render(title, True, border_color)
        surf.blit(lbl, (x + 8, y - lbl.get_height() // 2))
        pygame.draw.rect(surf, bg, (x + 6, y - lbl.get_height() // 2, lbl.get_width() + 4, lbl.get_height()))
        surf.blit(lbl, (x + 8, y - lbl.get_height() // 2))


def bar(surf: pygame.Surface, x: int, y: int, w: int, h: int, pct: float,
        fill_color: tuple, bg: tuple = (8, 18, 10), border: bool = True) -> None:
    pct = max(0.0, min(1.0, pct))
    pygame.draw.rect(surf, bg, (x, y, w, h))
    fw = int(w * pct)
    if fw > 0:
        # gradient: bright at left, slightly darker at right
        pygame.draw.rect(surf, fill_color, (x, y, fw, h))
        highlight = tuple(min(255, c + 50) for c in fill_color)
        pygame.draw.rect(surf, highlight, (x, y, fw, max(1, h // 3)))
    if border:
        pygame.draw.rect(surf, tuple(c // 2 for c in fill_color), (x, y, w, h), 1)


def health_color(pct: float) -> tuple:
    if pct > 0.55:
        return HUD_GREEN
    elif pct > 0.28:
        return HUD_AMBER
    return HUD_RED


# ── Rivet strip ──────────────────────────────────────────────────────────────
def draw_rivet_strip(surf: pygame.Surface, x: int, y: int, length: int,
                     horizontal: bool = True, spacing: int = 16) -> None:
    n = length // spacing
    for i in range(n):
        rx = x + i * spacing if horizontal else x
        ry = y if horizontal else y + i * spacing
        pygame.draw.circle(surf, RIVET_COLOR, (rx, ry), 2)
        pygame.draw.circle(surf, METAL_SHINE, (rx - 1, ry - 1), 1)


# ── Ship art ─────────────────────────────────────────────────────────────────
def _tint(color: tuple, factor: float) -> tuple:
    return tuple(max(0, min(255, int(c * factor))) for c in color[:3])


def _pt(cx: float, cy: float, angle_deg: float, dx: float, dy: float) -> tuple:
    """Rotate point (dx,dy) around (cx,cy) by angle_deg."""
    a = math.radians(angle_deg)
    cos_a, sin_a = math.cos(a), math.sin(a)
    rx = dx * cos_a - dy * sin_a + cx
    ry = dx * sin_a + dy * cos_a + cy
    return (rx, ry)


def draw_ship(surf: pygame.Surface, ship_id: str, cx: float, cy: float,
              size: float, base_color: tuple, angle_deg: float = 0,
              engine_glow: bool = True) -> None:
    """Draw a detailed ship sprite. size is half-height in pixels."""
    fn = _SHIP_DRAW.get(ship_id, _draw_generic)
    fn(surf, cx, cy, size, base_color, angle_deg, engine_glow)


def _draw_generic(surf, cx, cy, s, color, angle, glow):
    pts = [_pt(cx, cy, angle, dx * s, dy * s) for dx, dy in [
        (0, -1.0), (0.55, 0.4), (0.2, 0.1), (-0.2, 0.1), (-0.55, 0.4)
    ]]
    pygame.draw.polygon(surf, _tint(color, 0.8), pts)
    pygame.draw.polygon(surf, color, pts, 1)


def _draw_scout_marauder(surf, cx, cy, s, color, angle, glow):
    dark  = _tint(color, 0.55)
    mid   = _tint(color, 0.75)
    light = _tint(color, 1.15)

    # Delta wing body
    body = [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in [
        (0,     -1.05),
        (0.85,   0.55),
        (0.35,   0.30),
        (0.12,   0.55),
        (-0.12,  0.55),
        (-0.35,  0.30),
        (-0.85,  0.55),
    ]]
    pygame.draw.polygon(surf, mid, body)

    # Central spine
    spine = [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in [
        (0.14, -0.55), (0.14, 0.55), (-0.14, 0.55), (-0.14, -0.55)
    ]]
    pygame.draw.polygon(surf, dark, spine)

    # Cockpit blister
    cpit = [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in [
        (0, -0.75), (0.14, -0.55), (0.10, -0.30), (-0.10, -0.30), (-0.14, -0.55)
    ]]
    pygame.draw.polygon(surf, (60, 110, 160), cpit)
    pygame.draw.polygon(surf, (100, 180, 255), cpit, 1)

    # Wing leading edges
    pygame.draw.polygon(surf, light, body, 1)

    # Engine exhausts
    if glow:
        for ex_dx in [-0.22, 0.22]:
            ep = _pt(cx, cy, angle, ex_dx*s, 0.55*s)
            r = max(2, int(s * 0.12))
            draw_glow_circle(surf, (80, 140, 255), int(ep[0]), int(ep[1]), r, layers=3)


def _draw_cinder_pact(surf, cx, cy, s, color, angle, glow):
    dark  = _tint(color, 0.50)
    mid   = _tint(color, 0.70)
    light = _tint(color, 0.95)

    # Main hull — boxy freighter shape
    hull = [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in [
        (0,     -0.80),
        (0.42,  -0.55),
        (0.48,   0.30),
        (0.38,   0.75),
        (-0.38,  0.75),
        (-0.48,  0.30),
        (-0.42, -0.55),
    ]]
    pygame.draw.polygon(surf, mid, hull)

    # Cargo pods on sides
    for side in [-1, 1]:
        pod = [_pt(cx, cy, angle, dx*s*side, dy*s) for dx, dy in [
            (0.42, -0.20),
            (0.68, -0.10),
            (0.72,  0.45),
            (0.42,  0.55),
        ]]
        pygame.draw.polygon(surf, dark, pod)
        pygame.draw.polygon(surf, mid, pod, 1)

    # Cockpit / bridge
    bridge = [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in [
        (0,    -0.80),
        (0.20, -0.55),
        (0.14, -0.30),
        (-0.14,-0.30),
        (-0.20,-0.55),
    ]]
    pygame.draw.polygon(surf, (40, 70, 100), bridge)
    pygame.draw.polygon(surf, (80, 140, 200), bridge, 1)

    # Hull outline
    pygame.draw.polygon(surf, light, hull, 1)

    # Panel detail lines
    for dy_frac in [-0.10, 0.25]:
        p1 = _pt(cx, cy, angle, -0.40*s, dy_frac*s)
        p2 = _pt(cx, cy, angle,  0.40*s, dy_frac*s)
        pygame.draw.line(surf, dark, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), 1)

    # Engines
    if glow:
        for ex_dx in [-0.28, 0.28]:
            ep = _pt(cx, cy, angle, ex_dx*s, 0.72*s)
            r = max(2, int(s * 0.14))
            draw_glow_circle(surf, (60, 120, 255), int(ep[0]), int(ep[1]), r, layers=4)
        # Center engine
        ep = _pt(cx, cy, angle, 0, 0.75*s)
        draw_glow_circle(surf, (100, 160, 255), int(ep[0]), int(ep[1]), max(2, int(s*0.10)), 3)


def _draw_merchant_hauler(surf, cx, cy, s, color, angle, glow):
    dark = _tint(color, 0.45)
    mid  = _tint(color, 0.65)
    light = _tint(color, 0.90)

    # Massive boxy hull
    hull = [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in [
        (0.10, -0.90), (-0.10, -0.90),
        (-0.55, -0.60), (-0.65, 0.40), (-0.50, 0.90),
        (0.50, 0.90), (0.65, 0.40), (0.55, -0.60),
    ]]
    pygame.draw.polygon(surf, mid, hull)

    # Cargo containers stacked
    for row_dy, row_h in [(-0.30, 0.28), (0.10, 0.28), (0.50, 0.24)]:
        for col_dx, col_w in [(-0.35, 0.28), (0.07, 0.28)]:
            rect_pts = [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in [
                (col_dx, row_dy), (col_dx+col_w, row_dy),
                (col_dx+col_w, row_dy+row_h), (col_dx, row_dy+row_h)
            ]]
            pygame.draw.polygon(surf, dark, rect_pts)
            pygame.draw.polygon(surf, mid, rect_pts, 1)

    pygame.draw.polygon(surf, light, hull, 1)

    if glow:
        for ex_dx in [-0.35, 0, 0.35]:
            ep = _pt(cx, cy, angle, ex_dx*s, 0.88*s)
            r = max(2, int(s * 0.13))
            draw_glow_circle(surf, (80, 130, 230), int(ep[0]), int(ep[1]), r, 3)


def _draw_ironveil_corvette(surf, cx, cy, s, color, angle, glow):
    dark  = _tint(color, 0.50)
    mid   = _tint(color, 0.72)
    light = _tint(color, 1.0)

    # Angular corvette hull
    hull = [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in [
        (0,    -1.0),
        (0.30, -0.70),
        (0.55,  0.0),
        (0.50,  0.65),
        (0.20,  0.85),
        (-0.20, 0.85),
        (-0.50, 0.65),
        (-0.55, 0.0),
        (-0.30,-0.70),
    ]]
    pygame.draw.polygon(surf, mid, hull)

    # Wing fins
    for side in [-1, 1]:
        fin = [_pt(cx, cy, angle, dx*s*side, dy*s) for dx, dy in [
            (0.55, 0.0), (0.85, 0.10), (0.80, 0.55), (0.50, 0.65)
        ]]
        pygame.draw.polygon(surf, dark, fin)
        pygame.draw.polygon(surf, light, fin, 1)

    # Central ridge
    ridge = [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in [
        (0.08, -0.9), (0.08, 0.65), (-0.08, 0.65), (-0.08, -0.9)
    ]]
    pygame.draw.polygon(surf, _tint(color, 0.40), ridge)

    pygame.draw.polygon(surf, light, hull, 1)

    if glow:
        for ex_dx in [-0.25, 0.25]:
            ep = _pt(cx, cy, angle, ex_dx*s, 0.85*s)
            draw_glow_circle(surf, (120, 170, 255), int(ep[0]), int(ep[1]), max(2, int(s*0.14)), 4)


def _draw_apex_enforcer(surf, cx, cy, s, color, angle, glow):
    dark  = _tint(color, 0.40)
    mid   = _tint(color, 0.65)
    light = (255, 120, 80)

    # Aggressive forward-swept design
    hull = [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in [
        (0,    -1.15),
        (0.22, -0.80),
        (0.60, -0.20),
        (0.65,  0.45),
        (0.30,  0.80),
        (0,     0.60),
        (-0.30, 0.80),
        (-0.65, 0.45),
        (-0.60,-0.20),
        (-0.22,-0.80),
    ]]
    pygame.draw.polygon(surf, mid, hull)

    # Weapon pods
    for side in [-1, 1]:
        pod = [_pt(cx, cy, angle, dx*s*side, dy*s) for dx, dy in [
            (0.60, -0.30), (0.80, -0.20), (0.82, 0.20), (0.65, 0.35)
        ]]
        pygame.draw.polygon(surf, dark, pod)
        pygame.draw.polygon(surf, (200, 80, 60), pod, 1)
        # Gun barrel
        barrel_s = _pt(cx, cy, angle, 0.78*s*side, -0.25*s)
        barrel_e = _pt(cx, cy, angle, 0.78*s*side, -0.55*s)
        pygame.draw.line(surf, (200, 100, 80),
                        (int(barrel_s[0]), int(barrel_s[1])),
                        (int(barrel_e[0]), int(barrel_e[1])), 2)

    # Cockpit (narrow, predatory)
    cpit = [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in [
        (0, -1.0), (0.12, -0.70), (0.10, -0.40), (-0.10, -0.40), (-0.12, -0.70)
    ]]
    pygame.draw.polygon(surf, (80, 20, 20), cpit)
    pygame.draw.polygon(surf, (200, 60, 60), cpit, 1)

    pygame.draw.polygon(surf, light, hull, 1)

    if glow:
        for ex_dx in [-0.22, 0, 0.22]:
            ep = _pt(cx, cy, angle, ex_dx*s, 0.78*s)
            draw_glow_circle(surf, (255, 100, 60), int(ep[0]), int(ep[1]), max(2, int(s*0.13)), 4)


def _draw_ghost_wraith(surf, cx, cy, s, color, angle, glow):
    c = color  # (100, 220, 220)
    dark_c = _tint(c, 0.4)
    mid_c  = _tint(c, 0.7)

    # Organic, asymmetric alien shape — two overlapping swept forms
    form1 = [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in [
        (0,     -1.20),
        (0.70,   0.0),
        (0.90,   0.55),
        (0.30,   0.90),
        (-0.10,  0.60),
        (-0.20, -0.30),
    ]]
    form2 = [_pt(cx, cy, angle, dx*s, dy*s) for dx, dy in [
        (0,      -1.20),
        (-0.70,   0.0),
        (-0.90,   0.55),
        (-0.30,   0.90),
        (0.10,    0.60),
        (0.20,   -0.30),
    ]]
    pygame.draw.polygon(surf, dark_c, form1)
    pygame.draw.polygon(surf, dark_c, form2)

    # Glowing core in center
    if glow:
        core = _pt(cx, cy, angle, 0, -0.10*s)
        draw_glow_circle(surf, c, int(core[0]), int(core[1]), max(3, int(s*0.20)), 6)

    # Glowing edges
    for pts in [form1, form2]:
        for i in range(len(pts)):
            p1 = pts[i]
            p2 = pts[(i+1) % len(pts)]
            alpha = 160
            edge = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            pygame.draw.line(edge, c + (alpha,), (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), 2)
            surf.blit(edge)

    # Secondary glow nodes
    if glow:
        for dx, dy in [(0.60, 0.20), (-0.60, 0.20), (0, -0.80)]:
            ep = _pt(cx, cy, angle, dx*s, dy*s)
            draw_glow_circle(surf, c, int(ep[0]), int(ep[1]), max(2, int(s*0.10)), 3)


_SHIP_DRAW = {
    "scout_marauder":   _draw_scout_marauder,
    "cinder_pact":      _draw_cinder_pact,
    "merchant_hauler":  _draw_merchant_hauler,
    "ironveil_corvette":_draw_ironveil_corvette,
    "apex_enforcer":    _draw_apex_enforcer,
    "ghost_wraith":     _draw_ghost_wraith,
}


# ── Faction logo ──────────────────────────────────────────────────────────────
def draw_faction_logo(surf: pygame.Surface, faction_id: str, cx: int, cy: int, size: int) -> None:
    color = FACTION_COLORS.get(faction_id, METAL_MID)
    s = size
    if faction_id == "apex_syndicate":
        # Triangle with crosshair
        pts = [(cx, cy-s), (cx+s, cy+s//2), (cx-s, cy+s//2)]
        pygame.draw.polygon(surf, _tint(color, 0.3), pts)
        pygame.draw.polygon(surf, color, pts, 2)
        pygame.draw.line(surf, color, (cx, cy-s//2), (cx, cy+s//2), 1)
        pygame.draw.line(surf, color, (cx-s//2, cy+s//4), (cx+s//2, cy+s//4), 1)
    elif faction_id == "helix_commerce":
        # Double helix circle
        pygame.draw.circle(surf, _tint(color, 0.2), (cx, cy), s)
        pygame.draw.circle(surf, color, (cx, cy), s, 2)
        for i in range(6):
            a = i * math.pi / 3
            px = int(cx + s * 0.6 * math.cos(a))
            py = int(cy + s * 0.6 * math.sin(a))
            pygame.draw.circle(surf, color, (px, py), s // 5)
    elif faction_id == "drift_cartel":
        # Star/comet shape
        for i in range(5):
            a = i * 2 * math.pi / 5 - math.pi / 2
            ox = int(cx + s * math.cos(a))
            oy = int(cy + s * math.sin(a))
            pygame.draw.line(surf, color, (cx, cy), (ox, oy), 2)
        pygame.draw.circle(surf, color, (cx, cy), s // 3)
    elif faction_id == "the_remnant":
        # Broken chain / fist
        pygame.draw.circle(surf, _tint(color, 0.2), (cx, cy), s)
        pygame.draw.circle(surf, color, (cx, cy), s, 2)
        for a in [0, math.pi]:
            px = int(cx + s * 0.5 * math.cos(a))
            py = int(cy + s * 0.5 * math.sin(a))
            pygame.draw.circle(surf, color, (px, py), s // 4, 2)
    elif faction_id == "ghost_fleet":
        # Eye-like symbol
        for r_add in range(4, 0, -1):
            pygame.draw.circle(surf, color + (40 * r_add // 4,) if len(color) == 3 else color,
                               (cx, cy), s + r_add * 3, 1)
        pygame.draw.circle(surf, color, (cx, cy), s // 3)
    elif faction_id == "ironveil_trading":
        # Gear / cog outline
        n_teeth = 8
        for i in range(n_teeth):
            a1 = i * 2 * math.pi / n_teeth
            a2 = (i + 0.4) * 2 * math.pi / n_teeth
            p1 = (cx + int(s * math.cos(a1)), cy + int(s * math.sin(a1)))
            p2 = (cx + int(s * math.cos(a2)), cy + int(s * math.sin(a2)))
            p3 = (cx + int(s*0.7 * math.cos(a2)), cy + int(s*0.7 * math.sin(a2)))
            p4 = (cx + int(s*0.7 * math.cos(a1)), cy + int(s*0.7 * math.sin(a1)))
            pygame.draw.polygon(surf, _tint(color, 0.4), [p1, p2, p3, p4])
            pygame.draw.polygon(surf, color, [p1, p2, p3, p4], 1)
        pygame.draw.circle(surf, _tint(color, 0.3), (cx, cy), s // 3)
        pygame.draw.circle(surf, color, (cx, cy), s // 3, 2)


# ── Scanline overlay ──────────────────────────────────────────────────────────
_scanline_cache: dict[tuple, pygame.Surface] = {}

def get_scanline_overlay(width: int, height: int, alpha: int = 18) -> pygame.Surface:
    key = (width, height, alpha)
    if key not in _scanline_cache:
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        for y in range(0, height, 2):
            pygame.draw.line(surf, (0, 0, 0, alpha), (0, y), (width, y), 1)
        _scanline_cache[key] = surf
    return _scanline_cache[key]


# ── Vignette overlay ──────────────────────────────────────────────────────────
_vignette_cache: dict[tuple, pygame.Surface] = {}

def get_vignette(width: int, height: int) -> pygame.Surface:
    key = (width, height)
    if key not in _vignette_cache:
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        cx, cy = width // 2, height // 2
        max_r = math.sqrt(cx**2 + cy**2)
        for y in range(0, height, 2):
            for x in range(0, width, 4):
                d = math.sqrt((x - cx)**2 + (y - cy)**2)
                alpha = int(180 * (d / max_r) ** 2.5)
                if alpha > 0:
                    pygame.draw.rect(surf, (0, 0, 0, alpha), (x, y, 4, 2))
        _vignette_cache[key] = surf
    return _vignette_cache[key]
