"""
Pre-rendered cockpit frame for Wing Commander-style combat view.
Built once, blitted every frame. All drawn with pygame primitives.

The cockpit has:
- Structural frame (four beams + diagonal corner braces)
- Bottom instrument console (three panels: shields, nav, weapons)
- Side cheek panels with detail
- Viewport window frame with HUD glass tint
- Rivets, wear marks, warning lights
"""
import math
import pygame
from rendering.art import (
    METAL_DARK, METAL_MID, METAL_LIGHT, METAL_SHINE,
    HUD_GREEN, HUD_GREEN_D, HUD_AMBER, HUD_RED, HUD_DIM,
    draw_rivet_strip, bar,
)


# Viewport extents (percentage of screen)
VP_LEFT   = 0.075
VP_RIGHT  = 0.925
VP_TOP    = 0.065
VP_BOTTOM = 0.725


def _metal_rect(surf, x, y, w, h, base=(25, 32, 28)):
    """A metallic-looking filled rectangle with highlight edge."""
    pygame.draw.rect(surf, base, (x, y, w, h))
    light = tuple(min(255, c + 35) for c in base)
    dark  = tuple(max(0,   c - 15) for c in base)
    pygame.draw.line(surf, light, (x, y),         (x + w, y),         1)
    pygame.draw.line(surf, light, (x, y),         (x, y + h),         1)
    pygame.draw.line(surf, dark,  (x + w, y),     (x + w, y + h),     1)
    pygame.draw.line(surf, dark,  (x, y + h),     (x + w, y + h),     1)


def _scratches(surf, rng, x, y, w, h, n=8):
    for _ in range(n):
        sx = rng.randint(x, x + w)
        sy = rng.randint(y, y + h)
        ex = sx + rng.randint(-20, 20)
        ey = sy + rng.randint(-3, 3)
        alpha = rng.randint(20, 50)
        sc = pygame.Surface((abs(ex-sx)+2, 4), pygame.SRCALPHA)
        pygame.draw.line(sc, (180, 200, 180, alpha), (0, 2), (abs(ex-sx)+1, 2), 1)
        surf.blit(sc, (min(sx, ex), sy - 1))


def build_cockpit(width: int, height: int) -> tuple[pygame.Surface, dict]:
    """
    Returns (cockpit_surface, viewport_rect).
    cockpit_surface has SRCALPHA — the viewport area is transparent.
    viewport_rect = {'x', 'y', 'w', 'h'} in pixels.
    """
    import random
    rng = random.Random(7)

    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    W, H = width, height

    vp_x  = int(W * VP_LEFT)
    vp_y  = int(H * VP_TOP)
    vp_w  = int(W * (VP_RIGHT - VP_LEFT))
    vp_h  = int(H * (VP_BOTTOM - VP_TOP))
    vp_x2 = vp_x + vp_w
    vp_y2 = vp_y + vp_h

    console_h = H - vp_y2

    # ── Fill outer areas ──────────────────────────────────────────
    # Top beam
    _metal_rect(surf, 0, 0, W, vp_y + 2, (22, 28, 24))
    # Bottom console
    _metal_rect(surf, 0, vp_y2 - 2, W, console_h + 2, (18, 24, 20))
    # Left strut
    _metal_rect(surf, 0, vp_y, vp_x + 2, vp_h, (20, 26, 22))
    # Right strut
    _metal_rect(surf, vp_x2 - 2, vp_y, W - vp_x2 + 2, vp_h, (20, 26, 22))

    # ── Viewport inner edge glow ───────────────────────────────────
    for i in range(5):
        alpha = 80 - i * 14
        color = HUD_GREEN + (alpha,)
        pygame.draw.rect(surf, color, (vp_x - i - 1, vp_y - i - 1, vp_w + (i+1)*2, vp_h + (i+1)*2), 1)

    # ── HUD glass tint over viewport ──────────────────────────────
    glass = pygame.Surface((vp_w, vp_h), pygame.SRCALPHA)
    # Very subtle green tint and corner darkening
    pygame.draw.rect(glass, (20, 60, 30, 12), (0, 0, vp_w, vp_h))
    # Corner darkening
    for corner_x, corner_y in [(0, 0), (vp_w, 0), (0, vp_h), (vp_w, vp_h)]:
        for r in range(60, 0, -10):
            pygame.draw.circle(glass, (0, 0, 0, 5), (corner_x, corner_y), r * 2)
    surf.blit(glass, (vp_x, vp_y))

    # ── Corner diagonal braces ────────────────────────────────────
    brace_len = min(80, int(vp_w * 0.08))
    brace_color = (45, 60, 50)
    brace_high  = (70, 95, 78)
    # Top-left
    pts = [(vp_x, vp_y), (vp_x + brace_len, vp_y), (vp_x, vp_y + brace_len)]
    pygame.draw.polygon(surf, brace_color, pts)
    pygame.draw.polygon(surf, brace_high, pts, 1)
    # Top-right
    pts = [(vp_x2, vp_y), (vp_x2 - brace_len, vp_y), (vp_x2, vp_y + brace_len)]
    pygame.draw.polygon(surf, brace_color, pts)
    pygame.draw.polygon(surf, brace_high, pts, 1)
    # Bottom-left
    pts = [(vp_x, vp_y2), (vp_x + brace_len, vp_y2), (vp_x, vp_y2 - brace_len)]
    pygame.draw.polygon(surf, brace_color, pts)
    pygame.draw.polygon(surf, brace_high, pts, 1)
    # Bottom-right
    pts = [(vp_x2, vp_y2), (vp_x2 - brace_len, vp_y2), (vp_x2, vp_y2 - brace_len)]
    pygame.draw.polygon(surf, brace_color, pts)
    pygame.draw.polygon(surf, brace_high, pts, 1)

    # ── Side panel details ────────────────────────────────────────
    for side_x, flip in [(10, 1), (W - vp_x + 6, -1)]:
        panel_w = vp_x - 20
        if panel_w < 20:
            continue
        # Horizontal rib lines
        for rib_y in range(vp_y + 20, vp_y2 - 20, 28):
            pygame.draw.line(surf, METAL_LIGHT, (side_x, rib_y), (side_x + panel_w, rib_y), 1)
        # Rivets
        draw_rivet_strip(surf, side_x + 4, vp_y + 10, vp_h - 20, horizontal=False, spacing=28)

    # ── Structural cross-brace on struts ──────────────────────────
    brace_y = vp_y + vp_h // 2
    for sx, ex in [(6, vp_x - 4), (vp_x2 + 4, W - 6)]:
        pygame.draw.line(surf, METAL_LIGHT, (sx, brace_y), (ex, brace_y), 1)
        pygame.draw.line(surf, METAL_MID,   (sx, vp_y + 10), (ex, brace_y), 1)
        pygame.draw.line(surf, METAL_MID,   (sx, vp_y2 - 10), (ex, brace_y), 1)

    # ── Top bar content ────────────────────────────────────────────
    # Center heading strip
    hstrip_w = vp_w // 3
    hstrip_x = W // 2 - hstrip_w // 2
    pygame.draw.rect(surf, (12, 18, 14), (hstrip_x, 4, hstrip_w, vp_y - 6))
    pygame.draw.rect(surf, HUD_GREEN_D, (hstrip_x, 4, hstrip_w, vp_y - 6), 1)
    # Tick marks
    for i in range(9):
        tx = hstrip_x + (i + 1) * hstrip_w // 10
        h_tick = vp_y - 10 if i == 4 else vp_y - 14
        pygame.draw.line(surf, HUD_GREEN, (tx, h_tick), (tx, vp_y - 6), 1)

    # Warning lights (top bar sides)
    light_colors = [(200, 60, 40), (200, 160, 40), (60, 200, 80)]
    for i, lc in enumerate(light_colors):
        lx = vp_x + 20 + i * 22
        ly = vp_y // 2
        pygame.draw.circle(surf, (20, 20, 20), (lx, ly), 6)
        pygame.draw.circle(surf, lc, (lx, ly), 4)
        pygame.draw.circle(surf, tuple(min(255, c + 80) for c in lc), (lx - 1, ly - 1), 2)
    for i, lc in enumerate(reversed(light_colors)):
        lx = vp_x2 - 20 - i * 22
        ly = vp_y // 2
        pygame.draw.circle(surf, (20, 20, 20), (lx, ly), 6)
        pygame.draw.circle(surf, lc, (lx, ly), 4)
        pygame.draw.circle(surf, tuple(min(255, c + 80) for c in lc), (lx - 1, ly - 1), 2)

    # ── Bottom console ─────────────────────────────────────────────
    cy_console = vp_y2 + 4
    # Three panel sections
    panel_margin = 12
    third_w = (W - panel_margin * 4) // 3
    # Divider ridges
    for div_x in [panel_margin + third_w + panel_margin // 2,
                  panel_margin * 2 + third_w * 2 + panel_margin // 2]:
        pygame.draw.rect(surf, METAL_SHINE, (div_x, cy_console, 2, console_h - 8))

    # Left panel — shield diagram area
    _metal_rect(surf, panel_margin, cy_console + 4, third_w, console_h - 12, (16, 22, 18))
    draw_rivet_strip(surf, panel_margin + 4, cy_console + console_h - 14, third_w - 8, True, 20)

    # Center panel — radar area
    center_x = panel_margin * 2 + third_w
    _metal_rect(surf, center_x, cy_console + 4, third_w, console_h - 12, (14, 20, 16))
    draw_rivet_strip(surf, center_x + 4, cy_console + console_h - 14, third_w - 8, True, 20)

    # Right panel — weapons area
    right_x = panel_margin * 3 + third_w * 2
    _metal_rect(surf, right_x, cy_console + 4, third_w, console_h - 12, (16, 22, 18))
    draw_rivet_strip(surf, right_x + 4, cy_console + console_h - 14, third_w - 8, True, 20)

    # Console top edge highlight strip
    pygame.draw.rect(surf, HUD_GREEN_D, (0, vp_y2 - 2, W, 3))
    pygame.draw.line(surf, HUD_GREEN, (vp_x, vp_y2 - 1), (vp_x2, vp_y2 - 1), 1)

    # Wear/scratches on struts
    _scratches(surf, rng, 0, vp_y, vp_x, vp_h)
    _scratches(surf, rng, vp_x2, vp_y, W - vp_x2, vp_h)
    _scratches(surf, rng, 0, vp_y2, W, console_h)

    # ── Rivet strip along viewport frame ─────────────────────────
    draw_rivet_strip(surf, vp_x + 10, vp_y + 4, vp_w - 20, True, 40)
    draw_rivet_strip(surf, vp_x + 10, vp_y2 - 6, vp_w - 20, True, 40)

    vp_rect = {"x": vp_x, "y": vp_y, "w": vp_w, "h": vp_h}
    return surf, vp_rect
