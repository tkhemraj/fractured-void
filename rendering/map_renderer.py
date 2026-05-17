"""
Renders the sector map (TradeWars-style top-down navigation view).
Shows sectors as nodes, warp links as edges, ports/planets as icons.
Player position highlighted. Color-coded by controlling faction.
"""
import math
import pygame
from world.galaxy import Galaxy
from world.sector import Sector

FACTION_COLORS = {
    "apex_syndicate":   (220, 60, 40),
    "helix_commerce":   (60, 180, 100),
    "ironveil_trading": (160, 130, 70),
    "drift_cartel":     (180, 80, 220),
    "the_remnant":      (80, 160, 220),
    "ghost_fleet":      (100, 220, 220),
    None:               (80, 80, 80),
}

MAP_BG = (4, 6, 12)
NODE_RADIUS = 5
PLAYER_RADIUS = 8


class MapRenderer:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.zoom = 1.0
        self.fonts: dict = {}
        self._initialized = False
        self._warp_surf: pygame.Surface | None = None
        self._node_cache: dict = {}

    def init_fonts(self) -> None:
        if self._initialized:
            return
        try:
            mono = pygame.font.match_font("courier,couriernew,dejavusansmono")
            self.fonts["sm"] = pygame.font.Font(mono, 12)
            self.fonts["md"] = pygame.font.Font(mono, 16)
        except Exception:
            self.fonts["sm"] = pygame.font.SysFont("monospace", 12)
            self.fonts["md"] = pygame.font.SysFont("monospace", 16)
        self._initialized = True

    def world_to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        sx = int((wx + self.pan_x) * self.zoom + self.width / 2)
        sy = int((wy + self.pan_y) * self.zoom + self.height / 2)
        return sx, sy

    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        wx = (sx - self.width / 2) / self.zoom - self.pan_x
        wy = (sy - self.height / 2) / self.zoom - self.pan_y
        return wx, wy

    def center_on_sector(self, sector: Sector) -> None:
        self.pan_x = -sector.x
        self.pan_y = -sector.y

    def zoom_in(self) -> None:
        self.zoom = min(4.0, self.zoom * 1.25)

    def zoom_out(self) -> None:
        self.zoom = max(0.15, self.zoom / 1.25)

    def pan(self, dx: float, dy: float) -> None:
        self.pan_x += dx / self.zoom
        self.pan_y += dy / self.zoom

    def get_sector_at_screen(self, galaxy: Galaxy, sx: int, sy: int) -> Sector | None:
        wx, wy = self.screen_to_world(sx, sy)
        best = None
        best_dist = 20 / self.zoom
        for sector in galaxy.sectors.values():
            d = math.dist((sector.x, sector.y), (wx, wy))
            if d < best_dist:
                best_dist = d
                best = sector
        return best

    def draw(
        self,
        surface: pygame.Surface,
        galaxy: Galaxy,
        current_sector_id: int,
        visited: set[int],
        selected_sector_id: int | None = None,
    ) -> None:
        if not self._initialized:
            self.init_fonts()

        surface.fill(MAP_BG)

        cx = current_sector_id

        # Draw warp links first (behind nodes)
        drawn_links = set()
        for sector in galaxy.sectors.values():
            sx, sy = self.world_to_screen(sector.x, sector.y)
            if not (-200 < sx < self.width + 200 and -200 < sy < self.height + 200):
                continue
            for link_id in sector.warp_links:
                link_key = tuple(sorted((sector.sector_id, link_id)))
                if link_key in drawn_links:
                    continue
                drawn_links.add(link_key)
                other = galaxy.sectors.get(link_id)
                if not other:
                    continue
                # Only draw if both are visited OR one is current
                both_known = sector.sector_id in visited and link_id in visited
                adj_to_current = sector.sector_id == cx or link_id == cx
                if not (both_known or adj_to_current):
                    continue
                ox, oy = self.world_to_screen(other.x, other.y)
                color = (25, 40, 25)
                if adj_to_current:
                    color = (50, 90, 50)
                pygame.draw.line(surface, color, (sx, sy), (ox, oy), 1)

        # Draw sector nodes
        for sector in galaxy.sectors.values():
            sx, sy = self.world_to_screen(sector.x, sector.y)
            if not (-50 < sx < self.width + 50 and -50 < sy < self.height + 50):
                continue

            is_current = sector.sector_id == cx
            is_selected = sector.sector_id == selected_sector_id
            is_visited = sector.sector_id in visited
            is_adjacent = sector.sector_id in galaxy.sectors[cx].warp_links

            if not (is_visited or is_current or is_adjacent):
                # Unvisited, not adjacent: show as dim unknown
                pygame.draw.circle(surface, (20, 20, 25), (sx, sy), 2)
                continue

            faction_color = FACTION_COLORS.get(sector.controlling_faction, FACTION_COLORS[None])
            if not is_visited and not is_current:
                faction_color = tuple(c // 3 for c in faction_color)

            r = NODE_RADIUS
            if is_current:
                r = PLAYER_RADIUS
                # Pulsing ring
                pygame.draw.circle(surface, (100, 255, 100), (sx, sy), r + 4, 2)

            pygame.draw.circle(surface, faction_color, (sx, sy), r)

            if is_selected:
                pygame.draw.circle(surface, (255, 255, 100), (sx, sy), r + 3, 2)

            # Icons for port and planet
            if sector.has_port() and is_visited:
                pygame.draw.circle(surface, (200, 180, 80), (sx + 7, sy - 6), 3)
            if sector.has_planet() and is_visited:
                pygame.draw.circle(surface, (80, 180, 80), (sx - 7, sy - 6), 3)

            # Sector name for zoom > 1.5
            if self.zoom > 1.5 and is_visited and self.fonts:
                name_surf = self.fonts["sm"].render(sector.name, True, (80, 100, 80))
                surface.blit(name_surf, (sx + 6, sy - 6))

        # Legend
        self._draw_legend(surface)

    def _draw_legend(self, surface: pygame.Surface) -> None:
        if not self.fonts:
            return
        font = self.fonts["sm"]
        items = [
            ("APEX",  FACTION_COLORS["apex_syndicate"]),
            ("HELIX", FACTION_COLORS["helix_commerce"]),
            ("ITV",   FACTION_COLORS["ironveil_trading"]),
            ("DRIFT", FACTION_COLORS["drift_cartel"]),
            ("RMN",   FACTION_COLORS["the_remnant"]),
            ("GHOST", FACTION_COLORS["ghost_fleet"]),
        ]
        x, y = 10, self.height - 10 - len(items) * 16
        for name, color in items:
            pygame.draw.circle(surface, color, (x + 6, y + 7), 5)
            lbl = font.render(name, True, color)
            surface.blit(lbl, (x + 14, y))
            y += 16
