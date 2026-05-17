"""
Galaxy map renderer — cinematic top-down navigation view.
Faction territory zones, glowing warp lanes, rich sector icons.
"""
import math
import random
import pygame

FACTION_COLORS = {
    "apex_syndicate":   (220, 60,  40),
    "helix_commerce":  (60,  180, 100),
    "ironveil_trading": (160, 130, 70),
    "drift_cartel":    (180, 80,  220),
    "the_remnant":     (80,  160, 220),
    "ghost_fleet":     (100, 220, 220),
    None:              (70,  80,  90),
}

MAP_BG = (3, 5, 12)

# Pre-build star field once
_STAR_CACHE: dict = {}

def _get_starfield(W, H, seed=77):
    key = (W, H)
    if key in _STAR_CACHE:
        return _STAR_CACHE[key]
    rng = random.Random(seed)
    surf = pygame.Surface((W, H))
    surf.fill(MAP_BG)
    star_colors = [(255,255,255),(200,215,255),(255,240,210),(180,200,255)]
    for _ in range(380):
        x = rng.randint(0, W-1)
        y = rng.randint(0, H-1)
        r = rng.choice([0,0,0,1])
        c = rng.choice(star_colors)
        a = rng.randint(60, 200)
        sc = tuple(int(ch * a / 255) for ch in c)
        if r == 0:
            surf.set_at((x, y), sc)
        else:
            pygame.draw.circle(surf, sc, (x, y), 1)
    _STAR_CACHE[key] = surf
    return surf

_TERRITORY_CACHE: dict = {}

def _get_territory_surf(W, H, galaxy):
    key = (W, H, id(galaxy))
    if key in _TERRITORY_CACHE:
        return _TERRITORY_CACHE[key]
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    # Draw per-faction zone clouds based on sector positions (world space)
    # We'll draw them at a fixed scale / unzoomed since this is regenerated on zoom anyway
    _TERRITORY_CACHE[key] = surf
    return surf


class MapRenderer:
    def __init__(self, width: int, height: int):
        self.width  = width
        self.height = height
        self.pan_x  = 0.0
        self.pan_y  = 0.0
        self.zoom   = 1.0
        self.fonts: dict = {}
        self._initialized = False
        self._time = 0.0
        self._territory_surfs: dict = {}   # faction_id -> Surface
        self._territory_dirty = True

    def init_fonts(self) -> None:
        if self._initialized:
            return
        try:
            mono = pygame.font.match_font("courier,couriernew,dejavusansmono")
            self.fonts["xs"] = pygame.font.Font(mono, 10)
            self.fonts["sm"] = pygame.font.Font(mono, 12)
            self.fonts["md"] = pygame.font.Font(mono, 15)
        except Exception:
            self.fonts["xs"] = pygame.font.SysFont("monospace", 10)
            self.fonts["sm"] = pygame.font.SysFont("monospace", 12)
            self.fonts["md"] = pygame.font.SysFont("monospace", 15)
        self._initialized = True

    def world_to_screen(self, wx, wy):
        sx = int((wx + self.pan_x) * self.zoom + self.width  / 2)
        sy = int((wy + self.pan_y) * self.zoom + self.height / 2)
        return sx, sy

    def screen_to_world(self, sx, sy):
        wx = (sx - self.width  / 2) / self.zoom - self.pan_x
        wy = (sy - self.height / 2) / self.zoom - self.pan_y
        return wx, wy

    def center_on_sector(self, sector) -> None:
        self.pan_x = -sector.x
        self.pan_y = -sector.y
        self._territory_dirty = True

    def zoom_in(self) -> None:
        self.zoom = min(4.0, self.zoom * 1.25)
        self._territory_dirty = True

    def zoom_out(self) -> None:
        self.zoom = max(0.15, self.zoom / 1.25)
        self._territory_dirty = True

    def pan(self, dx, dy) -> None:
        self.pan_x += dx / self.zoom
        self.pan_y += dy / self.zoom
        self._territory_dirty = True

    def get_sector_at_screen(self, galaxy, sx, sy):
        wx, wy = self.screen_to_world(sx, sy)
        best, best_dist = None, 22 / self.zoom
        for sector in galaxy.sectors.values():
            d = math.dist((sector.x, sector.y), (wx, wy))
            if d < best_dist:
                best_dist = d
                best = sector
        return best

    # ── Main draw ─────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface, galaxy, current_sector_id: int,
             visited: set, selected_sector_id: int | None = None) -> None:
        if not self._initialized:
            self.init_fonts()

        self._time += 0.016  # approximate dt

        # ── Background star field ──
        bg = _get_starfield(self.width, self.height)
        surface.blit(bg, (0, 0))

        # ── Faction territory halos ──
        self._draw_territory(surface, galaxy, visited, current_sector_id)

        # ── Warp links ──
        self._draw_warp_links(surface, galaxy, current_sector_id, visited)

        # ── Sector nodes ──
        current = galaxy.sectors.get(current_sector_id)
        adj_ids = set(current.warp_links) if current else set()

        for sector in galaxy.sectors.values():
            sx, sy = self.world_to_screen(sector.x, sector.y)
            if not (-60 < sx < self.width + 60 and -60 < sy < self.height + 60):
                continue
            is_current  = sector.sector_id == current_sector_id
            is_selected = sector.sector_id == selected_sector_id
            is_visited  = sector.sector_id in visited
            is_adjacent = sector.sector_id in adj_ids

            if not (is_visited or is_current or is_adjacent):
                # Fog of war — tiny dim dot
                pygame.draw.circle(surface, (18, 22, 30), (sx, sy), 2)
                continue

            self._draw_sector_node(surface, sector, sx, sy,
                                   is_current, is_selected, is_visited, is_adjacent)

        # ── UI overlays ──
        self._draw_compass(surface)
        self._draw_legend(surface)

    # ── Territory zones ───────────────────────────────────────────────────
    def _draw_territory(self, surface, galaxy, visited, current_sid):
        # Build per-faction average positions for visible sectors
        faction_centers: dict = {}
        for sector in galaxy.sectors.values():
            if sector.sector_id not in visited and sector.sector_id != current_sid:
                continue
            f = sector.controlling_faction
            if not f:
                continue
            sx, sy = self.world_to_screen(sector.x, sector.y)
            if not (-200 < sx < self.width + 200 and -200 < sy < self.height + 200):
                continue
            if f not in faction_centers:
                faction_centers[f] = []
            faction_centers[f].append((sx, sy))

        t_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        rng = random.Random(42)
        for faction, positions in faction_centers.items():
            if not positions:
                continue
            col = FACTION_COLORS.get(faction, (80, 80, 80))
            for px, py in positions:
                r = int(28 * self.zoom + 18)
                for i in range(4, 0, -1):
                    alpha = int(18 * i / 4)
                    pygame.draw.circle(t_surf, col + (alpha,), (px, py), r + i * 8)
        surface.blit(t_surf, (0, 0))

    # ── Warp links ────────────────────────────────────────────────────────
    def _draw_warp_links(self, surface, galaxy, current_sid, visited):
        drawn = set()
        current = galaxy.sectors.get(current_sid)
        adj_ids = set(current.warp_links) if current else set()

        link_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        for sector in galaxy.sectors.values():
            sx, sy = self.world_to_screen(sector.x, sector.y)
            if not (-300 < sx < self.width + 300 and -300 < sy < self.height + 300):
                continue

            for lid in sector.warp_links:
                key = tuple(sorted((sector.sector_id, lid)))
                if key in drawn:
                    continue
                drawn.add(key)
                other = galaxy.sectors.get(lid)
                if not other:
                    continue

                a_vis = sector.sector_id in visited or sector.sector_id == current_sid
                b_vis = lid in visited or lid == current_sid
                a_adj = sector.sector_id in adj_ids
                b_adj = lid in adj_ids

                if not (a_vis or b_vis or a_adj or b_adj):
                    continue

                ox, oy = self.world_to_screen(other.x, other.y)

                if sector.sector_id == current_sid or lid == current_sid:
                    # Adjacent to player — bright glowing lane
                    pygame.draw.line(link_surf, (60, 120, 60, 120), (sx, sy), (ox, oy), 2)
                    pygame.draw.line(link_surf, (100, 200, 100, 50), (sx, sy), (ox, oy), 4)
                elif a_adj or b_adj:
                    pygame.draw.line(link_surf, (40, 80, 40, 90), (sx, sy), (ox, oy), 1)
                else:
                    pygame.draw.line(link_surf, (25, 45, 25, 70), (sx, sy), (ox, oy), 1)

        surface.blit(link_surf, (0, 0))

    # ── Individual sector node ─────────────────────────────────────────────
    def _draw_sector_node(self, surface, sector, sx, sy,
                          is_current, is_selected, is_visited, is_adjacent):
        faction_col = FACTION_COLORS.get(sector.controlling_faction, FACTION_COLORS[None])
        if not is_visited and not is_current:
            faction_col = tuple(c // 3 for c in faction_col)

        base_r = max(4, int(6 * min(self.zoom, 2)))

        if is_current:
            # ── Player node: large pulsing ship indicator ──
            pulse = 0.75 + 0.25 * math.sin(self._time * 4.0)
            # Outer glow rings
            for i in range(5, 0, -1):
                r = base_r + 6 + i * 4
                alpha = int(40 * i / 5 * pulse)
                g = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
                pygame.draw.circle(g, (60, 255, 100, alpha), (r+1, r+1), r)
                surface.blit(g, (sx-r-1, sy-r-1))
            # Compass ring
            ring_r = base_r + 14
            pygame.draw.circle(surface, (40, 100, 40), (sx, sy), ring_r, 1)
            # N/S/E/W tick marks
            for a in [0, math.pi/2, math.pi, 3*math.pi/2]:
                tx = int(sx + math.cos(a) * ring_r)
                ty = int(sy + math.sin(a) * ring_r)
                pygame.draw.circle(surface, (80, 200, 80), (tx, ty), 2)
            # Ship dot
            pygame.draw.circle(surface, (60, 255, 100), (sx, sy), base_r + 2)
            pygame.draw.circle(surface, (200, 255, 200), (sx, sy), base_r - 1)
            # Crosshair
            for dx, dy in [(-base_r-6, 0),(base_r+6, 0),(0,-base_r-6),(0,base_r+6)]:
                pygame.draw.line(surface, (60, 200, 60),
                                 (sx + dx//2, sy + dy//2), (sx + dx, sy + dy), 1)

        elif is_selected:
            # Target bracket around selected
            bw = base_r + 6
            for bx2, by2, dx, dy in [
                (sx-bw, sy-bw, 1, 1),(sx+bw, sy-bw, -1, 1),
                (sx-bw, sy+bw, 1, -1),(sx+bw, sy+bw, -1, -1)]:
                pygame.draw.line(surface, (255, 220, 60), (bx2, by2), (bx2+dx*5, by2), 2)
                pygame.draw.line(surface, (255, 220, 60), (bx2, by2), (bx2, by2+dy*5), 2)
            # Glow
            pulse = 0.8 + 0.2 * math.sin(self._time * 5)
            g = pygame.Surface(((base_r+8)*2, (base_r+8)*2), pygame.SRCALPHA)
            pygame.draw.circle(g, (255, 220, 60, int(80*pulse)),
                               (base_r+8, base_r+8), base_r+8)
            surface.blit(g, (sx-base_r-8, sy-base_r-8))
            pygame.draw.circle(surface, faction_col, (sx, sy), base_r)
            pygame.draw.circle(surface, (255, 220, 60), (sx, sy), base_r, 1)

        elif is_adjacent:
            # Adjacent sectors — slightly larger, brighter, dashed indicator
            r = base_r + 1
            g = pygame.Surface(((r+6)*2, (r+6)*2), pygame.SRCALPHA)
            pygame.draw.circle(g, faction_col + (40,), (r+6, r+6), r+6)
            surface.blit(g, (sx-r-6, sy-r-6))
            pygame.draw.circle(surface, faction_col, (sx, sy), r)
            # Warp-available indicator (small orbit dot)
            angle = self._time * 2.5
            od = r + 5
            ox2 = int(sx + math.cos(angle) * od)
            oy2 = int(sy + math.sin(angle) * od)
            pygame.draw.circle(surface, (120, 200, 120), (ox2, oy2), 2)

        else:
            # Standard visited sector
            r = base_r
            # Glow
            g = pygame.Surface(((r+5)*2, (r+5)*2), pygame.SRCALPHA)
            pygame.draw.circle(g, faction_col + (30,), (r+5, r+5), r+5)
            surface.blit(g, (sx-r-5, sy-r-5))
            pygame.draw.circle(surface, faction_col, (sx, sy), r)

        # ── Port icon ──
        if sector.has_port() and (is_visited or is_current):
            self._draw_port_icon(surface, sx, sy, base_r, faction_col)

        # ── Planet icon ──
        if sector.has_planet() and (is_visited or is_current):
            self._draw_planet_icon(surface, sx, sy, base_r, sector.planet)

        # ── Anomaly glow ──
        if sector.anomaly and (is_visited or is_current):
            ag = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(ag, (100, 220, 220, 60), (10, 10), 10)
            surface.blit(ag, (sx - 10, sy - base_r - 16))

        # ── Sector name label ──
        if self.fonts and (is_visited or is_current or is_adjacent):
            zoom_thresh = 1.0 if (is_current or is_selected) else 1.8
            if self.zoom >= zoom_thresh:
                col = (140, 200, 140) if is_current else (80, 120, 80)
                lbl = self.fonts["xs"].render(sector.name, True, col)
                surface.blit(lbl, (sx + base_r + 3, sy - lbl.get_height() // 2))

    def _draw_port_icon(self, surface, sx, sy, base_r, col):
        """Hexagonal station icon above node."""
        px, py = sx, sy - base_r - 10
        r = max(5, int(6 * min(self.zoom, 1.5)))
        pts = [(px + int(r * math.cos(math.pi/6 + i * math.pi/3)),
                py + int(r * math.sin(math.pi/6 + i * math.pi/3))) for i in range(6)]
        g = pygame.Surface((r*2+6, r*2+6), pygame.SRCALPHA)
        pygame.draw.polygon(g, col + (60,),
                            [(p[0]-px+r+3, p[1]-py+r+3) for p in pts])
        surface.blit(g, (px-r-3, py-r-3))
        pygame.draw.polygon(surface, col, pts, 1)
        pygame.draw.circle(surface, col, (px, py), max(1, r//3))

    def _draw_planet_icon(self, surface, sx, sy, base_r, planet):
        """Small planet circle to the right of node."""
        px, py = sx + base_r + 10, sy
        r = max(4, int(5 * min(self.zoom, 1.5)))
        # Color from planet name hash
        h = hash(planet.name) if planet else 42
        hue = (h % 360)
        if hue < 60:    col = (80, 160, 80)
        elif hue < 120: col = (80, 120, 160)
        elif hue < 180: col = (160, 120, 60)
        elif hue < 240: col = (100, 80, 160)
        elif hue < 300: col = (60, 160, 140)
        else:           col = (160, 80, 80)
        pygame.draw.circle(surface, col, (px, py), r)
        # Atmosphere halo
        g = pygame.Surface(((r+4)*2, (r+4)*2), pygame.SRCALPHA)
        pygame.draw.circle(g, col + (40,), (r+4, r+4), r+4)
        surface.blit(g, (px-r-4, py-r-4))
        # Highlight
        pygame.draw.circle(surface, tuple(min(255, c+60) for c in col),
                           (px - max(1,r//3), py - max(1,r//3)), max(1, r//3))

    # ── UI chrome ─────────────────────────────────────────────────────────
    def _draw_compass(self, surface):
        cx, cy = self.width - 50, 50
        r = 28
        pygame.draw.circle(surface, (8, 14, 10), (cx, cy), r)
        pygame.draw.circle(surface, (30, 60, 35), (cx, cy), r, 1)
        # N marker
        n_lbl = self.fonts["xs"].render("N", True, (60, 200, 80)) if self.fonts else None
        if n_lbl:
            surface.blit(n_lbl, (cx - n_lbl.get_width()//2, cy - r + 2))
        pygame.draw.line(surface, (60, 200, 80),
                         (cx, cy - r + 12), (cx, cy - 4), 1)
        pygame.draw.polygon(surface, (60, 200, 80),
                            [(cx, cy - r + 12), (cx-3, cy-r+20), (cx+3, cy-r+20)])
        # Zoom level
        if self.fonts:
            z_lbl = self.fonts["xs"].render(f"x{self.zoom:.1f}", True, (40, 90, 50))
            surface.blit(z_lbl, (cx - z_lbl.get_width()//2, cy + r - 12))

    def _draw_legend(self, surface):
        if not self.fonts:
            return
        font = self.fonts["xs"]
        items = [
            ("APEX SYN",    FACTION_COLORS["apex_syndicate"]),
            ("HELIX COMM",  FACTION_COLORS["helix_commerce"]),
            ("IRONVEIL",    FACTION_COLORS["ironveil_trading"]),
            ("DRIFT CRTL",  FACTION_COLORS["drift_cartel"]),
            ("REMNANT",     FACTION_COLORS["the_remnant"]),
            ("GHOST FLT",   FACTION_COLORS["ghost_fleet"]),
        ]
        panel_w = 108
        panel_h = len(items) * 15 + 8
        px, py = 6, self.height - panel_h - 28

        bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(bg, (4, 8, 6, 180), (0, 0, panel_w, panel_h))
        pygame.draw.rect(bg, (30, 60, 35, 200), (0, 0, panel_w, panel_h), 1)
        surface.blit(bg, (px, py))

        y = py + 4
        for name, col in items:
            g = pygame.Surface((10, 10), pygame.SRCALPHA)
            pygame.draw.circle(g, col + (180,), (5, 5), 5)
            surface.blit(g, (px + 4, y + 2))
            lbl = font.render(name, True, col)
            surface.blit(lbl, (px + 14, y))
            y += 15

        # Port/Planet key
        y += 4
        if y + 22 < self.height - 10:
            port_lbl = font.render("⬡ PORT   ● PLANET", True, (60, 100, 60))
            surface.blit(port_lbl, (px, y))
