"""
Character portrait renderer — bold illustrative style.
Works at small sizes (140×180+) because it uses circles & filled rects, not thin polygons.
Each portrait is cached per (faction, seed, emotion, size).
"""
import math
import pygame
import random

FACTION_PORTRAIT_STYLES = {
    "apex_syndicate":   "military",
    "helix_commerce":   "corporate",
    "ironveil_trading": "corporate",
    "drift_cartel":     "drift",
    "the_remnant":      "remnant",
    "ghost_fleet":      "ghost",
}

# ── Palette pools ──────────────────────────────────────────────────────────
SKIN_TONES = [
    (255, 218, 175), (240, 195, 145), (210, 165, 115),
    (175, 125, 80),  (135, 88,  52),  (88,  52,  30),
]
HAIR = {
    "military":  [(20, 20, 20), (55, 40, 25), (80, 55, 35), (195, 190, 180)],
    "corporate": [(15, 15, 15), (55, 45, 35), (175, 155, 95), (215, 205, 185)],
    "drift":     [(195, 45, 25), (235, 175, 0), (45, 195, 215), (15, 15, 15)],
    "remnant":   [(75, 55, 25), (115, 85, 45), (45, 38, 28), (175, 165, 135)],
    "ghost":     [(0, 0, 0)],
}
UNIFORM = {
    "military":  (25, 30, 55),
    "corporate": (35, 35, 75),
    "drift":     (65, 35, 12),
    "remnant":   (38, 48, 28),
    "ghost":     (0,  0,  0),
}
FACTION_ACCENT = {
    "apex_syndicate":   (220, 55, 40),
    "helix_commerce":   (55,  180, 95),
    "ironveil_trading": (160, 130, 65),
    "drift_cartel":     (175, 80,  220),
    "the_remnant":      (75,  155, 220),
    "ghost_fleet":      (95,  220, 220),
}

# ── Emotion → expression params ────────────────────────────────────────────
EMOTIONS = {
    "neutral": dict(brow_y=0,  mouth_w=1.0, smile=0,    eye_h=1.0),
    "taunting":dict(brow_y=-3, mouth_w=0.9, smile=0.6,  eye_h=0.75),
    "angry":   dict(brow_y=5,  mouth_w=0.8, smile=-0.3, eye_h=0.65),
    "scared":  dict(brow_y=-6, mouth_w=0.9, smile=-0.5, eye_h=1.35),
    "dying":   dict(brow_y=-3, mouth_w=0.85,smile=-0.2, eye_h=0.45),
}


class PortraitRenderer:
    def __init__(self, faction_id: str, char_seed: int = 0):
        self.faction_id = faction_id
        self.style = FACTION_PORTRAIT_STYLES.get(faction_id, "remnant")
        self._rng = random.Random(char_seed ^ (hash(faction_id) & 0xFFFF))
        self._ghost = self.style == "ghost"
        self._pick()
        self._cache: dict = {}

    def _pick(self):
        r = self._rng
        self.skin       = r.choice(SKIN_TONES)
        self.hair_col   = r.choice(HAIR.get(self.style, HAIR["remnant"]))
        self.uniform    = UNIFORM.get(self.style, UNIFORM["remnant"])
        self.accent     = FACTION_ACCENT.get(self.faction_id, (80, 80, 80))
        self.eye_col    = r.choice([(80,120,180),(55,145,75),(135,95,55),(80,80,80)])
        self.has_scar   = r.random() < 0.3
        self.scar_side  = r.choice([-1, 1])
        self.has_beard  = r.random() < 0.35 and self.style in ("drift", "remnant", "military")
        self.hair_style = r.choice(["short","medium","bald"]) if self.style != "drift" else r.choice(["short","medium"])
        self.face_w_fac = r.uniform(0.82, 1.08)
        if self._ghost:
            self.ghost_col = r.choice([(40,200,220),(80,255,160),(200,80,255)])
            self.n_tendrils = r.randint(4, 7)

    def draw(self, surface: pygame.Surface, rect: pygame.Rect,
             emotion: str = "neutral") -> None:
        key = f"{emotion}_{rect.w}_{rect.h}"
        if key not in self._cache:
            buf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            self._render(buf, emotion)
            self._cache[key] = buf
        surface.blit(self._cache[key], rect.topleft)

    def _render(self, surf, emotion):
        W, H = surf.get_size()
        ep = EMOTIONS.get(emotion, EMOTIONS["neutral"])
        if self._ghost:
            self._draw_ghost(surf, W, H, ep)
        else:
            self._draw_human(surf, W, H, ep)

    # ─────────────────────────────────────────────────────────── HUMAN ──
    def _draw_human(self, surf, W, H, ep):
        cx = W // 2

        # ── Gradient background (dark at top, faction-tinted at bottom) ──
        acc = self.accent
        for y in range(H):
            t = y / H
            r = int(8 + acc[0] * 0.12 * t)
            g = int(8 + acc[1] * 0.12 * t)
            b = int(12 + acc[2] * 0.14 * t)
            pygame.draw.line(surf, (r, g, b), (0, y), (W, y))

        # ── Uniform / torso ──
        uni = self.uniform
        torso_top = int(H * 0.70)
        pygame.draw.polygon(surf, uni, [
            (cx - int(W*0.55), H),
            (cx + int(W*0.55), H),
            (cx + int(W*0.32), torso_top),
            (cx - int(W*0.32), torso_top),
        ])
        # Collar highlight
        uni_light = tuple(min(255, c+30) for c in uni)
        pygame.draw.line(surf, uni_light,
                         (cx - int(W*0.22), torso_top + 4),
                         (cx + int(W*0.22), torso_top + 4), 2)
        # Accent stripe on uniform
        pygame.draw.rect(surf, self.accent,
                         (cx - int(W*0.28), torso_top + 8, int(W*0.56), 4))

        # ── Neck ──
        neck_w = int(W * 0.13)
        neck_top = int(H * 0.62)
        pygame.draw.rect(surf, self.skin, (cx - neck_w, neck_top, neck_w*2, torso_top - neck_top + 4))

        # ── Face oval — big, filling most of upper area ──
        face_cy = int(H * 0.36)
        face_rx = int(W * 0.38 * self.face_w_fac)
        face_ry = int(H * 0.30)
        face_rx = min(face_rx, W//2 - 4)

        # Shadow below face
        sh_surf = pygame.Surface((face_rx*2+8, face_ry*2+8), pygame.SRCALPHA)
        pygame.draw.ellipse(sh_surf, (0,0,0,80),
                            (4, 8, face_rx*2, face_ry*2))
        surf.blit(sh_surf, (cx - face_rx - 4, face_cy - face_ry - 4))

        # Face fill
        pygame.draw.ellipse(surf, self.skin,
                            (cx - face_rx, face_cy - face_ry, face_rx*2, face_ry*2))

        # Jaw / chin rectangle for squareness
        jaw_h = int(face_ry * 0.45)
        pygame.draw.rect(surf, self.skin,
                         (cx - int(face_rx*0.88), face_cy, int(face_rx*1.76), jaw_h))

        # ── Hair ──
        self._draw_hair(surf, cx, face_cy, face_rx, face_ry, W)

        # ── Eyes ──
        eye_y = face_cy - int(face_ry * 0.12)
        eye_sep = int(face_rx * 0.50)
        for side, ex in [(-1, cx - eye_sep), (1, cx + eye_sep)]:
            self._draw_eye(surf, ex, eye_y, face_rx, ep)

        # ── Eyebrows ──
        brow_y = eye_y - int(face_ry * 0.22) + ep["brow_y"]
        brow_w = int(face_rx * 0.30)
        brow_h = max(3, int(face_ry * 0.07))
        bc = tuple(max(0, c - 20) for c in self.hair_col)
        for ex in [cx - eye_sep, cx + eye_sep]:
            pygame.draw.rect(surf, bc,
                             (ex - brow_w//2, brow_y, brow_w, brow_h),
                             border_radius=2)

        # ── Nose ──
        nose_y = face_cy + int(face_ry * 0.08)
        nose_w = int(face_rx * 0.22)
        nose_h = int(face_ry * 0.24)
        nose_c = tuple(max(0, c - 28) for c in self.skin)
        pygame.draw.ellipse(surf, nose_c,
                            (cx - nose_w//2, nose_y, nose_w, nose_h))

        # ── Mouth ──
        mouth_y = face_cy + int(face_ry * 0.42)
        mouth_w = int(face_rx * 0.52 * ep["mouth_w"])
        mouth_h = max(3, int(face_ry * 0.10))
        smile = ep["smile"]
        lip_c = (160, 75, 75)
        if smile > 0.4:
            pygame.draw.arc(surf, lip_c,
                            (cx - mouth_w, mouth_y - mouth_h//2, mouth_w*2, mouth_h*2),
                            0, math.pi, max(2, mouth_h))
        elif smile < -0.3:
            pygame.draw.arc(surf, lip_c,
                            (cx - mouth_w, mouth_y, mouth_w*2, mouth_h*2),
                            math.pi, math.pi*2, max(2, mouth_h))
        else:
            pygame.draw.rect(surf, lip_c,
                             (cx - mouth_w, mouth_y, mouth_w*2, max(3, mouth_h)),
                             border_radius=2)

        # ── Beard ──
        if self.has_beard:
            beard_y = face_cy + int(face_ry * 0.32)
            beard_c = tuple(max(0, c-25) for c in self.hair_col) + (160,)
            bs = pygame.Surface((int(face_rx*1.5), jaw_h + 8), pygame.SRCALPHA)
            pygame.draw.ellipse(bs, beard_c, (0, 0, int(face_rx*1.5), jaw_h + 8))
            surf.blit(bs, (cx - int(face_rx*0.75), beard_y))

        # ── Scar ──
        if self.has_scar:
            sx2 = cx + int(face_rx * 0.28 * self.scar_side)
            sc = tuple(min(255, c+50) for c in self.skin)
            pygame.draw.line(surf, sc,
                             (sx2, face_cy - int(face_ry*0.05)),
                             (sx2 + 4*self.scar_side, face_cy + int(face_ry*0.38)), 3)

        # ── Lighting: subtle left-side highlight on face ──
        hl_surf = pygame.Surface((face_rx, face_ry*2), pygame.SRCALPHA)
        pygame.draw.ellipse(hl_surf, (255,255,255,18),
                            (0, 0, face_rx, face_ry*2))
        surf.blit(hl_surf, (cx - face_rx, face_cy - face_ry))

        # ── Faction detail (over uniform) ──
        self._draw_detail(surf, cx, torso_top, W, H)

    def _draw_hair(self, surf, cx, face_cy, face_rx, face_ry, W):
        if self.hair_style == "bald":
            hc = tuple(min(255, c+35) for c in self.skin)
            pygame.draw.ellipse(surf, hc,
                                (cx - face_rx//2, face_cy - face_ry - 4, face_rx, face_ry//2))
            return
        hc = self.hair_col
        top_y = face_cy - face_ry
        extra = int(face_ry * (0.35 if self.hair_style == "short" else 0.60))
        # Crown mass
        pygame.draw.ellipse(surf, hc,
                            (cx - face_rx - 4, top_y - extra,
                             (face_rx + 4)*2, extra + face_ry//2 + 2))
        # Side masses
        side_h = int(face_ry * (0.65 if self.hair_style == "short" else 1.05))
        for side in [-1, 1]:
            hx = cx + side * (face_rx - 3)
            pygame.draw.ellipse(surf, hc,
                                (hx - 10, top_y, 22, side_h))

    def _draw_eye(self, surf, ex, ey, face_rx, ep):
        eye_h_fac = max(0.3, ep["eye_h"])
        ew = int(face_rx * 0.28)
        eh = int(face_rx * 0.16 * eye_h_fac)
        eh = max(2, eh)
        # White
        pygame.draw.ellipse(surf, (235, 232, 225), (ex - ew, ey - eh, ew*2, eh*2))
        # Iris
        ir = max(2, int(eh * 0.88))
        pygame.draw.circle(surf, self.eye_col, (ex, ey), ir)
        # Pupil
        pr = max(1, int(ir * 0.52))
        pygame.draw.circle(surf, (8, 8, 8), (ex, ey), pr)
        # Catch light
        pygame.draw.circle(surf, (255, 255, 255),
                           (ex - max(1, ir//3), ey - max(1, ir//3)),
                           max(1, ir//4))
        # Eyelid line
        lid_c = tuple(max(0, c-15) for c in (235, 232, 225))
        pygame.draw.ellipse(surf, lid_c, (ex - ew, ey - eh, ew*2, eh*2), 1)

    def _draw_detail(self, surf, cx, torso_top, W, H):
        if self.style == "military":
            # Rank stripe
            pygame.draw.rect(surf, (200, 165, 40),
                             (cx - 22, torso_top + 18, 44, 4), border_radius=1)
            pygame.draw.rect(surf, (200, 165, 40),
                             (cx - 22, torso_top + 24, 44, 4), border_radius=1)
        elif self.style == "corporate":
            # Tie
            pygame.draw.polygon(surf, (175, 155, 115), [
                (cx, torso_top + 2),
                (cx - 6, torso_top + 14),
                (cx, H),
                (cx + 6, torso_top + 14),
            ])
        elif self.style == "drift":
            # Goggles on forehead
            gy = torso_top - int((H - torso_top) * 2.8) - 14
            if gy > 4:
                pygame.draw.rect(surf, (35, 35, 35),
                                 (cx - 28, gy, 56, 14), border_radius=5)
                pygame.draw.rect(surf, (55, 155, 195, 140),
                                 (cx - 24, gy + 2, 46, 10))

    # ──────────────────────────────────────────────────────────── GHOST ──
    def _draw_ghost(self, surf, W, H, ep):
        cx, cy = W//2, H//2
        gc = self.ghost_col
        dark = (4, 5, 10)
        surf.fill(dark)

        # Subtle scanline grid
        gs = pygame.Surface((W, H), pygame.SRCALPHA)
        for y in range(0, H, 4):
            pygame.draw.line(gs, gc + (8,), (0, y), (W, y))
        for x in range(0, W, 12):
            pygame.draw.line(gs, gc + (4,), (x, 0), (x, H))
        surf.blit(gs, (0, 0))

        # ── Body mass ──
        body_rx = int(W * 0.34)
        body_ry = int(H * 0.42)
        body_cy = int(H * 0.55)
        b_surf = pygame.Surface((body_rx*2+6, body_ry*2+6), pygame.SRCALPHA)
        pygame.draw.ellipse(b_surf, gc + (50,), (0, 0, body_rx*2, body_ry*2))
        pygame.draw.ellipse(b_surf, gc + (25,),
                            (body_rx//3, body_ry//3, body_rx*4//3, body_ry*4//3))
        surf.blit(b_surf, (cx - body_rx - 3, body_cy - body_ry - 3))

        # Tendrils at bottom
        tc = self.n_tendrils
        for i in range(tc):
            ang = math.pi * i / max(1, tc-1) + math.pi * 0.05
            tx = cx + int(math.cos(ang) * body_rx * 0.85)
            ty = body_cy + int(body_ry * 0.5)
            ex2 = cx + int(math.cos(ang) * body_rx * 1.25)
            ts = pygame.Surface((W, H), pygame.SRCALPHA)
            pygame.draw.line(ts, gc + (160,), (tx, ty), (ex2, H - 2), 2)
            surf.blit(ts, (0, 0))

        # ── Head ──
        head_cy = int(H * 0.30)
        head_r  = int(W * 0.24)
        h_surf = pygame.Surface((head_r*2+4, head_r*2+4), pygame.SRCALPHA)
        pygame.draw.circle(h_surf, gc + (75,), (head_r+2, head_r+2), head_r)
        surf.blit(h_surf, (cx - head_r - 2, head_cy - head_r - 2))

        # ── Eyes (sensor cluster) ──
        eye_h_fac = max(0.3, ep["eye_h"])
        num_eyes = self._rng.choice([2, 3, 4])
        for i in range(num_eyes):
            ang = math.pi * 0.2 + math.pi * 0.6 * (i / max(1, num_eyes-1))
            ex2 = cx + int(math.cos(ang) * head_r * 0.52)
            ey2 = head_cy + int(math.sin(ang - math.pi*0.5) * head_r * 0.32)
            ro = max(5, int(head_r * 0.22))
            ri = max(2, int(ro * 0.60 * eye_h_fac))
            pygame.draw.circle(surf, (8, 8, 8), (ex2, ey2), ro)
            pygame.draw.circle(surf, gc, (ex2, ey2), ri)
            pygame.draw.circle(surf, (255, 255, 255),
                               (ex2 - max(1, ri//3), ey2 - max(1, ri//3)),
                               max(1, ri//4))
            g_s = pygame.Surface(((ro+6)*2, (ro+6)*2), pygame.SRCALPHA)
            pygame.draw.circle(g_s, gc + (50,), (ro+6, ro+6), ro+6)
            surf.blit(g_s, (ex2-ro-6, ey2-ro-6))

        # ── Vein network on head ──
        vs = pygame.Surface((W, H), pygame.SRCALPHA)
        rng2 = random.Random(self._rng.randint(0, 9999))
        for _ in range(7):
            a1 = rng2.uniform(0, math.pi*2)
            a2 = rng2.uniform(0, math.pi*2)
            x1 = cx + int(math.cos(a1) * head_r * 0.62)
            y1 = head_cy + int(math.sin(a1) * head_r * 0.62)
            x2 = cx + int(math.cos(a2) * head_r * 0.62)
            y2 = head_cy + int(math.sin(a2) * head_r * 0.62)
            pygame.draw.line(vs, gc + (80,), (x1, y1), (x2, y2), 1)
        surf.blit(vs, (0, 0))

        # Outer glow
        go = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(5, 0, -1):
            pygame.draw.circle(go, gc + (int(10*i),),
                               (cx, head_cy), head_r + i*5)
        surf.blit(go, (0, 0))

        # Glitch bars on angry/dying
        if ep["brow_y"] > 3 or ep["eye_h"] < 0.5:
            for _ in range(3):
                gy2 = self._rng.randint(0, H)
                gs2 = pygame.Surface((W, 3), pygame.SRCALPHA)
                gs2.fill(gc + (55,))
                surf.blit(gs2, (0, gy2))
