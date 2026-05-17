"""
Wing Commander-style cockpit HUD rendered on top of space.
Draws: cockpit frame, radar, shield display, weapon status,
target info panel, speed indicator, and kill stats.
"""
import math
import pygame
from combat.ship_3d import CombatShip
from combat.combat_engine import CombatEngine

HUD_GREEN = (60, 220, 80)
HUD_AMBER = (220, 160, 40)
HUD_RED   = (220, 60, 40)
HUD_BLUE  = (60, 160, 255)
HUD_DIM   = (40, 80, 50)
HUD_WHITE = (200, 200, 200)
HUD_CYAN  = (60, 220, 220)


def _health_color(pct: float) -> tuple:
    if pct > 0.6:
        return HUD_GREEN
    elif pct > 0.3:
        return HUD_AMBER
    return HUD_RED


def _bar(surface: pygame.Surface, x: int, y: int, w: int, h: int, pct: float, color: tuple, bg: tuple = (20, 30, 20)) -> None:
    pygame.draw.rect(surface, bg, (x, y, w, h))
    fill = max(0, int(w * pct))
    if fill > 0:
        pygame.draw.rect(surface, color, (x, y, fill, h))
    pygame.draw.rect(surface, color, (x, y, w, h), 1)


class HUDRenderer:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.fonts: dict[str, pygame.font.Font] = {}
        self._cockpit_overlay: pygame.Surface | None = None
        self._radar_bg: pygame.Surface | None = None
        self._initialized = False
        self._scan_angle = 0.0

    def init_fonts(self) -> None:
        if self._initialized:
            return
        try:
            mono = pygame.font.match_font("courier,couriernew,monospace,dejavusansmono")
            self.fonts["sm"] = pygame.font.Font(mono, 13)
            self.fonts["md"] = pygame.font.Font(mono, 17)
            self.fonts["lg"] = pygame.font.Font(mono, 24)
            self.fonts["xl"] = pygame.font.Font(mono, 36)
        except Exception:
            self.fonts["sm"] = pygame.font.SysFont("monospace", 13)
            self.fonts["md"] = pygame.font.SysFont("monospace", 17)
            self.fonts["lg"] = pygame.font.SysFont("monospace", 24)
            self.fonts["xl"] = pygame.font.SysFont("monospace", 36)
        self._build_cockpit_overlay()
        self._initialized = True

    def _build_cockpit_overlay(self) -> None:
        """Build the static cockpit frame that masks the edges of the viewport."""
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        W, H = self.width, self.height

        # Viewport hole — elliptical clear area in center
        vx, vy = int(W * 0.08), int(H * 0.10)
        vw, vh = W - vx * 2, H - vy * 2

        # Fill everything dark
        surf.fill((8, 8, 12, 240))

        # Cut out viewport
        pygame.draw.ellipse(surf, (0, 0, 0, 0), (vx, vy, vw, vh))

        # Cockpit frame border ring
        pygame.draw.ellipse(surf, (40, 60, 40, 200), (vx - 4, vy - 4, vw + 8, vh + 8), 4)
        pygame.draw.ellipse(surf, HUD_GREEN + (120,), (vx - 8, vy - 8, vw + 16, vh + 16), 2)

        # Structural ribs at sides
        rib_color = (20, 35, 20, 180)
        for i in range(3):
            xoff = int(W * 0.04) + i * 4
            pygame.draw.line(surf, rib_color, (xoff, 0), (xoff, H), 3)
            pygame.draw.line(surf, rib_color, (W - xoff, 0), (W - xoff, H), 3)

        # Bottom console panel
        pygame.draw.rect(surf, (6, 10, 6, 220), (0, H - int(H * 0.22), W, int(H * 0.22)))
        pygame.draw.line(surf, HUD_GREEN + (150,), (0, H - int(H * 0.22)), (W, H - int(H * 0.22)), 2)

        self._cockpit_overlay = surf

    def draw(self, surface: pygame.Surface, engine: "CombatEngine", dt: float, ship_name: str) -> None:
        if not self._initialized:
            self.init_fonts()

        self._scan_angle = (self._scan_angle + dt * 120) % 360

        H = self.height
        W = self.width

        # Cockpit frame
        if self._cockpit_overlay:
            surface.blit(self._cockpit_overlay, (0, 0))

        panel_y = H - int(H * 0.21)

        self._draw_shield_display(surface, engine, 20, panel_y + 10)
        self._draw_radar(surface, engine, W // 2 - 80, panel_y + 8)
        self._draw_weapon_status(surface, engine, W - 240, panel_y + 10)
        self._draw_target_info(surface, engine, W - 250, 20)
        self._draw_speed(surface, engine, 20, H // 2 - 60)
        self._draw_hud_header(surface, engine, ship_name)
        self._draw_crosshair(surface)

    def _draw_crosshair(self, surface: pygame.Surface) -> None:
        cx, cy = self.width // 2, self.height // 2
        size = 12
        gap = 5
        color = (100, 255, 100, 180)
        pygame.draw.line(surface, HUD_GREEN, (cx - size - gap, cy), (cx - gap, cy), 1)
        pygame.draw.line(surface, HUD_GREEN, (cx + gap, cy), (cx + size + gap, cy), 1)
        pygame.draw.line(surface, HUD_GREEN, (cx, cy - size - gap), (cx, cy - gap), 1)
        pygame.draw.line(surface, HUD_GREEN, (cx, cy + gap), (cx, cy + size + gap), 1)
        pygame.draw.circle(surface, HUD_GREEN, (cx, cy), 3, 1)

    def _draw_shield_display(self, surface: pygame.Surface, engine: "CombatEngine", x: int, y: int) -> None:
        font_sm = self.fonts["sm"]
        font_md = self.fonts["md"]

        # Title
        label = font_sm.render("SHIELDS / ARMOR", True, HUD_DIM)
        surface.blit(label, (x, y))
        y += 18

        # Ship outline (top view, hexagon-ish)
        ship_cx, ship_cy = x + 70, y + 55
        ship_pts = [
            (ship_cx, ship_cy - 35),
            (ship_cx + 22, ship_cy - 10),
            (ship_cx + 22, ship_cy + 20),
            (ship_cx, ship_cy + 35),
            (ship_cx - 22, ship_cy + 20),
            (ship_cx - 22, ship_cy - 10),
        ]
        s_pct = engine.player.shield_pct
        a_pct = engine.player.armor_pct
        ship_color = _health_color(min(s_pct, a_pct))
        pygame.draw.polygon(surface, HUD_DIM, ship_pts)
        pygame.draw.polygon(surface, ship_color, ship_pts, 2)

        # Shield bar
        _bar(surface, x, y + 120, 140, 10, s_pct, _health_color(s_pct))
        lbl = font_sm.render(f"SHD {int(engine.player.shields):>3}", True, _health_color(s_pct))
        surface.blit(lbl, (x, y + 133))

        # Armor bar
        _bar(surface, x, y + 150, 140, 10, a_pct, _health_color(a_pct))
        lbl2 = font_sm.render(f"ARM {int(engine.player.armor):>3}", True, _health_color(a_pct))
        surface.blit(lbl2, (x, y + 163))

    def _draw_radar(self, surface: pygame.Surface, engine: "CombatEngine", x: int, y: int) -> None:
        font_sm = self.fonts["sm"]
        R = 70
        cx, cy = x + R, y + R

        # Radar background
        pygame.draw.circle(surface, (5, 15, 5), (cx, cy), R)
        pygame.draw.circle(surface, HUD_DIM, (cx, cy), R, 2)
        # Grid rings
        for r in [R // 3, R * 2 // 3]:
            pygame.draw.circle(surface, HUD_DIM, (cx, cy), r, 1)
        # Cross hairs
        pygame.draw.line(surface, HUD_DIM, (cx - R, cy), (cx + R, cy), 1)
        pygame.draw.line(surface, HUD_DIM, (cx, cy - R), (cx, cy + R), 1)

        # Sweep line
        sweep_rad = math.radians(self._scan_angle)
        ex = int(cx + math.cos(sweep_rad) * R)
        ey = int(cy + math.sin(sweep_rad) * R)
        pygame.draw.line(surface, HUD_GREEN + (80,), (cx, cy), (ex, ey), 1)

        # Plot enemies
        living = [e for e in engine.enemies if e.alive]
        for ship in living:
            rel = ship.pos - engine.player.pos
            dist = rel.length()
            if dist < 0.01:
                continue
            max_range = 1500.0
            d_norm = min(dist / max_range, 1.0)
            angle = math.atan2(rel.x, -rel.z)
            bx = int(cx + math.sin(angle) * d_norm * (R - 5))
            by = int(cy - math.cos(angle) * d_norm * (R - 5))
            is_tgt = ship is engine.current_target
            color = HUD_RED if is_tgt else HUD_AMBER
            pygame.draw.circle(surface, color, (bx, by), 4 if is_tgt else 2)

        # Player dot
        pygame.draw.circle(surface, HUD_GREEN, (cx, cy), 3)

        label = font_sm.render("RADAR", True, HUD_DIM)
        surface.blit(label, (cx - 22, y + R * 2 + 5))

    def _draw_weapon_status(self, surface: pygame.Surface, engine: "CombatEngine", x: int, y: int) -> None:
        font_sm = self.fonts["sm"]
        font_md = self.fonts["md"]

        lbl = font_sm.render("WEAPONS", True, HUD_DIM)
        surface.blit(lbl, (x, y))
        y += 18

        # Gun cooldown indicator
        gun_rdy = engine.player_gun_cooldown <= 0
        gun_color = HUD_GREEN if gun_rdy else HUD_AMBER
        gun_lbl = font_md.render("GUN   " + ("READY" if gun_rdy else " COOL"), True, gun_color)
        surface.blit(gun_lbl, (x, y))
        y += 22

        # Missiles
        for weapon_id, count in engine.player_missile_counts.items():
            color = HUD_GREEN if count > 0 else HUD_DIM
            short = weapon_id.replace("_", " ").upper()[:12]
            msl = font_sm.render(f"{short:<12} x{count:>2}", True, color)
            surface.blit(msl, (x, y))
            y += 16

        # Missile cooldown bar
        if engine.player_missile_cooldown > 0:
            max_cd = 4.0
            pct = 1.0 - (engine.player_missile_cooldown / max_cd)
            _bar(surface, x, y + 4, 160, 6, pct, HUD_AMBER)
            surface.blit(font_sm.render("MSL RELOAD", True, HUD_AMBER), (x, y + 13))

    def _draw_target_info(self, surface: pygame.Surface, engine: "CombatEngine", x: int, y: int) -> None:
        font_sm = self.fonts["sm"]
        font_md = self.fonts["md"]
        target = engine.current_target
        if not target:
            no_tgt = font_sm.render("NO TARGET", True, HUD_DIM)
            surface.blit(no_tgt, (x + 20, y))
            return

        dist = target.distance_to(engine.player)
        angle = engine.player.angle_to(target)

        lbl = font_sm.render("TARGET", True, HUD_DIM)
        surface.blit(lbl, (x, y))
        y += 16

        name_lbl = font_md.render(target.ship_id.replace("_", " ").upper(), True, HUD_RED)
        surface.blit(name_lbl, (x, y))
        y += 22

        faction = target.faction.replace("_", " ").upper() if target.faction else "UNKNOWN"
        f_lbl = font_sm.render(faction, True, HUD_AMBER)
        surface.blit(f_lbl, (x, y))
        y += 18

        dist_lbl = font_sm.render(f"DIST  {int(dist):>5}m", True, HUD_WHITE)
        surface.blit(dist_lbl, (x, y))
        y += 16

        ang_lbl = font_sm.render(f"ANGLE {int(angle):>3}deg", True, HUD_WHITE)
        surface.blit(ang_lbl, (x, y))
        y += 20

        _bar(surface, x, y, 160, 8, target.shield_pct, _health_color(target.shield_pct))
        surface.blit(font_sm.render("SHD", True, HUD_DIM), (x + 165, y - 2))
        y += 12

        _bar(surface, x, y, 160, 8, target.armor_pct, _health_color(target.armor_pct))
        surface.blit(font_sm.render("ARM", True, HUD_DIM), (x + 165, y - 2))

    def _draw_speed(self, surface: pygame.Surface, engine: "CombatEngine", x: int, y: int) -> None:
        font_sm = self.fonts["sm"]
        speed = engine.player.velocity.length()
        ab = engine.player_afterburner

        lbl = font_sm.render("SPEED", True, HUD_DIM)
        surface.blit(lbl, (x, y))
        y += 14

        max_spd = engine.player.afterburner_speed
        _bar(surface, x, y, 12, 80, min(1.0, speed / max_spd), HUD_GREEN if not ab else HUD_CYAN, bg=(10, 20, 10))
        spd_lbl = font_sm.render(f"{int(speed):>3}", True, HUD_CYAN if ab else HUD_GREEN)
        surface.blit(spd_lbl, (x - 2, y + 83))
        if ab:
            ab_lbl = font_sm.render("AB", True, HUD_CYAN)
            surface.blit(ab_lbl, (x - 2, y + 97))

    def _draw_hud_header(self, surface: pygame.Surface, engine: "CombatEngine", ship_name: str) -> None:
        font_sm = self.fonts["sm"]
        W = self.width

        kills = sum(1 for e in engine.enemies if not e.alive)
        total = len(engine.enemies)
        kills_lbl = font_sm.render(f"KILLS {kills}/{total}", True, HUD_GREEN)
        surface.blit(kills_lbl, (W // 2 - 50, 12))

        time_lbl = font_sm.render(f"{int(engine.time_elapsed):>4}s", True, HUD_DIM)
        surface.blit(time_lbl, (W - 60, 12))

        ship_lbl = font_sm.render(ship_name.upper(), True, HUD_DIM)
        surface.blit(ship_lbl, (12, 12))
