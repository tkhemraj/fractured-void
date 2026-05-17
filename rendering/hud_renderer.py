"""
Wing Commander-style HUD renderer.
Uses the pre-rendered cockpit frame from cockpit.py.
Draws all instrument panels in the console area.
Supports screen shake on hit.
"""
import math
import pygame
from combat.ship_3d import CombatShip
from rendering.cockpit import build_cockpit, VP_LEFT, VP_RIGHT, VP_TOP, VP_BOTTOM
from rendering.art import (
    HUD_GREEN, HUD_GREEN_D, HUD_AMBER, HUD_RED, HUD_CYAN,
    HUD_DIM, HUD_WHITE, FACTION_COLORS, bar, health_color,
    draw_panel, glow_text, draw_glow_circle,
)


class HUDRenderer:
    def __init__(self, width: int, height: int):
        self.W = width
        self.H = height
        self.fonts: dict = {}
        self._cockpit_surf: pygame.Surface | None = None
        self._vp_rect: dict = {}
        self._initialized = False
        self._scan_angle = 0.0
        self._shake_x = 0
        self._shake_y = 0
        self._shake_decay = 0.0

    def init(self) -> None:
        if self._initialized:
            return
        try:
            mono = pygame.font.match_font("courier,couriernew,dejavusansmono")
            self.fonts["xs"] = pygame.font.Font(mono, 11)
            self.fonts["sm"] = pygame.font.Font(mono, 13)
            self.fonts["md"] = pygame.font.Font(mono, 17)
            self.fonts["lg"] = pygame.font.Font(mono, 24)
            self.fonts["xl"] = pygame.font.Font(mono, 36)
        except Exception:
            for k, s in [("xs", 11), ("sm", 13), ("md", 17), ("lg", 24), ("xl", 36)]:
                self.fonts[k] = pygame.font.SysFont("monospace", s)

        self._cockpit_surf, self._vp_rect = build_cockpit(self.W, self.H)
        self._initialized = True

    def shake(self, intensity: float = 8.0) -> None:
        import random
        rng = random.Random()
        self._shake_x = int(rng.uniform(-intensity, intensity))
        self._shake_y = int(rng.uniform(-intensity * 0.5, intensity * 0.5))
        self._shake_decay = 0.0

    def update_shake(self, dt: float) -> tuple[int, int]:
        if self._shake_x == 0 and self._shake_y == 0:
            return 0, 0
        self._shake_decay += dt * 15
        factor = max(0.0, 1.0 - self._shake_decay)
        ox = int(self._shake_x * factor)
        oy = int(self._shake_y * factor)
        if factor <= 0:
            self._shake_x = self._shake_y = 0
        return ox, oy

    def draw(self, surface: pygame.Surface, engine, dt: float,
             ship_name: str, shake_offset: tuple = (0, 0)) -> None:
        if not self._initialized:
            self.init()

        self._scan_angle = (self._scan_angle + dt * 110) % 360

        # Blit cockpit frame (transparent viewport stays clear)
        ox, oy = shake_offset
        surface.blit(self._cockpit_surf, (ox, oy))

        vp = self._vp_rect
        console_y = vp["y"] + vp["h"] + 4
        console_h  = self.H - console_y

        W = self.W
        panel_m = 12
        third_w = (W - panel_m * 4) // 3

        # Three console panels
        self._draw_shield_panel(surface, engine,
                                panel_m, console_y + 4, third_w, console_h - 10)
        self._draw_radar_panel(surface, engine,
                               panel_m * 2 + third_w, console_y + 4, third_w, console_h - 10)
        self._draw_weapon_panel(surface, engine,
                                panel_m * 3 + third_w * 2, console_y + 4, third_w, console_h - 10)

        # Floating elements inside viewport
        self._draw_crosshair(surface)
        self._draw_target_info(surface, engine, vp)
        self._draw_speed_tape(surface, engine, vp)
        self._draw_header_info(surface, engine, ship_name, vp)

    def _draw_shield_panel(self, surf, engine, px, py, pw, ph):
        font_sm = self.fonts["sm"]
        font_xs = self.fonts["xs"]
        p = engine.player

        # Title
        surf.blit(font_xs.render("SHIELDS / ARMOR", True, HUD_DIM), (px + 4, py + 2))

        # Ship top-view silhouette
        mid_x = px + pw // 2
        mid_y = py + 48
        sz = min(28, pw // 3)
        # Draw Cinder Pact from art module
        from rendering.art import draw_ship, _tint
        s_pct = p.shield_pct
        ship_color = health_color(s_pct)
        draw_ship(surf, "cinder_pact", mid_x, mid_y, sz * 0.9, ship_color, engine_glow=False)

        # Shield bar
        sy = py + sz * 2 + 22
        surf.blit(font_xs.render("SHD", True, HUD_DIM), (px + 4, sy))
        color_s = health_color(p.shield_pct)
        bar(surf, px + 28, sy + 2, pw - 32, 9, p.shield_pct, color_s)
        surf.blit(font_xs.render(f"{int(p.shields)}", True, color_s), (px + pw - 26, sy))
        sy += 18

        # Armor bar
        surf.blit(font_xs.render("ARM", True, HUD_DIM), (px + 4, sy))
        color_a = health_color(p.armor_pct)
        bar(surf, px + 28, sy + 2, pw - 32, 9, p.armor_pct, color_a)
        surf.blit(font_xs.render(f"{int(p.armor)}", True, color_a), (px + pw - 26, sy))
        sy += 20

        # Energy/throttle
        surf.blit(font_xs.render("PWR", True, HUD_DIM), (px + 4, sy))
        bar(surf, px + 28, sy + 2, pw - 32, 9,
            engine.player_throttle, HUD_CYAN)
        surf.blit(font_xs.render(f"{int(engine.player_throttle * 100)}%", True, HUD_CYAN),
                  (px + pw - 30, sy))

    def _draw_radar_panel(self, surf, engine, px, py, pw, ph):
        font_xs = self.fonts["xs"]
        R = min(pw // 2 - 8, ph // 2 - 14)
        cx = px + pw // 2
        cy = py + R + 12

        # Background
        pygame.draw.circle(surf, (4, 12, 6), (cx, cy), R)
        pygame.draw.circle(surf, HUD_DIM, (cx, cy), R, 1)

        # Range rings
        for r_frac in [0.33, 0.67]:
            pygame.draw.circle(surf, HUD_GREEN_D, (cx, cy), int(R * r_frac), 1)

        # Cardinal lines
        pygame.draw.line(surf, HUD_GREEN_D, (cx - R, cy), (cx + R, cy), 1)
        pygame.draw.line(surf, HUD_GREEN_D, (cx, cy - R), (cx, cy + R), 1)

        # Sweep
        sweep_r = math.radians(self._scan_angle)
        ex = int(cx + math.cos(sweep_r) * R)
        ey = int(cy + math.sin(sweep_r) * R)
        sweep_surf = pygame.Surface((R * 2 + 2, R * 2 + 2), pygame.SRCALPHA)
        pygame.draw.line(sweep_surf, HUD_GREEN + (60,),
                         (R + 1, R + 1), (ex - cx + R + 1, ey - cy + R + 1), 2)
        surf.blit(sweep_surf, (cx - R - 1, cy - R - 1))

        # Enemy blips
        for ship in engine.enemies:
            if not ship.alive:
                continue
            rel = ship.pos - engine.player.pos
            dist = rel.length()
            max_range = 1500.0
            d_norm = min(dist / max_range, 1.0)
            angle = math.atan2(rel.x, -rel.z)
            bx = int(cx + math.sin(angle) * d_norm * (R - 5))
            by = int(cy - math.cos(angle) * d_norm * (R - 5))
            is_tgt = ship is engine.current_target
            if is_tgt:
                draw_glow_circle(surf, HUD_RED, bx, by, 4, layers=2)
            else:
                pygame.draw.circle(surf, HUD_AMBER, (bx, by), 3)

        # Player dot
        draw_glow_circle(surf, HUD_GREEN, cx, cy, 3, layers=2)

        # Title below radar
        lbl = self.fonts["xs"].render("RADAR", True, HUD_DIM)
        surf.blit(lbl, (cx - lbl.get_width() // 2, cy + R + 4))

        # Kill counter
        kills = sum(1 for e in engine.enemies if not e.alive)
        total = len(engine.enemies)
        kill_lbl = self.fonts["xs"].render(f"K {kills}/{total}", True, HUD_GREEN)
        surf.blit(kill_lbl, (px + 4, py + ph - 14))

        # Time
        t_lbl = self.fonts["xs"].render(f"{int(engine.time_elapsed)}s", True, HUD_DIM)
        surf.blit(t_lbl, (px + pw - t_lbl.get_width() - 4, py + ph - 14))

    def _draw_weapon_panel(self, surf, engine, px, py, pw, ph):
        font_xs = self.fonts["xs"]
        font_sm = self.fonts["sm"]

        surf.blit(font_xs.render("WEAPONS", True, HUD_DIM), (px + 4, py + 2))
        y = py + 16

        # Gun readiness
        gun_rdy = engine.player_gun_cooldown <= 0
        color = HUD_GREEN if gun_rdy else HUD_AMBER
        txt = "GUN  READY" if gun_rdy else "GUN  RELOADING"
        surf.blit(font_xs.render(txt, True, color), (px + 4, y))
        y += 14

        # Gun cooldown mini-bar
        if not gun_rdy:
            max_cd = 0.4
            bar(surf, px + 4, y, pw - 8, 5,
                1 - engine.player_gun_cooldown / max_cd, HUD_AMBER)
            y += 8

        y += 4

        # Missiles
        for weapon_id, count in engine.player_missile_counts.items():
            color = HUD_GREEN if count > 0 else HUD_DIM
            name = weapon_id.replace("_", " ")[:14].upper()
            surf.blit(font_xs.render(name, True, color), (px + 4, y))
            cnt_txt = f"x{count:02}"
            cnt_lbl = font_xs.render(cnt_txt, True, color)
            surf.blit(cnt_lbl, (px + pw - cnt_lbl.get_width() - 4, y))
            # Dot indicators
            for i in range(min(count, 8)):
                dot_x = px + 4 + i * (pw - 8) // 8
                pygame.draw.circle(surf, color, (dot_x + 4, y + 14), 3)
            y += 22

        # Missile cooldown
        if engine.player_missile_cooldown > 0:
            bar(surf, px + 4, py + ph - 18, pw - 8, 7,
                1 - engine.player_missile_cooldown / 4.0, HUD_AMBER)
            surf.blit(font_xs.render("MSL RELOADING", True, HUD_AMBER), (px + 4, py + ph - 28))

        # Afterburner indicator
        if engine.player_afterburner:
            glow_text(surf, font_sm, "AFTERBURN", HUD_CYAN,
                      (px + pw // 2 - 40, py + ph - 42))

    def _draw_crosshair(self, surf):
        cx, cy = self.W // 2, int(self.H * (VP_TOP + (VP_BOTTOM - VP_TOP) * 0.5))
        size = 14
        gap  = 6
        pygame.draw.line(surf, HUD_GREEN, (cx - size - gap, cy), (cx - gap, cy), 1)
        pygame.draw.line(surf, HUD_GREEN, (cx + gap, cy), (cx + size + gap, cy), 1)
        pygame.draw.line(surf, HUD_GREEN, (cx, cy - size - gap), (cx, cy - gap), 1)
        pygame.draw.line(surf, HUD_GREEN, (cx, cy + gap), (cx, cy + size + gap), 1)
        pygame.draw.circle(surf, HUD_GREEN, (cx, cy), 3, 1)
        pygame.draw.circle(surf, HUD_GREEN, (cx, cy), size + gap, 1)

    def _draw_target_info(self, surf, engine, vp):
        target = engine.current_target
        font_xs = self.fonts["xs"]
        font_sm = self.fonts["sm"]

        px = vp["x"] + 6
        py = vp["y"] + 6
        pw = 190

        if not target:
            surf.blit(font_xs.render("NO TARGET", True, HUD_DIM), (px, py))
            return

        dist = target.distance_to(engine.player)
        angle = engine.player.angle_to(target)
        faction_color = FACTION_COLORS.get(target.faction, HUD_WHITE)

        # Semi-transparent backdrop
        bg = pygame.Surface((pw, 110), pygame.SRCALPHA)
        pygame.draw.rect(bg, (4, 10, 6, 180), (0, 0, pw, 110))
        pygame.draw.rect(bg, HUD_GREEN_D + (150,), (0, 0, pw, 110), 1)
        surf.blit(bg, (px - 2, py - 2))

        surf.blit(font_xs.render("TARGET", True, HUD_DIM), (px, py))
        py += 14
        tgt_name = target.ship_id.replace("_", " ").upper()[:20]
        glow_text(surf, font_sm, tgt_name, HUD_RED, (px, py))
        py += 20
        surf.blit(font_xs.render(target.faction.replace("_", " ").upper() if target.faction else "UNKNOWN",
                                 True, faction_color), (px, py))
        py += 14
        surf.blit(font_xs.render(f"DIST  {int(dist):>5}m", True, HUD_WHITE), (px, py))
        py += 13
        surf.blit(font_xs.render(f"ANGLE {int(angle):>4}°",  True, HUD_WHITE), (px, py))
        py += 16
        bar(surf, px, py, pw - 4, 7, target.shield_pct, health_color(target.shield_pct))
        surf.blit(font_xs.render("S", True, HUD_DIM), (px + pw - 4, py - 1))
        py += 10
        bar(surf, px, py, pw - 4, 7, target.armor_pct, health_color(target.armor_pct))
        surf.blit(font_xs.render("A", True, HUD_DIM), (px + pw - 4, py - 1))

    def _draw_speed_tape(self, surf, engine, vp):
        font_xs = self.fonts["xs"]
        x = vp["x"] + vp["w"] - 54
        y = vp["y"] + 6
        h = int(vp["h"] * 0.55)

        # Backdrop
        bg = pygame.Surface((50, h + 28), pygame.SRCALPHA)
        pygame.draw.rect(bg, (4, 10, 6, 180), (0, 0, 50, h + 28))
        pygame.draw.rect(bg, HUD_GREEN_D + (140,), (0, 0, 50, h + 28), 1)
        surf.blit(bg, (x - 2, y - 2))

        surf.blit(font_xs.render("SPD", True, HUD_DIM), (x, y))
        y += 14

        speed = engine.player.velocity.length()
        max_s = engine.player.afterburner_speed
        pct   = min(1.0, speed / max(1, max_s))
        ab    = engine.player_afterburner
        color = HUD_CYAN if ab else HUD_GREEN

        # Vertical tape bar
        tape_x = x + 18
        pygame.draw.rect(surf, (8, 18, 10), (tape_x, y, 14, h))
        fill_h = int(h * pct)
        if fill_h > 0:
            pygame.draw.rect(surf, color, (tape_x, y + h - fill_h, 14, fill_h))
        pygame.draw.rect(surf, color, (tape_x, y, 14, h), 1)

        # Tick marks
        for i in range(0, 5):
            ty = y + h - int(h * i / 4)
            pygame.draw.line(surf, HUD_DIM, (tape_x - 3, ty), (tape_x, ty), 1)

        y += h + 4
        spd_lbl = font_xs.render(f"{int(speed)}", True, color)
        surf.blit(spd_lbl, (x + 25 - spd_lbl.get_width() // 2, y))
        y += 12
        if ab:
            glow_text(surf, font_xs, "AB", HUD_CYAN, (x + 14, y))

    def _draw_header_info(self, surf, engine, ship_name, vp):
        font_xs = self.fonts["xs"]
        font_sm = self.fonts["sm"]

        # Top bar center — ship name and heading
        cx = self.W // 2
        ty = 4
        glow_text(surf, font_sm, ship_name.upper(), HUD_GREEN,
                  (cx - 60, ty + 2))

        # Top bar far left — combat timer
        lbl = font_xs.render(f"T+{int(engine.time_elapsed):>3}s", True, HUD_DIM)
        surf.blit(lbl, (vp["x"] + 8, ty + 6))

        # Top bar far right — kills
        kills = sum(1 for e in engine.enemies if not e.alive)
        total = len(engine.enemies)
        k_lbl = font_xs.render(f"KILLS {kills}/{total}", True, HUD_GREEN)
        surf.blit(k_lbl, (vp["x"] + vp["w"] - k_lbl.get_width() - 8, ty + 6))
