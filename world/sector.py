"""
A sector is one node in the galaxy graph.
Sectors contain ports, planets, deployed fighters, mines, and warp links.
"""
from dataclasses import dataclass, field
from typing import Optional


PORT_CLASSES = {
    # (buys, sells)
    # Based on TradeWars 2002 port class system adapted for Fractured Void commodities
    1: {"buys": ["equipment"],          "sells": ["fuel_ore", "organics"],    "name": "Class I"},
    2: {"buys": ["fuel_ore"],           "sells": ["equipment", "organics"],   "name": "Class II"},
    3: {"buys": ["organics"],           "sells": ["fuel_ore", "equipment"],   "name": "Class III"},
    4: {"buys": ["metals"],             "sells": ["equipment"],               "name": "Class IV"},
    5: {"buys": ["fuel_ore", "metals"], "sells": [],                          "name": "Class V"},
    6: {"buys": [],                     "sells": ["organics", "medicine"],    "name": "Class VI"},
    7: {"buys": ["fuel_ore", "organics", "equipment"], "sells": ["arms"],     "name": "Class VII"},
    8: {"buys": ["arms", "contraband"], "sells": ["fuel_ore", "organics"],    "name": "Class VIII (Drift)"},
    9: {"buys": [],                     "sells": ["arms", "medicine", "contraband", "information"], "name": "Class IX (Black Market)"},
}


@dataclass
class Port:
    port_class: int
    faction: Optional[str] = None
    stock: dict = field(default_factory=dict)
    prices: dict = field(default_factory=dict)
    haggle_count: int = 0

    @property
    def buys(self) -> list:
        return PORT_CLASSES[self.port_class]["buys"]

    @property
    def sells(self) -> list:
        return PORT_CLASSES[self.port_class]["sells"]

    @property
    def class_name(self) -> str:
        return PORT_CLASSES[self.port_class]["name"]


@dataclass
class Planet:
    name: str
    owner: Optional[str] = None
    colonists: int = 0
    fighters: int = 0
    shields: int = 0
    fuel_ore: int = 0
    organics: int = 0
    equipment: int = 0
    citadel_level: int = 0


@dataclass
class Sector:
    sector_id: int
    name: str = ""
    x: float = 0.0
    y: float = 0.0
    warp_links: list = field(default_factory=list)
    port: Optional[Port] = None
    planet: Optional[Planet] = None
    fighters: dict = field(default_factory=dict)
    mines: int = 0
    anomaly: Optional[str] = None
    controlling_faction: Optional[str] = None
    visited: bool = False
    nebula: bool = False
    beacon: str = ""

    def is_safe(self) -> bool:
        return self.mines == 0 and not self.anomaly

    def has_port(self) -> bool:
        return self.port is not None

    def has_planet(self) -> bool:
        return self.planet is not None
