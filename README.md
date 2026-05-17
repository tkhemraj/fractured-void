# FRACTURED VOID

> *"Where corporations own the stars, and you own nothing but your ship."*

A space game merging **TradeWars 2002** sector-based trading with **Wing Commander** cockpit combat. Built in Python with Pygame. Dystopian near-future, 2387.

---

## Story

Five mega-corporations carved up human space after the Corporate Consolidation Wars. You are **Vael Korr** — former Apex Syndicate pilot, dishonorably discharged for refusing to fire on civilians. You own a battered freighter called *The Cinder Pact* and 5,000 credits.

The Fracture Zone is spreading. Ghost Fleet vessels are crossing sectors that were safe six months ago. Nobody is coming to explain it to you.

---

## Gameplay

### TradeWars: The Galaxy
- Navigate a 500-sector galaxy connected by warp links
- Buy and sell 10 commodities at classified ports (fuel ore, organics, equipment, arms, contraband, and more)
- Ports are controlled by factions: **Apex Syndicate, Helix Commerce, Ironveil Trading Co., Drift Cartel, The Remnant, Ghost Fleet**
- Colonize planets, deploy fighters, build influence
- Every warp costs turns — manage them wisely

### Wing Commander: The Combat
- Real-time 3D cockpit combat when you're intercepted
- Full HUD: radar, shield display, target tracking, weapon status
- Ship AI with three skill tiers: Novice, Veteran, Ace
- Guns, heat-seeking missiles, image-recognition missiles, photon torpedoes
- Afterburner for speed bursts, shield rebalancing under fire

---

## Controls

### Sector Map
| Key | Action |
|-----|--------|
| Click sector | Select |
| Double-click / Enter | Warp to selected sector |
| P | Enter port (trading) |
| C | Center map on your ship |
| Scroll | Zoom in/out |
| Middle-click drag | Pan |

### Combat
| Key | Action |
|-----|--------|
| WASD / Arrow keys | Steer ship |
| Space | Fire guns |
| F | Fire missile |
| T | Cycle target |
| Shift | Afterburner |
| 1 | Cycle missile type |
| Escape | Attempt to flee |

### Trading
| Key | Action |
|-----|--------|
| Up/Down | Select commodity |
| Left/Right | Adjust quantity |
| M | Set quantity to maximum affordable |
| Enter/Space | Execute trade |
| L / Escape | Leave port |

---

## Install & Run

```bash
pip install pygame-ce numpy
python main.py
```

Requires Python 3.10+.

---

## Architecture

```
fractured-void/
├── main.py                  # Game loop & screen transitions
├── engine/
│   ├── game_state.py        # Central state (player, ship, cargo)
│   └── event_bus.py         # Pub/sub events between systems
├── world/
│   ├── galaxy.py            # Procedural 500-sector galaxy
│   └── sector.py            # Sector, Port, Planet definitions
├── combat/
│   ├── combat_engine.py     # Combat simulation
│   ├── ship_3d.py           # 3D ships, perspective projection
│   └── enemy_ai.py          # Novice/Veteran/Ace AI
├── rendering/
│   ├── space_renderer.py    # Star field + 3D ship rendering
│   ├── hud_renderer.py      # Wing Commander cockpit HUD
│   └── map_renderer.py      # Sector map
├── screens/
│   ├── main_menu.py
│   ├── sector_map_screen.py
│   ├── trading_screen.py
│   └── combat_screen.py
└── data/
    ├── ships.json           # Ship stats
    ├── weapons.json         # Weapon definitions
    ├── commodities.json     # Trade goods
    └── factions.json        # Faction lore & data
```

The combat renderer uses **perspective projection** — the same technique Wing Commander 1 & 2 used. Ships are polygon silhouettes scaled by distance (`screen_scale = focal_length / world_z`). No game engine required.

---

## Roadmap

- [ ] Mission system with character portraits and dialogue
- [ ] Planet colonization mechanics
- [ ] Save/load game
- [ ] Ship upgrades at shipyards
- [ ] Corporation system (join/found a corp)
- [ ] Faction war events (dynamic sector control)
- [ ] Sound effects and music
- [ ] Sprite art for ships (replacing polygon silhouettes)
- [ ] **Unreal Engine port** (long-term goal)

---

## Factions

| Faction | Controls | Starting Relation |
|---------|----------|-------------------|
| Apex Syndicate | Weapons, mercenaries | -30 (they discharged you) |
| Helix Commerce | Food, medicine | 0 |
| Ironveil Trading Co. | Fuel ore, metals | +10 |
| Drift Cartel | Black market, information | +5 |
| The Remnant | Free sectors (growing) | +20 |
| Ghost Fleet | The Fracture Zone | 0 (enigmatic) |

---

*Built with Python + Pygame-CE. Designed for eventual Unreal Engine port.*
