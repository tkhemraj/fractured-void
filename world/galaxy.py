"""
Procedurally generates the Fractured Void galaxy.
~500 sectors connected by warp links, with ports, planets, anomalies, and faction zones.
"""
import random
import math
from typing import Optional
from world.sector import Sector, Port, Planet, PORT_CLASSES


GALAXY_SIZE = 500
SECTOR_NAMES_PREFIX = [
    "Vega", "Cinder", "Null", "Ash", "Drift", "Iron", "Helix", "Apex",
    "Ghost", "Fracture", "Void", "Rust", "Pale", "Dark", "Echo", "Broken",
    "Nova", "Dead", "Cold", "Red", "Blue", "Stone", "Steel", "Ember",
]
SECTOR_NAMES_SUFFIX = [
    "Point", "Reach", "Gate", "Cross", "Deep", "Run", "Margin", "Hold",
    "Scar", "Field", "Mark", "Lane", "Edge", "Pass", "Drift", "Zone",
    "Corridor", "Expanse", "Belt", "Breach", "Fold", "Rift", "Sink",
]

FACTION_ZONES = {
    "apex_syndicate":   (1,   80),
    "helix_commerce":   (81,  160),
    "ironveil_trading": (161, 240),
    "drift_cartel":     (241, 320),
    "the_remnant":      (321, 400),
    "ghost_fleet":      (401, 450),
}

FRACTURE_ZONE = range(401, 451)
SECTOR_1_NAME = "Sol Station"


class Galaxy:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.sectors: dict[int, Sector] = {}
        self._rng = random.Random(seed)
        self._generate()

    def _generate(self) -> None:
        self._place_sectors()
        self._generate_warp_links()
        self._place_ports()
        self._place_planets()
        self._place_anomalies()
        self._mark_faction_zones()

    def _place_sectors(self) -> None:
        rng = self._rng
        used_names = set()

        for sid in range(1, GALAXY_SIZE + 1):
            angle = rng.uniform(0, 2 * math.pi)
            radius = rng.uniform(50, 900)
            x = math.cos(angle) * radius
            y = math.sin(angle) * radius

            if sid == 1:
                name = SECTOR_1_NAME
                x, y = 0.0, 0.0
            elif sid in FRACTURE_ZONE:
                name = f"Fracture-{sid - 400}"
            else:
                for _ in range(20):
                    n = rng.choice(SECTOR_NAMES_PREFIX) + " " + rng.choice(SECTOR_NAMES_SUFFIX)
                    if n not in used_names:
                        name = n
                        used_names.add(n)
                        break
                else:
                    name = f"Sector {sid}"

            self.sectors[sid] = Sector(
                sector_id=sid,
                name=name,
                x=x,
                y=y,
                nebula=sid in FRACTURE_ZONE,
            )

    def _generate_warp_links(self) -> None:
        rng = self._rng
        sectors = list(self.sectors.values())

        # Each sector gets 2-5 warp links to nearby sectors
        for sector in sectors:
            others = sorted(
                [s for s in sectors if s.sector_id != sector.sector_id],
                key=lambda s: math.dist((sector.x, sector.y), (s.x, s.y))
            )
            n_links = rng.randint(2, 5)
            for target in others[:n_links]:
                if target.sector_id not in sector.warp_links:
                    sector.warp_links.append(target.sector_id)
                if sector.sector_id not in target.warp_links:
                    target.warp_links.append(sector.sector_id)

        # Ensure sector 1 is well-connected
        if len(self.sectors[1].warp_links) < 4:
            nearby = sorted(
                [s for s in sectors if s.sector_id != 1],
                key=lambda s: math.dist((0, 0), (s.x, s.y))
            )
            for s in nearby:
                if s.sector_id not in self.sectors[1].warp_links:
                    self.sectors[1].warp_links.append(s.sector_id)
                    s.warp_links.append(1)
                if len(self.sectors[1].warp_links) >= 5:
                    break

    def _place_ports(self) -> None:
        rng = self._rng
        commodities_data = self._load_commodities()

        # ~60% of sectors get ports; ghost/fracture zone has none
        for sid, sector in self.sectors.items():
            if sid in FRACTURE_ZONE:
                continue
            if sid == 1 or rng.random() < 0.6:
                port_class = 1 if sid == 1 else rng.randint(1, 9)
                if 241 <= sid <= 320:
                    port_class = rng.choice([8, 9, 8, 7])
                faction = self._get_faction_for_sector(sid)
                stock = {}
                prices = {}
                for item in PORT_CLASSES[port_class]["sells"]:
                    stock[item] = rng.randint(50, 500)
                    base = commodities_data.get(item, {}).get("base_price", 100)
                    variance = commodities_data.get(item, {}).get("variance", 30)
                    prices[item] = int(base + rng.uniform(-variance, variance * 0.3))
                for item in PORT_CLASSES[port_class]["buys"]:
                    base = commodities_data.get(item, {}).get("base_price", 100)
                    variance = commodities_data.get(item, {}).get("variance", 30)
                    prices[item] = int(base - rng.uniform(0, variance * 0.5))
                sector.port = Port(
                    port_class=port_class,
                    faction=faction,
                    stock=stock,
                    prices=prices,
                )

    def _place_planets(self) -> None:
        rng = self._rng
        planet_names = [
            "Ashford", "Cinder Prime", "New Meridian", "Voss Colony",
            "Rustholm", "Pale Reach", "Irongate", "Echo Station",
            "Remnant's Hope", "Drifter's End", "Nova Basin", "Cold Reach",
        ]
        used = set()
        for sid, sector in self.sectors.items():
            if sid in FRACTURE_ZONE:
                continue
            if rng.random() < 0.2:
                for _ in range(10):
                    name = rng.choice(planet_names)
                    if name not in used:
                        used.add(name)
                        break
                else:
                    name = f"World-{sid}"
                sector.planet = Planet(
                    name=name,
                    colonists=rng.randint(0, 500),
                    fighters=rng.randint(0, 50),
                    shields=rng.randint(0, 30),
                )

    def _place_anomalies(self) -> None:
        for sid in FRACTURE_ZONE:
            self.sectors[sid].anomaly = "fracture_rift"

    def _mark_faction_zones(self) -> None:
        for faction_id, (start, end) in FACTION_ZONES.items():
            for sid in range(start, end + 1):
                if sid in self.sectors:
                    self.sectors[sid].controlling_faction = faction_id

    def _get_faction_for_sector(self, sid: int) -> Optional[str]:
        for faction_id, (start, end) in FACTION_ZONES.items():
            if start <= sid <= end:
                return faction_id
        return None

    def _load_commodities(self) -> dict:
        import json, os
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "commodities.json")
        with open(path) as f:
            return json.load(f)

    def get_sector(self, sector_id: int) -> Optional[Sector]:
        return self.sectors.get(sector_id)

    def get_neighbors(self, sector_id: int) -> list[Sector]:
        sector = self.sectors.get(sector_id)
        if not sector:
            return []
        return [self.sectors[wid] for wid in sector.warp_links if wid in self.sectors]
