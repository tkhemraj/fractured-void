"""
Planet colonization screen — TradeWars-style planetary management.
Claim unclaimed worlds, build citadels, harvest resources, deploy defenders.
"""
import math
import random
import pygame
from world.sector import Planet
from engine.game_state import GameState
from audio.sound_gen import sounds

HUD_GREEN = (60, 220, 80)
HUD_AMBER = (220, 160, 40)
HUD_RED   = (220, 60, 40)
HUD_DIM   = (30, 60, 35)
HUD_WHITE = (200, 210, 200)
HUD_CYAN  = (60, 220, 220)
BG        = (4, 8, 6)

CITADEL_COSTS = {
    1: {"credits": 10000, "equipment": 20},
    2: {"credits": 25000, "equipment": 50},
    3: {"credits": 60000, "equipment": 100},
    4: {"credits": 150000, "equipment": 200},
}

ACTIONS_OWNED = [
    {"id": "drop_colonists",   "label": "Drop Colonists",     "desc": "Transfer colonists from cargo to planet"},
    {"id": "deploy_fighters",  "label": "Deploy Fighters",    "desc": "Transfer fighters from ship to planet defense"},
    {"id": "build_citadel",    "label": "Build Citadel",      "desc": "Upgrade citadel level (boosts production)"},
    {"id": "collect_resources","label": "Collect Resources",  "desc": "Load planet output into cargo hold"},
    {"id": "withdraw_fighters","label": "Withdraw Fighters",  "desc": "Recover planet fighters to ship"},
]

ACTIONS_UNCLAIMED = [
    {"id": "claim",  "label": "Claim Planet", "desc": "Requires 10 colonists in cargo + 2,000 CR"},
]

ACTIONS_HOSTILE = [
    {"id": "raid",   "label": "Raid Planet",  "desc": "Attack using ship fighters (costs fighters)"},
]


def _planet_color(name: str) -> tuple:
    h = abs(hash(name)) % 360
    r = int(128 + 80 * math.cos(math.radians(h)))
    g = int(128 + 80 * math.cos(math.radians(h + 120)))
    b = int(128 + 80 * math.cos(math.radians(h + 240)))
    return (max(40, min(200, r)), max(40, min(200, g)), max(40, min(200, b)))


def _draw_planet(surface: pygame.Surface, planet: Planet, cx: int, cy: int, radius: int) -> None:
    color = _planet_color(planet.name)
    rng = random.Random(abs(hash(planet.name)))

    # Atmosphere glow
    for i in range(12, 0, -1):
        alpha = int(30 * (i / 12))
        atm_color = tuple(min(255, c + 40) for c in color) + (alpha,)
        glow_surf = pygame.Surface((radius * 3, radius * 3), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, atm_color, (radius * 3 // 2, radius * 3 // 2), radius + i * 3)
        surface.blit(glow_surf, (cx - radius * 3 // 2, cy - radius * 3 // 2))

    # Planet body
    pygame.draw.circle(surface, color, (cx, cy), radius)

    # Surface features (continents)
    dark = tuple(max(0, c - 50) for c in color)
    light = tuple(min(255, c + 40) for c in color)
    for _ in range(5):
        bx = cx + rng.randint(-radius // 2, radius // 2)
        by = cy + rng.randint(-radius // 2, radius // 2)
        bw = rng.randint(radius // 5, radius // 2)
        bh = rng.randint(radius // 6, radius // 3)
        angle = rng.uniform(0, 360)
        blob_surf = pygame.Surface((bw * 2, bh * 2), pygame.SRCALPHA)
        c_blob = dark if rng.random() < 0.5 else light
        pygame.draw.ellipse(blob_surf, c_blob + (120,), (0, 0, bw * 2, bh * 2))
        rotated = pygame.transform.rotate(blob_surf, angle)
        # Clip to planet circle
        surface.blit(rotated, (bx - rotated.get_width() // 2, by - rotated.get_height() // 2),
                     special_flags=pygame.BLEND_RGBA_MIN)
        pygame.draw.ellipse(surface, c_blob, (bx - bw // 2, by - bh // 2, bw, bh))

    # Re-draw circle edge
    pygame.draw.circle(surface, tuple(min(255, c + 20) for c in color), (cx, cy), radius, 3)
    pygame.draw.circle(surface, (200, 220, 255), (cx, cy), radius, 1)

    # Citadel icon
    if planet.citadel_level > 0:
        cit_x, cit_y = cx + int(radius * 0.55), cy - int(radius * 0.4)
        h = 8 + planet.citadel_level * 4
        pygame.draw.rect(surface, (200, 180, 80), (cit_x - 5, cit_y - h, 10, h))
        pygame.draw.polygon(surface, (255, 220, 100), [
            (cit_x, cit_y - h - 10), (cit_x - 8, cit_y - h), (cit_x + 8, cit_y - h)
        ])


class PlanetScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.fonts: dict = {}
        self._initialized = False
        self._planet: Planet | None = None
        self._state: GameState | None = None
        self.sector_name = ""
        self.selected = 0
        self.message = ""
        self.message_timer = 0.0
        self._msg_ok = True
        self._planet_surf: pygame.Surface | None = None

    def init_fonts(self) -> None:
        if self._initialized:
            return
        try:
            mono = pygame.font.match_font("courier,couriernew,dejavusansmono")
            self.fonts["sm"] = pygame.font.Font(mono, 13)
            self.fonts["md"] = pygame.font.Font(mono, 17)
            self.fonts["lg"] = pygame.font.Font(mono, 26)
            self.fonts["xl"] = pygame.font.Font(mono, 38)
        except Exception:
            self.fonts["sm"] = pygame.font.SysFont("monospace", 13)
            self.fonts["md"] = pygame.font.SysFont("monospace", 17)
            self.fonts["lg"] = pygame.font.SysFont("monospace", 26)
            self.fonts["xl"] = pygame.font.SysFont("monospace", 38)
        self._initialized = True

    def open(self, planet: Planet, sector_name: str, game_state: GameState) -> None:
        self.init_fonts()
        self._planet = planet
        self._state = game_state
        self.sector_name = sector_name
        self.selected = 0
        self.message = ""
        self.message_timer = 0.0
        # Produce resources on visit
        self._produce_resources()
        # Pre-render planet
        self._planet_surf = pygame.Surface((320, 320), pygame.SRCALPHA)
        _draw_planet(self._planet_surf, planet, 160, 160, 130)

    def _produce_resources(self) -> None:
        p = self._planet
        if not p or p.owner != self._state.player.name:
            return
        bonus = 1.0 + p.citadel_level * 0.25
        p.fuel_ore    += int(p.colonists // 10 * bonus)
        p.organics    += int(p.colonists // 8  * bonus)
        p.equipment   += int(p.colonists // 15 * bonus)

    def _get_actions(self) -> list[dict]:
        p = self._planet
        if not p:
            return []
        if p.owner is None:
            return ACTIONS_UNCLAIMED
        if p.owner == self._state.player.name:
            return ACTIONS_OWNED
        return ACTIONS_HOSTILE

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type != pygame.KEYDOWN:
            return None
        actions = self._get_actions()
        if event.key == pygame.K_ESCAPE:
            return "sector_map"
        elif event.key in (pygame.K_UP, pygame.K_w):
            self.selected = (self.selected - 1) % max(1, len(actions))
            sounds.play("beep_low", 0.3)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected = (self.selected + 1) % max(1, len(actions))
            sounds.play("beep_low", 0.3)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if actions:
                self._execute_action(actions[self.selected]["id"])
        return None

    def _execute_action(self, action_id: str) -> None:
        p = self._planet
        s = self._state
        if not p or not s:
            return

        if action_id == "claim":
            cargo_colonists = s.cargo.contents.get("colonists", 0)
            if cargo_colonists < 10:
                self._msg("Need 10 colonists in cargo to claim.", ok=False)
                sounds.play("trade_fail")
                return
            if not s.player.spend_credits(2000):
                self._msg("Need 2,000 CR to establish colony.", ok=False)
                sounds.play("trade_fail")
                return
            s.cargo.remove("colonists", 10)
            p.owner = s.player.name
            p.colonists = 10
            self._msg(f"{p.name} is now your colony!")
            s.player.add_log(f"Claimed planet: {p.name}")
            sounds.play("mission_accept", 0.9)

        elif action_id == "drop_colonists":
            qty = s.cargo.contents.get("colonists", 0)
            if qty == 0:
                self._msg("No colonists in cargo.", ok=False)
                sounds.play("trade_fail")
                return
            s.cargo.remove("colonists", qty)
            p.colonists += qty
            self._msg(f"Dropped {qty} colonists on {p.name}.")
            sounds.play("trade_ok")

        elif action_id == "deploy_fighters":
            if s.ship.fighters <= 0:
                self._msg("No fighters aboard.", ok=False)
                sounds.play("trade_fail")
                return
            qty = min(s.ship.fighters, 20)
            s.ship.fighters -= qty
            p.fighters += qty
            self._msg(f"Deployed {qty} fighters to {p.name}.")
            sounds.play("trade_ok")

        elif action_id == "build_citadel":
            lvl = p.citadel_level
            if lvl >= 4:
                self._msg("Citadel already at maximum level.", ok=False)
                return
            cost = CITADEL_COSTS[lvl + 1]
            eq_needed = cost["equipment"]
            if s.cargo.contents.get("equipment", 0) < eq_needed:
                self._msg(f"Need {eq_needed} equipment in cargo.", ok=False)
                sounds.play("trade_fail")
                return
            if not s.player.spend_credits(cost["credits"]):
                self._msg(f"Need {cost['credits']:,} CR.", ok=False)
                sounds.play("trade_fail")
                return
            s.cargo.remove("equipment", eq_needed)
            p.citadel_level += 1
            self._msg(f"Citadel level {p.citadel_level} built on {p.name}!")
            s.player.add_log(f"Built citadel Lv.{p.citadel_level} on {p.name}")
            sounds.play("mission_accept", 0.7)
            # Redraw planet with new citadel
            self._planet_surf = pygame.Surface((320, 320), pygame.SRCALPHA)
            _draw_planet(self._planet_surf, p, 160, 160, 130)

        elif action_id == "collect_resources":
            loaded = []
            for item in ["fuel_ore", "organics", "equipment"]:
                qty = getattr(p, item)
                if qty > 0 and s.cargo.free > 0:
                    can_take = min(qty, s.cargo.free)
                    if s.cargo.add(item, can_take):
                        setattr(p, item, qty - can_take)
                        loaded.append(f"{can_take}x {item}")
            if loaded:
                self._msg("Loaded: " + ", ".join(loaded))
                sounds.play("trade_ok")
            else:
                self._msg("No resources to collect (or cargo full).", ok=False)

        elif action_id == "withdraw_fighters":
            if p.fighters == 0:
                self._msg("No fighters deployed here.", ok=False)
                return
            space = s.ship.max_fighters - s.ship.fighters
            qty = min(p.fighters, space)
            if qty == 0:
                self._msg("Fighter bays full.", ok=False)
                return
            p.fighters -= qty
            s.ship.fighters += qty
            self._msg(f"Recovered {qty} fighters from {p.name}.")
            sounds.play("trade_ok")

        elif action_id == "raid":
            if s.ship.fighters == 0:
                self._msg("No fighters to raid with.", ok=False)
                sounds.play("trade_fail")
                return
            raid_power = s.ship.fighters
            defend_power = p.fighters + p.shields
            if raid_power > defend_power:
                losses = max(1, defend_power // 3)
                s.ship.fighters -= losses
                p.fighters = 0
                p.shields = max(0, p.shields - raid_power // 2)
                self._msg(f"Raid successful! Lost {losses} fighters.")
                s.player.add_log(f"Raided {p.name} — success.")
                sounds.play("explosion_large", 0.7)
            else:
                losses = max(1, raid_power // 2)
                s.ship.fighters -= losses
                self._msg(f"Raid repelled. Lost {losses} fighters.", ok=False)
                sounds.play("shield_hit", 0.7)

    def _msg(self, text: str, ok: bool = True) -> None:
        self.message = text
        self.message_timer = 0.0
        self._msg_ok = ok

    def update(self, dt: float) -> None:
        self.message_timer += dt

    def draw(self, surface: pygame.Surface) -> None:
        if not self._initialized:
            self.init_fonts()
        surface.fill(BG)

        p = self._planet
        if not p:
            surface.blit(self.fonts["lg"].render("No planet in this sector.", True, HUD_DIM),
                         (self.width // 2 - 150, self.height // 2))
            return

        self._draw_header(surface)
        self._draw_planet_visual(surface)
        self._draw_stats_panel(surface)
        self._draw_action_menu(surface)
        self._draw_message(surface)
        self._draw_hints(surface)

    def _draw_header(self, surface: pygame.Surface) -> None:
        p = self._planet
        pygame.draw.rect(surface, (5, 14, 8), (0, 0, self.width, 50))
        pygame.draw.line(surface, (40, 100, 50), (0, 50), (self.width, 50), 1)
        title = self.fonts["xl"].render(p.name.upper(), True, HUD_GREEN)
        surface.blit(title, (20, 6))
        sub = self.fonts["md"].render(f"Sector: {self.sector_name}", True, HUD_DIM)
        surface.blit(sub, (self.width - sub.get_width() - 20, 14))

    def _draw_planet_visual(self, surface: pygame.Surface) -> None:
        if self._planet_surf:
            surface.blit(self._planet_surf, (40, 60))

    def _draw_stats_panel(self, surface: pygame.Surface) -> None:
        font_sm = self.fonts["sm"]
        font_md = self.fonts["md"]
        font_lg = self.fonts["lg"]
        p = self._planet

        px, py = 380, 60
        pw = self.width - px - 20

        pygame.draw.rect(surface, (3, 8, 4), (px, py, pw, 350))
        pygame.draw.rect(surface, HUD_DIM, (px, py, pw, 350), 1)

        y = py + 10
        owner_text = p.owner if p.owner else "UNCLAIMED"
        owner_color = HUD_GREEN if p.owner == (self._state.player.name if self._state else "") else HUD_AMBER if p.owner else HUD_RED
        surface.blit(font_lg.render(f"Status: {owner_text}", True, owner_color), (px + 12, y))
        y += 36

        stats = [
            ("Colonists",     f"{p.colonists:,}"),
            ("Fighters",      f"{p.fighters:,}"),
            ("Shields",       f"{p.shields:,}"),
            ("Citadel",       f"Level {p.citadel_level}" if p.citadel_level > 0 else "None"),
        ]
        for label, val in stats:
            surface.blit(font_sm.render(f"{label:<14}", True, HUD_DIM), (px + 12, y))
            surface.blit(font_sm.render(val, True, HUD_WHITE), (px + 130, y))
            y += 20

        y += 12
        surface.blit(font_md.render("STORED RESOURCES", True, HUD_GREEN), (px + 12, y))
        y += 22
        for item, qty in [("Fuel Ore", p.fuel_ore), ("Organics", p.organics), ("Equipment", p.equipment)]:
            color = HUD_CYAN if qty > 0 else HUD_DIM
            surface.blit(font_sm.render(f"  {item:<14} {qty:>5}", True, color), (px + 12, y))
            y += 18

        if p.citadel_level < 4 and p.owner == (self._state.player.name if self._state else ""):
            y += 8
            next_lvl = p.citadel_level + 1
            cost = CITADEL_COSTS.get(next_lvl, {})
            hint = f"Next citadel: {cost.get('credits', 0):,} CR + {cost.get('equipment', 0)} equip"
            surface.blit(font_sm.render(hint, True, HUD_DIM), (px + 12, y))

    def _draw_action_menu(self, surface: pygame.Surface) -> None:
        font_sm = self.fonts["sm"]
        font_md = self.fonts["md"]
        actions = self._get_actions()

        px, py = 40, 395
        pw = self.width - 60

        pygame.draw.rect(surface, (3, 7, 4), (px, py, pw, self.height - py - 55))
        pygame.draw.rect(surface, HUD_DIM, (px, py, pw, self.height - py - 55), 1)

        surface.blit(font_md.render("ACTIONS", True, HUD_GREEN), (px + 12, py + 8))
        y = py + 36

        for i, action in enumerate(actions):
            is_sel = i == self.selected
            bg = (10, 28, 14) if is_sel else (3, 7, 4)
            pygame.draw.rect(surface, bg, (px + 4, y, pw - 8, 38))
            if is_sel:
                pygame.draw.rect(surface, HUD_GREEN, (px + 4, y, pw - 8, 38), 1)

            lbl = font_md.render(action["label"], True, HUD_WHITE if is_sel else HUD_GREEN)
            surface.blit(lbl, (px + 12, y + 6))
            desc = font_sm.render(action["desc"], True, (80, 160, 80) if is_sel else HUD_DIM)
            surface.blit(desc, (px + 12, y + 24))
            y += 44

    def _draw_message(self, surface: pygame.Surface) -> None:
        if not self.message or self.message_timer > 3.5:
            return
        font_md = self.fonts["md"]
        color = HUD_GREEN if self._msg_ok else HUD_RED
        lbl = font_md.render(self.message, True, color)
        surface.blit(lbl, (20, self.height - 50))

    def _draw_hints(self, surface: pygame.Surface) -> None:
        hints = self.fonts["sm"].render(
            "Up/Down: Select action    Enter: Execute    Esc: Leave orbit",
            True, HUD_DIM
        )
        surface.blit(hints, (10, self.height - 22))
