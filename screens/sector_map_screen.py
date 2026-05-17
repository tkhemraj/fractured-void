"""
The sector map screen — TradeWars-style navigation.
Player moves between sectors, sees ports/planets/anomalies, initiates combat or trading.
"""
import pygame
from rendering.map_renderer import MapRenderer
from world.galaxy import Galaxy
from world.sector import Sector
from engine.game_state import GameState
from engine.event_bus import bus


class SectorMapScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.map_renderer = MapRenderer(width, height)
        self.galaxy: Galaxy | None = None
        self.state: GameState | None = None
        self.selected_sector: Sector | None = None
        self.visited: set[int] = set()
        self.fonts: dict = {}
        self._initialized = False
        self._info_panel_open = False
        self._log_scroll = 0

    def init(self, galaxy: Galaxy, game_state: GameState) -> None:
        self.galaxy = galaxy
        self.state = game_state
        self.visited = {game_state.player.current_sector}

        try:
            mono = pygame.font.match_font("courier,couriernew,dejavusansmono")
            self.fonts["sm"] = pygame.font.Font(mono, 13)
            self.fonts["md"] = pygame.font.Font(mono, 17)
            self.fonts["lg"] = pygame.font.Font(mono, 22)
        except Exception:
            self.fonts["sm"] = pygame.font.SysFont("monospace", 13)
            self.fonts["md"] = pygame.font.SysFont("monospace", 17)
            self.fonts["lg"] = pygame.font.SysFont("monospace", 22)

        current = galaxy.sectors.get(game_state.player.current_sector)
        if current:
            self.map_renderer.center_on_sector(current)
        self._initialized = True

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if not self._initialized or not self.galaxy or not self.state:
            return None

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                clicked = self.map_renderer.get_sector_at_screen(self.galaxy, event.pos[0], event.pos[1])
                if clicked:
                    if clicked == self.selected_sector:
                        return self._try_warp_to(clicked)
                    self.selected_sector = clicked
            elif event.button == 4:
                self.map_renderer.zoom_in()
            elif event.button == 5:
                self.map_renderer.zoom_out()

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and self.selected_sector:
                return self._try_warp_to(self.selected_sector)
            if event.key == pygame.K_c:
                current = self.galaxy.sectors.get(self.state.player.current_sector)
                if current:
                    self.map_renderer.center_on_sector(current)

            current = self.galaxy.sectors.get(self.state.player.current_sector)
            if not current:
                return None

            if event.key == pygame.K_p:
                if current.has_port():
                    return "trading"
                elif current.has_planet():
                    self.state.combat_context["planet"] = current.planet
                    self.state.combat_context["sector_name"] = current.name
                    return "planet"

            if event.key == pygame.K_u:
                self.state.combat_context["sector_name"] = current.name
                return "shipyard"

            if event.key == pygame.K_m:
                from engine.mission_manager import missions as mission_mgr
                mission_mgr.load()
                available = mission_mgr.get_available_for_sector(
                    current.sector_id, self.state.player.faction_relations
                )
                self.state.combat_context["available_missions"] = available
                return "mission_board"

        elif event.type == pygame.MOUSEMOTION and (event.buttons[1] or event.buttons[2]):
            self.map_renderer.pan(event.rel[0], event.rel[1])

        return None

    def _try_warp_to(self, target: Sector) -> str | None:
        if not self.state or not self.galaxy:
            return None
        current_sector = self.galaxy.sectors.get(self.state.player.current_sector)
        if not current_sector:
            return None

        if target.sector_id == current_sector.sector_id:
            # Already here — open sector info
            self._info_panel_open = not self._info_panel_open
            return None

        if target.sector_id not in current_sector.warp_links:
            self._log("Can only warp to adjacent sectors.")
            return None

        if not self.state.player.use_turns(1):
            self._log("Out of turns. Dock at a port to refresh.")
            return None

        self.state.player.current_sector = target.sector_id
        self.visited.add(target.sector_id)
        target.visited = True
        self.selected_sector = target
        self.map_renderer.center_on_sector(target)

        self._log(f"Warped to sector {target.sector_id}: {target.name}")

        from engine.event_bus import bus as _bus
        _bus.post("sector_entered", sector_id=target.sector_id)
        from engine.mission_manager import missions as _missions
        _missions.load()
        if self.state.cargo:
            _missions.check_carry_objectives(self.state.cargo.contents)

        # Random encounter check (20% in hostile zones, 10% otherwise)
        import random
        encounter_chance = 0.20 if target.controlling_faction in ("drift_cartel", "ghost_fleet") else 0.10
        if random.random() < encounter_chance:
            self._setup_encounter(target)
            return "combat"

        return None

    def _setup_encounter(self, sector: Sector) -> None:
        if not self.state:
            return
        import json, os, random
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        with open(os.path.join(data_dir, "ships.json")) as f:
            all_ships = json.load(f)

        faction = sector.controlling_faction or "drift_cartel"
        faction_ship_map = {
            "apex_syndicate":   "apex_enforcer",
            "helix_commerce":   "merchant_hauler",
            "ironveil_trading": "ironveil_corvette",
            "drift_cartel":     "scout_marauder",
            "the_remnant":      "scout_marauder",
            "ghost_fleet":      "ghost_wraith",
        }
        ship_id = faction_ship_map.get(faction, "scout_marauder")
        ship_data = all_ships.get(ship_id, all_ships["scout_marauder"])

        skills = {"ghost_fleet": "ace", "apex_syndicate": "veteran"}
        skill = skills.get(faction, "novice")

        n_enemies = random.randint(1, 3) if faction != "ghost_fleet" else 1
        self.state.combat_context = {
            "enemies": [
                {"ship_id": ship_id, "ship_data": ship_data, "skill": skill, "faction": faction}
                for _ in range(n_enemies)
            ],
            "in_fracture_zone": sector.anomaly == "fracture_rift",
        }
        self._log(f"COMBAT ALERT — {n_enemies} {faction.replace('_', ' ').upper()} vessel(s) detected!")

    def _log(self, msg: str) -> None:
        if self.state and self.state.player:
            self.state.player.add_log(msg)

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        if not self._initialized or not self.galaxy or not self.state:
            surface.fill((4, 6, 12))
            return

        self.map_renderer.draw(
            surface,
            self.galaxy,
            self.state.player.current_sector,
            self.visited,
            self.selected_sector.sector_id if self.selected_sector else None,
        )

        self._draw_hud_overlay(surface)
        if self.selected_sector:
            self._draw_sector_info(surface, self.selected_sector)
        self._draw_log(surface)

    def _draw_hud_overlay(self, surface: pygame.Surface) -> None:
        if not self.fonts or not self.state:
            return
        font_sm = self.fonts["sm"]
        font_md = self.fonts["md"]
        p = self.state.player

        # Top bar
        pygame.draw.rect(surface, (6, 10, 8), (0, 0, self.width, 34))
        pygame.draw.line(surface, (40, 80, 40), (0, 34), (self.width, 34), 1)

        name = font_md.render(f"{p.name}", True, (100, 220, 100))
        surface.blit(name, (10, 8))

        credits = font_md.render(f"CR {p.credits:>8,}", True, (180, 160, 60))
        surface.blit(credits, (240, 8))

        turns = font_md.render(f"TURNS {p.turns:>4}", True, (80, 160, 220))
        surface.blit(turns, (440, 8))

        current = self.galaxy.sectors.get(p.current_sector)
        if current:
            loc = font_sm.render(f"LOC: {current.name} [{p.current_sector}]", True, (80, 120, 80))
            surface.blit(loc, (600, 10))

        # Controls hint (bottom)
        hints = font_sm.render(
            "Click=Select  Enter=Warp  P=Trade/Planet  U=Shipyard  M=Missions  C=Center  Scroll=Zoom  MMB=Pan",
            True, (40, 70, 40)
        )
        surface.blit(hints, (10, self.height - 20))

    def _draw_sector_info(self, surface: pygame.Surface, sector: Sector) -> None:
        if not self.fonts:
            return
        font_sm = self.fonts["sm"]
        font_md = self.fonts["md"]
        font_lg = self.fonts["lg"]

        panel_w = 260
        panel_x = self.width - panel_w - 10
        panel_y = 44
        panel_h = 280

        pygame.draw.rect(surface, (5, 10, 5, 220), (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.rect(surface, (40, 80, 40), (panel_x, panel_y, panel_w, panel_h), 1)

        y = panel_y + 8
        name_lbl = font_lg.render(sector.name, True, (120, 220, 120))
        surface.blit(name_lbl, (panel_x + 8, y))
        y += 28

        sid = font_sm.render(f"Sector #{sector.sector_id}", True, (60, 100, 60))
        surface.blit(sid, (panel_x + 8, y))
        y += 18

        from rendering.map_renderer import FACTION_COLORS
        faction = sector.controlling_faction
        fc = FACTION_COLORS.get(faction, FACTION_COLORS[None])
        faction_lbl = font_sm.render(faction.replace("_", " ").upper() if faction else "UNCLAIMED", True, fc)
        surface.blit(faction_lbl, (panel_x + 8, y))
        y += 22

        if sector.has_port() and sector.port:
            port = sector.port
            pygame.draw.rect(surface, (20, 15, 5), (panel_x + 4, y, panel_w - 8, 14))
            p_lbl = font_sm.render(f"PORT: {port.class_name}", True, (220, 180, 60))
            surface.blit(p_lbl, (panel_x + 8, y))
            y += 16
            if port.sells:
                sells = font_sm.render(f"  Sells: {', '.join(port.sells)}", True, (60, 180, 60))
                surface.blit(sells, (panel_x + 8, y))
                y += 14
            if port.buys:
                buys = font_sm.render(f"  Buys:  {', '.join(port.buys)}", True, (180, 80, 80))
                surface.blit(buys, (panel_x + 8, y))
                y += 14
            if sector.sector_id == self.state.player.current_sector:
                trade_hint = font_sm.render("[P] Enter port", True, (180, 160, 60))
                surface.blit(trade_hint, (panel_x + 8, y))
                y += 14

        if sector.has_planet() and sector.planet:
            planet = sector.planet
            p_lbl = font_sm.render(f"PLANET: {planet.name}", True, (80, 200, 80))
            surface.blit(p_lbl, (panel_x + 8, y))
            y += 14
            col = font_sm.render(f"  Pop: {planet.colonists:,}", True, (60, 140, 60))
            surface.blit(col, (panel_x + 8, y))
            y += 14

        if sector.anomaly:
            anom = font_sm.render(f"ANOMALY: {sector.anomaly.replace('_', ' ').upper()}", True, (100, 220, 220))
            surface.blit(anom, (panel_x + 8, y))
            y += 14

        warps = font_sm.render(f"Warps to: {sector.warp_links[:5]}", True, (60, 80, 60))
        surface.blit(warps, (panel_x + 8, y))

    def _draw_log(self, surface: pygame.Surface) -> None:
        if not self.fonts or not self.state or not self.state.player.log:
            return
        font_sm = self.fonts["sm"]
        log = self.state.player.log[-8:]
        y = self.height - 25 - len(log) * 14
        for entry in log:
            lbl = font_sm.render(entry, True, (50, 90, 50))
            surface.blit(lbl, (10, y))
            y += 14
