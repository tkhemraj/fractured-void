"""
Manages an active combat encounter.
Owns all ships, projectiles, AI controllers, and collision detection.
The combat screen calls update() each frame and reads state for rendering.
"""
import math
import random
import json
import os
from combat.ship_3d import CombatShip, Vec3, Projectile
from combat.enemy_ai import EnemyAI
from engine.event_bus import bus

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _load_weapons() -> dict:
    with open(os.path.join(DATA_DIR, "weapons.json")) as f:
        return json.load(f)


FOCAL_LENGTH = 800.0
HIT_RADIUS = 35.0


class CombatEngine:
    def __init__(self, player_ship_data: dict, enemies: list[dict]):
        """
        enemies: list of {"ship_data": dict, "skill": str, "faction": str}
        """
        self._weapon_data = _load_weapons()
        self.rng = random.Random()

        # Player ship starts at origin facing enemies
        self.player = CombatShip("player", player_ship_data, Vec3(0, 0, 0))
        self.player.heading = Vec3(0, 0, -1)

        self.enemies: list[CombatShip] = []
        self.ai_controllers: list[EnemyAI] = []
        self._spawn_enemies(enemies)

        self.projectiles: list[Projectile] = []
        self.explosions: list[dict] = []

        # Player controls state
        self.player_pitch = 0.0
        self.player_yaw = 0.0
        self.player_roll = 0.0
        self.player_afterburner = False
        self.player_throttle = 0.6

        # Weapon cooldowns
        self.player_gun_cooldown = 0.0
        self.player_missile_cooldown = 0.0

        # Target lock
        self.target_index = 0 if self.enemies else -1

        self.result = None  # "victory" | "defeat" | "fled"
        self.time_elapsed = 0.0

        self.player_missile_counts: dict[str, int] = {}
        self._init_player_missiles(player_ship_data)

    def _spawn_enemies(self, enemies: list[dict]) -> None:
        angle_step = (2 * math.pi) / max(len(enemies), 1)
        for i, enemy_spec in enumerate(enemies):
            angle = i * angle_step
            dist = self.rng.uniform(600, 900)
            pos = Vec3(
                math.cos(angle) * dist * 0.5,
                self.rng.uniform(-50, 50),
                -dist,
            )
            ship = CombatShip(
                enemy_spec.get("ship_id", "scout_marauder"),
                enemy_spec["ship_data"],
                pos,
                faction=enemy_spec.get("faction", ""),
            )
            self.enemies.append(ship)
            self.ai_controllers.append(EnemyAI(ship, skill=enemy_spec.get("skill", "novice")))

    def _init_player_missiles(self, ship_data: dict) -> None:
        weapons = ship_data.get("weapons", [])
        for w in weapons:
            if "_x" in w:
                base, count = w.rsplit("_x", 1)
                count = int(count)
            else:
                base, count = w, None
            if base in self._weapon_data:
                wd = self._weapon_data[base]
                if wd["type"] in ("missile", "torpedo"):
                    default = wd.get("count", 4)
                    self.player_missile_counts[base] = self.player_missile_counts.get(base, 0) + (count or default)

    @property
    def current_target(self) -> CombatShip | None:
        living = [e for e in self.enemies if e.alive]
        if not living or self.target_index < 0:
            return None
        return living[self.target_index % len(living)]

    def cycle_target(self) -> None:
        living = [e for e in self.enemies if e.alive]
        if living:
            self.target_index = (self.target_index + 1) % len(living)

    def player_fire_gun(self) -> None:
        if self.player_gun_cooldown > 0:
            return
        # Use the first gun weapon
        weapon_id = self._get_player_gun()
        if not weapon_id:
            return
        wd = self._weapon_data[weapon_id]
        self.player_gun_cooldown = wd["fire_rate"]

        # Add spread based on weapon type
        spread = 0.02
        vel = Vec3(
            self.player.heading.x * wd["speed"] + self.rng.uniform(-spread, spread) * wd["speed"],
            self.player.heading.y * wd["speed"] + self.rng.uniform(-spread, spread) * wd["speed"],
            self.player.heading.z * wd["speed"],
        )
        p = Projectile(Vec3(self.player.pos.x, self.player.pos.y, self.player.pos.z), vel, wd, "player")
        self.projectiles.append(p)
        bus.post("gun_fired", weapon=weapon_id)

    def player_fire_missile(self, weapon_id: str) -> bool:
        if self.player_missile_cooldown > 0:
            return False
        if self.player_missile_counts.get(weapon_id, 0) <= 0:
            return False
        target = self.current_target
        if not target and self._weapon_data[weapon_id].get("tracking", False):
            return False

        wd = self._weapon_data[weapon_id]
        self.player_missile_cooldown = wd["fire_rate"]
        self.player_missile_counts[weapon_id] -= 1

        vel = self.player.heading * wd["speed"]
        p = Projectile(Vec3(self.player.pos.x, self.player.pos.y, self.player.pos.z), vel, wd, "player")
        self.projectiles.append(p)
        bus.post("missile_fired", weapon=weapon_id, remaining=self.player_missile_counts[weapon_id])
        return True

    def _get_player_gun(self) -> str | None:
        ship_guns = ["mass_driver", "laser_cannon", "neutron_gun", "tachyon_gun"]
        for w in ship_guns:
            if w in self._weapon_data:
                return w
        return None

    def update(self, dt: float, player_inputs: dict) -> None:
        if self.result:
            return
        self.time_elapsed += dt

        self._handle_player_inputs(dt, player_inputs)
        self._update_player_position(dt)
        self._update_enemies(dt)
        self._update_projectiles(dt)
        self._check_collisions()
        self._update_cooldowns(dt)
        self._update_explosions(dt)
        self._check_result()

    def _handle_player_inputs(self, dt: float, inputs: dict) -> None:
        turn_speed = math.radians(90) * dt

        if inputs.get("pitch_up"):
            self.player_pitch = -turn_speed
        elif inputs.get("pitch_down"):
            self.player_pitch = turn_speed
        else:
            self.player_pitch = 0.0

        if inputs.get("yaw_left"):
            self.player_yaw = -turn_speed
        elif inputs.get("yaw_right"):
            self.player_yaw = turn_speed
        else:
            self.player_yaw = 0.0

        self.player_afterburner = inputs.get("afterburner", False)

        # Apply rotation to player heading
        h = self.player.heading
        if self.player_pitch != 0:
            # Pitch: rotate around the X-axis perpendicular to heading
            cos_p = math.cos(self.player_pitch)
            sin_p = math.sin(self.player_pitch)
            new_y = h.y * cos_p - h.z * sin_p
            new_z = h.y * sin_p + h.z * cos_p
            h = Vec3(h.x, new_y, new_z).normalized()
        if self.player_yaw != 0:
            cos_y = math.cos(self.player_yaw)
            sin_y = math.sin(self.player_yaw)
            new_x = h.x * cos_y - h.z * sin_y
            new_z = h.x * sin_y + h.z * cos_y
            h = Vec3(new_x, h.y, new_z).normalized()
        self.player.heading = h

        if inputs.get("fire_gun"):
            self.player_fire_gun()
        if inputs.get("fire_missile"):
            missile_id = inputs.get("missile_id", "heat_seeker")
            self.player_fire_missile(missile_id)

    def _update_player_position(self, dt: float) -> None:
        speed = self.player.afterburner_speed if self.player_afterburner else (self.player.speed * self.player_throttle)
        self.player.velocity = self.player.heading * speed
        self.player.pos = self.player.pos + self.player.velocity * dt

    def _update_enemies(self, dt: float) -> None:
        for ship, ai in zip(self.enemies, self.ai_controllers):
            if not ship.alive:
                continue
            actions = ai.update(dt, self.player)
            for action, value in actions:
                if action == "fire" and value == "primary":
                    self._enemy_fire(ship)
                elif action == "afterburner":
                    ship.afterburning = value
            ship.pos = ship.pos + ship.velocity * dt

    def _enemy_fire(self, ship: CombatShip) -> None:
        wd = self._weapon_data.get("mass_driver", {})
        if not wd:
            return
        to_player = (self.player.pos - ship.pos).normalized()
        vel = to_player * wd.get("speed", 600)
        p = Projectile(Vec3(ship.pos.x, ship.pos.y, ship.pos.z), vel, wd, "enemy")
        self.projectiles.append(p)

    def _update_projectiles(self, dt: float) -> None:
        target = self.current_target
        player_pos = self.player.pos
        for p in self.projectiles:
            if not p.alive:
                continue
            if p.owner == "player" and target:
                p.update(dt, target.pos)
            elif p.owner == "enemy":
                p.update(dt, player_pos)
            else:
                p.update(dt)
        self.projectiles = [p for p in self.projectiles if p.alive]

    def _check_collisions(self) -> None:
        for p in self.projectiles:
            if not p.alive:
                continue

            if p.owner == "player":
                for ship in self.enemies:
                    if not ship.alive:
                        continue
                    if (p.pos - ship.pos).length() < HIT_RADIUS:
                        ship.take_hit(p.weapon_data["damage"])
                        p.alive = False
                        self._spawn_explosion(ship.pos, small=True)
                        if not ship.alive:
                            self._spawn_explosion(ship.pos, small=False)
                            bus.post("enemy_destroyed", faction=ship.faction)
                        break

            elif p.owner == "enemy":
                if (p.pos - self.player.pos).length() < HIT_RADIUS:
                    destroyed = self.player.take_hit(p.weapon_data["damage"])
                    p.alive = False
                    self._spawn_explosion(self.player.pos, small=True)
                    if destroyed:
                        self._spawn_explosion(self.player.pos, small=False)
                    bus.post("player_hit", damage=p.weapon_data["damage"])

    def _spawn_explosion(self, pos: Vec3, small: bool) -> None:
        self.explosions.append({
            "pos": Vec3(pos.x, pos.y, pos.z),
            "timer": 0.0,
            "max_time": 0.4 if small else 1.5,
            "small": small,
        })

    def _update_explosions(self, dt: float) -> None:
        for exp in self.explosions:
            exp["timer"] += dt
        self.explosions = [e for e in self.explosions if e["timer"] < e["max_time"]]

    def _update_cooldowns(self, dt: float) -> None:
        self.player_gun_cooldown = max(0.0, self.player_gun_cooldown - dt)
        self.player_missile_cooldown = max(0.0, self.player_missile_cooldown - dt)

    def _check_result(self) -> None:
        if not self.player.alive:
            self.result = "defeat"
            bus.post("combat_ended", result="defeat")
        elif all(not e.alive for e in self.enemies):
            self.result = "victory"
            bus.post("combat_ended", result="victory")
