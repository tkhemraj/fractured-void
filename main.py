"""
Fractured Void — main entry point.

TradeWars 2002 sector trading + Wing Commander cockpit combat.
Dystopian near-future: corps own the stars, you own your ship.

Run: python main.py
"""
import sys
import pygame

from engine.game_state import state
from world.galaxy import Galaxy
from screens.main_menu import MainMenu
from screens.sector_map_screen import SectorMapScreen
from screens.trading_screen import TradingScreen
from screens.combat_screen import CombatScreen

WIDTH, HEIGHT = 1280, 800
FPS = 60
TITLE_TEXT = "FRACTURED VOID"


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE_TEXT)
    clock = pygame.time.Clock()

    # Screens
    main_menu = MainMenu(WIDTH, HEIGHT)
    sector_map = SectorMapScreen(WIDTH, HEIGHT)
    trading = TradingScreen(WIDTH, HEIGHT)
    combat = CombatScreen(WIDTH, HEIGHT)

    galaxy: Galaxy | None = None
    current_screen = "main_menu"

    main_menu.init_fonts()

    def transition(new_screen: str) -> None:
        nonlocal current_screen, galaxy

        if new_screen == "new_game":
            state.new_game()
            galaxy = Galaxy(seed=42)
            state.galaxy = galaxy
            sector_map.init(galaxy, state)
            state.player.add_log("Year 2387. The Cinder Pact drifts at Sol Station.")
            state.player.add_log("Corp patrols on three sides. Drift Cartel scouts on the fourth.")
            state.player.add_log("Your move.")
            current_screen = "sector_map"

        elif new_screen == "sector_map":
            if combat.engine and combat.engine.result == "victory":
                state.player.kills += len(combat.engine.enemies)
                state.player.add_credits(500 * len(combat.engine.enemies))
                state.player.experience += 100 * len(combat.engine.enemies)
                state.player.add_log(f"Combat won. +{500 * len(combat.engine.enemies):,} CR salvage.")

                # Restore some shields after combat
                if state.ship:
                    state.ship.shields = min(state.ship.max_shields, state.ship.shields + 10)

            elif combat.engine and combat.engine.result == "fled":
                state.player.add_log("Disengaged from combat.")

            combat.stop()
            current_screen = "sector_map"

        elif new_screen == "trading":
            current_sector = galaxy.sectors.get(state.player.current_sector) if galaxy else None
            if current_sector and current_sector.has_port():
                trading.open(current_sector.port, state, current_sector.name)
                current_screen = "trading"
            else:
                current_screen = "sector_map"

        elif new_screen == "combat":
            ctx = state.combat_context
            ship_data = state.get_ship_data(state.ship.ship_id) if state.ship else {}
            combat.start_combat(
                player_ship_data=ship_data,
                enemies=ctx.get("enemies", []),
                ship_name=ship_data.get("name", "Your Ship"),
                in_fracture_zone=ctx.get("in_fracture_zone", False),
            )
            current_screen = "combat"

        elif new_screen == "quit":
            pygame.quit()
            sys.exit(0)

        else:
            current_screen = new_screen

    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            result = None
            if current_screen == "main_menu":
                result = main_menu.handle_event(event)
            elif current_screen == "sector_map":
                result = sector_map.handle_event(event)
            elif current_screen == "trading":
                result = trading.handle_event(event)
            elif current_screen == "combat":
                result = combat.handle_event(event)

            if result:
                transition(result)

        # Update
        if current_screen == "main_menu":
            main_menu.update(dt)
        elif current_screen == "sector_map":
            sector_map.update(dt)
        elif current_screen == "trading":
            trading.update(dt)
        elif current_screen == "combat":
            result = combat.update(dt)
            if result:
                transition(result)

        # Draw
        if current_screen == "main_menu":
            main_menu.draw(screen)
        elif current_screen == "sector_map":
            sector_map.draw(screen)
        elif current_screen == "trading":
            trading.draw(screen)
        elif current_screen == "combat":
            combat.draw(screen)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
