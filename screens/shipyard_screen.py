"""
Shipyard screen — buy ship upgrades or a whole new ship.
Available at well-equipped sectors. Pure terminal green aesthetic.
"""
import json
import os
import pygame
from engine.game_state import GameState, CargoHold
from audio.sound_gen import sounds

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

HUD_GREEN = (60, 220, 80)
HUD_AMBER = (220, 160, 40)
HUD_RED   = (220, 60, 40)
HUD_DIM   = (30, 60, 35)
HUD_WHITE = (200, 210, 200)
HUD_CYAN  = (60, 220, 220)
BG        = (4, 8, 6)

UPGRADES = [
    {"id": "cargo",    "name": "Expand Cargo Hold",   "desc": "+20 cargo capacity",        "cost": 5000,  "stat": "max_hold",     "delta": 20,  "cap": 500},
    {"id": "shields",  "name": "Shield Boost",         "desc": "+10 max shield points",     "cost": 8000,  "stat": "max_shields",  "delta": 10,  "cap": 120},
    {"id": "fighters", "name": "Fighter Bay Expansion","desc": "+10 max fighter capacity",  "cost": 6000,  "stat": "max_fighters", "delta": 10,  "cap": 80},
    {"id": "armor",    "name": "Reinforce Armor",      "desc": "+20 max armor points",      "cost": 7000,  "stat": "max_armor",    "delta": 20,  "cap": 150},
    {"id": "missiles", "name": "Missile Restock",      "desc": "+4 heat seekers",           "cost": 3000,  "stat": "missiles",     "delta": 4,   "cap": 999},
]

TRADE_IN_RATIO = 0.30
NEW_SHIP_BASE_TRADE = 5000


def _load_ships() -> dict:
    with open(os.path.join(DATA_DIR, "ships.json")) as f:
        return json.load(f)


def _bar(surface, x, y, w, h, pct, color, bg=(15, 30, 15)):
    pygame.draw.rect(surface, bg, (x, y, w, h))
    fill = int(w * max(0, min(1, pct)))
    if fill > 0:
        pygame.draw.rect(surface, color, (x, y, fill, h))
    pygame.draw.rect(surface, color, (x, y, w, h), 1)


class ShipyardScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.fonts: dict = {}
        self._initialized = False
        self._state: GameState | None = None
        self._all_ships: dict = {}
        self.sector_name = ""
        self.tab = "upgrades"
        self.selected = 0
        self.message = ""
        self.message_timer = 0.0
        self._msg_ok = True
        self._ship_list: list[tuple[str, dict]] = []

    def init_fonts(self) -> None:
        if self._initialized:
            return
        try:
            mono = pygame.font.match_font("courier,couriernew,dejavusansmono")
            self.fonts["sm"] = pygame.font.Font(mono, 13)
            self.fonts["md"] = pygame.font.Font(mono, 17)
            self.fonts["lg"] = pygame.font.Font(mono, 24)
            self.fonts["xl"] = pygame.font.Font(mono, 36)
        except Exception:
            self.fonts["sm"] = pygame.font.SysFont("monospace", 13)
            self.fonts["md"] = pygame.font.SysFont("monospace", 17)
            self.fonts["lg"] = pygame.font.SysFont("monospace", 24)
            self.fonts["xl"] = pygame.font.SysFont("monospace", 36)
        self._initialized = True

    def open(self, sector_name: str, game_state: GameState) -> None:
        self.init_fonts()
        self._state = game_state
        self.sector_name = sector_name
        self._all_ships = _load_ships()
        self.tab = "upgrades"
        self.selected = 0
        self.message = ""
        self.message_timer = 0.0
        self._rebuild_ship_list()

    def _rebuild_ship_list(self) -> None:
        current_id = self._state.ship.ship_id if self._state and self._state.ship else ""
        self._ship_list = [
            (sid, sdata) for sid, sdata in self._all_ships.items()
            if sid != current_id and sdata.get("price", -1) >= 0
        ]

    def _current_items(self) -> list:
        return UPGRADES if self.tab == "upgrades" else self._ship_list

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type != pygame.KEYDOWN:
            return None
        items = self._current_items()
        if event.key == pygame.K_ESCAPE:
            return "sector_map"
        elif event.key == pygame.K_TAB:
            self.tab = "ships" if self.tab == "upgrades" else "upgrades"
            self.selected = 0
            sounds.play("beep_low", 0.4)
        elif event.key in (pygame.K_UP, pygame.K_w):
            self.selected = (self.selected - 1) % max(1, len(items))
            sounds.play("beep_low", 0.3)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected = (self.selected + 1) % max(1, len(items))
            sounds.play("beep_low", 0.3)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.tab == "upgrades":
                self._buy_upgrade(self.selected)
            else:
                self._buy_ship(self.selected)
        return None

    def _buy_upgrade(self, idx: int) -> None:
        if not self._state or idx >= len(UPGRADES):
            return
        upg = UPGRADES[idx]
        cost = upg["cost"]
        if not self._state.player.spend_credits(cost):
            self._msg("Not enough credits.", ok=False)
            sounds.play("trade_fail", 0.7)
            return

        s = self._state.ship
        stat = upg["stat"]
        delta = upg["delta"]
        cap = upg["cap"]

        if stat == "max_shields":
            if s.max_shields >= cap:
                self._state.player.add_credits(cost)
                self._msg("Shields already at maximum.", ok=False)
                return
            s.max_shields = min(cap, s.max_shields + delta)
            s.shields = min(s.max_shields, s.shields + delta)
        elif stat == "max_fighters":
            if s.max_fighters >= cap:
                self._state.player.add_credits(cost)
                self._msg("Fighter bays already at maximum.", ok=False)
                return
            s.max_fighters = min(cap, s.max_fighters + delta)
        elif stat == "max_armor":
            if s.max_armor >= cap:
                self._state.player.add_credits(cost)
                self._msg("Armor already at maximum.", ok=False)
                return
            s.max_armor = min(cap, s.max_armor + delta)
            s.armor = min(s.max_armor, s.armor + delta)
        elif stat == "max_hold" and self._state.cargo:
            if self._state.cargo.capacity >= cap:
                self._state.player.add_credits(cost)
                self._msg("Cargo hold already at maximum.", ok=False)
                return
            self._state.cargo.capacity = min(cap, self._state.cargo.capacity + delta)
        elif stat == "missiles":
            s.missile_counts["heat_seeker"] = s.missile_counts.get("heat_seeker", 0) + delta
            if "heat_seeker" not in s.weapons:
                s.weapons.append("heat_seeker")

        self._msg(f"Installed: {upg['name']}. -{cost:,} CR.")
        self._state.player.add_log(f"Upgraded: {upg['name']}")
        sounds.play("trade_ok", 0.8)

    def _buy_ship(self, idx: int) -> None:
        if not self._state or idx >= len(self._ship_list):
            return
        ship_id, ship_data = self._ship_list[idx]
        price = ship_data.get("price", 0)

        current_id = self._state.ship.ship_id
        current_data = self._all_ships.get(current_id, {})
        trade_in = max(NEW_SHIP_BASE_TRADE, int(current_data.get("price", 0) * TRADE_IN_RATIO))
        net_cost = max(0, price - trade_in)

        if not self._state.player.spend_credits(net_cost):
            self._msg(f"Need {net_cost:,} CR after trade-in of {trade_in:,} CR.", ok=False)
            sounds.play("trade_fail", 0.7)
            return

        # Rebuild ship
        from engine.game_state import PlayerShip
        self._state.ship = PlayerShip(
            ship_id=ship_id,
            shields=float(ship_data["shields"]),
            max_shields=float(ship_data["max_shields"]),
            armor=float(ship_data["armor"]),
            max_armor=float(ship_data["armor"]),
            fighters=min(self._state.ship.fighters, ship_data["max_fighters"]),
            max_fighters=ship_data["max_fighters"],
            weapons=self._state._expand_weapons(ship_data["weapons"]),
            missile_counts=self._state._init_missile_counts(ship_data["weapons"]),
        )
        # Trim cargo if new hold is smaller
        if self._state.cargo:
            new_cap = ship_data["hold"]
            self._state.cargo.capacity = new_cap
            used = self._state.cargo.used
            while used > new_cap and self._state.cargo.contents:
                item = next(iter(self._state.cargo.contents))
                self._state.cargo.contents.pop(item)
                used = self._state.cargo.used

        self._rebuild_ship_list()
        self._msg(f"Acquired {ship_data['name']}! Trade-in: {trade_in:,} CR")
        self._state.player.add_log(f"New ship: {ship_data['name']}")
        sounds.play("mission_accept", 0.9)

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
        self._draw_header(surface)
        self._draw_left_panel(surface)
        self._draw_right_panel(surface)
        self._draw_message(surface)
        self._draw_hints(surface)

    def _draw_header(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, (5, 14, 8), (0, 0, self.width, 50))
        pygame.draw.line(surface, (40, 100, 50), (0, 50), (self.width, 50), 1)
        title = self.fonts["xl"].render(f"SHIPYARD — {self.sector_name.upper()}", True, HUD_GREEN)
        surface.blit(title, (20, 8))
        if self._state:
            cr = self.fonts["md"].render(f"CREDITS: {self._state.player.credits:,}", True, HUD_AMBER)
            surface.blit(cr, (self.width - cr.get_width() - 20, 14))

    def _draw_left_panel(self, surface: pygame.Surface) -> None:
        font_sm = self.fonts["sm"]
        font_md = self.fonts["md"]
        font_lg = self.fonts["lg"]

        px, py, pw, ph = 20, 60, self.width // 2 - 30, self.height - 100

        # Tabs
        for i, (tid, tlabel) in enumerate([("upgrades", "UPGRADES"), ("ships", "BUY SHIP")]):
            is_tab = tid == self.tab
            tab_x = px + i * 180
            pygame.draw.rect(surface, (10, 30, 14) if is_tab else (4, 10, 6), (tab_x, py, 170, 28))
            pygame.draw.rect(surface, HUD_GREEN if is_tab else HUD_DIM, (tab_x, py, 170, 28), 1)
            tlbl = font_md.render(tlabel, True, HUD_GREEN if is_tab else HUD_DIM)
            surface.blit(tlbl, (tab_x + 10, py + 5))

        py += 36

        pygame.draw.rect(surface, (3, 7, 4), (px, py, pw, ph - 36))
        pygame.draw.rect(surface, HUD_DIM, (px, py, pw, ph - 36), 1)

        items = self._current_items()
        item_h = 72 if self.tab == "upgrades" else 55
        y = py + 8

        for i, item in enumerate(items):
            is_sel = i == self.selected
            iy = y + i * item_h
            bg = (10, 28, 14) if is_sel else (3, 7, 4)
            pygame.draw.rect(surface, bg, (px + 4, iy, pw - 8, item_h - 4))
            if is_sel:
                pygame.draw.rect(surface, HUD_GREEN, (px + 4, iy, pw - 8, item_h - 4), 1)

            if self.tab == "upgrades":
                upg = item
                name = font_md.render(upg["name"], True, HUD_WHITE if is_sel else HUD_GREEN)
                surface.blit(name, (px + 12, iy + 6))
                desc = font_sm.render(upg["desc"], True, HUD_DIM if not is_sel else (100, 180, 100))
                surface.blit(desc, (px + 12, iy + 28))
                cost = font_md.render(f"{upg['cost']:,} CR", True, HUD_AMBER)
                surface.blit(cost, (px + pw - cost.get_width() - 16, iy + 10))
            else:
                sid, sdata = item
                name = font_md.render(sdata.get("name", sid), True, HUD_WHITE if is_sel else HUD_GREEN)
                surface.blit(name, (px + 12, iy + 6))
                cls = font_sm.render(sdata.get("class", ""), True, HUD_DIM if not is_sel else (100, 180, 100))
                surface.blit(cls, (px + 12, iy + 26))
                price = sdata.get("price", 0)
                current_id = self._state.ship.ship_id if self._state and self._state.ship else ""
                trade_in = max(NEW_SHIP_BASE_TRADE, int(self._all_ships.get(current_id, {}).get("price", 0) * TRADE_IN_RATIO))
                net = max(0, price - trade_in)
                cost_lbl = font_sm.render(f"Net: {net:,} CR  (trade-in: {trade_in:,})", True, HUD_AMBER)
                surface.blit(cost_lbl, (px + 12, iy + 40))

    def _draw_right_panel(self, surface: pygame.Surface) -> None:
        font_sm = self.fonts["sm"]
        font_md = self.fonts["md"]
        font_lg = self.fonts["lg"]

        px = self.width // 2 + 10
        py = 60
        pw = self.width // 2 - 30
        ph = self.height - 100

        pygame.draw.rect(surface, (3, 7, 4), (px, py, pw, ph))
        pygame.draw.rect(surface, HUD_DIM, (px, py, pw, ph), 1)

        if not self._state or not self._state.ship:
            return

        s = self._state.ship
        ship_data = self._state.get_ship_data(s.ship_id)
        ship_name = ship_data.get("name", s.ship_id)

        title = font_lg.render("CURRENT SHIP", True, HUD_GREEN)
        surface.blit(title, (px + 12, py + 10))
        name_lbl = font_md.render(ship_name, True, HUD_WHITE)
        surface.blit(name_lbl, (px + 12, py + 38))
        cls_lbl = font_sm.render(ship_data.get("class", ""), True, HUD_DIM)
        surface.blit(cls_lbl, (px + 12, py + 60))

        # Stats with bars
        stats = [
            ("Shields", s.shields, s.max_shields, 120),
            ("Armor",   s.armor,   s.max_armor,   150),
            ("Fighters",float(s.fighters), float(s.max_fighters), 80),
            ("Cargo",   float(self._state.cargo.capacity if self._state.cargo else 0), 500.0, 500),
        ]
        sy = py + 88
        for label, current, maximum, cap in stats:
            lbl = font_sm.render(f"{label}", True, HUD_DIM)
            surface.blit(lbl, (px + 12, sy))
            val = font_sm.render(f"{int(current)}/{int(maximum)}", True, HUD_WHITE)
            surface.blit(val, (px + 100, sy))
            pct = current / max(1, cap)
            _bar(surface, px + 160, sy + 2, pw - 175, 10, pct, HUD_GREEN)
            sy += 22

        # Weapons
        sy += 10
        surface.blit(font_md.render("WEAPONS", True, HUD_GREEN), (px + 12, sy))
        sy += 22
        for wid in s.weapons[:6]:
            wd = self._state.get_weapon_data(wid)
            w_name = wd.get("name", wid) if wd else wid
            count = s.missile_counts.get(wid, "")
            suffix = f"  x{count}" if count else ""
            surface.blit(font_sm.render(f"  {w_name}{suffix}", True, HUD_AMBER), (px + 12, sy))
            sy += 16

        # Preview of selected upgrade/ship
        sy += 16
        pygame.draw.line(surface, HUD_DIM, (px + 12, sy), (px + pw - 12, sy), 1)
        sy += 10
        items = self._current_items()
        if self.selected < len(items):
            surface.blit(font_md.render("AFTER PURCHASE:", True, HUD_DIM), (px + 12, sy))
            sy += 22
            if self.tab == "upgrades":
                upg = items[self.selected]
                stat = upg["stat"]
                delta = upg["delta"]
                changes = {
                    "max_shields":  f"Shields max: {s.max_shields} → {min(upg['cap'], s.max_shields + delta)}",
                    "max_armor":    f"Armor max: {s.max_armor} → {min(upg['cap'], s.max_armor + delta)}",
                    "max_fighters": f"Fighters max: {s.max_fighters} → {min(upg['cap'], s.max_fighters + delta)}",
                    "max_hold":     f"Cargo: {self._state.cargo.capacity if self._state.cargo else 0} → {min(upg['cap'], (self._state.cargo.capacity if self._state.cargo else 0) + delta)}",
                    "missiles":     f"+{delta} heat seekers in hold",
                }
                if stat in changes:
                    lbl = font_sm.render(changes[stat], True, HUD_CYAN)
                    surface.blit(lbl, (px + 12, sy))
            else:
                sid, sdata = items[self.selected]
                for key, label in [("shields","Shields"), ("armor","Armor"), ("hold","Cargo"), ("max_fighters","Fighters")]:
                    val = sdata.get(key, 0)
                    lbl = font_sm.render(f"  {label}: {val}", True, HUD_CYAN)
                    surface.blit(lbl, (px + 12, sy))
                    sy += 16

    def _draw_message(self, surface: pygame.Surface) -> None:
        if not self.message or self.message_timer > 3.0:
            return
        font_md = self.fonts["md"]
        color = HUD_GREEN if self._msg_ok else HUD_RED
        lbl = font_md.render(self.message, True, color)
        surface.blit(lbl, (20, self.height - 50))

    def _draw_hints(self, surface: pygame.Surface) -> None:
        hints = self.fonts["sm"].render(
            "Up/Down: Select    Tab: Switch panel    Enter: Purchase    Esc: Leave",
            True, HUD_DIM
        )
        surface.blit(hints, (10, self.height - 22))
