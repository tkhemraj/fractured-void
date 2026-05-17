"""
JSON save/load system.
Saves everything needed to resume a game: player, ship, cargo, galaxy visit state,
faction relations, active missions, and world seed.
"""
import json
import os
import time
from dataclasses import asdict
from typing import Optional

SAVES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "saves")


def _ensure_saves_dir() -> None:
    os.makedirs(SAVES_DIR, exist_ok=True)


def list_saves() -> list[dict]:
    """Returns list of save metadata dicts, newest first."""
    _ensure_saves_dir()
    saves = []
    for fname in os.listdir(SAVES_DIR):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(SAVES_DIR, fname)
        try:
            with open(path) as f:
                data = json.load(f)
            saves.append({
                "filename": fname,
                "path": path,
                "name": data.get("player", {}).get("name", "Unknown"),
                "sector": data.get("player", {}).get("current_sector", 1),
                "credits": data.get("player", {}).get("credits", 0),
                "turns": data.get("player", {}).get("turns", 0),
                "timestamp": data.get("timestamp", 0),
                "play_time": data.get("play_time", 0),
            })
        except Exception:
            pass
    return sorted(saves, key=lambda s: s["timestamp"], reverse=True)


def save_game(game_state, galaxy, visited: set[int], missions: list[dict], play_time: float) -> str:
    """Write game state to a timestamped JSON file. Returns filename."""
    _ensure_saves_dir()
    from engine.game_state import PlayerCharacter, PlayerShip, CargoHold

    p = game_state.player
    s = game_state.ship
    c = game_state.cargo

    data = {
        "timestamp": time.time(),
        "play_time": play_time,
        "galaxy_seed": galaxy.seed if galaxy else 42,
        "player": {
            "name": p.name,
            "credits": p.credits,
            "turns": p.turns,
            "experience": p.experience,
            "kills": p.kills,
            "alignment": p.alignment,
            "current_sector": p.current_sector,
            "faction_relations": p.faction_relations,
            "log": p.log[-50:],
        },
        "ship": {
            "ship_id": s.ship_id,
            "shields": s.shields,
            "max_shields": s.max_shields,
            "armor": s.armor,
            "max_armor": s.max_armor,
            "fighters": s.fighters,
            "max_fighters": s.max_fighters,
            "weapons": s.weapons,
            "missile_counts": s.missile_counts,
        },
        "cargo": {
            "capacity": c.capacity,
            "contents": c.contents,
        },
        "visited": list(visited),
        "active_missions": missions,
        "planet_ownership": _serialize_planet_ownership(galaxy),
    }

    ts = time.strftime("%Y%m%d_%H%M%S")
    filename = f"save_{p.name.replace(' ', '_')}_{ts}.json"
    path = os.path.join(SAVES_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return filename


def load_game(path: str) -> Optional[dict]:
    """Load raw save data. Caller reconstructs game objects from it."""
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        print(f"[Save] Load failed: {e}")
        return None


def apply_save(data: dict, game_state, galaxy_factory) -> tuple:
    """
    Reconstruct game state from save data.
    Returns (game_state, galaxy, visited_set, missions, play_time).
    """
    from engine.game_state import PlayerCharacter, PlayerShip, CargoHold
    from world.galaxy import Galaxy

    seed = data.get("galaxy_seed", 42)
    galaxy = galaxy_factory(seed)

    pd = data["player"]
    game_state.player = PlayerCharacter(
        name=pd["name"],
        credits=pd["credits"],
        turns=pd["turns"],
        experience=pd["experience"],
        kills=pd["kills"],
        alignment=pd["alignment"],
        current_sector=pd["current_sector"],
        faction_relations=pd["faction_relations"],
        log=pd.get("log", []),
    )

    sd = data["ship"]
    game_state.ship = PlayerShip(
        ship_id=sd["ship_id"],
        shields=sd["shields"],
        max_shields=sd["max_shields"],
        armor=sd["armor"],
        max_armor=sd["max_armor"],
        fighters=sd["fighters"],
        max_fighters=sd["max_fighters"],
        weapons=sd["weapons"],
        missile_counts=sd["missile_counts"],
    )

    cd = data["cargo"]
    game_state.cargo = CargoHold(capacity=cd["capacity"])
    game_state.cargo.contents = cd["contents"]

    visited = set(data.get("visited", [pd["current_sector"]]))

    # Restore planet ownership
    for planet_info in data.get("planet_ownership", []):
        sector = galaxy.sectors.get(planet_info["sector_id"])
        if sector and sector.planet:
            sector.planet.owner = planet_info.get("owner")
            sector.planet.colonists = planet_info.get("colonists", 0)
            sector.planet.fighters = planet_info.get("fighters", 0)
            sector.planet.citadel_level = planet_info.get("citadel_level", 0)

    missions = data.get("active_missions", [])
    play_time = data.get("play_time", 0.0)

    return game_state, galaxy, visited, missions, play_time


def _serialize_planet_ownership(galaxy) -> list[dict]:
    if not galaxy:
        return []
    result = []
    for sector in galaxy.sectors.values():
        if sector.planet and sector.planet.owner:
            result.append({
                "sector_id": sector.sector_id,
                "owner": sector.planet.owner,
                "colonists": sector.planet.colonists,
                "fighters": sector.planet.fighters,
                "citadel_level": sector.planet.citadel_level,
            })
    return result
