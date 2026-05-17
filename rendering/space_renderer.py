"""
3D space renderer — colored star field with parallax, perspective-projected ships,
projectile bolts, explosion particles. Uses the art.py ship drawings.
"""
import math
import random
import pygame
from combat.ship_3d import CombatShip, Vec3, Projectile, FOCAL_LENGTH
from rendering.art import draw_ship, draw_glow_circle, get_scanline_overlay, get_vignette
from rendering.particles import ParticleSystem

STAR_COLORS = [
    (255, 255, 255), (200, 210, 255), (255, 240, 200),
    (180, 200, 255), (255, 220, 180), (160, 220, 255),
]


class Star:
    __slots__ = ["x", "y", "z", "max_z", "color", "size"]

    def __init__(self, rng, W, H, initial=False):
        self.max_z = float(W)
        self.reset(rng, W, H, initial)

    def reset(self, rng, W, H, initial=False):
        self.x = rng.uniform(0, W)
        self.y = rng.uniform(0, H)
        self.z = rng.uniform(1, self.max_z) if not initial else rng.uniform(self.max_z * 0.1, self.max_z)
        self.color = rng.choice(STAR_COLORS)
        self.size = rng.choice([1, 1, 1, 1, 2, 2, 3])

    def update(self, speed, W, H, rng):
        self.z -= speed
        if self.z <= 0:
            self.reset(rng, W, H)
            self.z = self.max_z

    def draw(self, surf, W, H):
        cx, cy = W / 2, H / 2
        scale = self.max_z / self.z
        sx = int((self.x - cx) * scale + cx)
        sy = int((self.y - cy) * scale + cy)
        if not (0 <= sx < W and 0 <= sy < H):
            return
        brightness = max(50, int(255 * (1 - self.z / self.max_z) ** 1.5))
        color = tuple(int(ch * brightness / 255) for ch in self.color)
        r = max(1, min(self.size, int(scale * 0.8)))
        if r <= 1:
            surf.set_at((sx, sy), color)
        else:
            pygame.draw.circle(surf, color, (sx, sy), r)
            # Bright core
            if r > 2:
                pygame.draw.circle(surf, (255, 255, 255), (sx, sy), max(1, r // 2))


class NebulaLayer:
    def __init__(self, W, H, seed=13):
        self._surf = pygame.Surface((W, H), pygame.SRCALPHA)
        rng = random.Random(seed)
        # Richer palette: multiple complementary color pairs
        palettes = [
            [(90, 30, 140), (40, 70, 160), (120, 40, 70), (20, 50, 120)],
            [(30, 100, 90), (70, 30, 130), (90, 60, 20), (40, 80, 140)],
            [(20, 50, 110), (110, 35, 90), (45, 90, 55), (80, 50, 20)],
            [(120, 40, 20), (40, 100, 140), (80, 20, 120), (20, 120, 80)],
        ]
        pal = rng.choice(palettes)

        # Large background nebula clouds
        for _ in range(6):
            cx = rng.randint(-W // 4, W + W // 4)
            cy = rng.randint(-H // 4, H + H // 4)
            r  = rng.randint(220, 550)
            col = rng.choice(pal)
            for i in range(r, 0, -max(1, r // 18)):
                t = i / r
                alpha = int(25 * t * (1 - t) * 4.2)
                pygame.draw.circle(self._surf, col + (alpha,), (cx, cy), i)

        # Medium bright filaments / wisps
        for _ in range(8):
            cx = rng.randint(0, W)
            cy = rng.randint(0, H)
            r  = rng.randint(60, 160)
            col = rng.choice(pal)
            bright = tuple(min(255, c + 40) for c in col)
            for i in range(r, 0, -max(1, r // 10)):
                t = i / r
                alpha = int(18 * t * (1 - t) * 5)
                pygame.draw.circle(self._surf, bright + (alpha,), (cx, cy), i)

        # Small bright star-forming knots
        for _ in range(12):
            kx = rng.randint(0, W)
            ky = rng.randint(0, H)
            kr = rng.randint(10, 35)
            kcol = rng.choice(pal)
            kbright = tuple(min(255, c + 80) for c in kcol)
            for i in range(kr, 0, -max(1, kr // 6)):
                t = i / kr
                alpha = int(30 * (1 - t) ** 1.5)
                pygame.draw.circle(self._surf, kbright + (alpha,), (kx, ky), i)

    def draw(self, surf):
        surf.blit(self._surf, (0, 0))


class SpaceRenderer:
    def __init__(self, width: int, height: int, num_stars: int = 350):
        self.W = width
        self.H = height
        self.cx = width // 2
        self.cy = height // 2
        self.rng = random.Random(7)
        self.stars = [Star(self.rng, width, height, initial=True) for _ in range(num_stars)]
        self.nebula = NebulaLayer(width, height, seed=17)
        self.fracture_nebula = NebulaLayer(width, height, seed=99)
        self.particles = ParticleSystem()
        self._scanline = None
        self._vignette = None

    def _get_overlays(self):
        if self._scanline is None:
            self._scanline = get_scanline_overlay(self.W, self.H, alpha=22)
        if self._vignette is None:
            self._vignette = get_vignette(self.W, self.H)

    def update(self, dt: float, player_ship=None, speed: float = 5.0) -> None:
        warp_speed = speed * dt * 25
        for star in self.stars:
            star.update(warp_speed, self.W, self.H, self.rng)

        if player_ship:
            self.particles.emit_engine_trail(player_ship.pos, player_ship.velocity)
        self.particles.update(dt)

    def draw_background(self, surface: pygame.Surface, in_fracture: bool = False) -> None:
        surface.fill((2, 3, 10))
        if in_fracture:
            self.fracture_nebula.draw(surface)
        else:
            self.nebula.draw(surface)
        for star in self.stars:
            star.draw(surface, self.W, self.H)
        self.particles.draw(surface, FOCAL_LENGTH, self.cx, self.cy)

    def draw_ships(self, surface: pygame.Surface, enemies: list,
                   target) -> list:
        rendered = []
        # Sort back-to-front
        visible = [(e, -e.pos.z) for e in enemies if e.alive and -e.pos.z > 10]
        visible.sort(key=lambda t: t[1], reverse=True)

        for ship, _ in visible:
            sx, sy, scale = ship.project_to_screen(FOCAL_LENGTH, self.cx, self.cy)
            if sx is None:
                continue
            size = max(6.0, min(110.0, scale * 32))
            self._draw_ship_art(surface, ship, int(sx), int(sy), size,
                                is_target=(ship is target))
            rendered.append((ship, int(sx), int(sy), scale))
        return rendered

    def _draw_ship_art(self, surface, ship: CombatShip, sx: int, sy: int,
                       size: float, is_target: bool) -> None:
        dist_factor = min(1.0, size / 35.0)
        base_color = tuple(max(20, int(c * dist_factor)) for c in ship.color)

        draw_ship(surface, ship.ship_id, sx, sy, size * 0.5,
                  base_color, engine_glow=(size > 14))

        # Shield glow when shields are low
        if 0 < ship.shields < ship.max_shields * 0.5:
            glow_alpha = int(100 * (1 - ship.shield_pct))
            glow_r = int(size * 0.65)
            glow_surf = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (80, 150, 255, glow_alpha),
                               (glow_r + 2, glow_r + 2), glow_r)
            surface.blit(glow_surf, (sx - glow_r - 2, sy - glow_r - 2))

        if is_target:
            self._draw_target_bracket(surface, sx, sy, size)

    def _draw_target_bracket(self, surface, sx, sy, size):
        hw = int(size * 0.75)
        corner = max(5, hw // 3)
        c1 = (255, 60, 60)
        c2 = (255, 180, 60)
        # Outer rotating rectangle
        pygame.draw.rect(surface, c1, (sx - hw, sy - hw, hw * 2, hw * 2), 1)
        # Corner L-brackets
        for bx, by, dx, dy in [
            (sx - hw, sy - hw,  1,  1),
            (sx + hw, sy - hw, -1,  1),
            (sx - hw, sy + hw,  1, -1),
            (sx + hw, sy + hw, -1, -1),
        ]:
            pygame.draw.line(surface, c2, (bx, by), (bx + dx * corner, by), 2)
            pygame.draw.line(surface, c2, (bx, by), (bx, by + dy * corner), 2)
        # Crosshair marks on target center
        pygame.draw.line(surface, c2, (sx - 4, sy), (sx - 2, sy), 1)
        pygame.draw.line(surface, c2, (sx + 2, sy), (sx + 4, sy), 1)
        pygame.draw.line(surface, c2, (sx, sy - 4), (sx, sy - 2), 1)
        pygame.draw.line(surface, c2, (sx, sy + 2), (sx, sy + 4), 1)

    def draw_projectiles(self, surface: pygame.Surface, projectiles: list) -> None:
        for p in projectiles:
            z = -p.pos.z
            if z <= 10:
                continue
            scale = FOCAL_LENGTH / z
            sx = int(p.pos.x * scale + self.cx)
            sy = int(-p.pos.y * scale + self.cy)
            if not (0 <= sx < self.W and 0 <= sy < self.H):
                continue
            color = tuple(p.weapon_data.get("color", (255, 220, 80)))
            size = p.weapon_data.get("projectile_size", 3)
            r = max(1, min(size + 2, int(scale * size * 0.25)))

            if p.weapon_data["type"] in ("missile", "torpedo"):
                draw_glow_circle(surface, color, sx, sy, r, layers=3)
                # Exhaust trail
                tail_end_x = int(sx + (p.velocity.x / max(1, abs(p.velocity.z + 0.01))) * r * 3)
                tail_end_y = int(sy + (p.velocity.y / max(1, abs(p.velocity.z + 0.01))) * r * 3)
                tail_surf = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
                pygame.draw.line(tail_surf, color + (100,), (sx, sy), (tail_end_x, tail_end_y), max(1, r))
                surface.blit(tail_surf)
            else:
                # Gun bolt — elongated bright dot
                pygame.draw.circle(surface, (255, 255, 255), (sx, sy), max(1, r // 2))
                pygame.draw.circle(surface, color, (sx, sy), r)

    def emit_explosion(self, pos: Vec3, large: bool = False) -> None:
        self.particles.emit_explosion(pos, large)

    def emit_hit_sparks(self, pos: Vec3) -> None:
        self.particles.emit_hit_sparks(pos)

    def draw_post_effects(self, surface: pygame.Surface) -> None:
        """Scanlines + vignette — call after all game rendering."""
        self._get_overlays()
        if self._scanline:
            surface.blit(self._scanline, (0, 0))
        if self._vignette:
            surface.blit(self._vignette, (0, 0))

    def reset_particles(self) -> None:
        self.particles.clear()
