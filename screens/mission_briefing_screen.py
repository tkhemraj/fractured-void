"""
Mission briefing screen — Wing Commander style.
Shows character portrait (procedurally drawn), mission intro dialogue,
objectives, and rewards. Player accepts or declines.
"""
import math
import pygame
from engine.mission_manager import missions as mission_mgr
from engine.game_state import GameState
from audio.sound_gen import sounds


class PortraitRenderer:
    """Draws procedural character portraits using pygame shapes."""

    STYLES = {
        "remnant":   {"bg": (15, 25, 35), "accent": (80, 160, 220), "uniform": (50, 80, 100)},
        "drift":     {"bg": (20, 10, 30), "accent": (180, 80, 220), "uniform": (60, 40, 80)},
        "corporate": {"bg": (25, 20, 10), "accent": (160, 130, 70), "uniform": (80, 70, 50)},
        "scientist": {"bg": (10, 25, 15), "accent": (60, 180, 100), "uniform": (40, 80, 60)},
        "military":  {"bg": (25, 8, 8),   "accent": (200, 60, 40),  "uniform": (80, 30, 30)},
        "ghost":     {"bg": (5, 20, 20),  "accent": (100, 220, 220), "uniform": (20, 60, 60)},
    }

    @staticmethod
    def draw(surface: pygame.Surface, char_data: dict, x: int, y: int, w: int, h: int) -> None:
        style = PortraitRenderer.STYLES.get(char_data.get("portrait_style", "corporate"), PortraitRenderer.STYLES["corporate"])
        skin = tuple(char_data.get("skin_color", [160, 120, 100]))
        hair = tuple(char_data.get("hair_color", [60, 40, 30]))
        eyes = tuple(char_data.get("eye_color", [80, 120, 160]))
        scar = char_data.get("scar", False)
        is_ghost = char_data.get("portrait_style") == "ghost"

        # Background
        pygame.draw.rect(surface, style["bg"], (x, y, w, h))
        pygame.draw.rect(surface, style["accent"], (x, y, w, h), 2)

        cx = x + w // 2
        if is_ghost:
            PortraitRenderer._draw_ghost(surface, cx, y, w, h, style, eyes)
            return

        # Uniform / body
        body_y = y + int(h * 0.62)
        body_h = int(h * 0.40)
        pygame.draw.rect(surface, style["uniform"], (x, body_y, w, body_h))
        # Collar
        pygame.draw.polygon(surface, style["accent"], [
            (cx, body_y + 5),
            (cx - 18, body_y + 28),
            (cx + 18, body_y + 28),
        ])

        # Neck
        neck_y = y + int(h * 0.53)
        pygame.draw.rect(surface, skin, (cx - 10, neck_y, 20, int(h * 0.12)))

        # Head (ellipse)
        head_cx, head_cy = cx, y + int(h * 0.32)
        head_w, head_h = int(w * 0.42), int(h * 0.35)
        pygame.draw.ellipse(surface, skin, (head_cx - head_w // 2, head_cy - head_h // 2, head_w, head_h))

        # Hair
        hair_rect = (head_cx - head_w // 2, head_cy - head_h // 2, head_w, head_h // 2)
        pygame.draw.ellipse(surface, hair, hair_rect)
        pygame.draw.rect(surface, hair, (head_cx - head_w // 2, head_cy - head_h // 2, head_w, head_h // 4))

        # Eyes
        eye_y = head_cy - 5
        for ex in [head_cx - 14, head_cx + 14]:
            pygame.draw.ellipse(surface, (240, 230, 220), (ex - 8, eye_y - 5, 16, 10))
            pygame.draw.circle(surface, eyes, (ex, eye_y), 5)
            pygame.draw.circle(surface, (10, 10, 10), (ex, eye_y), 3)
            pygame.draw.circle(surface, (240, 240, 240), (ex + 2, eye_y - 2), 1)

        # Nose
        pygame.draw.line(surface, tuple(max(0, c - 30) for c in skin), (head_cx - 3, eye_y + 8), (head_cx, eye_y + 16), 2)

        # Mouth
        pygame.draw.arc(surface, tuple(max(0, c - 40) for c in skin),
                        (head_cx - 12, eye_y + 20, 24, 10), math.pi, 0, 2)

        # Scar
        if scar:
            pygame.draw.line(surface, tuple(max(0, c - 60) for c in skin),
                             (head_cx + 8, eye_y - 20), (head_cx + 18, eye_y + 15), 2)

        # Ambient lighting gradient
        for i in range(6):
            alpha = 40 - i * 6
            pygame.draw.rect(surface, style["accent"] + (alpha,),
                             (x + i, y + i, w - i * 2, h - i * 2), 1)

    @staticmethod
    def _draw_ghost(surface, cx, y, w, h, style, eyes):
        accent = style["accent"]
        # Pulsing outline figure
        for r in range(0, 40, 8):
            alpha = max(0, 80 - r * 2)
            pygame.draw.circle(surface, accent + (alpha,), (cx, y + h // 3), r + 30)
        pygame.draw.circle(surface, accent, (cx, y + h // 3), 30, 2)
        # Eye-like patterns
        for ex in [cx - 14, cx + 14]:
            pygame.draw.circle(surface, eyes, (ex, y + h // 3), 8)
            pygame.draw.circle(surface, (255, 255, 255), (ex, y + h // 3), 4)
        # Signal wave lines at bottom
        import math
        for i, row_y in enumerate(range(y + h * 2 // 3, y + h - 10, 10)):
            pts = []
            for xo in range(0, w, 4):
                wave_y = row_y + int(6 * math.sin((xo + i * 20) * 0.15))
                pts.append((x + xo, wave_y))
            if len(pts) > 1:
                pygame.draw.lines(surface, accent + (100 - i * 20,), False, pts, 1)


class MissionBriefingScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.fonts: dict = {}
        self._initialized = False

        self.current_mission: dict | None = None
        self.current_char: dict | None = None
        self.available_missions: list[dict] = []
        self.selected_mission_idx = 0
        self.dialogue_line = 0
        self.dialogue_timer = 0.0
        self.dialogue_speed = 0.04
        self.char_visible = 0
        self.state = "list"
        self._all_chars: dict = {}
        self._game_state: GameState | None = None

    def init_fonts(self) -> None:
        if self._initialized:
            return
        try:
            mono = pygame.font.match_font("courier,couriernew,dejavusansmono")
            self.fonts["sm"] = pygame.font.Font(mono, 13)
            self.fonts["md"] = pygame.font.Font(mono, 17)
            self.fonts["lg"] = pygame.font.Font(mono, 24)
            self.fonts["xl"] = pygame.font.Font(mono, 36)
        except Exception:
            self.fonts["sm"] = pygame.font.SysFont("monospace", 13)
            self.fonts["md"] = pygame.font.SysFont("monospace", 17)
            self.fonts["lg"] = pygame.font.SysFont("monospace", 24)
            self.fonts["xl"] = pygame.font.SysFont("monospace", 36)
        import json, os
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        with open(os.path.join(data_dir, "characters.json")) as f:
            self._all_chars = json.load(f)
        self._initialized = True

    def open(self, available: list[dict], game_state: GameState) -> None:
        self.init_fonts()
        self.available_missions = available
        self._game_state = game_state
        self.selected_mission_idx = 0
        self.state = "list"
        self.dialogue_line = 0
        self.dialogue_timer = 0.0
        self.char_visible = 0

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type != pygame.KEYDOWN:
            return None

        if self.state == "list":
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected_mission_idx = (self.selected_mission_idx - 1) % max(1, len(self.available_missions))
                sounds.play("beep_low", 0.4)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_mission_idx = (self.selected_mission_idx + 1) % max(1, len(self.available_missions))
                sounds.play("beep_low", 0.4)
            elif event.key == pygame.K_RETURN and self.available_missions:
                self._open_briefing(self.available_missions[self.selected_mission_idx])
            elif event.key == pygame.K_ESCAPE:
                return "sector_map"

        elif self.state == "briefing":
            if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                if self.dialogue_line < len(self._current_dialogue) - 1:
                    self.dialogue_line += 1
                    self.char_visible = 0
                else:
                    # Advance to accept/decline
                    self.state = "accept_prompt"
                    sounds.play("beep_high", 0.5)
            elif event.key == pygame.K_ESCAPE:
                self.state = "list"

        elif self.state == "accept_prompt":
            if event.key == pygame.K_y or event.key == pygame.K_RETURN:
                self._accept_mission()
                return "sector_map"
            elif event.key == pygame.K_n or event.key == pygame.K_ESCAPE:
                self.state = "list"

        return None

    def _open_briefing(self, mission: dict) -> None:
        self.current_mission = mission
        self.current_char = self._all_chars.get(mission.get("giver", ""), {})
        self._current_dialogue = mission.get("dialogue_intro", ["No briefing available."])
        self.dialogue_line = 0
        self.char_visible = 0
        self.dialogue_timer = 0.0
        self.state = "briefing"
        sounds.play("beep_high", 0.5)

    def _accept_mission(self) -> None:
        if self.current_mission:
            mission_mgr.load()
            mission_mgr.accept_mission(self.current_mission["id"])
            if self._game_state:
                self._game_state.player.add_log(f"Mission accepted: {self.current_mission['title']}")
            sounds.play("mission_accept", 0.9)

    def update(self, dt: float) -> None:
        if self.state == "briefing":
            self.dialogue_timer += dt
            line = self._current_dialogue[self.dialogue_line] if self._current_dialogue else ""
            chars_per_sec = 40
            self.char_visible = min(len(line), int(self.dialogue_timer * chars_per_sec))

    def draw(self, surface: pygame.Surface) -> None:
        if not self._initialized:
            self.init_fonts()
        surface.fill((4, 8, 6))

        if self.state == "list":
            self._draw_mission_list(surface)
        elif self.state in ("briefing", "accept_prompt"):
            self._draw_briefing(surface)

    def _draw_mission_list(self, surface: pygame.Surface) -> None:
        font_lg = self.fonts["lg"]
        font_md = self.fonts["md"]
        font_sm = self.fonts["sm"]

        pygame.draw.rect(surface, (5, 14, 8), (0, 0, self.width, 50))
        pygame.draw.line(surface, (40, 100, 50), (0, 50), (self.width, 50), 1)
        title = font_lg.render("MISSION BOARD", True, (80, 220, 100))
        surface.blit(title, (20, 12))

        if not self.available_missions:
            no_miss = font_md.render("No missions available in this sector.", True, (60, 100, 60))
            surface.blit(no_miss, (self.width // 2 - no_miss.get_width() // 2, self.height // 2))
            esc = font_sm.render("Press Esc to leave", True, (40, 70, 40))
            surface.blit(esc, (self.width // 2 - esc.get_width() // 2, self.height // 2 + 40))
            return

        y = 70
        for i, m in enumerate(self.available_missions):
            is_sel = i == self.selected_mission_idx
            bg = (10, 28, 14) if is_sel else (4, 8, 6)
            pygame.draw.rect(surface, bg, (10, y, self.width - 20, 80))
            pygame.draw.rect(surface, (40, 80, 40) if is_sel else (20, 40, 20), (10, y, self.width - 20, 80), 1)

            from rendering.map_renderer import FACTION_COLORS
            fc = FACTION_COLORS.get(m.get("faction", ""), (80, 80, 80))
            title_lbl = font_md.render(m.get("title", ""), True, (200, 255, 200) if is_sel else (100, 180, 100))
            surface.blit(title_lbl, (20, y + 8))

            giver_name = self._all_chars.get(m.get("giver", ""), {}).get("name", m.get("giver", ""))
            giver_lbl = font_sm.render(f"From: {giver_name}", True, fc)
            surface.blit(giver_lbl, (20, y + 32))

            reward = font_sm.render(f"Reward: {m.get('reward_credits', 0):,} CR", True, (180, 160, 60))
            surface.blit(reward, (20, y + 50))

            type_lbl = font_sm.render(m.get("type", "").upper(), True, (60, 120, 80))
            surface.blit(type_lbl, (self.width - 120, y + 8))

            y += 90

        hints = font_sm.render("Up/Down: Select    Enter: View briefing    Esc: Back", True, (40, 70, 40))
        surface.blit(hints, (10, self.height - 22))

    def _draw_briefing(self, surface: pygame.Surface) -> None:
        font_lg = self.fonts["lg"]
        font_md = self.fonts["md"]
        font_sm = self.fonts["sm"]
        m = self.current_mission
        char = self.current_char
        if not m:
            return

        # Portrait panel
        port_w, port_h = 280, 340
        port_x, port_y = 30, 60
        if char:
            PortraitRenderer.draw(surface, char, port_x, port_y, port_w, port_h)
            name_lbl = font_md.render(char.get("name", ""), True, (180, 255, 180))
            surface.blit(name_lbl, (port_x, port_y + port_h + 8))
            title_lbl = font_sm.render(char.get("title", ""), True, (80, 160, 80))
            surface.blit(title_lbl, (port_x, port_y + port_h + 30))

        # Dialogue panel
        dlg_x = port_x + port_w + 30
        dlg_w = self.width - dlg_x - 20
        dlg_y = 60

        pygame.draw.rect(surface, (5, 14, 8), (dlg_x, dlg_y, dlg_w, 300))
        pygame.draw.rect(surface, (40, 100, 50), (dlg_x, dlg_y, dlg_w, 300), 1)

        mission_title = font_lg.render(m.get("title", ""), True, (80, 220, 100))
        surface.blit(mission_title, (dlg_x + 12, dlg_y + 10))

        if self._current_dialogue:
            line = self._current_dialogue[self.dialogue_line]
            visible = line[:self.char_visible]
            # Word-wrap at ~55 chars
            words = visible.split(" ")
            wrapped_lines, current = [], ""
            for w in words:
                test = (current + " " + w).strip()
                if len(test) > 52:
                    wrapped_lines.append(current)
                    current = w
                else:
                    current = test
            wrapped_lines.append(current)

            for li, wl in enumerate(wrapped_lines):
                dlg_lbl = font_md.render(wl, True, (160, 220, 160))
                surface.blit(dlg_lbl, (dlg_x + 12, dlg_y + 55 + li * 26))

            # Progress indicator
            prog = f"{self.dialogue_line + 1}/{len(self._current_dialogue)}"
            prog_lbl = font_sm.render(prog, True, (40, 80, 40))
            surface.blit(prog_lbl, (dlg_x + dlg_w - 60, dlg_y + 270))

            if self.char_visible >= len(line):
                cont = font_sm.render("[ Space: Continue ]", True, (60, 160, 60))
                surface.blit(cont, (dlg_x + 12, dlg_y + 272))

        # Objectives / rewards panel
        obj_y = 380
        pygame.draw.rect(surface, (4, 10, 6), (dlg_x, obj_y, dlg_w, 200))
        pygame.draw.rect(surface, (30, 70, 35), (dlg_x, obj_y, dlg_w, 200), 1)

        obj_title = font_md.render("OBJECTIVES", True, (60, 160, 80))
        surface.blit(obj_title, (dlg_x + 12, obj_y + 10))
        oy = obj_y + 36
        for obj in m.get("objectives", []):
            otype = obj["type"]
            if otype == "carry":
                desc = f"  Carry {obj['quantity']}x {obj['item']}"
            elif otype == "deliver_to_sector":
                desc = f"  Deliver to sector {obj['sector']}"
            elif otype == "visit_sector":
                desc = f"  Visit sector {obj['sector']}"
            elif otype == "combat_victory":
                desc = f"  Destroy {obj['count']}x {obj.get('faction', 'enemy').replace('_', ' ')} vessel(s)"
            else:
                desc = f"  {otype}"
            surface.blit(font_sm.render(desc, True, (100, 200, 120)), (dlg_x, oy))
            oy += 18

        rew_x = dlg_x + dlg_w // 2
        rew_title = font_md.render("REWARD", True, (180, 160, 60))
        surface.blit(rew_title, (rew_x, obj_y + 10))
        cr = m.get("reward_credits", 0)
        surface.blit(font_sm.render(f"  {cr:,} credits", True, (220, 200, 80)), (rew_x, obj_y + 36))
        for fid, delta in m.get("reward_relation", {}).items():
            sign = "+" if delta > 0 else ""
            color = (80, 200, 80) if delta > 0 else (200, 80, 80)
            surface.blit(font_sm.render(f"  {sign}{delta} {fid.replace('_', ' ')}", True, color), (rew_x, obj_y + 54 + list(m.get("reward_relation", {}).keys()).index(fid) * 16))

        if self.state == "accept_prompt":
            pygame.draw.rect(surface, (10, 30, 12), (dlg_x, dlg_y + 305, dlg_w, 60))
            pygame.draw.rect(surface, (60, 160, 60), (dlg_x, dlg_y + 305, dlg_w, 60), 2)
            prompt = font_lg.render("Accept mission? [Y] Yes  [N] No", True, (120, 255, 120))
            surface.blit(prompt, (dlg_x + 12, dlg_y + 320))
