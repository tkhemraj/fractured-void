"""
A ship in 3D combat space.
Position is in world-space units. Player is always at origin facing -Z.
Ships are rendered using perspective projection (the same technique Wing Commander used).
"""
import math
import random
from dataclasses import dataclass, field
from typing import Optional
import pygame

FOCAL_LENGTH = 800.0


@dataclass
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> "Vec3":
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def length(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalized(self) -> "Vec3":
        l = self.length()
        if l < 0.0001:
            return Vec3(0, 0, 1)
        return Vec3(self.x / l, self.y / l, self.z / l)

    def dot(self, other: "Vec3") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z


class Projectile:
    def __init__(self, pos: Vec3, velocity: Vec3, weapon_data: dict, owner: str):
        self.pos = pos
        self.velocity = velocity
        self.weapon_data = weapon_data
        self.owner = owner
        self.age = 0.0
        self.max_age = 3.0
        self.tracking = weapon_data.get("tracking", False)
        self.tracking_strength = weapon_data.get("tracking_strength", 0.0)
        self.alive = True

    def update(self, dt: float, target_pos: Optional[Vec3] = None) -> None:
        if self.tracking and target_pos and self.tracking_strength > 0:
            to_target = (target_pos - self.pos).normalized()
            current_dir = self.velocity.normalized()
            speed = self.velocity.length()
            t = min(1.0, self.tracking_strength * dt)
            new_dir = Vec3(
                current_dir.x + (to_target.x - current_dir.x) * t,
                current_dir.y + (to_target.y - current_dir.y) * t,
                current_dir.z + (to_target.z - current_dir.z) * t,
            ).normalized()
            self.velocity = new_dir * speed

        self.pos = self.pos + self.velocity * dt
        self.age += dt
        if self.age > self.max_age:
            self.alive = False


class CombatShip:
    """Represents any ship in the 3D combat arena (player or enemy NPC)."""

    def __init__(self, ship_id: str, ship_data: dict, pos: Vec3, faction: str = ""):
        self.ship_id = ship_id
        self.ship_data = ship_data
        self.faction = faction
        self.pos = pos
        self.velocity = Vec3(0, 0, 0)
        self.heading = Vec3(0, 0, -1)

        self.shields = float(ship_data.get("shields", 30))
        self.max_shields = float(ship_data.get("max_shields", ship_data.get("shields", 30)))
        self.armor = float(ship_data.get("armor", 40))
        self.max_armor = float(ship_data.get("armor", 40))
        self.speed = float(ship_data.get("speed", 5))
        self.afterburner_speed = float(ship_data.get("afterburner", self.speed * 1.6))
        self.turn_rate = float(ship_data.get("turn_rate", 3.0))

        self.alive = True
        self.exploding = False
        self.explosion_timer = 0.0
        self.color = tuple(ship_data.get("color", [180, 180, 180]))

        self.fire_cooldowns: dict[str, float] = {}
        self.afterburning = False

    @property
    def current_speed(self) -> float:
        return self.afterburner_speed if self.afterburning else self.speed

    @property
    def shield_pct(self) -> float:
        return max(0.0, self.shields / self.max_shields)

    @property
    def armor_pct(self) -> float:
        return max(0.0, self.armor / self.max_armor)

    def take_hit(self, damage: float) -> bool:
        """Returns True if the ship is destroyed."""
        if self.shields > 0:
            absorbed = min(self.shields, damage * 0.75)
            self.shields -= absorbed
            damage -= absorbed
        self.armor -= damage
        if self.armor <= 0:
            self.alive = False
            self.exploding = True
            return True
        return False

    def project_to_screen(
        self, focal: float, screen_cx: float, screen_cy: float
    ) -> tuple[Optional[float], Optional[float], float]:
        """
        Perspective project this ship's 3D position onto the screen.
        Returns (screen_x, screen_y, scale) or (None, None, 0) if behind camera.
        The player camera looks down -Z from the origin.
        """
        z = -self.pos.z
        if z <= 10:
            return None, None, 0.0
        scale = focal / z
        sx = self.pos.x * scale + screen_cx
        sy = -self.pos.y * scale + screen_cy
        return sx, sy, scale

    def distance_to(self, other: "CombatShip") -> float:
        return (self.pos - other.pos).length()

    def angle_to(self, target: "CombatShip") -> float:
        """Returns angle in degrees between this ship's heading and target direction."""
        to_target = (target.pos - self.pos).normalized()
        dot = max(-1.0, min(1.0, self.heading.dot(to_target)))
        return math.degrees(math.acos(dot))

    def update_explosion(self, dt: float) -> None:
        self.explosion_timer += dt
