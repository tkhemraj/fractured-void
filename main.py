"""
Fractured Void — main entry point.

TradeWars 2002 sector trading + Wing Commander cockpit combat.
Dystopian near-future: corps own the stars, you own your ship.

Run: python main.py
Controls on sector map: WASD/click to navigate, P=Trade/Planet, U=Shipyard, M=Missions
"""
import sys
import pygame

from engine.game_state import state
from engine.event_bus import bus
from engine.mission_manager import missions as mission_mgr
from engine.save_system import save_game, load_game, apply_save, list_saves
from audio.sound_gen import sounds
from world.galaxy import Galaxy
from screens.main_menu import MainMenu
from screens.sector_map_screen import SectorMapScreen
from screens.trading_screen import TradingScreen
from screens.combat_screen import CombatScreen
from screens.shipyard_screen import ShipyardScreen
from screens.planet_screen import PlanetScreen
from screens.mission_briefing_screen import MissionBriefingScreen

WIDTH, HEIGHT = 1280, 800
FPS = 60
TITLE_TEXT = "FRACTURED VOID"


def make_galaxy(seed: int = 42) -> Galaxy:
    return Galaxy(seed=seed)


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE_TEXT)
    clock = pygame.time.Clock()

    # Initialize sound (non-fatal if audio fails)
    sounds.init()

    # Screens
    main_menu    = MainMenu(WIDTH, HEIGHT)
    sector_map   = SectorMapScreen(WIDTH, HEIGHT)
    trading      = TradingScreen(WIDTH, HEIGHT)
    combat       = CombatScreen(WIDTH, HEIGHT)
    shipyard     = ShipyardScreen(WIDTH, HEIGHT)
    planet_scr   = PlanetScreen(WIDTH, HEIGHT)
    mission_brf  = MissionBriefingScreen(WIDTH, HEIGHT)

    galaxy: Galaxy | None = None
    current_screen = "main_menu"
    play_time = 0.0
    save_message = ""
    save_msg_timer = 0.0

    main_menu.init_fonts()

    # Wire up mission completion notifications
    def _on_mission_complete(mission_id: str, mission_data: dict, **kw):
        rewards = mission_data.get("reward_credits", 0)
        if rewards and state.player:
            state.player.add_credits(rewards)
            state.player.add_log(f"Mission complete: {mission_data.get('title', '')}. +{rewards:,} CR")
        for fid, delta in mission_data.get("reward_relation", {}).items():
            if state.player:
                state.player.modify_relation(fid, delta)
        if state.player:
            state.player.experience += mission_data.get("reward_experience", 0)
        sounds.play("mission_accept", 1.0)

    bus.subscribe("mission_completed", _on_mission_complete)

    def transition(new_screen: str) -> None:
        nonlocal current_screen, galaxy

        if new_screen == "new_game":
            state.new_game()
            galaxy = make_galaxy(seed=42)
            state.galaxy = galaxy
            mission_mgr.load()
            sector_map.init(galaxy, state)
            state.player.add_log("Year 2387. The Cinder Pact drifts at Sol Station.")
            state.player.add_log("Corp patrols on three sides. Drift Cartel scouts on the fourth.")
            state.player.add_log("Your move. [P=Port  U=Shipyard  M=Missions]")
            sounds.start_engine()
            current_screen = "sector_map"

        elif new_screen == "load_game":
            saves = list_saves()
            if saves:
                # Load most recent save automatically for now
                data = load_game(saves[0]["path"])
                if data:
                    nonlocal play_time
                    _state, _galaxy, visited, missions_data, _play_time = apply_save(data, state, make_galaxy)
                    galaxy = _galaxy
                    state.galaxy = galaxy
                    play_time = _play_time
                    mission_mgr.load()
                    mission_mgr.deserialize(missions_data)
                    sector_map.init(galaxy, state)
                    sector_map.visited = visited
                    state.player.add_log("Game loaded.")
                    sounds.start_engine()
                    current_screen = "sector_map"
            else:
                current_screen = "main_menu"

        elif new_screen == "sector_map":
            trading.close()
            if combat.engine and combat.engine.result == "victory":
                kills = len([e for e in combat.engine.enemies if not e.alive])
                salvage = 500 * kills
                state.player.kills += kills
                state.player.add_credits(salvage)
                state.player.experience += 100 * kills
                state.player.add_log(f"Combat won. +{salvage:,} CR salvage.")
                # Update mission kill objectives
                for enemy in combat.engine.enemies:
                    if not enemy.alive:
                        bus.post("enemy_destroyed", faction=enemy.faction)
                if state.ship:
                    state.ship.shields = min(state.ship.max_shields, state.ship.shields + 10)
                sounds.play("mission_accept", 0.5)
            elif combat.engine and combat.engine.result == "fled":
                state.player.add_log("Disengaged from combat.")
            combat.stop()
            sounds.start_engine()
            current_screen = "sector_map"

        elif new_screen == "trading":
            current_sector = galaxy.sectors.get(state.player.current_sector) if galaxy else None
            if current_sector and current_sector.has_port():
                trading.open(current_sector.port, state, current_sector.name)
                # Refresh turns at port
                bonus_turns = 50
                state.player.turns = min(200, state.player.turns + bonus_turns)
                state.player.add_log(f"Docked at {current_sector.name}. Turns refreshed (+{bonus_turns}).")
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
            sounds.stop_engine()
            sounds.play("alert", 0.8)
            current_screen = "combat"

        elif new_screen == "shipyard":
            sector_name = state.combat_context.get("sector_name", "Unknown Sector")
            shipyard.open(sector_name, state)
            current_screen = "shipyard"

        elif new_screen == "planet":
            planet = state.combat_context.get("planet")
            sector_name = state.combat_context.get("sector_name", "Unknown Sector")
            if planet:
                planet_scr.open(planet, sector_name, state)
                current_screen = "planet"
            else:
                current_screen = "sector_map"

        elif new_screen == "mission_board":
            available = state.combat_context.get("available_missions", [])
            mission_brf.open(available, state)
            current_screen = "mission_board"

        elif new_screen == "quit":
            # Auto-save before quit
            if galaxy and state.player:
                save_game(state, galaxy, sector_map.visited, mission_mgr.serialize(), play_time)
            pygame.quit()
            sys.exit(0)

        else:
            current_screen = new_screen

    def do_save() -> None:
        nonlocal save_message, save_msg_timer
        if galaxy and state.player:
            fname = save_game(state, galaxy, sector_map.visited, mission_mgr.serialize(), play_time)
            save_message = f"Saved: {fname}"
            save_msg_timer = 0.0
            sounds.play("beep_high", 0.5)

    running = True
    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        play_time += dt
        save_msg_timer += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                transition("quit")
                running = False
                break

            # Global save shortcut
            if event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                if event.key == pygame.K_s and (mods & pygame.KMOD_CTRL):
                    do_save()
                    continue

            result = None
            if current_screen == "main_menu":
                result = main_menu.handle_event(event)
            elif current_screen == "sector_map":
                result = sector_map.handle_event(event)
            elif current_screen == "trading":
                result = trading.handle_event(event)
            elif current_screen == "combat":
                result = combat.handle_event(event)
            elif current_screen == "shipyard":
                result = shipyard.handle_event(event)
            elif current_screen == "planet":
                result = planet_scr.handle_event(event)
            elif current_screen == "mission_board":
                result = mission_brf.handle_event(event)

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
            # Update engine sound with speed
            if combat.engine:
                max_s = combat.engine.player.afterburner_speed
                cur_s = combat.engine.player.velocity.length()
                sounds.update_engine(cur_s / max(1.0, max_s))
            if result:
                transition(result)
        elif current_screen == "shipyard":
            shipyard.update(dt)
        elif current_screen == "planet":
            planet_scr.update(dt)
        elif current_screen == "mission_board":
            mission_brf.update(dt)

        # Draw
        if current_screen == "main_menu":
            main_menu.draw(screen)
        elif current_screen == "sector_map":
            sector_map.draw(screen)
        elif current_screen == "trading":
            trading.draw(screen)
        elif current_screen == "combat":
            combat.draw(screen)
        elif current_screen == "shipyard":
            shipyard.draw(screen)
        elif current_screen == "planet":
            planet_scr.draw(screen)
        elif current_screen == "mission_board":
            mission_brf.draw(screen)

        # Global HUD overlay: save message
        if save_message and save_msg_timer < 3.0 and current_screen != "main_menu":
            if not hasattr(main_menu, '_save_font'):
                try:
                    mono = pygame.font.match_font("courier,couriernew,dejavusansmono")
                    main_menu._save_font = pygame.font.Font(mono, 14)
                except Exception:
                    main_menu._save_font = pygame.font.SysFont("monospace", 14)
            alpha = int(255 * max(0, 1 - save_msg_timer / 3.0))
            lbl = main_menu._save_font.render(save_message, True, (60, 220, 80))
            lbl.set_alpha(alpha)
            screen.blit(lbl, (WIDTH - lbl.get_width() - 10, HEIGHT - 24))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
