"""
3D space renderer using Pygame.
Star field with parallax + perspective-projected ships (Wing Commander-style sprite scaling).
Ships are drawn as polygon silhouettes with color, scaled by distance.
Real art can replace the polygon drawing later — the projection math stays the same.
"""
import math
import random
import pygame
from combat.ship_3d import CombatShip, Vec3, Projectile, FOCAL_LENGTH


class Star:
    def __init__(self, rng: random.Random, width: int, height: int):
        self.reset(rng, width, height, initial=True)

    def reset(self, rng: random.Random, width: int, height: int, initial: bool = False) -> None:
        self.x = rng.uniform(0, width)
        self.y = rng.uniform(0, height)
        self.z = rng.uniform(1, width) if not initial else rng.uniform(1, width * 0.5)
        self.max_z = float(width)

    def update(self, speed: float, width: int, height: int, rng: random.Random) -> None:
        self.z -= speed
        if self.z <= 0:
            self.reset(rng, width, height)
            self.z = self.max_z

    def draw(self, surface: pygame.Surface, width: int, height: int) -> None:
        cx, cy = width / 2, height / 2
        scale = self.max_z / self.z
        sx = int((self.x - cx) * scale + cx)
        sy = int((self.y - cy) * scale + cy)
        if 0 <= sx < width and 0 <= sy < height:
            brightness = int(255 * (1 - self.z / self.max_z))
            r = max(1, min(3, int(scale)))
            color = (brightness, brightness, min(255, brightness + 20))
            if r == 1:
                surface.set_at((sx, sy), color)
            else:
                pygame.draw.circle(surface, color, (sx, sy), r)


SHIP_SHAPES = {
    "default": [
        (0, -1.0),
        (0.6, 0.5),
        (0.0, 0.0),
        (-0.6, 0.5),
    ],
    "apex_enforcer": [
        (0, -1.2),
        (0.8, 0.4),
        (0.3, 0.8),
        (0, 0.5),
        (-0.3, 0.8),
        (-0.8, 0.4),
    ],
    "scout_marauder": [
        (0, -1.0),
        (0.4, 0.7),
        (-0.4, 0.7),
    ],
    "ghost_wraith": [
        (0, -1.4),
        (1.0, 0.0),
        (0.6, 0.8),
        (0, 0.3),
        (-0.6, 0.8),
        (-1.0, 0.0),
    ],
}


class SpaceRenderer:
    def __init__(self, width: int, height: int, num_stars: int = 300):
        self.width = width
        self.height = height
        self.cx = width // 2
        self.cy = height // 2
        self.rng = random.Random(7)
        self.stars = [Star(self.rng, width, height) for _ in range(num_stars)]
        self.nebula_surf: pygame.Surface | None = None
        self._build_nebula()

    def _build_nebula(self) -> None:
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        rng = random.Random(13)
        for _ in range(12):
            cx = rng.randint(0, self.width)
            cy = rng.randint(0, self.height)
            r = rng.randint(80, 250)
            color_choice = rng.choice([
                (80, 40, 120, 25),
                (40, 80, 120, 20),
                (120, 50, 50, 18),
            ])
            for i in range(r, 0, -max(1, r // 8)):
                alpha = int(color_choice[3] * (i / r))
                c = (color_choice[0], color_choice[1], color_choice[2], alpha)
                pygame.draw.circle(surf, c, (cx, cy), i)
        self.nebula_surf = surf

    def update(self, dt: float, speed: float = 5.0) -> None:
        for star in self.stars:
            star.update(speed * dt * 30, self.width, self.height, self.rng)

    def draw_background(self, surface: pygame.Surface, in_fracture_zone: bool = False) -> None:
        surface.fill((3, 3, 12))
        if in_fracture_zone and self.nebula_surf:
            surface.blit(self.nebula_surf, (0, 0))
        for star in self.stars:
            star.draw(surface, self.width, self.height)

    def draw_ships(
        self,
        surface: pygame.Surface,
        enemies: list[CombatShip],
        target: CombatShip | None,
    ) -> list[tuple[CombatShip, int, int, float]]:
        """
        Draw all enemy ships using perspective projection.
        Returns list of (ship, screen_x, screen_y, scale) for HUD targeting.
        """
        rendered = []
        for ship in enemies:
            if not ship.alive:
                continue
            sx, sy, scale = ship.project_to_screen(FOCAL_LENGTH, self.cx, self.cy)
            if sx is None:
                continue
            self._draw_ship_sprite(surface, ship, int(sx), int(sy), scale, is_target=(ship is target))
            rendered.append((ship, int(sx), int(sy), scale))
        return rendered

    def _draw_ship_sprite(
        self,
        surface: pygame.Surface,
        ship: CombatShip,
        sx: int,
        sy: int,
        scale: float,
        is_target: bool,
    ) -> None:
        shape = SHIP_SHAPES.get(ship.ship_id, SHIP_SHAPES["default"])
        size = max(6.0, min(120.0, scale * 28))
        base_color = ship.color
        # Dim distant ships
        dist_factor = min(1.0, scale / 0.5)
        color = tuple(int(c * dist_factor) for c in base_color)

        points = [(sx + dx * size, sy + dy * size) for dx, dy in shape]
        if len(points) >= 3:
            pygame.draw.polygon(surface, color, points)
            pygame.draw.polygon(surface, (min(255, color[0] + 60), min(255, color[1] + 60), min(255, color[2] + 60)), points, 1)

        # Shield glow when hit
        if ship.shield_pct < 0.5 and ship.shields > 0:
            glow_r = int(size * 1.2)
            glow_alpha = int((0.5 - ship.shield_pct) * 200)
            glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (100, 160, 255, glow_alpha), (glow_r, glow_r), glow_r)
            surface.blit(glow_surf, (sx - glow_r, sy - glow_r))

        if is_target:
            hw = int(size * 0.9)
            pygame.draw.rect(surface, (255, 100, 100), (sx - hw, sy - hw, hw * 2, hw * 2), 1)
            corner = hw // 3
            c = (255, 180, 60)
            for cx, cy, dx, dy in [
                (sx - hw, sy - hw, 1, 1),
                (sx + hw, sy - hw, -1, 1),
                (sx - hw, sy + hw, 1, -1),
                (sx + hw, sy + hw, -1, -1),
            ]:
                pygame.draw.line(surface, c, (cx, cy), (cx + dx * corner, cy), 2)
                pygame.draw.line(surface, c, (cx, cy), (cx, cy + dy * corner), 2)

    def draw_projectiles(self, surface: pygame.Surface, projectiles: list[Projectile]) -> None:
        for p in projectiles:
            z = -p.pos.z
            if z <= 10:
                continue
            scale = FOCAL_LENGTH / z
            sx = int(p.pos.x * scale + self.cx)
            sy = int(-p.pos.y * scale + self.cy)
            if not (0 <= sx < self.width and 0 <= sy < self.height):
                continue
            color = tuple(p.weapon_data.get("color", (255, 255, 100)))
            size = p.weapon_data.get("projectile_size", 3)
            scaled_size = max(1, min(size * 2, int(scale * size * 0.3)))
            if p.weapon_data["type"] in ("missile", "torpedo"):
                pygame.draw.circle(surface, color, (sx, sy), scaled_size)
                tail_len = int(scaled_size * 2.5)
                tail_color = (color[0] // 3, color[1] // 3, color[2] // 3)
                pygame.draw.line(surface, tail_color, (sx, sy), (sx, sy + tail_len), max(1, scaled_size // 2))
            else:
                # Gun bolt — draw a short line in the direction of travel
                pygame.draw.circle(surface, color, (sx, sy), max(1, scaled_size))

    def draw_explosions(self, surface: pygame.Surface, explosions: list[dict]) -> None:
        for exp in explosions:
            pos = exp["pos"]
            z = -pos.z
            if z <= 10:
                continue
            scale = FOCAL_LENGTH / z
            sx = int(pos.x * scale + self.cx)
            sy = int(-pos.y * scale + self.cy)
            t = exp["timer"] / exp["max_time"]
            if exp["small"]:
                r = int(scale * 15 * (1 - t * 0.5))
                alpha = int(255 * (1 - t))
                color = (255, int(200 * (1 - t)), 50, alpha)
            else:
                r = int(scale * 50 * (0.5 + t * 0.5))
                alpha = int(255 * (1 - t * 0.8))
                color = (255, int(150 * (1 - t)), 20, alpha)
            if r > 0 and 0 <= sx < self.width and 0 <= sy < self.height:
                exp_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(exp_surf, color, (r, r), r)
                surface.blit(exp_surf, (sx - r, sy - r))
