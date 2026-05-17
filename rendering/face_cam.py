"""
Wing Commander-style face cam overlay.
Shows enemy pilot or port master in a corner box with
faction-styled border, name tag, and scrolling dialogue.
"""
import json
import math
import os
import random
import pygame
from rendering.portraits import PortraitRenderer
from rendering.art import HUD_GREEN, HUD_AMBER, HUD_RED, FACTION_COLORS, glow_text

# ── Load dialogue ──────────────────────────────────────────────────────────
_DIALOGUE_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "combat_dialogue.json")
try:
    with open(_DIALOGUE_PATH) as f:
        _DIALOGUE = json.load(f)
except Exception:
    _DIALOGUE = {}

# Box placement constants
COMBAT_BOX_W  = 260
COMBAT_BOX_H  = 240
PORT_BOX_W    = 260
PORT_BOX_H    = 240

COMBAT_MARGIN = 12      # px from bottom-left corner
PORT_MARGIN   = 12      # px from bottom-right corner

# How often a new dialogue line is picked
DIALOGUE_INTERVAL = 4.0
TYPEWRITER_CPS    = 45  # characters per second


# ── Faction border colours ─────────────────────────────────────────────────
FACTION_BORDER = {
    "apex_syndicate":    ((180, 30,  30),  (255, 80,  80)),
    "helix_commerce":    ((30,  80,  180), (80,  160, 255)),
    "ironveil_trading":  ((140, 100, 30),  (220, 170, 60)),
    "drift_cartel":      ((140, 60,  160), (220, 100, 255)),
    "the_remnant":       ((30,  120, 50),  (60,  220, 80)),
    "ghost_fleet":       ((20,  200, 220), (80,  255, 240)),
}

DEFAULT_BORDER = ((80, 80, 80), (150, 150, 150))

# Named pilots per faction — shown in the name tag
FACTION_PILOTS = {
    "apex_syndicate":    ["Cmdr. Reyes", "Lt. Vance", "Capt. Ström", "Cmdr. Kell"],
    "helix_commerce":    ["Agent Puri", "VP Larche", "Exec. Doss", "Broker Ylva"],
    "ironveil_trading":  ["Pilot Grunn", "Hauler Osk", "Sec. Faye", "Cpt. Wren"],
    "drift_cartel":      ["Slick", "Vero", "Kaz the Red", "Dex"],
    "the_remnant":       ["Mira Dahl", "Cpt. Orin", "Sgt. Lenne", "Rebel Frix"],
    "ghost_fleet":       ["UNIT-7", "NODE-Σ", "ENTITY-4", "RELAY-Ω"],
}

FACTION_PORT_MASTERS = {
    "apex_syndicate":    "Port Authority",
    "helix_commerce":    "Helix Concierge",
    "ironveil_trading":  "Ironveil Dock",
    "drift_cartel":      "The Handler",
    "the_remnant":       "Free Dockmaster",
}


class FaceCam:
    """
    Manages a single face-cam box (either combat enemy or port master).

    mode: "combat"  — bottom-left, updates on combat state
          "port"    — bottom-right, greeting lines only
    """

    def __init__(self, mode: str = "combat"):
        self.mode = mode
        self.faction_id: str = ""
        self.char_seed: int = 0
        self.pilot_name: str = ""
        self._portrait: PortraitRenderer | None = None
        self._portrait_cache: pygame.Surface | None = None
        self._dialogue_timer = 0.0
        self._current_line  = ""
        self._typed_chars   = 0
        self._type_timer    = 0.0
        self._emotion       = "neutral"
        self._active        = False
        self._rng           = random.Random()
        self._fonts: dict   = {}
        self._initialized   = False
        self._anim_time     = 0.0
        self._scanline_alpha = 40
        self._portrait_surf: pygame.Surface | None = None
        self._portrait_rect: pygame.Rect | None = None
        self._box_w = COMBAT_BOX_W if mode == "combat" else PORT_BOX_W
        self._box_h = COMBAT_BOX_H if mode == "combat" else PORT_BOX_H

    # ── Public API ─────────────────────────────────────────────────────────
    def activate(self, faction_id: str, char_seed: int = 0) -> None:
        self.faction_id = faction_id
        self.char_seed = char_seed
        self._rng = random.Random(char_seed ^ hash(faction_id) & 0xFFFF)
        self._portrait = PortraitRenderer(faction_id, char_seed)
        self._portrait_surf = None
        self._portrait_rect = None
        self._active = True
        self._dialogue_timer = DIALOGUE_INTERVAL  # trigger immediate pick
        self._current_line = ""
        self._typed_chars = 0
        self._type_timer = 0.0
        self._emotion = "neutral"

        # pick pilot name
        pool = FACTION_PILOTS.get(faction_id, ["Unknown"])
        self.pilot_name = pool[char_seed % len(pool)]
        if self.mode == "port":
            self.pilot_name = FACTION_PORT_MASTERS.get(faction_id, "Dockmaster")

    def deactivate(self) -> None:
        self._active = False

    def set_emotion(self, emotion: str) -> None:
        if emotion != self._emotion:
            self._emotion = emotion
            self._portrait_surf = None   # bust portrait cache on emotion change
            self._dialogue_timer = DIALOGUE_INTERVAL  # pick new line

    def update(self, dt: float) -> None:
        if not self._active:
            return
        self._anim_time += dt
        self._dialogue_timer += dt
        if self._dialogue_timer >= DIALOGUE_INTERVAL:
            self._dialogue_timer = 0.0
            self._pick_dialogue()

        # Typewriter advance
        chars_needed = int(self._type_timer * TYPEWRITER_CPS)
        if self._typed_chars < len(self._current_line):
            self._type_timer += dt
            self._typed_chars = min(len(self._current_line),
                                    int(self._type_timer * TYPEWRITER_CPS))

    def draw(self, surface: pygame.Surface, screen_w: int, screen_h: int) -> None:
        if not self._active:
            return
        if not self._initialized:
            self._init_fonts()

        BW, BH = self._box_w, self._box_h
        if self.mode == "combat":
            bx = COMBAT_MARGIN
        else:
            bx = screen_w - BW - PORT_MARGIN
        by = screen_h - BH - COMBAT_MARGIN

        border_dark, border_light = FACTION_BORDER.get(self.faction_id, DEFAULT_BORDER)
        pulse = 0.85 + 0.15 * math.sin(self._anim_time * 2.5)

        # Outer box background
        box_surf = pygame.Surface((BW, BH), pygame.SRCALPHA)
        pygame.draw.rect(box_surf, (4, 8, 4, 210), (0, 0, BW, BH))
        pygame.draw.rect(box_surf, border_dark + (255,), (0, 0, BW, BH), 2)

        # Corner accent brackets
        ca = int(14)
        cl = tuple(int(c * pulse) for c in border_light)
        for cx2, cy2, dx, dy in [(0, 0, 1, 1), (BW-1, 0, -1, 1),
                                  (0, BH-1, 1, -1), (BW-1, BH-1, -1, -1)]:
            pygame.draw.line(box_surf, cl, (cx2, cy2), (cx2 + dx * ca, cy2), 2)
            pygame.draw.line(box_surf, cl, (cx2, cy2), (cx2, cy2 + dy * ca), 2)

        surface.blit(box_surf, (bx, by))

        # ── Portrait (upper ~60% of box) ──
        PORTRAIT_H = int(BH * 0.60)
        port_rect = pygame.Rect(bx + 2, by + 2, BW - 4, PORTRAIT_H - 2)
        if self._portrait_surf is None or self._portrait_rect != port_rect:
            self._portrait_rect = port_rect
            self._portrait_surf = pygame.Surface((port_rect.w, port_rect.h), pygame.SRCALPHA)
            if self._portrait:
                self._portrait.draw(self._portrait_surf,
                                    pygame.Rect(0, 0, port_rect.w, port_rect.h),
                                    self._emotion)
        surface.blit(self._portrait_surf, port_rect.topleft)

        # Scanline effect over portrait
        sc_surf = pygame.Surface((port_rect.w, port_rect.h), pygame.SRCALPHA)
        for y in range(0, port_rect.h, 3):
            sc_line = pygame.Surface((port_rect.w, 1), pygame.SRCALPHA)
            sc_line.fill((0, 0, 0, self._scanline_alpha))
            sc_surf.blit(sc_line, (0, y))
        surface.blit(sc_surf, port_rect.topleft)

        # Portrait border
        pygame.draw.rect(surface, border_dark, port_rect, 1)

        # ── Name tag ──
        name_y = by + PORTRAIT_H + 2
        name_font = self._fonts.get("name")
        if name_font:
            name_col = tuple(int(c * pulse) for c in border_light)
            name_lbl = name_font.render(self.pilot_name, True, name_col)
            surface.blit(name_lbl, (bx + 6, name_y))

        # Emotion badge (small)
        em_font = self._fonts.get("em")
        if em_font and self.mode == "combat":
            em_str = f"[{self._emotion.upper()}]"
            em_col = {
                "neutral": (80, 140, 80),
                "taunting": (180, 140, 40),
                "angry":   (220, 60, 40),
                "scared":  (140, 200, 220),
                "dying":   (160, 80, 80),
            }.get(self._emotion, (80, 80, 80))
            em_lbl = em_font.render(em_str, True, em_col)
            surface.blit(em_lbl, (bx + BW - em_lbl.get_width() - 6, name_y))

        # ── Dialogue text (bottom strip) ──
        text_y = name_y + (name_font.get_height() if name_font else 14) + 3
        dial_font = self._fonts.get("dial")
        if dial_font and self._current_line:
            visible = self._current_line[:self._typed_chars]
            cursor = "|" if int(self._anim_time * 3) % 2 == 0 and self._typed_chars < len(self._current_line) else ""
            self._draw_wrapped(surface, dial_font, visible + cursor,
                               (180, 200, 180), bx + 5, text_y, BW - 10, by + BH - 4)

    # ── Internal ───────────────────────────────────────────────────────────
    def _init_fonts(self) -> None:
        try:
            mono = pygame.font.match_font("courier,couriernew,dejavusansmono")
            self._fonts["name"] = pygame.font.Font(mono, 12)
            self._fonts["em"]   = pygame.font.Font(mono, 10)
            self._fonts["dial"] = pygame.font.Font(mono, 11)
        except Exception:
            self._fonts["name"] = pygame.font.SysFont("monospace", 12)
            self._fonts["em"]   = pygame.font.SysFont("monospace", 10)
            self._fonts["dial"] = pygame.font.SysFont("monospace", 11)
        self._initialized = True

    def _pick_dialogue(self) -> None:
        if self.mode == "port":
            pool = _DIALOGUE.get("port_greetings", {}).get(self.faction_id, [])
        else:
            faction_data = _DIALOGUE.get(self.faction_id, {})
            pool = faction_data.get(self._emotion, [])
            if not pool:
                pool = faction_data.get("neutral", [])

        if pool:
            self._current_line = self._rng.choice(pool)
        else:
            self._current_line = "..."

        self._typed_chars = 0
        self._type_timer  = 0.0
        self._portrait_surf = None   # refresh portrait to new emotion

    def _draw_wrapped(self, surface, font, text, color, x, y, max_w, max_y):
        """Word-wrap text into box."""
        words = text.split(" ")
        line = ""
        cy = y
        lh = font.get_height() + 1
        for word in words:
            test = (line + " " + word).strip()
            if font.size(test)[0] <= max_w:
                line = test
            else:
                if cy + lh > max_y:
                    break
                lbl = font.render(line, True, color)
                surface.blit(lbl, (x, cy))
                cy += lh
                line = word
        if line and cy + lh <= max_y:
            lbl = font.render(line, True, color)
            surface.blit(lbl, (x, cy))


# ── Convenience class combining combat + port cams ─────────────────────────
class FaceCamSystem:
    """
    Holds one combat cam (bottom-left) and one port cam (bottom-right).
    Combat screen uses combat_cam; trading screen uses port_cam.
    """
    def __init__(self):
        self.combat_cam = FaceCam("combat")
        self.port_cam   = FaceCam("port")

    def start_combat(self, faction_id: str, char_seed: int = 0) -> None:
        self.combat_cam.activate(faction_id, char_seed)
        self.port_cam.deactivate()

    def stop_combat(self) -> None:
        self.combat_cam.deactivate()

    def enter_port(self, faction_id: str) -> None:
        self.port_cam.activate(faction_id, abs(hash(faction_id)) % 999)
        self.combat_cam.deactivate()

    def leave_port(self) -> None:
        self.port_cam.deactivate()

    def set_combat_emotion(self, emotion: str) -> None:
        self.combat_cam.set_emotion(emotion)

    def update(self, dt: float) -> None:
        self.combat_cam.update(dt)
        self.port_cam.update(dt)

    def draw_combat(self, surface: pygame.Surface, screen_w: int, screen_h: int) -> None:
        self.combat_cam.draw(surface, screen_w, screen_h)

    def draw_port(self, surface: pygame.Surface, screen_w: int, screen_h: int) -> None:
        self.port_cam.draw(surface, screen_w, screen_h)


# Module-level singleton
face_cams = FaceCamSystem()
