"""Generate Victoria 3 Lite's patched copies of vanilla script.

Usage: python tools/gen_vanilla_overrides.py <path to Victoria 3/game>

Reads the vanilla files, applies text patches and writes:
  common/ai_strategies/vl_ai_strategy_inject.txt    (INJECT: two values of ai_strategy_default)
  common/political_movements/vl_movement_overrides.txt  (REPLACE: blocks)
  common/script_values/vl_movement_values.txt           (REPLACE: blocks)
  common/scripted_triggers/vl_scripted_triggers.txt     (REPLACE: blocks)
  common/treaty_articles/vl_treaty_overrides.txt        (REPLACE: blocks)
  common/scripted_progress_bars/vl_progress_bar_inject.txt (INJECT: monthly_progress of the fascism bar)
  common/ai_regional_objectives/00_ai_regional_objectives.txt (full-file override; folder has no INJECT)

Every patch asserts that it matched exactly once, so a game patch that changes
the vanilla text makes this script fail loudly instead of writing a broken file.
Re-run it after every game patch.
"""
import re
import sys
from pathlib import Path

GAME = Path(sys.argv[1]) if len(sys.argv) > 1 else None
ROOT = Path(__file__).resolve().parent.parent
BOM = "﻿"


def read(rel):
    return (GAME / rel).read_text(encoding="utf-8-sig")


def write(rel, text):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(BOM + text, encoding="utf-8", newline="\n")
    print("wrote", rel)


def find_block(text, key, start=0):
    """Return (start, open_brace, end) of `key = { ... }` (end is index after the closing brace)."""
    m = re.compile(r"(?m)^(\s*)" + re.escape(key) + r"\s*=\s*\{").search(text, start)
    assert m, f"block {key} not found"
    i = m.end() - 1
    depth, j = 0, i
    while j < len(text):
        c = text[j]
        if c == "#":  # skip comments
            nl = text.find("\n", j)
            j = len(text) if nl == -1 else nl
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return m.start(), i, j + 1
        j += 1
    raise AssertionError(f"unbalanced block {key}")


def block_text(text, key, start=0):
    s, _, e = find_block(text, key, start)
    return text[s:e]


def brace_scan(text):
    """Brace matcher that ignores comments; returns dict open->close."""
    pairs, stack, j = {}, [], 0
    while j < len(text):
        c = text[j]
        if c == "#":
            nl = text.find("\n", j)
            j = len(text) if nl == -1 else nl
            continue
        if c == "{":
            stack.append(j)
        elif c == "}":
            pairs[stack.pop()] = j
        j += 1
    return pairs


def sub_once(pattern, repl, text, what):
    new, n = re.subn(pattern, repl, text, count=0)
    assert n == 1, f"{what}: expected 1 match, got {n}"
    return new


def ws(s):
    """Turn a template with single spaces into a whitespace-tolerant regex."""
    return r"\s*".join(re.escape(tok) for tok in s.split())


def wrap_field(block, field, before, after):
    """Insert text right after `field = {` and right before its closing brace."""
    s, o, e = find_block(block, field)
    inner = block[o + 1 : e - 1]
    return block[: o + 1] + before + inner + after + block[e - 1 :]


# ---------------------------------------------------------------- AI strategy
def patch_ai():
    rel = "common/ai_strategies/00_default_strategy.txt"
    text = read(rel)

    # 1. strategic_region_scores: minor powers skip regions they neither own a state in nor border.
    s, o, e = find_block(text, "strategic_region_scores")
    blk = text[s:e]
    blk = sub_once(
        ws("scope:region = { every_scope_state = { limit = { is_homeland_of_country_cultures = root } add = 10 } }"),
        "if = { # Victoria 3 Lite: with one culture every state is a homeland, so this only measured region size\n"
        "\t\t\t\tlimit = { NOT = { has_game_rule = vl_one_culture } }\n"
        "\t\t\t\tscope:region = { every_scope_state = { limit = { is_homeland_of_country_cultures = root } add = 10 } }\n"
        "\t\t\t}",
        blk, "homeland loop")
    blk = sub_once(
        r"(strategic_region_scores\s*=\s*\{\s*value\s*=\s*0\s*\n)",
        r"\1"
        "\t\t# Victoria 3 Lite: minor powers ignore regions they do not touch (their stances there are always none)\n"
        "\t\tif = {\n"
        "\t\t\tlimit = {\n"
        "\t\t\t\tcountry_rank <= rank_value:minor_power\n"
        "\t\t\t\tNOT = { any_scope_state = { region = scope:region } }\n"
        "\t\t\t\tNOT = { any_neighbouring_state = { region = scope:region } }\n"
        "\t\t\t}\n"
        "\t\t\tadd = 0\n"
        "\t\t}\n"
        "\t\telse = {\n",
        blk, "region scores gate")
    blk = blk[:-1].rstrip() + "\n\t\t} # Victoria 3 Lite: end of else\n\t}"
    text = text[:s] + blk + text[e:]

    # 2. Stance scores: vanilla multiplies by 0 at the end for minor powers outside their capital region.
    #    Check that first and skip the whole calculation instead (same result).
    s, o, e = find_block(text, "strategic_region_stance_type_scores")
    stances = text[s:e]
    gate_end = ws('if = { limit = { country_rank <= rank_value:minor_power scope:target_region != capital.region } '
                  'multiply = { desc = "AI_REGION_STANCE_SMALL_COUNTRY" value = 0 } }')
    for stance in ("stance_conquer_region", "stance_protect_region", "stance_colonize_region"):
        ss, so, se = find_block(stances, stance)
        st = stances[ss:se]
        st = sub_once(gate_end, "", st, stance + " trailing gate")
        st = sub_once(
            r"(=\s*\{\s*value\s*=\s*0\s*\n)",
            r"\1"
            "\t\t\t# Victoria 3 Lite: vanilla's small-country multiply-by-0 moved up front\n"
            "\t\t\tif = {\n"
            "\t\t\t\tlimit = { NAND = { country_rank <= rank_value:minor_power scope:target_region != capital.region } }\n",
            st, stance + " gate")
        st = st[:-1].rstrip() + "\n\t\t\t}\n\t\t}"
        stances = stances[:ss] + st + stances[se:]
    text = text[:s] + stances + text[e:]

    # Only the two patched values are injected (see the INJECT note at the top of the output file).
    out = [
        "# Victoria 3 Lite: patched copies of two vanilla AI strategy values. Generated by tools/gen_vanilla_overrides.py; do not edit by hand.\n"
        "# INJECT appends these to ai_strategy_default after vanilla's own definitions. The wiki does not say whether a\n"
        "# duplicate value block overrides vanilla's or is ignored; check with the script profiler that these lines\n"
        "# appear and vanilla's 00_default_strategy.txt lines for the same values do not. If vanilla's still appear,\n"
        "# replace ai_strategy_default as a whole instead (REPLACE:).\n",
        "INJECT:ai_strategy_default = {",
        "\t" + block_text(text, "strategic_region_scores").strip(),
        "",
        "\t" + block_text(text, "strategic_region_stance_type_scores").strip(),
        "}",
    ]
    write("common/ai_strategies/vl_ai_strategy_inject.txt", "\n".join(out) + "\n")


# ---------------------------------------------------------------- Movements
NEIGHBOUR_SCAN = ws("owner = { any_neighbouring_state = { owner = {")
NEIGHBOUR_LIST = (
    "any_in_global_list = { # Victoria 3 Lite: only countries with an insurrection (list refreshed monthly), not every neighbouring state\n"
    "\t\t\t\t\tvariable = vl_insurgent_countries\n"
    "\t\t\t\t\tis_adjacent_to_country = ROOT.owner\n"
    "\t\t\t\t\tAND = { AND = {"
)


def gate_movement(blk, rule):
    blk = wrap_field(blk, "creation_trigger",
                     f"\n\t\tNOT = {{ has_game_rule = {rule} }} # Victoria 3 Lite\n", "")
    blk = wrap_field(blk, "disband_trigger",
                     f"\n\t\tOR = {{\n\t\t\thas_game_rule = {rule} # Victoria 3 Lite\n\t\t\tAND = {{",
                     "\t\t\t}\n\t\t}\n\t")
    return blk


def patch_movements():
    cult = read("common/political_movements/02_cultural_movement.txt")
    rel = read("common/political_movements/01_religious_movements.txt")
    out = ["# Victoria 3 Lite: vanilla movements with performance patches. Generated by tools/gen_vanilla_overrides.py; do not edit by hand.\n"]

    maj = block_text(cult, "movement_cultural_majority")
    maj = gate_movement(maj, "vl_one_culture")
    maj = sub_once(NEIGHBOUR_SCAN, NEIGHBOUR_LIST, maj, "cultural majority neighbour scan")
    out.append("REPLACE:" + maj.lstrip() + "\n")

    mino = block_text(cult, "movement_cultural_minority")
    mino = sub_once(NEIGHBOUR_SCAN, NEIGHBOUR_LIST, mino, "cultural minority neighbour scan")
    out.append("REPLACE:" + mino.lstrip() + "\n")

    rmaj = block_text(rel, "movement_religious_majority")
    rmaj = gate_movement(rmaj, "vl_religion_one_faith")
    out.append("REPLACE:" + rmaj.lstrip() + "\n")

    write("common/political_movements/vl_movement_overrides.txt", "\n".join(out))

    sv = read("common/script_values/movement_values.txt")
    rr = block_text(sv, "movement_radicalism_neighboring_religious_revolution")
    rr = sub_once(ws("owner ?= { any_neighbouring_state = { owner ?= {"),
                  NEIGHBOUR_LIST.replace("ROOT.owner", "ROOT.owner"), rr, "religious neighbour scan")
    write("common/script_values/vl_movement_values.txt",
          "# Victoria 3 Lite: generated by tools/gen_vanilla_overrides.py; do not edit by hand.\n\nREPLACE:" + rr.lstrip() + "\n")


# ---------------------------------------------------------------- Ideological movements, treaties
def patch_ideological():
    # 1. The neighbouring-insurrection check used by ~30 movements (scripted trigger, REPLACE-only).
    st = read("common/scripted_triggers/00_scripted_triggers.txt")
    trig = block_text(st, "neighboring_country_has_insurrectionary_movement_trigger")
    trig = sub_once(ws("owner ?= { any_neighbouring_state = { owner ?= {"), NEIGHBOUR_LIST, trig,
                    "insurrection scripted trigger")
    write("common/scripted_triggers/vl_scripted_triggers.txt",
          "# Victoria 3 Lite: generated by tools/gen_vanilla_overrides.py; do not edit by hand.\n\nREPLACE:"
          + trig.lstrip() + "\n")

    # 2. Pro-slavery radicalism walked every building in the country to find barracks and naval
    #    administrations in slave states. Walk the slave states instead (same sum).
    im = read("common/political_movements/00_ideological_movements.txt")
    ps = block_text(im, "movement_pro_slavery")
    for b in ("building_barrack", "building_naval_administration"):
        ps = sub_once(
            ws("every_scope_building = { limit = { is_building_type = " + b + " state = { is_slave_state = yes } } add = this.level }"),
            "every_scope_state = { # Victoria 3 Lite: states, not every building\n"
            "\t\t\t\t\t\tlimit = { is_slave_state = yes has_building = " + b + " }\n"
            "\t\t\t\t\t\tadd = b:" + b + ".level\n"
            "\t\t\t\t\t}",
            ps, "pro-slavery " + b)
    path = ROOT / "common/political_movements/vl_movement_overrides.txt"
    cur = path.read_text(encoding="utf-8-sig")
    path.write_text(BOM + cur + "\nREPLACE:" + ps.lstrip() + "\n", encoding="utf-8", newline="\n")
    print("appended movement_pro_slavery")

    # 3. Law commitment treaty: check the cheap conditions before walking every law, and match the
    #    law type before asking whether it is available (same result).
    tr = read("common/treaty_articles/20_law_commitment.txt")
    lc = block_text(tr, "law_commitment")
    s, o, e = find_block(lc, "law_type_valid_trigger")
    old = lc[s:e]
    any_law = block_text(old, "any_law")
    new = old.replace(any_law, "", 1)
    assert ws("law_is_available = yes type = scope:input") and re.search(ws("law_is_available = yes type = scope:input"), any_law)
    new = new[:-1].rstrip() + (
        "\n\t\t# Victoria 3 Lite: moved last, and type checked first\n"
        "\t\tany_law = {\n\t\t\ttype = scope:input\n\t\t\tlaw_is_available = yes\n\t\t}\n\t}")
    lc = lc[:s] + new + lc[e:]
    write("common/treaty_articles/vl_treaty_overrides.txt",
          "# Victoria 3 Lite: generated by tools/gen_vanilla_overrides.py; do not edit by hand.\n"
          "# REPLACE because INJECT cannot override a trigger block the article already has.\n\nREPLACE:"
          + lc.lstrip() + "\n")


# ---------------------------------------------------------------- Fascism progress bar
def patch_fascism():
    # The revanchism factor walked every state in the world twice. With One culture every state is a
    # homeland of every country, so it also filled the bar by +0.1 per foreign state each month.
    pb = read("common/scripted_progress_bars/00_victoria_progress_bars.txt")
    bar = block_text(pb, "fascism_progress_bar")
    mp = block_text(bar, "monthly_progress")
    old = ws("OR = { has_claim_by = ROOT is_homeland_of_country_cultures = ROOT } NOT = { owner = ROOT }")
    new = ("NOT = { owner = ROOT } # Victoria 3 Lite: cheap check first\n"
           "\t\t\t\t\tOR = {\n\t\t\t\t\t\thas_claim_by = ROOT\n"
           "\t\t\t\t\t\tAND = { # Victoria 3 Lite: with One culture every state is a homeland\n"
           "\t\t\t\t\t\t\tNOT = { has_game_rule = vl_one_culture }\n"
           "\t\t\t\t\t\t\tis_homeland_of_country_cultures = ROOT\n\t\t\t\t\t\t}\n\t\t\t\t\t}")
    mp2, n = re.subn(old, new, mp)
    assert n == 2, f"fascism revanchism: expected 2 matches, got {n}"
    write("common/scripted_progress_bars/vl_progress_bar_inject.txt",
          "# Victoria 3 Lite: generated by tools/gen_vanilla_overrides.py; do not edit by hand.\n"
          "# INJECT of a patched copy of monthly_progress; check with the script profiler that these lines\n"
          "# replace vanilla's 00_victoria_progress_bars.txt:1097 entries.\n\n"
          "INJECT:fascism_progress_bar = {\n\t" + mp2.strip() + "\n}\n")


# ---------------------------------------------------------------- AI regional objectives
def patch_regional_objectives():
    # This folder does not support INJECT/REPLACE, so the whole file is overridden (user decision, 14 Nov 2026).
    rel = "common/ai_regional_objectives/00_ai_regional_objectives.txt"
    text = read(rel)
    s, o, e = find_block(text, "ai_regional_objective_protect_country")
    blk = text[s:e]
    blk = sub_once(r"(possible\s*=\s*\{\s*\n)",
                   r"\1\t\t# Victoria 3 Lite: the target must border a rival, so skip countries with no rivals at all (same result)\n"
                   "\t\tOR = {\n\t\t\tany_rival_country = { count >= 1 }\n\t\t\tany_rivaling_country = { count >= 1 }\n\t\t}\n",
                   blk, "protect possible")
    text = text[:s] + blk + text[e:]
    write(rel, "# Victoria 3 Lite: full copy of vanilla with performance patches (this folder has no INJECT/REPLACE).\n"
               "# Generated by tools/gen_vanilla_overrides.py; do not edit by hand.\n" + text)


if __name__ == "__main__":
    assert GAME and GAME.is_dir(), __doc__
    patch_ai()
    patch_movements()
    patch_ideological()
    patch_fascism()
    patch_regional_objectives()
