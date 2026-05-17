"""
Main menu screen with the game's title and backstory introduction.
"""
import math
import pygame


TITLE = "FRACTURED VOID"
SUBTITLE = "A game of trade, war, and survival in the ruins of empire"
TAGLINE = "Where corporations own the stars, and you own nothing but your ship."

LORE_LINES = [
    "2387. The Corporate Consolidation Wars ended seventeen years ago.",
    "Five Syndicates carved up human space and called it peace.",
    "",
    "You are Vael Korr — ex-Apex Syndicate pilot, recently discharged.",
    "Your ship: The Cinder Pact. 80 tons of battered freight capacity.",
    "Your credits: 5,000. Your agenda: survival.",
    "",
    "The Fracture Zone is spreading. Ghost Fleet vessels cross sectors",
    "that were safe six months ago. Something is happening out there.",
    "",
    "Nobody is coming to explain it to you.",
]

MENU_ITEMS = ["NEW GAME", "LOAD GAME", "QUIT"]


class MainMenu:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.fonts: dict = {}
        self._initialized = False
        self.selected = 0
        self._star_field = self._build_stars()
        self._time = 0.0
        self._lore_index = 0
        self._lore_timer = 0.0

    def init_fonts(self) -> None:
        if self._initialized:
            return
        try:
            mono = pygame.font.match_font("courier,couriernew,dejavusansmono")
            self.fonts["sm"] = pygame.font.Font(mono, 14)
            self.fonts["md"] = pygame.font.Font(mono, 18)
            self.fonts["lg"] = pygame.font.Font(mono, 30)
            self.fonts["xl"] = pygame.font.Font(mono, 60)
            self.fonts["tag"] = pygame.font.Font(mono, 15)
        except Exception:
            self.fonts["sm"] = pygame.font.SysFont("monospace", 14)
            self.fonts["md"] = pygame.font.SysFont("monospace", 18)
            self.fonts["lg"] = pygame.font.SysFont("monospace", 30)
            self.fonts["xl"] = pygame.font.SysFont("monospace", 60)
            self.fonts["tag"] = pygame.font.SysFont("monospace", 15)
        self._initialized = True

    def _build_stars(self) -> list[tuple[float, float, float, float]]:
        import random
        rng = random.Random(99)
        return [
            (rng.uniform(0, self.width), rng.uniform(0, self.height),
             rng.uniform(0.2, 1.5), rng.uniform(0.1, 0.8))
            for _ in range(200)
        ]

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
        elif event.type == pygame.MOUSEMOTION:
            pass
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pass
        return None

    def _activate(self) -> str | None:
        item = MENU_ITEMS[self.selected]
        if item == "NEW GAME":
            return "new_game"
        elif item == "LOAD GAME":
            return "load_game"
        elif item == "QUIT":
            return "quit"
        return None

    def update(self, dt: float) -> None:
        if not self._initialized:
            self.init_fonts()
        self._time += dt
        self._lore_timer += dt
        if self._lore_timer > 4.0:
            self._lore_timer = 0.0
            self._lore_index = (self._lore_index + 1) % len(LORE_LINES)

    def draw(self, surface: pygame.Surface) -> None:
        if not self._initialized:
            self.init_fonts()
        surface.fill((2, 2, 8))
        self._draw_stars(surface)
        self._draw_title(surface)
        self._draw_lore(surface)
        self._draw_menu(surface)
        self._draw_footer(surface)

    def _draw_stars(self, surface: pygame.Surface) -> None:
        for x, y, speed, brightness in self._star_field:
            t = self._time * speed * 0.3
            sx = (x + t * 15) % self.width
            alpha = int(180 * brightness * (0.7 + 0.3 * math.sin(self._time * speed * 2)))
            c = (alpha, alpha, min(255, alpha + 30))
            surface.set_at((int(sx), int(y)), c)

    def _draw_title(self, surface: pygame.Surface) -> None:
        font_xl = self.fonts["xl"]
        font_lg = self.fonts["lg"]
        font_tag = self.fonts["tag"]

        t = self._time
        pulse = 0.85 + 0.15 * math.sin(t * 1.5)
        glow_alpha = int(255 * pulse)

        title_surf = font_xl.render(TITLE, True, (int(80 * pulse), int(220 * pulse), int(120 * pulse)))
        tx = self.width // 2 - title_surf.get_width() // 2
        ty = 80

        # Glow effect
        for offset in range(4, 0, -1):
            glow = pygame.Surface(title_surf.get_size(), pygame.SRCALPHA)
            glow.blit(title_surf, (0, 0))
            glow.set_alpha(glow_alpha // (offset * 3))
            surface.blit(glow, (tx - offset, ty))
            surface.blit(glow, (tx + offset, ty))

        surface.blit(title_surf, (tx, ty))

        sub = font_lg.render(SUBTITLE, True, (60, 130, 70))
        surface.blit(sub, (self.width // 2 - sub.get_width() // 2, ty + 70))

        tag = font_tag.render(TAGLINE, True, (50, 90, 55))
        surface.blit(tag, (self.width // 2 - tag.get_width() // 2, ty + 105))

    def _draw_lore(self, surface: pygame.Surface) -> None:
        font_sm = self.fonts["sm"]
        start_y = 240
        visible_count = min(len(LORE_LINES), 8)
        for i in range(visible_count):
            line_idx = (self._lore_index + i) % len(LORE_LINES)
            line = LORE_LINES[line_idx]
            if not line:
                continue
            # Fade in/out for top and bottom lines
            if i == 0:
                alpha = int(255 * (self._lore_timer / 4.0))
            elif i == visible_count - 1:
                alpha = int(255 * (1 - self._lore_timer / 4.0))
            else:
                alpha = 200

            brightness = max(60, min(200, alpha))
            color = (int(brightness * 0.3), brightness, int(brightness * 0.4))
            lbl = font_sm.render(line, True, color)
            x = self.width // 2 - lbl.get_width() // 2
            surface.blit(lbl, (x, start_y + i * 20))

    def _draw_menu(self, surface: pygame.Surface) -> None:
        font_md = self.fonts["md"]
        start_y = self.height - 220
        for i, item in enumerate(MENU_ITEMS):
            is_sel = i == self.selected
            if is_sel:
                t = self._time
                pulse = 0.8 + 0.2 * math.sin(t * 3)
                color = (int(80 * pulse), int(255 * pulse), int(100 * pulse))
                prefix = "> "
                suffix = " <"
            else:
                color = (40, 100, 50)
                prefix = "  "
                suffix = "  "
            lbl = font_md.render(f"{prefix}{item}{suffix}", True, color)
            x = self.width // 2 - lbl.get_width() // 2
            surface.blit(lbl, (x, start_y + i * 40))

    def _draw_footer(self, surface: pygame.Surface) -> None:
        font_sm = self.fonts["sm"]
        ver = font_sm.render("v0.1.0  —  Fractured Void  —  github.com/riquo", True, (30, 50, 35))
        surface.blit(ver, (10, self.height - 20))
        controls = font_sm.render("Up/Down: Select    Enter: Confirm", True, (30, 60, 35))
        surface.blit(controls, (self.width - controls.get_width() - 10, self.height - 20))
