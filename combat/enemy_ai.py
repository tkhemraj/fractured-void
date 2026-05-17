"""
Enemy AI for combat. Three skill tiers modeled on Wing Commander's pilot grades.
Each tick, the AI decides movement and firing based on its skill and situation.
"""
import math
import random
from combat.ship_3d import CombatShip, Vec3


class EnemyAI:
    NOVICE = "novice"
    VETERAN = "veteran"
    ACE = "ace"

    def __init__(self, ship: CombatShip, skill: str = "novice"):
        self.ship = ship
        self.skill = skill
        self.rng = random.Random()

        # State machine
        self.state = "approach"
        self.state_timer = 0.0
        self.maneuver_timer = 0.0
        self.dodge_vector = Vec3(0, 0, 0)

        # Skill parameters
        self.params = {
            self.NOVICE:   {"accuracy": 0.4, "reaction": 1.5, "aggression": 0.5, "dodge_chance": 0.1},
            self.VETERAN:  {"accuracy": 0.65, "reaction": 0.8, "aggression": 0.75, "dodge_chance": 0.3},
            self.ACE:      {"accuracy": 0.9,  "reaction": 0.3, "aggression": 1.0,  "dodge_chance": 0.6},
        }.get(skill, {"accuracy": 0.5, "reaction": 1.0, "aggression": 0.6, "dodge_chance": 0.2})

    def update(self, dt: float, player_ship: CombatShip) -> list:
        """
        Returns a list of actions: [("fire", weapon_id), ("afterburner", bool), ...]
        """
        actions = []
        self.state_timer += dt
        self.maneuver_timer += dt

        dist = self.ship.distance_to(player_ship)
        angle = self.ship.angle_to(player_ship)

        # State transitions
        if self.state == "approach" and dist < 400:
            self.state = "attack"
            self.state_timer = 0.0
        elif self.state == "attack" and dist > 600:
            self.state = "approach"
            self.state_timer = 0.0
        elif self.state == "attack" and self.state_timer > 3.0 and self.skill == self.ACE:
            if self.rng.random() < 0.3:
                self.state = "barrel_roll"
                self.state_timer = 0.0

        self._update_movement(dt, player_ship, dist, angle, actions)
        self._update_weapons(dt, player_ship, dist, angle, actions)

        return actions

    def _update_movement(self, dt: float, player: CombatShip, dist: float, angle: float, actions: list) -> None:
        params = self.params
        to_player = (player.pos - self.ship.pos).normalized()

        if self.state == "approach":
            self._turn_toward(to_player, dt)
            self.ship.velocity = self.ship.heading * self.ship.speed
            actions.append(("afterburner", dist > 500))

        elif self.state == "attack":
            self._turn_toward(to_player, dt)
            self.ship.velocity = self.ship.heading * self.ship.current_speed

            # Dodge if taking fire (ace/veteran only)
            if self.rng.random() < params["dodge_chance"] * dt:
                self._start_dodge()
            if self.maneuver_timer < 0.5 and self.dodge_vector.length() > 0:
                self.ship.velocity = (self.ship.heading + self.dodge_vector * 0.5) * self.ship.current_speed
            else:
                self.dodge_vector = Vec3(0, 0, 0)

        elif self.state == "barrel_roll":
            # Ace maneuver: roll perpendicular to player
            perpendicular = Vec3(-to_player.y, to_player.x, 0).normalized()
            roll_target = (to_player + perpendicular * 1.5).normalized()
            self._turn_toward(roll_target, dt * 2)
            self.ship.velocity = self.ship.heading * self.ship.afterburner_speed
            actions.append(("afterburner", True))
            if self.state_timer > 1.2:
                self.state = "attack"
                self.state_timer = 0.0

    def _update_weapons(self, dt: float, player: CombatShip, dist: float, angle: float, actions: list) -> None:
        params = self.params
        if self.state == "attack" and dist < 500 and angle < 30:
            if self.rng.random() < params["accuracy"] * dt * 2:
                actions.append(("fire", "primary"))

    def _turn_toward(self, direction: Vec3, dt: float) -> None:
        rate = self.ship.turn_rate * dt
        current = self.ship.heading
        new_x = current.x + (direction.x - current.x) * rate
        new_y = current.y + (direction.y - current.y) * rate
        new_z = current.z + (direction.z - current.z) * rate
        self.ship.heading = Vec3(new_x, new_y, new_z).normalized()

    def _start_dodge(self) -> None:
        angle = self.rng.uniform(0, math.pi * 2)
        self.dodge_vector = Vec3(math.cos(angle), math.sin(angle), 0)
        self.maneuver_timer = 0.0
