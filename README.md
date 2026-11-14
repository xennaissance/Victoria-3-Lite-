# Victoria 3 Lite

A performance mod for Victoria 3 (game version 1.15.1). Made for people who need the game to run on a potato computer, or who just want to finish a game in one afternoon.

## Design
- The gameplay loop stays: you still build an economy, run politics and laws, and fight diplomacy and wars.
- Anything the loop does not depend on may be simplified or removed for speed.
- Larger changes come with game rules so players can turn them off.

## Planned changes
- **Culture and religion unification** (on by default, with an opt-out game rule): every pop becomes one culture and one religion at game start, so pops merge and the simulation has far less to calculate.
- Simpler AI scoring, fewer countries, cheaper pop qualification checks, lighter portraits, and fewer costly alerts and progress bars. Each change is measured before it ships.

## Status
Early development (v0.1).

Done:
- **Pop Cultures** game rule (default: one culture). At game start every pop and every country's primary culture becomes Human.
- **Pop Religions** game rule (default: one religion). At game start every pop and every country's state religion becomes Atheist.

Not yet tested in game. Test checklist:
1. Start a new game with the mod on and both rules at their defaults. Check `logs/error.log` for lines mentioning `vl_`.
2. Open a few countries: primary culture should be Human, state religion Atheist, and pops should show no culture or religion discrimination.
3. Run to the benchmark date and time 50 s at speed 5. Compare against the same rules set to "Original".

## Installing for development
Clone this repository into `Documents\Paradox Interactive\Victoria 3\mod\` and enable it in the launcher.
