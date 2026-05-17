"""
Central game state. Single source of truth for everything the game knows.
All screens read from here and post events to mutate it through game_state methods.
"""
import json
import os
from dataclasses import dataclass, field
from typing import Optional
from engine.event_bus import bus

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def load_json(filename: str) -> dict:
    with open(os.path.join(DATA_DIR, filename)) as f:
        return json.load(f)


@dataclass
class CargoHold:
    capacity: int
    contents: dict = field(default_factory=dict)

    @property
    def used(self) -> int:
        commodities = load_json("commodities.json")
        return sum(
            qty * commodities[item]["weight"]
            for item, qty in self.contents.items()
            if item in commodities
        )

    @property
    def free(self) -> int:
        return self.capacity - self.used

    def add(self, item: str, qty: int) -> bool:
        commodities = load_json("commodities.json")
        weight = commodities[item]["weight"] * qty
        if weight > self.free:
            return False
        self.contents[item] = self.contents.get(item, 0) + qty
        return True

    def remove(self, item: str, qty: int) -> bool:
        if self.contents.get(item, 0) < qty:
            return False
        self.contents[item] -= qty
        if self.contents[item] == 0:
            del self.contents[item]
        return True


@dataclass
class PlayerShip:
    ship_id: str
    shields: float
    max_shields: float
    armor: float
    max_armor: float
    fighters: int
    max_fighters: int
    energy: float = 100.0
    max_energy: float = 100.0
    speed: float = 0.0
    heading: float = 0.0
    weapons: list = field(default_factory=list)
    active_weapon: int = 0
    missile_counts: dict = field(default_factory=dict)

    @property
    def shield_percent(self) -> float:
        return self.shields / self.max_shields if self.max_shields > 0 else 0

    @property
    def armor_percent(self) -> float:
        return self.armor / self.max_armor if self.max_armor > 0 else 0

    def take_hit(self, damage: float) -> bool:
        """Returns True if ship is destroyed."""
        if self.shields > 0:
            absorbed = min(self.shields, damage * 0.8)
            self.shields -= absorbed
            damage -= absorbed
        self.armor -= damage
        if self.armor <= 0:
            bus.post("ship_destroyed", ship="player")
            return True
        return False


@dataclass
class PlayerCharacter:
    name: str = "Vael Korr"
    credits: int = 5000
    turns: int = 200
    experience: int = 0
    kills: int = 0
    alignment: int = 0
    current_sector: int = 1
    faction_relations: dict = field(default_factory=dict)
    log: list = field(default_factory=list)

    def add_credits(self, amount: int) -> None:
        self.credits += amount
        bus.post("credits_changed", credits=self.credits, delta=amount)

    def spend_credits(self, amount: int) -> bool:
        if self.credits < amount:
            return False
        self.credits -= amount
        bus.post("credits_changed", credits=self.credits, delta=-amount)
        return True

    def use_turns(self, count: int) -> bool:
        if self.turns < count:
            return False
        self.turns -= count
        bus.post("turns_changed", turns=self.turns)
        return True

    def get_relation(self, faction_id: str) -> int:
        return self.faction_relations.get(faction_id, 0)

    def modify_relation(self, faction_id: str, delta: int) -> None:
        current = self.faction_relations.get(faction_id, 0)
        self.faction_relations[faction_id] = max(-100, min(100, current + delta))
        bus.post("relation_changed", faction=faction_id, relation=self.faction_relations[faction_id])

    def add_log(self, entry: str) -> None:
        self.log.append(entry)
        if len(self.log) > 200:
            self.log = self.log[-200:]


class GameState:
    def __init__(self):
        self.screen = "main_menu"
        self.previous_screen = None
        self.player: Optional[PlayerCharacter] = None
        self.ship: Optional[PlayerShip] = None
        self.cargo: Optional[CargoHold] = None
        self.galaxy = None
        self.in_combat = False
        self.combat_context: dict = {}
        self.running = True

        self._ship_data = load_json("ships.json")
        self._faction_data = load_json("factions.json")
        self._weapon_data = load_json("weapons.json")
        self._commodity_data = load_json("commodities.json")

    def new_game(self, player_name: str = "Vael Korr") -> None:
        factions = self._faction_data
        starting_relations = {fid: factions[fid]["starting_relation"] for fid in factions}
        starting_relations["the_remnant"] = 20
        starting_relations["apex_syndicate"] = -30

        self.player = PlayerCharacter(
            name=player_name,
            credits=5000,
            turns=200,
            current_sector=1,
            faction_relations=starting_relations,
        )

        ship_data = self._ship_data["cinder_pact"]
        self.ship = PlayerShip(
            ship_id="cinder_pact",
            shields=ship_data["shields"],
            max_shields=ship_data["max_shields"],
            armor=ship_data["armor"],
            max_armor=ship_data["armor"],
            fighters=ship_data["fighters"],
            max_fighters=ship_data["max_fighters"],
            weapons=self._expand_weapons(ship_data["weapons"]),
            missile_counts=self._init_missile_counts(ship_data["weapons"]),
        )

        self.cargo = CargoHold(capacity=ship_data["hold"])
        bus.post("new_game_started", player=self.player)

    def _expand_weapons(self, weapon_list: list) -> list:
        """'heat_seeker_x2' → ['heat_seeker', 'heat_seeker'] etc."""
        result = []
        for w in weapon_list:
            if "_x" in w:
                base, count = w.rsplit("_x", 1)
                base = base  # keep as-is for lookup
                result.append(base)
            else:
                result.append(w)
        return result

    def _init_missile_counts(self, weapon_list: list) -> dict:
        counts = {}
        weapon_data = self._weapon_data
        for w in weapon_list:
            if "_x" in w:
                base, count = w.rsplit("_x", 1)
                count = int(count)
            else:
                base = w
                count = None
            if base in weapon_data and weapon_data[base]["type"] in ("missile", "torpedo"):
                default_count = weapon_data[base].get("count", 4)
                counts[base] = counts.get(base, 0) + (count if count else default_count)
        return counts

    def change_screen(self, screen_name: str) -> None:
        self.previous_screen = self.screen
        self.screen = screen_name
        bus.post("screen_changed", screen=screen_name, previous=self.previous_screen)

    def get_ship_data(self, ship_id: str) -> dict:
        return self._ship_data.get(ship_id, {})

    def get_faction_data(self, faction_id: str) -> dict:
        return self._faction_data.get(faction_id, {})

    def get_weapon_data(self, weapon_id: str) -> dict:
        return self._weapon_data.get(weapon_id, {})

    def get_commodity_data(self, commodity_id: str) -> dict:
        return self._commodity_data.get(commodity_id, {})


state = GameState()
