"""
Main menu — dramatic title screen with animated ship silhouette,
procedural nebula background, and cinematic text reveal.
"""
import math
import random
import pygame
from rendering.art import (
    draw_ship, draw_faction_logo, glow_text, get_scanline_overlay,
    HUD_GREEN, HUD_AMBER, HUD_DIM, FACTION_COLORS, METAL_DARK,
)

TITLE    = "FRACTURED VOID"
SUBTITLE = "Trade. Fight. Survive."
TAGLINE  = "2387 — Five corporations own the stars. You own nothing but your ship."

MENU_ITEMS = ["NEW GAME", "LOAD GAME", "QUIT"]

LORE_SLIDES = [
    "Year 2387. The Corporate Consolidation Wars ended seventeen years ago.",
    "Five Syndicates carved up human space and called it peace.",
    "You are VAEL KORR — ex-Apex Syndicate pilot. Discharged.",
    "Your ship: The Cinder Pact. 80 tons of battered freight capacity.",
    "The Fracture Zone is spreading. Ghost Fleet vessels cross sectors",
    "that were safe six months ago. Something is happening out there.",
    "Nobody is coming to explain it to you.",
]


class Star2D:
    __slots__ = ["x", "y", "size", "speed", "color", "alpha"]

    def __init__(self, rng, W, H):
        self.x = rng.uniform(0, W)
        self.y = rng.uniform(0, H)
        self.speed = rng.uniform(0.1, 0.6)
        self.size = rng.choice([1, 1, 1, 2])
        choices = [(255, 255, 255), (200, 210, 255), (255, 240, 210), (180, 200, 255)]
        self.color = rng.choice(choices)
        self.alpha = rng.randint(100, 240)

    def update(self, dt, W):
        self.x -= self.speed * dt * 20
        if self.x < 0:
            self.x = W

    def draw(self, surf):
        a = int(self.alpha)
        c = tuple(int(ch * a / 255) for ch in self.color)
        if self.size == 1:
            surf.set_at((int(self.x), int(self.y)), c)
        else:
            pygame.draw.circle(surf, c, (int(self.x), int(self.y)), self.size)


class NebulaBackground:
    def __init__(self, W, H):
        rng = random.Random(42)
        self._surf = pygame.Surface((W, H), pygame.SRCALPHA)
        palettes = [
            [(60, 10, 100), (15, 30, 110), (90, 15, 60), (20, 60, 90)],
            [(15, 55, 80), (55, 10, 100), (25, 65, 35), (90, 30, 20)],
        ]
        pal = rng.choice(palettes)
        # Large background washes
        for _ in range(8):
            cx = rng.randint(-W // 4, W + W // 4)
            cy = rng.randint(-H // 4, H + H // 4)
            r  = rng.randint(200, 600)
            col = rng.choice(pal)
            for i in range(r, 0, -max(1, r // 16)):
                t = i / r
                alpha = int(22 * t * (1 - t) * 4.5)
                pygame.draw.circle(self._surf, col + (alpha,), (cx, cy), i)
        # Bright core knots
        for _ in range(10):
            kx = rng.randint(0, W)
            ky = rng.randint(0, H)
            kr = rng.randint(20, 80)
            kcol = rng.choice(pal)
            kbright = tuple(min(255, c + 70) for c in kcol)
            for i in range(kr, 0, -max(1, kr // 8)):
                alpha = int(28 * (1 - i / kr) ** 1.2)
                pygame.draw.circle(self._surf, kbright + (alpha,), (kx, ky), i)

    def draw(self, surf):
        surf.blit(self._surf, (0, 0))


class MainMenu:
    def __init__(self, width: int, height: int):
        self.W = width
        self.H = height
        self.fonts: dict = {}
        self._initialized = False
        self.selected = 0
        self._rng = random.Random(99)
        self._stars = [Star2D(self._rng, width, height) for _ in range(250)]
        self._nebula: NebulaBackground | None = None
        self._time = 0.0
        self._lore_idx = 0
        self._lore_timer = 0.0
        self._lore_char = 0
        self._scanline: pygame.Surface | None = None
        # Ship silhouettes drifting across background
        self._bg_ships = self._init_bg_ships()

    def _init_bg_ships(self):
        ships = []
        for sid, x_start, y_frac, size_base, speed in [
            ("apex_enforcer",    -200, 0.18, 55, 18),
            ("merchant_hauler",  self.W + 100, 0.72, 40, -12),
            ("scout_marauder",   -100, 0.55, 30, 22),
            ("ghost_wraith",     self.W // 2, 0.85, 35, 8),
        ]:
            ships.append({
                "id": sid, "x": float(x_start),
                "y": self.H * y_frac, "size": size_base,
                "speed": speed, "alpha": 35,
            })
        return ships

    def init_fonts(self) -> None:
        if self._initialized:
            return
        try:
            mono = pygame.font.match_font("courier,couriernew,dejavusansmono")
            self.fonts["xs"]    = pygame.font.Font(mono, 12)
            self.fonts["sm"]    = pygame.font.Font(mono, 15)
            self.fonts["md"]    = pygame.font.Font(mono, 20)
            self.fonts["lg"]    = pygame.font.Font(mono, 32)
            self.fonts["xl"]    = pygame.font.Font(mono, 68)
            self.fonts["tag"]   = pygame.font.Font(mono, 16)
        except Exception:
            for k, s in [("xs",12),("sm",15),("md",20),("lg",32),("xl",68),("tag",16)]:
                self.fonts[k] = pygame.font.SysFont("monospace", s)
        self._nebula = NebulaBackground(self.W, self.H)
        self._scanline = get_scanline_overlay(self.W, self.H, alpha=28)
        self._initialized = True

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if not self._initialized:
            return None
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(MENU_ITEMS)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(MENU_ITEMS)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self._activate()
        return None

    def _activate(self) -> str | None:
        mapping = {"NEW GAME": "new_game", "LOAD GAME": "load_game", "QUIT": "quit"}
        return mapping.get(MENU_ITEMS[self.selected])

    def update(self, dt: float) -> None:
        if not self._initialized:
            self.init_fonts()
        self._time += dt

        for star in self._stars:
            star.update(dt, self.W)

        for ship in self._bg_ships:
            ship["x"] += ship["speed"] * dt
            # Wrap around
            if ship["speed"] > 0 and ship["x"] > self.W + 200:
                ship["x"] = -200.0
            elif ship["speed"] < 0 and ship["x"] < -200:
                ship["x"] = float(self.W + 200)

        self._lore_timer += dt
        chars_per_sec = 35
        current_line = LORE_SLIDES[self._lore_idx]
        self._lore_char = min(len(current_line), int(self._lore_timer * chars_per_sec))
        if self._lore_timer > 4.5:
            self._lore_timer = 0.0
            self._lore_char = 0
            self._lore_idx = (self._lore_idx + 1) % len(LORE_SLIDES)

    def draw(self, surface: pygame.Surface) -> None:
        if not self._initialized:
            self.init_fonts()
        surface.fill((2, 3, 10))

        if self._nebula:
            self._nebula.draw(surface)

        for star in self._stars:
            star.draw(surface)

        self._draw_bg_ships(surface)
        self._draw_faction_strip(surface)
        self._draw_title(surface)
        self._draw_lore(surface)
        self._draw_menu(surface)
        self._draw_footer(surface)

        if self._scanline:
            surface.blit(self._scanline, (0, 0))

    def _draw_bg_ships(self, surface: pygame.Surface) -> None:
        for ship_info in self._bg_ships:
            ghost = pygame.Surface((ship_info["size"] * 4, ship_info["size"] * 4), pygame.SRCALPHA)
            sid = ship_info["id"]
            color = FACTION_COLORS.get(
                "apex_syndicate" if "enforcer" in sid else
                "ghost_fleet" if "ghost" in sid else
                "ironveil_trading" if "hauler" in sid else
                "drift_cartel", (80, 80, 80)
            )
            sz = ship_info["size"]
            draw_ship(ghost, sid, sz * 2, sz * 2, sz * 0.9, color,
                      angle_deg=90 if ship_info["speed"] > 0 else -90,
                      engine_glow=True)
            ghost.set_alpha(ship_info["alpha"])
            cx = int(ship_info["x"]) - sz * 2
            cy = int(ship_info["y"]) - sz * 2
            surface.blit(ghost, (cx, cy))

    def _draw_faction_strip(self, surface: pygame.Surface) -> None:
        strip_y = self.H - 60
        factions = list(FACTION_COLORS.keys())
        spacing = self.W // (len(factions) + 1)
        for i, fid in enumerate(factions):
            fx = spacing * (i + 1)
            draw_faction_logo(surface, fid, fx, strip_y, 14)

    def _draw_title(self, surface: pygame.Surface) -> None:
        t = self._time
        W, H = self.W, self.H

        # FRACTURED VOID — large glowing title
        pulse = 0.88 + 0.12 * math.sin(t * 1.4)
        color = (int(60 * pulse), int(220 * pulse), int(90 * pulse))

        font_xl = self.fonts["xl"]
        title_surf = font_xl.render(TITLE, True, color)
        tx = W // 2 - title_surf.get_width() // 2
        ty = int(H * 0.12)

        # Multi-pass glow
        for i in range(6, 0, -1):
            glow_s = font_xl.render(TITLE, True, (20, int(80 * i / 6), 30))
            glow_s.set_alpha(int(40 * i / 6))
            surface.blit(glow_s, (tx - i, ty - i // 2))
            surface.blit(glow_s, (tx + i, ty - i // 2))

        surface.blit(title_surf, (tx, ty))

        # Horizontal lines flanking title
        title_mid_y = ty + title_surf.get_height() // 2
        line_alpha = int(160 * pulse)
        for side_x, end_x in [(tx - 20, 20), (tx + title_surf.get_width() + 20, W - 20)]:
            line_surf = pygame.Surface((abs(end_x - side_x) + 2, 2), pygame.SRCALPHA)
            line_surf.fill(color + (line_alpha,))
            surface.blit(line_surf, (min(side_x, end_x), title_mid_y))

        # Subtitle
        sub_font = self.fonts["lg"]
        sub = sub_font.render(SUBTITLE, True, (50, 160, 60))
        surface.blit(sub, (W // 2 - sub.get_width() // 2, ty + title_surf.get_height() + 8))

        # Tagline
        tag_font = self.fonts["tag"]
        tag = tag_font.render(TAGLINE, True, (35, 80, 42))
        surface.blit(tag, (W // 2 - tag.get_width() // 2, ty + title_surf.get_height() + 46))

    def _draw_lore(self, surface: pygame.Surface) -> None:
        font_sm = self.fonts["sm"]
        lore_y = int(self.H * 0.44)

        # Backdrop for lore text
        lore_w = int(self.W * 0.65)
        lore_x = self.W // 2 - lore_w // 2
        bg = pygame.Surface((lore_w, 30), pygame.SRCALPHA)
        pygame.draw.rect(bg, (4, 10, 6, 140), (0, 0, lore_w, 30))
        surface.blit(bg, (lore_x, lore_y - 5))

        line = LORE_SLIDES[self._lore_idx][:self._lore_char]
        # Typing cursor
        cursor = "|" if int(self._time * 3) % 2 == 0 else ""
        display = line + cursor

        lbl = font_sm.render(display, True, (80, 200, 90))
        surface.blit(lbl, (self.W // 2 - lbl.get_width() // 2, lore_y))

        # Dim previous lines
        prev_y = lore_y - 28
        for i in range(1, 4):
            prev_idx = (self._lore_idx - i) % len(LORE_SLIDES)
            alpha = max(0, 120 - i * 40)
            prev_lbl = font_sm.render(LORE_SLIDES[prev_idx], True, (30, 90, 35))
            prev_lbl.set_alpha(alpha)
            surface.blit(prev_lbl, (self.W // 2 - prev_lbl.get_width() // 2, prev_y))
            prev_y -= 22

    def _draw_menu(self, surface: pygame.Surface) -> None:
        font_md = self.fonts["md"]
        font_sm = self.fonts["sm"]
        W, H = self.W, self.H
        t = self._time

        menu_y = int(H * 0.56)
        item_h = 52

        for i, item in enumerate(MENU_ITEMS):
            is_sel = i == self.selected
            iy = menu_y + i * item_h
            iw = 300

            if is_sel:
                # Animated selected background
                pulse = 0.8 + 0.2 * math.sin(t * 3.5)
                bg_alpha = int(100 * pulse)
                bg = pygame.Surface((iw, 38), pygame.SRCALPHA)
                pygame.draw.rect(bg, (10, 40, 15, bg_alpha), (0, 0, iw, 38))
                pygame.draw.rect(bg, HUD_GREEN + (int(200 * pulse),), (0, 0, iw, 38), 1)
                surface.blit(bg, (W // 2 - iw // 2, iy - 4))

                color = (int(80 * pulse), int(255 * pulse), int(100 * pulse))
                text = f"> {item} <"
                glow_text(surface, font_md, text, color,
                          (W // 2 - font_md.size(text)[0] // 2, iy + 4))
            else:
                color = (25, 80, 30)
                lbl = font_md.render(f"  {item}  ", True, color)
                surface.blit(lbl, (W // 2 - lbl.get_width() // 2, iy + 4))

        # Controls hint
        hint = font_sm.render("Up/Down: Select    Enter: Confirm", True, (20, 50, 25))
        surface.blit(hint, (W // 2 - hint.get_width() // 2, menu_y + len(MENU_ITEMS) * item_h + 10))

    def _draw_footer(self, surface: pygame.Surface) -> None:
        font_xs = self.fonts["xs"]
        ver = font_xs.render("v0.2.0  —  FRACTURED VOID", True, (20, 45, 25))
        surface.blit(ver, (10, self.H - 18))
        link = font_xs.render("github.com/tkhemraj/fractured-void", True, (20, 45, 25))
        surface.blit(link, (self.W - link.get_width() - 10, self.H - 18))
