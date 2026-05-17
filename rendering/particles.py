"""
Particle system for combat effects:
engine trails, hit sparks, explosion debris.
All lightweight — uses direct surface drawing, no blitting large assets.
"""
import math
import random
import pygame
from combat.ship_3d import Vec3, FOCAL_LENGTH


class Particle:
    __slots__ = ["x", "y", "z", "vx", "vy", "vz", "life", "max_life", "color", "size", "kind"]

    def __init__(self, pos: Vec3, vel: Vec3, life: float, color: tuple,
                 size: float, kind: str = "spark"):
        self.x, self.y, self.z = pos.x, pos.y, pos.z
        self.vx, self.vy, self.vz = vel.x, vel.y, vel.z
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.kind = kind

    @property
    def alive(self) -> bool:
        return self.life > 0

    def update(self, dt: float) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.z += self.vz * dt
        self.life -= dt

    def project(self, focal: float, scx: float, scy: float):
        z = -self.z
        if z <= 5:
            return None, None, 0.0
        scale = focal / z
        sx = self.x * scale + scx
        sy = -self.y * scale + scy
        return sx, sy, scale

    def draw(self, surf: pygame.Surface, focal: float, scx: float, scy: float) -> None:
        sx, sy, scale = self.project(focal, scx, scy)
        if sx is None:
            return
        t = max(0.0, self.life / self.max_life)
        alpha = int(255 * t)
        r = max(1, int(self.size * scale * t))
        W, H = surf.get_size()
        if not (0 <= sx < W and 0 <= sy < H):
            return

        if self.kind == "spark":
            c = tuple(int(ch * t) for ch in self.color)
            if r <= 1:
                surf.set_at((int(sx), int(sy)), c)
            else:
                pygame.draw.circle(surf, c, (int(sx), int(sy)), r)

        elif self.kind == "debris":
            c = tuple(int(ch * t) for ch in self.color)
            end_x = sx + self.vx * 0.05 * scale
            end_y = sy - self.vy * 0.05 * scale
            pygame.draw.line(surf, c, (int(sx), int(sy)), (int(end_x), int(end_y)), max(1, r))

        elif self.kind == "smoke":
            c = tuple(max(0, int(ch * t * 0.5)) for ch in self.color)
            if r > 1:
                smoke = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                pygame.draw.circle(smoke, c + (alpha // 3,), (r, r), r)
                surf.blit(smoke, (int(sx) - r, int(sy) - r))

        elif self.kind == "trail":
            c = tuple(int(ch * t) for ch in self.color)
            if r <= 1:
                surf.set_at((int(sx), int(sy)), c)
            else:
                trail = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                pygame.draw.circle(trail, c + (alpha // 2,), (r, r), r)
                surf.blit(trail, (int(sx) - r, int(sy) - r))


class ParticleSystem:
    def __init__(self):
        self.particles: list[Particle] = []
        self.rng = random.Random()

    def emit_explosion(self, pos: Vec3, large: bool = False) -> None:
        n = 40 if large else 15
        for _ in range(n):
            speed = self.rng.uniform(30, 200) if large else self.rng.uniform(20, 80)
            a_h = self.rng.uniform(0, math.pi * 2)
            a_v = self.rng.uniform(-math.pi / 3, math.pi / 3)
            vel = Vec3(
                math.cos(a_h) * math.cos(a_v) * speed,
                math.sin(a_v) * speed,
                math.sin(a_h) * math.cos(a_v) * speed,
            )
            if large:
                color_choice = self.rng.choice([
                    (255, 200, 80), (255, 120, 40), (255, 60, 20), (200, 200, 200)
                ])
                kind = self.rng.choice(["spark", "spark", "debris", "smoke"])
                size = self.rng.uniform(0.8, 2.5)
                life = self.rng.uniform(0.5, 1.8)
            else:
                color_choice = self.rng.choice([
                    (255, 220, 100), (255, 160, 60), (200, 200, 220)
                ])
                kind = "spark"
                size = self.rng.uniform(0.4, 1.2)
                life = self.rng.uniform(0.2, 0.6)
            self.particles.append(Particle(pos, vel, life, color_choice, size, kind))

    def emit_hit_sparks(self, pos: Vec3, count: int = 8) -> None:
        for _ in range(count):
            speed = self.rng.uniform(15, 60)
            a_h = self.rng.uniform(0, math.pi * 2)
            a_v = self.rng.uniform(-math.pi / 2, math.pi / 2)
            vel = Vec3(
                math.cos(a_h) * speed, math.sin(a_v) * speed, math.sin(a_h) * speed
            )
            color = self.rng.choice([(100, 180, 255), (200, 220, 255), (255, 255, 200)])
            self.particles.append(Particle(pos, vel, self.rng.uniform(0.1, 0.4), color,
                                           self.rng.uniform(0.3, 0.8), "spark"))

    def emit_engine_trail(self, pos: Vec3, ship_vel: Vec3) -> None:
        for _ in range(2):
            offset = Vec3(
                self.rng.uniform(-8, 8),
                self.rng.uniform(-8, 8),
                self.rng.uniform(-8, 8),
            )
            trail_pos = Vec3(pos.x + offset.x, pos.y + offset.y, pos.z + offset.z)
            vel = Vec3(
                ship_vel.x * -0.15 + self.rng.uniform(-5, 5),
                ship_vel.y * -0.15 + self.rng.uniform(-5, 5),
                ship_vel.z * -0.15 + self.rng.uniform(-5, 5),
            )
            color = self.rng.choice([(80, 120, 255), (60, 100, 220), (100, 180, 255)])
            self.particles.append(Particle(trail_pos, vel, self.rng.uniform(0.1, 0.3),
                                           color, self.rng.uniform(0.6, 1.5), "trail"))

    def update(self, dt: float) -> None:
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]

    def draw(self, surf: pygame.Surface, focal: float, scx: float, scy: float) -> None:
        for p in self.particles:
            p.draw(surf, focal, scx, scy)

    def clear(self) -> None:
        self.particles.clear()
