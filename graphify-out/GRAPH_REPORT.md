# Graph Report - .  (2026-06-16)

## Corpus Check
- Large corpus: 50 files � ~666,481 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 641 nodes · 1478 edges · 29 communities (23 shown, 6 thin omitted)
- Extraction: 82% EXTRACTED · 18% INFERRED · 0% AMBIGUOUS · INFERRED: 263 edges (avg confidence: 0.52)
- Token cost: 147,639 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Data Layer (DBDecoderItemsPeople)|Data Layer (DB/Decoder/Items/People)]]
- [[_COMMUNITY_Game Controller (Dungeon Turn Loop)|Game Controller (Dungeon Turn Loop)]]
- [[_COMMUNITY_Level Generation|Level Generation]]
- [[_COMMUNITY_Magic System & Menus|Magic System & Menus]]
- [[_COMMUNITY_Enemies & Status Effects|Enemies & Status Effects]]
- [[_COMMUNITY_UI Rendering & Wrapper|UI Rendering & Wrapper]]
- [[_COMMUNITY_LLM Features & Project Docs|LLM Features & Project Docs]]
- [[_COMMUNITY_LLM Client|LLM Client]]
- [[_COMMUNITY_Map Pathfinding & FOV|Map Pathfinding & FOV]]
- [[_COMMUNITY_Config Constants|Config Constants]]
- [[_COMMUNITY_Player Combat Stats|Player Combat Stats]]
- [[_COMMUNITY_Input Handling|Input Handling]]
- [[_COMMUNITY_Logging & Entry Point|Logging & Entry Point]]
- [[_COMMUNITY_Map Cells & Player Interaction|Map Cells & Player Interaction]]
- [[_COMMUNITY_Skills System|Skills System]]
- [[_COMMUNITY_Top-level Modules|Top-level Modules]]
- [[_COMMUNITY_Player Encumbrance & Evasion|Player Encumbrance & Evasion]]
- [[_COMMUNITY_Screenshots & Cross-references|Screenshots & Cross-references]]
- [[_COMMUNITY_Dependency Bootstrap|Dependency Bootstrap]]
- [[_COMMUNITY_Enemy Spawn Selection|Enemy Spawn Selection]]
- [[_COMMUNITY_TimePause System|Time/Pause System]]
- [[_COMMUNITY_Map Rendering (GlyphsViewport)|Map Rendering (Glyphs/Viewport)]]
- [[_COMMUNITY_Weapon Expansion Constraints|Weapon Expansion Constraints]]
- [[_COMMUNITY_XP Progression|XP Progression]]
- [[_COMMUNITY_Splash Screen Art|Splash Screen Art]]
- [[_COMMUNITY_Linux Launcher Script|Linux Launcher Script]]

## God Nodes (most connected - your core abstractions)
1. `Dungeon` - 74 edges
2. `style_text()` - 56 edges
3. `DungeonMenu` - 40 edges
4. `DungeonJSONDecoder` - 39 edges
5. `DungeonThrowable` - 32 edges
6. `DungeonWeaponTexts` - 31 edges
7. `DungeonItem` - 30 edges
8. `DungeonMap` - 27 edges
9. `DungeonWeapon` - 26 edges
10. `DungeonPotion` - 26 edges

## Surprising Connections (you probably didn't know these)
- `CodeQL Analysis Workflow` --conceptually_related_to--> `Dungeon (god-object controller)`  [AMBIGUOUS]
  .github/workflows/codeql-analysis.yml → Dungeon/Application/main.py
- `Dungeon Biome Example Screenshot` --references--> `DungeonPlayer`  [INFERRED]
  resources/Dungeon_Biome_Example.png → Dungeon/Application/classes/map.py
- `God-Object Coupling Anti-pattern` --rationale_for--> `DungeonMenu`  [EXTRACTED]
  CLAUDE.md → Dungeon/Application/classes/menus.py
- `README.md (project readme)` --references--> `Dungeon.gif (Splash/Title Animation)`  [AMBIGUOUS]
  README.md → resources/Dungeon.gif
- `Dungeon Biome Example Screenshot` --references--> `StyleConfig / SymbolConfig (terrain colors & symbols)`  [INFERRED]
  resources/Dungeon_Biome_Example.png → Dungeon/Application/config.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **LLM-powered optional flavor features (biome themes, hints, lore, dialogue) gated by LLMClient.enabled** — llm_llmclient, biome_theme_generation, dm_ambient_hints, item_lore_feature, npc_dialogue_feature [EXTRACTED 0.95]
- **Speculative LLM feature ideas that build on existing systems (NPC interaction, message log, identification)** — idea_llm_npc_dialogue, idea_adaptive_hints_dm, idea_procedural_item_lore, idea_llm_dungeon_themes [INFERRED 0.80]
- **Constraints jointly governing the weapon expansion milestone** — claude_balance_constraint, claude_no_new_equip_slots_constraint, claude_data_driven_constraint [EXTRACTED 1.00]

## Communities (29 total, 6 thin omitted)

### Community 0 - "Data Layer (DB/Decoder/Items/People)"
Cohesion: 0.06
Nodes (68): DungeonDatabase, DungeonEnemyDatabase, DungeonItemDatabase, DungeonPeopleDatabase, Root database that aggregates item, enemy, and people sub-databases., Stores and searches enemy loader instances., Stores and searches NPC loader instances., All loaders that sell or provide a service (traders + healers). (+60 more)

### Community 1 - "Game Controller (Dungeon Turn Loop)"
Cohesion: 0.05
Nodes (25): Dungeon, Pick what `fire()` should use: an equipped ranged weapon, or a thrown         i, Build a Rich-markup description string for the tile at (y, x)., DCSS-style examine mode: move cursor, read tile descriptions., Deplete one unit of a thrown item's stack, dropping it from the pack at zero., G key: prompt the player to navigate to nearest up or down stairs., Walk to the nearest known staircase of the given type ('up' or 'down')., [ / ] keys: pan the camera to a known staircase and highlight it. (+17 more)

### Community 2 - "Level Generation"
Cohesion: 0.05
Nodes (66): _apply_terrain_features(), _between(), _borders_interior(), _bsp_connect(), _bsp_leaf_center(), _bsp_place_rooms(), _bsp_split(), _BSPNode (+58 more)

### Community 3 - "Magic System & Menus"
Cohesion: 0.07
Nodes (39): clear_screen(), style_text(), calculate_failure(), _channel(), _execute(), _expanding_aoe(), _explosion(), _ignite_flora() (+31 more)

### Community 4 - "Enemies & Status Effects"
Cohesion: 0.08
Nodes (12): DungeonEnemy, EnemyTexts, _fmt(), Take one turn: wake near the player, then chase, fire, or bump-attack., Formatted combat text templates for an enemy., A living dungeon enemy: combat stats, position, and simple chase AI., Resolve one attack against the player, applying damage, status, and messaging., Status effects shared by the player and monsters.  A :class:`StatusSet` hangs of (+4 more)

### Community 5 - "UI Rendering & Wrapper"
Cohesion: 0.08
Nodes (24): GameWrapper, Displays the splash screen and routes input to start or exit., DungeonUI, The on-screen HUD: map panel, hero sidebar, and a scrolling message log., Owns the message log and renders the full game frame each turn., config singleton, DungeonEnemy / DungeonEnemyLoader, Energy-Scheduled Turn System (roguelike) (+16 more)

### Community 6 - "LLM Features & Project Docs"
Cohesion: 0.08
Nodes (24): Biome Theme Generation, v2.1 Caverns & Crosscuts, v2.2 Depths & Disciplines, Dynamic Floor Biomes, v2.0 Stone Soup Overhaul, v2.3 The Terrain Update, Three Sigil Shards Win Condition, Crawl Dungeon Feature Wiki Reference (+16 more)

### Community 7 - "LLM Client"
Cohesion: 0.09
Nodes (15): LLMClient, _load_dotenv(), Thin LLM client for Dungeon.py.  Supports three OpenAI-compatible providers co, Synchronous chat completion. Returns stripped text or None on any failure., Submit a completion to the background thread. Returns a Future., Like complete() but parses the result as a JSON object. Returns None on failure., Submit a JSON completion to the background thread. Returns a Future., Minimal .env loader — no external dependency required. (+7 more)

### Community 8 - "Map Pathfinding & FOV"
Cohesion: 0.14
Nodes (5): _bresenham(), DungeonMap, One dungeon floor: a matrix of cells plus structural anchors and fog-of-war., Chance to notice an adjacent secret door or trap; returns 'door'/'trap'/None., Breadth-first search; returns the step path (excluding start) to the nearest

### Community 9 - "Config Constants"
Cohesion: 0.11
Nodes (17): Config, DepthConfig, MapConfig, PlayerConfig, Central game configuration: colours, symbols, terrain, map size, depth and spawn, Single-character glyphs used to render the map., Per-floor map dimension ranges. Levels average ~70x70 and never exceed 80x80., Multi-floor descent settings. (+9 more)

### Community 10 - "Player Combat Stats"
Cohesion: 0.15
Nodes (7): DungeonPlayer, Total AC from all worn armour and Armour skill., Attempt to act in a direction. Returns True if a turn was spent., Apply a magical weapon's on-hit status effect (staves) to a surviving enemy., The player character: position, health, inventory and bump-to-attack combat., Return (damage_bonus, accuracy_bonus) from level, skills, and Might., skill_for_weapon()

### Community 11 - "Input Handling"
Cohesion: 0.23
Nodes (10): feed_keys(), _normalise(), Cross-platform, turn-based single-key input.  Replaces the old ``keyboard`` glob, Return the compass direction (e.g. "n"/"se") for a movement key, else None., Queue a sequence of logical keys to be returned by :func:`read_key`.      Intend, Block until a single logical keypress and return its token., read_direction(), read_key() (+2 more)

### Community 12 - "Logging & Entry Point"
Cohesion: 0.27
Nodes (3): Logger, LogType, current_time()

### Community 16 - "Player Encumbrance & Evasion"
Cohesion: 0.25
Nodes (4): Combined encumbrance rating of worn body armour and shield, eased by level, Shield SH plus Dodging skill, minus encumbrance., How much further away encumbered armour lets sleeping enemies notice you., Extra energy cost applied after firing a ranged weapon while encumbered.

### Community 17 - "Screenshots & Cross-references"
Cohesion: 0.29
Nodes (7): StyleConfig / SymbolConfig (terrain colors & symbols), DungeonItem / Potion System, Dungeon Controller (turn loop, energy scheduling), Procedural Floor Generation, DungeonTrader (Chemist NPC), DungeonUI HUD Rendering, Dungeon Biome Example Screenshot

### Community 18 - "Dependency Bootstrap"
Cohesion: 0.47
Nodes (5): check_modules(), _clear(), _pip_install(), Install *module* into the interpreter that is actually running the game.      Us, Ensure every required (and offered optional) module can be imported.

### Community 19 - "Enemy Spawn Selection"
Cohesion: 0.33
Nodes (3): Pick a spawnable enemy loader appropriate for the given floor (weighted)., Return all spawnable enemy loaders valid for a given depth (unweighted)., Like random_for_depth but biases towards preferred_names when possible.

### Community 22 - "Weapon Expansion Constraints"
Cohesion: 0.40
Nodes (5): Existing Balance Constraint, Data-Driven Content Constraint, No New Equip Slots Constraint, Weapon Expansion & Hands System Milestone, Dungeon/data/weapons.json

### Community 23 - "XP Progression"
Cohesion: 0.50
Nodes (3): ProgressionConfig, Character growth: XP curve and per-level stat gains., XP needed to advance from *level* to the next.

### Community 24 - "Splash Screen Art"
Cohesion: 0.50
Nodes (4): Dungeon.gif (Splash/Title Animation), DUNGEON.PY Pixel-Art Logo, README.md (project readme), GameWrapper Splash Screen

## Ambiguous Edges - Review These
- `CodeQL Analysis Workflow` → `Dungeon (god-object controller)`  [AMBIGUOUS]
  .github/workflows/codeql-analysis.yml · relation: conceptually_related_to
- `Dungeon.gif (Splash/Title Animation)` → `README.md (project readme)`  [AMBIGUOUS]
  README.md · relation: references

## Knowledge Gaps
- **25 isolated node(s):** `range`, `Path`, `linux_terminal.sh script`, `CodeQL Analysis Workflow`, `Dynamic Floor Biomes` (+20 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `CodeQL Analysis Workflow` and `Dungeon (god-object controller)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Dungeon.gif (Splash/Title Animation)` and `README.md (project readme)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `Dungeon` connect `Game Controller (Dungeon Turn Loop)` to `Magic System & Menus`, `LLM Client`, `UI Rendering & Wrapper`, `Top-level Modules`?**
  _High betweenness centrality (0.169) - this node is a cross-community bridge._
- **Why does `style_text()` connect `Magic System & Menus` to `Data Layer (DB/Decoder/Items/People)`, `Game Controller (Dungeon Turn Loop)`, `Player Combat Stats`, `Map Cells & Player Interaction`, `Top-level Modules`, `Time/Pause System`?**
  _High betweenness centrality (0.113) - this node is a cross-community bridge._
- **Why does `DungeonPlayer` connect `Player Combat Stats` to `Data Layer (DB/Decoder/Items/People)`, `Game Controller (Dungeon Turn Loop)`, `Enemies & Status Effects`, `Map Cells & Player Interaction`, `Skills System`, `Top-level Modules`, `Player Encumbrance & Evasion`, `Screenshots & Cross-references`?**
  _High betweenness centrality (0.090) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Dungeon` (e.g. with `LLMClient` and `GameWrapper`) actually correct?**
  _`Dungeon` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `DungeonMenu` (e.g. with `DungeonArmour` and `DungeonInventory`) actually correct?**
  _`DungeonMenu` has 9 INFERRED edges - model-reasoned connections that need verification._