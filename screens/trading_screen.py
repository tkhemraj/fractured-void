"""
TradeWars-style port trading screen.
Buy and sell commodities, with supply/demand-based pricing.
"""
import pygame
from world.sector import Port
from engine.game_state import GameState, CargoHold
from rendering.face_cam import face_cams


class TradingScreen:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.fonts: dict = {}
        self._initialized = False
        self.port: Port | None = None
        self.state: GameState | None = None
        self.cargo: CargoHold | None = None
        self.sector_name = ""
        self.selected_item = 0
        self.trade_qty = 1
        self.message = ""
        self.message_timer = 0.0
        self._all_commodities: dict = {}
        self._items: list[tuple[str, str]] = []  # (item_id, "buy"|"sell")

    def init_fonts(self) -> None:
        if self._initialized:
            return
        try:
            mono = pygame.font.match_font("courier,couriernew,dejavusansmono")
            self.fonts["sm"] = pygame.font.Font(mono, 14)
            self.fonts["md"] = pygame.font.Font(mono, 18)
            self.fonts["lg"] = pygame.font.Font(mono, 26)
            self.fonts["xl"] = pygame.font.Font(mono, 36)
        except Exception:
            self.fonts["sm"] = pygame.font.SysFont("monospace", 14)
            self.fonts["md"] = pygame.font.SysFont("monospace", 18)
            self.fonts["lg"] = pygame.font.SysFont("monospace", 26)
            self.fonts["xl"] = pygame.font.SysFont("monospace", 36)
        self._initialized = True

    def open(self, port: Port, state: GameState, sector_name: str) -> None:
        self.init_fonts()
        self.port = port
        self.state = state
        self.cargo = state.cargo
        self.sector_name = sector_name
        self._all_commodities = state._commodity_data
        self.selected_item = 0
        self.trade_qty = 1
        self.message = ""
        self._build_item_list()
        # Show port master face cam
        faction_id = getattr(port, "faction", "") or ""
        if faction_id:
            face_cams.enter_port(faction_id)

    def close(self) -> None:
        face_cams.leave_port()

    def _build_item_list(self) -> None:
        self._items = []
        if not self.port:
            return
        for item in self.port.sells:
            self._items.append((item, "buy"))
        for item in self.port.buys:
            self._items.append((item, "sell"))

    def handle_event(self, event: pygame.event.Event) -> str | None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_l:
                return "sector_map"
            elif event.key == pygame.K_UP or event.key == pygame.K_w:
                self.selected_item = (self.selected_item - 1) % max(1, len(self._items))
                self.trade_qty = 1
            elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                self.selected_item = (self.selected_item + 1) % max(1, len(self._items))
                self.trade_qty = 1
            elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                self.trade_qty = max(1, self.trade_qty - 1)
            elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                self.trade_qty = min(100, self.trade_qty + 1)
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                self._execute_trade()
            elif event.key == pygame.K_m:
                self.trade_qty = self._max_trade_qty()
        return None

    def _max_trade_qty(self) -> int:
        if not self._items or not self.port or not self.state:
            return 1
        item_id, direction = self._items[self.selected_item]
        price = self.port.prices.get(item_id, 100)
        if direction == "buy":
            by_credits = self.state.player.credits // max(1, price)
            by_cargo = self.cargo.free if self.cargo else 0
            by_stock = self.port.stock.get(item_id, 0)
            return max(1, min(by_credits, by_cargo, by_stock))
        else:
            return max(1, self.cargo.contents.get(item_id, 0) if self.cargo else 0)

    def _execute_trade(self) -> None:
        if not self._items or not self.port or not self.state or not self.cargo:
            return
        item_id, direction = self._items[self.selected_item]
        qty = self.trade_qty
        price = self.port.prices.get(item_id, 100)

        if direction == "buy":
            total_cost = price * qty
            if self.state.player.credits < total_cost:
                self._msg("Not enough credits.", error=True)
                return
            if self.port.stock.get(item_id, 0) < qty:
                self._msg(f"Port only has {self.port.stock.get(item_id, 0)} units.", error=True)
                return
            if not self.cargo.add(item_id, qty):
                self._msg("Cargo hold full.", error=True)
                return
            self.state.player.spend_credits(total_cost)
            self.port.stock[item_id] = self.port.stock.get(item_id, 0) - qty
            self._msg(f"Bought {qty}x {item_id} for {total_cost:,} CR")
        else:
            if self.cargo.contents.get(item_id, 0) < qty:
                self._msg(f"You only have {self.cargo.contents.get(item_id, 0)} units.", error=True)
                return
            total_earned = price * qty
            self.cargo.remove(item_id, qty)
            self.state.player.add_credits(total_earned)
            self._msg(f"Sold {qty}x {item_id} for {total_earned:,} CR")

    def _msg(self, text: str, error: bool = False) -> None:
        self.message = text
        self.message_timer = 0.0
        self._msg_error = error

    def update(self, dt: float) -> None:
        self.message_timer += dt
        face_cams.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        if not self._initialized:
            self.init_fonts()
        surface.fill((4, 8, 6))
        self._draw_header(surface)
        self._draw_commodity_list(surface)
        self._draw_cargo_panel(surface)
        self._draw_message(surface)
        self._draw_controls(surface)
        face_cams.draw_port(surface, self.width, self.height)

    def _draw_header(self, surface: pygame.Surface) -> None:
        if not self.port:
            return
        font_lg = self.fonts["lg"]
        font_md = self.fonts["md"]
        font_sm = self.fonts["sm"]

        pygame.draw.rect(surface, (5, 14, 8), (0, 0, self.width, 70))
        pygame.draw.line(surface, (40, 100, 50), (0, 70), (self.width, 70), 2)

        title = font_lg.render(f"PORT OF {self.sector_name.upper()}", True, (100, 220, 120))
        surface.blit(title, (20, 10))

        class_lbl = font_md.render(self.port.class_name, True, (80, 160, 80))
        surface.blit(class_lbl, (20, 42))

        credits = font_md.render(f"CREDITS: {self.state.player.credits:,}", True, (180, 160, 60))
        surface.blit(credits, (self.width - 280, 10))

        turns = font_sm.render(f"TURNS: {self.state.player.turns}", True, (80, 160, 220))
        surface.blit(turns, (self.width - 280, 42))

    def _draw_commodity_list(self, surface: pygame.Surface) -> None:
        font_md = self.fonts["md"]
        font_sm = self.fonts["sm"]

        x, y = 20, 90
        col_w = self.width // 2 - 30

        # Headers
        headers = font_sm.render(
            f"{'COMMODITY':<18} {'PRICE':>8}  {'STOCK':>6}  {'QTY':>4}  {'TOTAL':>8}",
            True, (60, 100, 60)
        )
        surface.blit(headers, (x, y))
        y += 18
        pygame.draw.line(surface, (30, 60, 30), (x, y), (x + col_w * 2, y), 1)
        y += 6

        if not self._items:
            surface.blit(font_md.render("No tradeable goods at this port.", True, (80, 80, 80)), (x, y))
            return

        for i, (item_id, direction) in enumerate(self._items):
            comm = self._all_commodities.get(item_id, {})
            price = self.port.prices.get(item_id, comm.get("base_price", 100)) if self.port else 100
            stock = self.port.stock.get(item_id, 999) if direction == "buy" else (self.cargo.contents.get(item_id, 0) if self.cargo else 0)
            qty = self.trade_qty if i == self.selected_item else 0
            total = price * qty if qty > 0 else 0

            is_selected = i == self.selected_item
            bg_color = (10, 30, 14) if is_selected else (4, 8, 6)
            row_color = (60, 220, 80) if direction == "buy" else (220, 80, 60)
            if is_selected:
                row_color = (200, 255, 200) if direction == "buy" else (255, 200, 200)

            pygame.draw.rect(surface, bg_color, (x - 4, y - 2, col_w * 2 + 8, 20))

            dir_tag = "BUY " if direction == "buy" else "SELL"
            name = comm.get("name", item_id)[:16]
            row = font_md.render(
                f"[{dir_tag}] {name:<16} {price:>7,}  {stock:>6}  {self.trade_qty if is_selected else '':>4}  {total:>8,}",
                True, row_color
            )
            surface.blit(row, (x, y))
            y += 22

    def _draw_cargo_panel(self, surface: pygame.Surface) -> None:
        if not self.cargo:
            return
        font_sm = self.fonts["sm"]
        font_md = self.fonts["md"]

        px = self.width - 260
        py = 90
        pygame.draw.rect(surface, (5, 10, 6), (px, py, 250, 300))
        pygame.draw.rect(surface, (30, 60, 30), (px, py, 250, 300), 1)

        lbl = font_md.render("CARGO HOLD", True, (80, 160, 80))
        surface.blit(lbl, (px + 8, py + 8))

        cap_bar_pct = (self.cargo.capacity - self.cargo.free) / max(1, self.cargo.capacity)
        pygame.draw.rect(surface, (20, 40, 20), (px + 8, py + 32, 234, 12))
        fill = int(234 * cap_bar_pct)
        bar_color = (60, 180, 60) if cap_bar_pct < 0.8 else (220, 160, 40) if cap_bar_pct < 0.95 else (220, 60, 40)
        pygame.draw.rect(surface, bar_color, (px + 8, py + 32, fill, 12))
        pygame.draw.rect(surface, (40, 80, 40), (px + 8, py + 32, 234, 12), 1)

        cap_lbl = font_sm.render(f"{self.cargo.used}/{self.cargo.capacity} used", True, (60, 120, 60))
        surface.blit(cap_lbl, (px + 8, py + 48))

        y = py + 68
        if not self.cargo.contents:
            surface.blit(font_sm.render("(empty)", True, (40, 60, 40)), (px + 8, y))
        for item_id, qty in self.cargo.contents.items():
            comm = self._all_commodities.get(item_id, {})
            row = font_sm.render(f"{comm.get('name', item_id)[:18]:<18} {qty:>4}", True, (100, 200, 100))
            surface.blit(row, (px + 8, y))
            y += 16

    def _draw_message(self, surface: pygame.Surface) -> None:
        if not self.message or self.message_timer > 3.0:
            return
        font_md = self.fonts["md"]
        alpha = max(0, int(255 * (1 - self.message_timer / 3.0)))
        color = (255, 80, 80) if getattr(self, "_msg_error", False) else (80, 255, 120)
        lbl = font_md.render(self.message, True, color)
        surface.blit(lbl, (20, self.height - 60))

    def _draw_controls(self, surface: pygame.Surface) -> None:
        font_sm = self.fonts["sm"]
        hints = "Up/Down: Select    Left/Right: Qty    M: Max qty    Enter: Trade    L/Esc: Leave port"
        lbl = font_sm.render(hints, True, (40, 80, 40))
        surface.blit(lbl, (10, self.height - 22))
