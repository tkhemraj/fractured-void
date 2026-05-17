"""
Mission system. Tracks available, active, and completed missions.
Missions have typed objectives; the manager checks completion conditions
each time the relevant game event fires.
"""
import json
import os
from engine.event_bus import bus

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _load_missions() -> dict:
    with open(os.path.join(DATA_DIR, "missions.json")) as f:
        return json.load(f)


class MissionProgress:
    def __init__(self, mission_id: str, mission_data: dict):
        self.mission_id = mission_id
        self.data = mission_data
        self.objective_progress: dict = {}
        self.completed = False

        for obj in mission_data.get("objectives", []):
            otype = obj["type"]
            if otype in ("carry", "combat_victory"):
                self.objective_progress[otype] = 0
            elif otype in ("deliver_to_sector", "visit_sector"):
                self.objective_progress[otype] = False

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "objective_progress": self.objective_progress,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: dict, all_missions: dict) -> "MissionProgress":
        mission_id = data["mission_id"]
        obj = cls(mission_id, all_missions.get(mission_id, {}))
        obj.objective_progress = data.get("objective_progress", {})
        obj.completed = data.get("completed", False)
        return obj


class MissionManager:
    def __init__(self):
        self._all_missions: dict = {}
        self.active: list[MissionProgress] = []
        self.completed_ids: set[str] = set()
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        self._all_missions = _load_missions()
        self._loaded = True

        bus.subscribe("sector_entered", self._on_sector_entered)
        bus.subscribe("enemy_destroyed", self._on_enemy_destroyed)
        bus.subscribe("trade_completed", self._on_trade_completed)

    def get_available_for_sector(self, sector_id: int, player_relations: dict) -> list[dict]:
        """Returns mission dicts available at this sector, filtered by faction relation."""
        self.load()
        available = []
        for mid, mdata in self._all_missions.items():
            if mid in self.completed_ids:
                continue
            if any(mp.mission_id == mid for mp in self.active):
                continue
            if sector_id not in mdata.get("available_at_sectors", []):
                continue
            faction = mdata.get("faction", "")
            min_rel = mdata.get("min_relation", -100)
            if player_relations.get(faction, 0) < min_rel:
                continue
            available.append(mdata)
        return available

    def accept_mission(self, mission_id: str) -> bool:
        self.load()
        if mission_id not in self._all_missions:
            return False
        if any(mp.mission_id == mission_id for mp in self.active):
            return False
        prog = MissionProgress(mission_id, self._all_missions[mission_id])
        self.active.append(prog)
        bus.post("mission_accepted", mission_id=mission_id)
        return True

    def check_carry_objectives(self, cargo_contents: dict) -> None:
        """Call this when cargo changes."""
        for prog in self.active:
            if prog.completed:
                continue
            for obj in prog.data.get("objectives", []):
                if obj["type"] == "carry":
                    item = obj["item"]
                    qty = obj["quantity"]
                    have = cargo_contents.get(item, 0)
                    prog.objective_progress["carry"] = min(have, qty)

    def _on_sector_entered(self, sector_id: int, **kw) -> None:
        for prog in self.active:
            if prog.completed:
                continue
            for obj in prog.data.get("objectives", []):
                if obj["type"] == "visit_sector" and obj["sector"] == sector_id:
                    prog.objective_progress["visit_sector"] = True
                elif obj["type"] == "deliver_to_sector" and obj["sector"] == sector_id:
                    # Check carry objective also satisfied
                    carry_obj = next((o for o in prog.data["objectives"] if o["type"] == "carry"), None)
                    if carry_obj:
                        needed = carry_obj["quantity"]
                        have = prog.objective_progress.get("carry", 0)
                        if have >= needed:
                            prog.objective_progress["deliver_to_sector"] = True
                    else:
                        prog.objective_progress["deliver_to_sector"] = True
            self._check_completion(prog)

    def _on_enemy_destroyed(self, faction: str, **kw) -> None:
        for prog in self.active:
            if prog.completed:
                continue
            for obj in prog.data.get("objectives", []):
                if obj["type"] == "combat_victory" and obj.get("faction") == faction:
                    needed = obj.get("count", 1)
                    current = prog.objective_progress.get("combat_victory", 0)
                    prog.objective_progress["combat_victory"] = min(needed, current + 1)
            self._check_completion(prog)

    def _on_trade_completed(self, **kw) -> None:
        pass

    def _check_completion(self, prog: MissionProgress) -> None:
        if prog.completed:
            return
        for obj in prog.data.get("objectives", []):
            otype = obj["type"]
            val = prog.objective_progress.get(otype)
            if otype in ("deliver_to_sector", "visit_sector"):
                if not val:
                    return
            elif otype == "carry":
                if val < obj.get("quantity", 1):
                    return
            elif otype == "combat_victory":
                if val < obj.get("count", 1):
                    return
        prog.completed = True
        self.completed_ids.add(prog.mission_id)
        bus.post("mission_completed", mission_id=prog.mission_id, mission_data=prog.data)

    def get_active_summary(self) -> list[dict]:
        return [
            {
                "id": p.mission_id,
                "title": p.data.get("title", ""),
                "progress": p.objective_progress,
                "completed": p.completed,
            }
            for p in self.active
        ]

    def serialize(self) -> list[dict]:
        return [p.to_dict() for p in self.active]

    def deserialize(self, data: list[dict]) -> None:
        self.load()
        self.active = [MissionProgress.from_dict(d, self._all_missions) for d in data]


missions = MissionManager()
