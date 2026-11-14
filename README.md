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
- **Pop Religions** game rule with four settings:
  - **One faith** (default): every pop and country follows a new neutral religion, the Faith. It is not Atheist, so clergy work normally.
  - **Heritage groups**: four religions (Abrahamic, Eastern, Naturalistic, Non-Spiritual), built on Catholic, Confucian, Animist and Atheist.
  - **Heritages**: seven religions (Christian, Islamic, Jewish, Dharmic, Taoic, Indigenous, Materialist), built on Catholic, Sunni, Jewish, Hindu, Confucian, Animist and Atheist.
  - **Original religions**: vanilla.
  Merged religions keep the underlying vanilla religion, so its events and journal entries still work, and show the group or heritage name on screen through customizable localization.
- **Pop Consolidation** game rule (default: off). At game start every pop in a state takes the state's largest culture and largest religion. Works on top of the other two rules; most useful with Original cultures or religions.
- **Costly Alerts** game rule (default: off). Skips the "low expected standard of living in state" alert, which is expensive to check.

Not yet tested in game. Test checklist:
1. Start a new game with the mod on and both rules at their defaults. Check `logs/error.log` for lines mentioning `vl_` or `alert_types`.
2. Open a few countries: primary culture should be Human, state religion the Faith, and pops should show no culture or religion discrimination.
3. Start games with Pop Religions on Heritage groups and on Heritages. Check that religion names read Abrahamic / Christian and so on everywhere (state panel, pop list, country panel, tooltips), and that no screen shows raw text like `[GetPlayer...]`. Check the main menu and lobby too. With Original religions, names must read as vanilla.
4. With Pop Cultures and Pop Religions on Original and Pop Consolidation on: every state should show a single culture and a single religion, the one that was largest before.
5. With Costly Alerts off, the low standard of living alert should never appear; with it on, it should.
6. Run to the benchmark date and time 50 s at speed 5. Compare against the same rules set to "Original".

## Installing for development
Clone this repository into `Documents\Paradox Interactive\Victoria 3\mod\` and enable it in the launcher.
