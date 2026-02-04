#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from typing import Any, Dict, List, Tuple, Optional

INPUT_FILE = "valid_actions_L4.txt"
OUTPUT_FILE = "zelda_dataset_L4.json"

VGDL_RULES = r"""BasicGame
  SpriteSet
    floor > Immovable img=oryx/floor3 hidden=True
    goal  > Door color=GREEN img=oryx/doorclosed1
    key   > Immovable color=ORANGE img=oryx/key2
    sword > OrientedFlicker limit=5 singleton=True img=oryx/slash1
    movable >
      avatar  > ShootAvatar   stype=sword frameRate=8
        nokey   > img=oryx/swordman1
        withkey > color=ORANGE img=oryx/swordmankey1
      enemy >  
        monsterQuick > RandomNPC cooldown=2 cons=6 img=oryx/bat1
        monsterNormal > RandomNPC cooldown=4 cons=8 img=oryx/spider2
        monsterSlow > RandomNPC cooldown=8 cons=12 img=oryx/scorpion1
      wall > Immovable autotiling=true img=oryx/wall3


  LevelMapping
    g > floor goal
    + > floor key        
    A > floor nokey
    1 > floor monsterQuick
    2 > floor monsterNormal
    3 > floor monsterSlow
    w > wall
    . > floor


  InteractionSet
    movable wall  > stepBack
    nokey goal    > stepBack
    goal withkey  > killSprite scoreChange=1
    enemy sword > killSprite scoreChange=2
    enemy enemy > stepBack
    avatar enemy > killSprite scoreChange=-1
    nokey key     > transformTo stype=withkey scoreChange=1 killSecond=True

  TerminationSet
    SpriteCounter stype=goal   win=True
    SpriteCounter stype=avatar win=False"""

TURN_ACTIONS = {"ACTION_UP", "ACTION_DOWN", "ACTION_LEFT", "ACTION_RIGHT"}


def fmt_pos(p: Any) -> str:
    if isinstance(p, list) and len(p) == 2:
        return f"(row {p[0]}, col {p[1]})"
    return "unknown position"


def action_to_face(action_str: Any) -> Optional[str]:
    if not isinstance(action_str, str):
        return None
    mapping = {
        "ACTION_LEFT": "LEFT",
        "ACTION_RIGHT": "RIGHT",
        "ACTION_UP": "UP",
        "ACTION_DOWN": "DOWN",
    }
    return mapping.get(action_str)


def map_to_text(game_map: List[List[str]]) -> str:
    return "\n".join("".join(row) for row in game_map)


def build_state_description_section(title: str, game_map: List[List[str]], dynamic_mapping: Dict[str, str]) -> str:
    sword_sym = None
    withkey_sym = None
    for k, v in dynamic_mapping.items():
        if isinstance(k, str) and k.lower() == "sword":
            sword_sym = v
        if isinstance(k, str) and k.lower() == "withkey":
            withkey_sym = v

    symbol_to_name = {
        ".": "floor",
        "w": "wall",
        "g": "goal",
        "+": "key",
        "A": "avatar (no key)",
        "1": "enemy (quick)",
        "2": "enemy (normal)",
        "3": "enemy (slow)",
    }
    if sword_sym:
        symbol_to_name[sword_sym] = "sword"
    if withkey_sym:
        symbol_to_name[withkey_sym] = "avatar (with key)"

    lines: List[str] = []
    lines.append(title)
    lines.append(map_to_text(game_map))
    lines.append("")
    lines.append("Each line below shows a non-floor entity at (row, col).")

    entries: List[Tuple[int, int, str, str]] = []
    for r, row in enumerate(game_map):
        for c, cell in enumerate(row):
            if cell == ".":
                continue
            meaning = symbol_to_name.get(cell, f"sprite '{cell}'")
            entries.append((r, c, cell, meaning))

    MAX_ENTRIES = 120
    for r, c, sym, meaning in entries[:MAX_ENTRIES]:
        lines.append(f"row={r}, col={c} -> {sym} ({meaning})")
    if len(entries) > MAX_ENTRIES:
        lines.append(f"... ({len(entries) - MAX_ENTRIES} more entities omitted)")
    return "\n".join(lines)


def main() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    in_path = os.path.join(script_dir, INPUT_FILE)
    out_path = os.path.join(script_dir, OUTPUT_FILE)

    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = data.get("summary", {})
    dynamic_mapping = data.get("dynamic_mapping", {}) or {}
    actions: List[Dict[str, Any]] = data.get("actions", [])

    # Resolve withkey symbol for NL rule text
    withkey_sym = None
    for k, v in dynamic_mapping.items():
        if isinstance(k, str) and k.lower() == "withkey" and isinstance(v, str):
            withkey_sym = v
            break
    if not withkey_sym:
        withkey_sym = "?"

    initial_map = actions[0].get("map", []) if actions else []

    # ---------------- INPUT ----------------
    nl_rules = [
        "=== Game Rules in Natural Language ===",
        "This is a grid-based dungeon game with combat.",
        f"You control an avatar. The avatar has two visual states: without key (A) and with key ({withkey_sym}).",
        "Your task is to take the key, go to the goal, and avoid monsters.",
        "Directional actions can change the facing direction; if the avatar is already facing that direction, it will move one cell in that direction (otherwise it only turns).",
        "You can use ACTION_USE to make the avatar swing a sword to attack enemies in the adjacent cell in the current facing direction. If the attack hits, that enemy is eliminated and the score increases by 2. When the avatar touches the key, it picks up the key and the score increases by 1. When the avatar carrying the key reaches the goal, the score increases by 1 and you win. If the avatar touches an enemy, the avatar is destroyed, the score decreases by 1, and the game is lost.",
    ]

    available_actions = [
        "=== Available Actions ===",
        "0: ACTION_UP",
        "1: ACTION_DOWN",
        "2: ACTION_LEFT",
        "3: ACTION_RIGHT",
        "4: ACTION_USE",
    ]

    mechanics_notice = [
        "=== Important Mechanics Notice ===",
        "The avatar's facing direction matters: the first time you press a direction, the avatar may only turn; it moves only when already facing that direction.",
        "The sword is a short-lived spawned sprite (singleton) and you cannot spawn a new sword immediately after a successful use.",
        "Enemies can block each other (enemy-enemy stepBack) and the avatar cannot move into walls (stepBack).",
    ]

    sprite_mapping_lines = [
        "=== Sprite Mapping ===",
        ". > floor",
        "w > wall",
        "g > goal",
        "+ > key",
        "A > avatar (no key)",
        "1 > monsterQuick",
        "2 > monsterNormal",
        "3 > monsterSlow",
    ]
    if isinstance(dynamic_mapping, dict):
        for k, v in sorted(dynamic_mapping.items(), key=lambda kv: str(kv[1])):
            if isinstance(k, str) and k.lower() == "withkey":
                sprite_mapping_lines.append(f"{v} > avatar (with key)")
            elif isinstance(k, str) and k.lower() == "sword":
                sprite_mapping_lines.append(f"{v} > sword")
            else:
                sprite_mapping_lines.append(f"{v} > {k}")

    parts_input = [
        "=== Game Rules in VGDL ===",
        VGDL_RULES.strip(),
        "",
        "\n".join(nl_rules),
        "",
        "\n".join(available_actions),
        "",
        "\n".join(mechanics_notice),
        "",
        "\n".join(sprite_mapping_lines),
        "",
        build_state_description_section("=== Current State ===", initial_map, dynamic_mapping),
    ]
    input_text = "\n".join(parts_input)

    # ---------------- OUTPUT (COMPRESSED THINK) ----------------
    def get_score(a: Dict[str, Any]) -> float:
        try:
            return float(a.get("score", 0.0))
        except Exception:
            return 0.0

    def get_score_change(a: Dict[str, Any]) -> float:
        try:
            return float(a.get("score_change", 0.0))
        except Exception:
            return 0.0

    def is_turn_type(vtype: Any) -> bool:
        return isinstance(vtype, str) and vtype.startswith("turn to ")

    def compress_steps(actions: List[Dict[str, Any]]) -> List[str]:
        lines: List[str] = []
        n = len(actions)
        i = 0
        step_no = 1

        while i < n:
            a = actions[i]
            act = a.get("action")
            vtype = a.get("valid_action_type", "")

            # ---- Key taken frame: keep it as an explicit action step ----
            # The pickup event happens at this moment (+1). The action itself may be a turn/no-op.
            if vtype == "key taken":
                pos = a.get("avatar_position")
                lines.append(
                    f"Action {step_no} is {act}: Avatar at {fmt_pos(pos)}. "
                    "The key is obtained and the avatar gains 1 point. This action itself does not change the game state."
                )
                i += 1
                step_no += 1
                continue

            # ---- Sword used block compression ----
            if vtype == "sword used" and act == "ACTION_USE":
                window_end = min(n - 1, i + 6)
                window = actions[i + 1: window_end + 1]

                critical = {"key taken", "reach goal"}
                if any(w.get("valid_action_type") in critical for w in window):
                    # Fall back to per-action printing if critical event appears (rare).
                    pass
                else:
                    face = a.get("face_to")
                    pos = a.get("avatar_position")

                    no_effect = []
                    for j, w in enumerate(window, start=i + 2):  # step numbers
                        if get_score_change(w) == 0.0:
                            no_effect.append(j)

                    lines.append(
                        f"Action {step_no} is ACTION_USE: Avatar at {fmt_pos(pos)}; using the sword towards {face}. "
                        "An enemy is eliminated and the score increases by 2."
                    )

                    if no_effect:
                        lines.append(
                            "Actions " + ", ".join(str(x) for x in no_effect)
                            + " do not change the game state, but the attack remains active during this window."
                        )

                    consumed = 1 + len(window)
                    i += consumed
                    step_no += consumed
                    continue

            # ---- Directional run compression ----
            if act in TURN_ACTIONS:
                dir_act = act
                j = i
                while j + 1 < n and actions[j + 1].get("action") == dir_act and actions[j + 1].get(
                        "action") in TURN_ACTIONS:
                    if actions[j + 1].get("valid_action_type") == "key taken":
                        break
                    j += 1

                moved_count = 0
                turned = False
                reached_goal = False

                for t in range(i, j + 1):
                    vt = actions[t].get("valid_action_type", "")
                    if vt == "actual move":
                        moved_count += 1
                    if is_turn_type(vt):
                        turned = True
                    if vt == "reach goal":
                        reached_goal = True
                        moved_count += 1  # treat reaching goal as final move

                start_pos = actions[i].get("avatar_position")

                last_pos = actions[j].get("avatar_position")
                dir_name = action_to_face(dir_act) or dir_act.replace("ACTION_", "")

                detail = []
                if turned:
                    detail.append(f"turned to face {dir_name}")
                if moved_count > 0:
                    detail.append(f"moved {dir_name} {moved_count} time(s)")
                if reached_goal:
                    detail.append("reached the goal and won the game")

                # If the very next frame is a key taken event, mention it as the RESULT of this movement,
                # but do NOT swallow the key-taken frame (it will still be printed as its own step).
                if j + 1 < n and actions[j + 1].get("valid_action_type") == "key taken":
                    key_pos = actions[j].get("key_at")
                    if isinstance(key_pos, list) and len(key_pos) == 2:
                        detail.append(f"picked up the key at {fmt_pos(key_pos)} and gained 1 point")
                    else:
                        detail.append("picked up the key and gained 1 point")

                # Build step numbers (1-based) for this directional group only.
                base_len = (j - i + 1)
                step_nums = list(range(step_no, step_no + base_len))
                step_str = ", ".join(str(x) for x in step_nums)
                line = f"Action {step_str} are {dir_act}: Avatar at {fmt_pos(start_pos)}."
                if detail:
                    line += " It " + ", ".join(detail) + "."
                lines.append(line)

                consumed = (j - i + 1)
                i += consumed
                step_no += consumed
                continue

            # ---- Fallback: concise single line ----
            pos = a.get("avatar_position")
            sc = get_score_change(a)
            extra = []
            if vtype:
                extra.append(str(vtype))
            if sc != 0.0:
                extra.append(f"score_change={sc}")
            extra_str = "; ".join(extra) if extra else "important"
            lines.append(f"Action {step_no} is {act}: {extra_str}. Avatar at {fmt_pos(pos)}.")
            i += 1
            step_no += 1

        return lines

    start_pos = actions[0].get("avatar_position") if actions else None
    end_pos = actions[-1].get("avatar_position") if actions else None

    last_score = get_score(actions[-1]) if actions else 0.0
    final_score = last_score + 1  # +1 for goal reward not yet reflected

    header_line = (
        f"The avatar starts at {fmt_pos(start_pos)} and ends at {fmt_pos(end_pos)} "
        f"one step before it reaches the goal with key. The final score is {final_score}."
    )

    step_lines = compress_steps(actions)

    answer_actions = [a.get("action") for a in actions]

    think_parts = [
        "<think>",
        header_line,
        "The agent executes the following (compressed) action steps:",
        *step_lines,
        "</think><answer>",
        json.dumps(answer_actions, ensure_ascii=False),
        "</answer>",
    ]
    output_text = "\n".join(think_parts)

    dataset = [{"input": input_text, "output": output_text}]

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"✅ Wrote {out_path} with {len(dataset)} sample(s).")


if __name__ == "__main__":
    main()
