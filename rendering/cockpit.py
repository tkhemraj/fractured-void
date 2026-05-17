"""
Pre-rendered cockpit frame for Wing Commander-style combat view.
Thick industrial hull, beveled console panels, dramatic structural geometry.
Built once at startup, blitted every frame (SRCALPHA transparent viewport).
"""
import math
import random
import pygame
from rendering.art import (
    METAL_DARK, METAL_MID, METAL_LIGHT, METAL_SHINE,
    HUD_GREEN, HUD_GREEN_D, HUD_AMBER, HUD_RED, HUD_DIM,
    draw_rivet_strip, bar, _shade, _add, _blend,
)

# Viewport extents as fraction of screen
VP_LEFT   = 0.075
VP_RIGHT  = 0.925
VP_TOP    = 0.065
VP_BOTTOM = 0.725


def _bevel_rect(surf, x, y, w, h, base, depth=4):
    """3D beveled rectangle — looks raised from the surface."""
    lit  = _add(base, 45)
    drk  = _shade(base, 0.55)
    vdrk = _shade(base, 0.35)
    # Fill
    pygame.draw.rect(surf, base, (x, y, w, h))
    # Top bevel
    pygame.draw.polygon(surf, lit,  [(x, y), (x+w, y), (x+w-depth, y+depth), (x+depth, y+depth)])
    # Left bevel
    pygame.draw.polygon(surf, lit,  [(x, y), (x, y+h), (x+depth, y+h-depth), (x+depth, y+depth)])
    # Bottom bevel
    pygame.draw.polygon(surf, drk,  [(x, y+h), (x+w, y+h), (x+w-depth, y+h-depth), (x+depth, y+h-depth)])
    # Right bevel
    pygame.draw.polygon(surf, vdrk, [(x+w, y), (x+w, y+h), (x+w-depth, y+h-depth), (x+w-depth, y+depth)])


def _inset_rect(surf, x, y, w, h, base, depth=3):
    """3D inset rectangle — looks recessed into the surface."""
    lit  = _add(base, 35)
    drk  = _shade(base, 0.55)
    pygame.draw.rect(surf, _shade(base, 0.7), (x, y, w, h))
    pygame.draw.polygon(surf, drk, [(x, y), (x+w, y), (x+w-depth, y+depth), (x+depth, y+depth)])
    pygame.draw.polygon(surf, drk, [(x, y), (x, y+h), (x+depth, y+h-depth), (x+depth, y+depth)])
    pygame.draw.polygon(surf, lit, [(x, y+h), (x+w, y+h), (x+w-depth, y+h-depth), (x+depth, y+h-depth)])
    pygame.draw.polygon(surf, lit, [(x+w, y), (x+w, y+h), (x+w-depth, y+h-depth), (x+w-depth, y+depth)])


def _hex_bolt(surf, cx, cy, r, base):
    """Hex-head bolt detail."""
    pts = [(cx + int(r * math.cos(math.pi / 6 + i * math.pi / 3)),
            cy + int(r * math.sin(math.pi / 6 + i * math.pi / 3))) for i in range(6)]
    pygame.draw.polygon(surf, _shade(base, 0.55), pts)
    pygame.draw.polygon(surf, _add(base, 20), pts, 1)
    pygame.draw.circle(surf, _shade(base, 0.40), (cx, cy), max(1, r // 2))


def _warning_light(surf, cx, cy, color, on=True):
    """Indicator light with bezel and glow."""
    bezel_r = 8
    pygame.draw.circle(surf, (15, 15, 15), (cx, cy), bezel_r + 2)
    pygame.draw.circle(surf, (35, 35, 35), (cx, cy), bezel_r + 2, 1)
    if on:
        glow = pygame.Surface(((bezel_r + 6) * 2, (bezel_r + 6) * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, color + (60,), (bezel_r + 6, bezel_r + 6), bezel_r + 6)
        surf.blit(glow, (cx - bezel_r - 6, cy - bezel_r - 6))
        pygame.draw.circle(surf, _shade(color, 0.6), (cx, cy), bezel_r)
        pygame.draw.circle(surf, color, (cx, cy), bezel_r - 2)
        # Highlight
        pygame.draw.circle(surf, _add(color, 100), (cx - 2, cy - 2), max(1, bezel_r // 3))
    else:
        pygame.draw.circle(surf, _shade(color, 0.2), (cx, cy), bezel_r - 2)


def _panel_screen(surf, x, y, w, h, label, font, line_color, text_color):
    """Small CRT-style data panel with label and scanlines."""
    # Screen bezel
    _inset_rect(surf, x, y, w, h, (10, 14, 12), depth=3)
    screen = pygame.Rect(x + 3, y + 3, w - 6, h - 6)
    # Screen fill
    pygame.draw.rect(surf, (4, 12, 7), screen)
    # Scanlines
    for sy in range(screen.y, screen.y + screen.h, 2):
        pygame.draw.line(surf, (0, 0, 0), (screen.x, sy), (screen.x + screen.w, sy), 1)
    # Data lines (faked)
    for i, dy in enumerate(range(4, h - 16, max(4, (h - 20) // 4))):
        bar_w = int((w - 12) * (0.4 + 0.5 * ((i * 73 + 17) % 100) / 100))
        pygame.draw.rect(surf, line_color, (x + 5, y + 4 + dy, bar_w, 2))
    # Label
    if font:
        lbl = font.render(label, True, text_color)
        surf.blit(lbl, (x + 4, y + h - lbl.get_height() - 3))


def _diagonal_hatch(surf, x, y, w, h, color, spacing=8):
    """Diagonal hatch pattern for industrial texture."""
    for i in range(0, w + h, spacing):
        x1 = x + max(0, i - h)
        y1 = y + min(h, i)
        x2 = x + min(w, i)
        y2 = y + max(0, i - w)
        if x1 <= x2:
            pygame.draw.line(surf, color, (x1, y1), (x2, y2), 1)


def build_cockpit(width: int, height: int) -> tuple[pygame.Surface, dict]:
    """
    Returns (cockpit_surface, viewport_rect).
    SRCALPHA surface — viewport area is transparent.
    """
    rng = random.Random(13)

    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    W, H = width, height

    vp_x  = int(W * VP_LEFT)
    vp_y  = int(H * VP_TOP)
    vp_w  = int(W * (VP_RIGHT - VP_LEFT))
    vp_h  = int(H * (VP_BOTTOM - VP_TOP))
    vp_x2 = vp_x + vp_w
    vp_y2 = vp_y + vp_h
    console_h = H - vp_y2

    frame_base  = (22, 30, 26)
    frame_mid   = (32, 42, 36)
    console_base = (18, 25, 21)
    strut_base  = (25, 34, 28)

    # ── TOP HEADER BAR ────────────────────────────────────────────────────
    _bevel_rect(surf, 0, 0, W, vp_y + 2, frame_base, depth=5)

    # Inner header recess
    _inset_rect(surf, vp_x + 20, 6, vp_w - 40, vp_y - 8, frame_mid, depth=3)

    # Heading strip — center element
    hstrip_w = vp_w // 3
    hstrip_x = W // 2 - hstrip_w // 2
    _inset_rect(surf, hstrip_x, 3, hstrip_w, vp_y - 4, (10, 16, 12), depth=2)
    # Tick marks on heading strip
    for i in range(11):
        tx = hstrip_x + i * hstrip_w // 10
        th = vp_y - 6 if i == 5 else vp_y - 10
        pygame.draw.line(surf, HUD_GREEN, (tx, th), (tx, vp_y - 4), 1)
    # Center heading marker
    pygame.draw.polygon(surf, HUD_GREEN, [
        (W // 2, vp_y - 3),
        (W // 2 - 5, vp_y - 11),
        (W // 2 + 5, vp_y - 11),
    ])

    # Warning light clusters — left side of header
    light_specs = [(200, 55, 40, True), (200, 160, 40, True), (60, 200, 80, False)]
    for i, (r, g, b, on) in enumerate(light_specs):
        lx = vp_x + 25 + i * 28
        _warning_light(surf, lx, vp_y // 2, (r, g, b), on)

    # Warning light clusters — right side
    light_specs_r = [(60, 200, 80, True), (200, 160, 40, False), (200, 55, 40, False)]
    for i, (r, g, b, on) in enumerate(light_specs_r):
        lx = vp_x2 - 25 - i * 28
        _warning_light(surf, lx, vp_y // 2, (r, g, b), on)

    # Bolts on header
    for bx in [vp_x + 8, W // 2 - 4, vp_x2 - 8]:
        _hex_bolt(surf, bx, vp_y // 2, 5, frame_base)

    # ── LEFT STRUT ────────────────────────────────────────────────────────
    _bevel_rect(surf, 0, vp_y - 2, vp_x + 4, vp_h + 4, strut_base, depth=6)

    # Structural ribs on left strut
    for rib_y in range(vp_y + 20, vp_y2 - 20, 30):
        pygame.draw.line(surf, _add(strut_base, 20), (4, rib_y), (vp_x - 2, rib_y), 1)
        pygame.draw.line(surf, _shade(strut_base, 0.7), (4, rib_y + 1), (vp_x - 2, rib_y + 1), 1)

    # Diagonal cross brace on left strut
    pygame.draw.line(surf, _add(strut_base, 15),
                     (6, vp_y + 10), (vp_x - 4, vp_y + vp_h // 2), 2)
    pygame.draw.line(surf, _add(strut_base, 15),
                     (6, vp_y2 - 10), (vp_x - 4, vp_y + vp_h // 2), 2)

    # Mini data panel on left strut
    if vp_x > 50:
        try:
            font_tiny = pygame.font.SysFont("monospace", 9)
            _panel_screen(surf, 5, vp_y + 20, vp_x - 10, 55, "NAV", font_tiny,
                          HUD_GREEN_D, HUD_DIM)
            _panel_screen(surf, 5, vp_y + 85, vp_x - 10, 45, "SYS", font_tiny,
                          HUD_AMBER, HUD_DIM)
        except Exception:
            pass

    # Bolt strip on left strut edge
    for by in range(vp_y + 15, vp_y2 - 15, 40):
        _hex_bolt(surf, vp_x - 6, by, 4, strut_base)

    # ── RIGHT STRUT ───────────────────────────────────────────────────────
    _bevel_rect(surf, vp_x2 - 4, vp_y - 2, W - vp_x2 + 4, vp_h + 4, strut_base, depth=6)

    for rib_y in range(vp_y + 20, vp_y2 - 20, 30):
        pygame.draw.line(surf, _add(strut_base, 20), (vp_x2 + 2, rib_y), (W - 4, rib_y), 1)
        pygame.draw.line(surf, _shade(strut_base, 0.7), (vp_x2 + 2, rib_y + 1), (W - 4, rib_y + 1), 1)

    pygame.draw.line(surf, _add(strut_base, 15),
                     (W - 6, vp_y + 10), (vp_x2 + 4, vp_y + vp_h // 2), 2)
    pygame.draw.line(surf, _add(strut_base, 15),
                     (W - 6, vp_y2 - 10), (vp_x2 + 4, vp_y + vp_h // 2), 2)

    if W - vp_x2 > 50:
        try:
            font_tiny = pygame.font.SysFont("monospace", 9)
            _panel_screen(surf, vp_x2 + 5, vp_y + 20, W - vp_x2 - 10, 55, "COM", font_tiny,
                          (60, 140, 220), HUD_DIM)
            _panel_screen(surf, vp_x2 + 5, vp_y + 85, W - vp_x2 - 10, 45, "TGT", font_tiny,
                          (220, 80, 60), HUD_DIM)
        except Exception:
            pass

    for by in range(vp_y + 15, vp_y2 - 15, 40):
        _hex_bolt(surf, vp_x2 + 6, by, 4, strut_base)

    # ── VIEWPORT FRAME ────────────────────────────────────────────────────
    # Multi-layer glow ring around viewport
    glow_col = HUD_GREEN
    for i in range(8, 0, -1):
        alpha = int(90 * i / 8)
        g = pygame.Surface((vp_w + i * 4, vp_h + i * 4), pygame.SRCALPHA)
        pygame.draw.rect(g, glow_col + (alpha,), (0, 0, vp_w + i * 4, vp_h + i * 4), 2)
        surf.blit(g, (vp_x - i * 2, vp_y - i * 2))

    # Viewport inner frame — thick beveled
    frame_thickness = 4
    for t in range(frame_thickness, 0, -1):
        shade = int(60 + 30 * t / frame_thickness)
        col = (shade // 2, shade, shade // 2)
        pygame.draw.rect(surf, col,
                         (vp_x - t, vp_y - t, vp_w + t * 2, vp_h + t * 2), 1)

    # Corner diagonal braces — much thicker and more dramatic
    brace_len = min(100, int(vp_w * 0.09))
    brace_c   = _shade(strut_base, 1.4)
    brace_hi  = _add(strut_base, 60)
    corners = [
        (vp_x, vp_y, 1, 1),
        (vp_x2, vp_y, -1, 1),
        (vp_x, vp_y2, 1, -1),
        (vp_x2, vp_y2, -1, -1),
    ]
    for (bx, by, dx, dy) in corners:
        pts = [(bx, by), (bx + dx * brace_len, by), (bx, by + dy * brace_len)]
        pygame.draw.polygon(surf, brace_c, pts)
        pygame.draw.polygon(surf, brace_hi, pts, 2)
        # Corner bolt
        _hex_bolt(surf, bx + dx * 8, by + dy * 8, 5, frame_base)

    # HUD glass tint over viewport (very subtle)
    glass = pygame.Surface((vp_w, vp_h), pygame.SRCALPHA)
    pygame.draw.rect(glass, (15, 45, 22, 8), (0, 0, vp_w, vp_h))
    # Corner vignette darkening inside viewport
    for corner_x, corner_y in [(0, 0), (vp_w, 0), (0, vp_h), (vp_w, vp_h)]:
        for r in range(80, 0, -12):
            pygame.draw.circle(glass, (0, 0, 0, 4), (corner_x, corner_y), r * 2)
    surf.blit(glass, (vp_x, vp_y))

    # ── BOTTOM CONSOLE ────────────────────────────────────────────────────
    # Main console plate
    _bevel_rect(surf, 0, vp_y2 - 3, W, console_h + 3, console_base, depth=6)

    # Console top accent line — bright green glow strip
    for i in range(4):
        alpha = 120 - i * 25
        g_line = pygame.Surface((W, 2), pygame.SRCALPHA)
        g_line.fill(HUD_GREEN + (alpha,))
        surf.blit(g_line, (0, vp_y2 - i - 1))

    # Rivet strip along console top
    draw_rivet_strip(surf, 10, vp_y2 + 6, W - 20, True, 30)

    # Three panel housings with bevel
    panel_margin = 12
    third_w = (W - panel_margin * 4) // 3

    for i, (px, label) in enumerate([
        (panel_margin, "SHIELDS"),
        (panel_margin * 2 + third_w, "RADAR"),
        (panel_margin * 3 + third_w * 2, "WEAPONS"),
    ]):
        panel_y = vp_y2 + 10
        panel_h = console_h - 18
        _bevel_rect(surf, px, panel_y, third_w, panel_h, _shade(console_base, 0.85), depth=5)
        # Inset screen area inside panel
        _inset_rect(surf, px + 5, panel_y + 5, third_w - 10, panel_h - 10,
                    (8, 13, 10), depth=3)
        # Diagonal hatch texture behind inset (subtle)
        _diagonal_hatch(surf, px + 6, panel_y + 6, third_w - 12, panel_h - 12,
                        (10, 15, 12), spacing=12)
        # Bottom rivet strip
        draw_rivet_strip(surf, px + 8, panel_y + panel_h - 8, third_w - 16, True, 18)
        # Panel corner bolts
        for bx2, by2 in [(px + 8, panel_y + 8), (px + third_w - 8, panel_y + 8),
                         (px + 8, panel_y + panel_h - 8), (px + third_w - 8, panel_y + panel_h - 8)]:
            _hex_bolt(surf, bx2, by2, 5, console_base)

    # ── Divider ridges between panels ──
    for div_x in [panel_margin + third_w + panel_margin // 2,
                  panel_margin * 2 + third_w * 2 + panel_margin // 2]:
        pygame.draw.rect(surf, METAL_SHINE, (div_x, vp_y2 + 8, 3, console_h - 16))
        pygame.draw.rect(surf, _shade(METAL_SHINE, 0.4), (div_x + 3, vp_y2 + 8, 1, console_h - 16))

    # ── Wear, scratches, and grime ────────────────────────────────────────
    sc_surf = pygame.Surface((W, H), pygame.SRCALPHA)
    for _ in range(18):
        sx = rng.randint(0, W)
        sy = rng.randint(vp_y, H)
        ex = sx + rng.randint(-30, 30)
        ey = sy + rng.randint(-4, 4)
        alpha = rng.randint(15, 45)
        pygame.draw.line(sc_surf, (200, 220, 200, alpha), (sx, sy), (ex, ey), 1)
    surf.blit(sc_surf, (0, 0))

    # ── Top strut rivet strips ──
    draw_rivet_strip(surf, vp_x + 15, vp_y - 5, vp_w - 30, True, 45)
    draw_rivet_strip(surf, vp_x + 15, vp_y2 + 2, vp_w - 30, True, 45)

    vp_rect = {"x": vp_x, "y": vp_y, "w": vp_w, "h": vp_h}
    return surf, vp_rect
