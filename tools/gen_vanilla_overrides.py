"""Generate Victoria 3 Lite's patched copies of vanilla script.

Usage: python tools/gen_vanilla_overrides.py <path to Victoria 3/game>

Reads the vanilla files, applies text patches and writes:
  common/ai_strategies/00_default_strategy.txt      (full-file override)
  common/political_movements/vl_movement_overrides.txt  (REPLACE: blocks)
  common/script_values/vl_movement_values.txt           (REPLACE: blocks)

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

    header = "# Victoria 3 Lite: full copy of vanilla with performance patches. Generated by tools/gen_vanilla_overrides.py; do not edit by hand.\n"
    write(rel, header + text)


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


if __name__ == "__main__":
    assert GAME and GAME.is_dir(), __doc__
    patch_ai()
    patch_movements()
