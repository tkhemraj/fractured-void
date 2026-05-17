"""
Wing Commander-style combat screen.
Handles player input, feeds it to CombatEngine, renders via SpaceRenderer + HUDRenderer.
"""
import pygame
from combat.combat_engine import CombatEngine
from rendering.space_renderer import SpaceRenderer
from rendering.hud_renderer import HUDRenderer
from engine.event_bus import bus


CONTROLS = {
    "pitch_up":    [pygame.K_w, pygame.K_UP],
    "pitch_down":  [pygame.K_s, pygame.K_DOWN],
    "yaw_left":    [pygame.K_a, pygame.K_LEFT],
    "yaw_right":   [pygame.K_d, pygame.K_RIGHT],
    "fire_gun":    [pygame.K_SPACE],
    "afterburner": [pygame.K_LSHIFT, pygame.K_RSHIFT],
    "target_next": [pygame.K_t],
    "fire_missile": [pygame.K_f],
    "flee":        [pygame.K_ESCAPE],
}


class CombatScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.engine: CombatEngine | None = None
        self.space = SpaceRenderer(width, height)
        self.hud = HUDRenderer(width, height)
        self.ship_name = "Cinder Pact"
        self.in_fracture_zone = False
        self.result_timer = 0.0
        self.result_shown = False
        self._flash_messages: list[dict] = []
        self._missile_id = "heat_seeker"

    def start_combat(
        self,
        player_ship_data: dict,
        enemies: list[dict],
        ship_name: str = "Cinder Pact",
        in_fracture_zone: bool = False,
    ) -> None:
        self.engine = CombatEngine(player_ship_data, enemies)
        self.ship_name = ship_name
        self.in_fracture_zone = in_fracture_zone
        self.result_timer = 0.0
        self.result_shown = False
        self._flash_messages = []

        # Choose first available missile
        if self.engine.player_missile_counts:
            self._missile_id = next(iter(self.engine.player_missile_counts))

        bus.subscribe("player_hit", self._on_player_hit)
        bus.subscribe("enemy_destroyed", self._on_enemy_destroyed)
        bus.subscribe("missile_fired", self._on_missile_fired)
        bus.subscribe("combat_ended", self._on_combat_ended)

    def stop(self) -> None:
        try:
            bus.unsubscribe("player_hit", self._on_player_hit)
            bus.unsubscribe("enemy_destroyed", self._on_enemy_destroyed)
            bus.unsubscribe("missile_fired", self._on_missile_fired)
            bus.unsubscribe("combat_ended", self._on_combat_ended)
        except (ValueError, KeyError):
            pass

    def _on_player_hit(self, damage: float) -> None:
        self._flash("HIT!", (255, 60, 60), duration=0.4)

    def _on_enemy_destroyed(self, faction: str) -> None:
        self._flash("ENEMY DESTROYED", (100, 255, 100), duration=1.2)

    def _on_missile_fired(self, weapon: str, remaining: int) -> None:
        self._flash(f"MISSILE AWAY  ({remaining} left)", (255, 200, 60), duration=0.8)

    def _on_combat_ended(self, result: str) -> None:
        self.result_shown = True
        if result == "victory":
            self._flash("MISSION COMPLETE", (60, 255, 60), duration=999)
        else:
            self._flash("SHIP DESTROYED", (255, 40, 40), duration=999)

    def _flash(self, msg: str, color: tuple, duration: float = 0.6) -> None:
        self._flash_messages.append({"msg": msg, "color": color, "timer": 0.0, "duration": duration})
        if len(self._flash_messages) > 5:
            self._flash_messages = self._flash_messages[-5:]

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Returns a screen transition string or None."""
        if not self.engine:
            return None

        if event.type == pygame.KEYDOWN:
            if event.key in CONTROLS["target_next"]:
                self.engine.cycle_target()
            if event.key in CONTROLS["flee"]:
                self.engine.result = "fled"
                return None
            if event.key == pygame.K_1 and self.engine.player_missile_counts:
                keys = list(self.engine.player_missile_counts.keys())
                idx = keys.index(self._missile_id) if self._missile_id in keys else 0
                self._missile_id = keys[(idx + 1) % len(keys)]

        if self.result_shown and self.result_timer > 2.0:
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                return "sector_map"
        return None

    def update(self, dt: float) -> str | None:
        if not self.engine:
            return None

        keys = pygame.key.get_pressed()
        inputs = {
            "pitch_up":    any(keys[k] for k in CONTROLS["pitch_up"]),
            "pitch_down":  any(keys[k] for k in CONTROLS["pitch_down"]),
            "yaw_left":    any(keys[k] for k in CONTROLS["yaw_left"]),
            "yaw_right":   any(keys[k] for k in CONTROLS["yaw_right"]),
            "fire_gun":    any(keys[k] for k in CONTROLS["fire_gun"]),
            "afterburner": any(keys[k] for k in CONTROLS["afterburner"]),
            "fire_missile": any(keys[k] for k in CONTROLS["fire_missile"]),
            "missile_id":  self._missile_id,
        }

        self.engine.update(dt, inputs)
        self.space.update(dt, speed=self.engine.player.velocity.length() * 0.05 + 2.0)

        for msg in self._flash_messages:
            msg["timer"] += dt
        self._flash_messages = [m for m in self._flash_messages if m["timer"] < m["duration"]]

        if self.engine.result:
            self.result_timer += dt
            if self.result_timer > 4.0 and not self.result_shown:
                return "sector_map"

        return None

    def draw(self, surface: pygame.Surface) -> None:
        if not self.engine:
            surface.fill((0, 0, 0))
            return

        target = self.engine.current_target
        self.space.draw_background(surface, self.in_fracture_zone)
        self.space.draw_ships(surface, self.engine.enemies, target)
        self.space.draw_projectiles(surface, self.engine.projectiles)
        self.space.draw_explosions(surface, self.engine.explosions)
        self.hud.draw(surface, self.engine, 0.016, self.ship_name)
        self._draw_flash_messages(surface)
        self._draw_controls_hint(surface)

    def _draw_flash_messages(self, surface: pygame.Surface) -> None:
        if not self._flash_messages or not self.hud.fonts:
            return
        font = self.hud.fonts.get("lg")
        if not font:
            return
        W, H = self.width, self.height
        y = H // 2 - 80
        for msg in reversed(self._flash_messages):
            t = msg["timer"] / max(0.01, msg["duration"])
            alpha = int(255 * (1 - min(1.0, t * 1.5)))
            color = msg["color"] + (alpha,)
            txt = font.render(msg["msg"], True, msg["color"])
            x = W // 2 - txt.get_width() // 2
            surface.blit(txt, (x, y))
            y -= 32

    def _draw_controls_hint(self, surface: pygame.Surface) -> None:
        if not self.hud.fonts or self.engine.time_elapsed > 8.0:
            return
        font = self.hud.fonts.get("sm")
        if not font:
            return
        hints = [
            "WASD/Arrows: Steer",
            "Space: Fire guns",
            "F: Fire missile",
            "T: Cycle target",
            "Shift: Afterburner",
        ]
        y = self.height - int(self.height * 0.22) - len(hints) * 14 - 10
        for hint in hints:
            lbl = font.render(hint, True, (50, 80, 50))
            surface.blit(lbl, (self.width // 2 - 60, y))
            y += 14
