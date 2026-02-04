import json
from collections import OrderedDict
from typing import Any, Dict, List, Optional

INPUT_FILE = "output_L0.txt"
OUTPUT_FILE = "output_formatted_L0.txt"

Coord = List[int]  # [row, col], 0-based indexing


# =========================
# Enrichment helpers
# =========================
def find_first(grid: List[List[Any]], target: Any) -> Coord:
    """Return first [row, col] of target in grid, else [-1, -1]."""
    for r, row in enumerate(grid):
        for c, v in enumerate(row):
            if v == target:
                return [r, c]
    return [-1, -1]


def count_enemies(grid: List[List[Any]]) -> int:
    """Count enemy symbols: '1', '2', '3'."""
    enemies = {"1", "2", "3"}
    return sum(v in enemies for row in grid for v in row)


def get_dynamic_symbol(dynamic_mapping: Any, key: str) -> Optional[str]:
    """
    Fetch symbol from dynamic_mapping with case-insensitive key match.
    Example: withkey / withKey / WITHKEY
    """
    if not isinstance(dynamic_mapping, dict):
        return None

    if key in dynamic_mapping and isinstance(dynamic_mapping[key], str):
        return dynamic_mapping[key]

    lk = key.lower()
    for k, v in dynamic_mapping.items():
        if isinstance(k, str) and k.lower() == lk and isinstance(v, str):
            return v
    return None


def get_initial_key_at(actions: List[Dict[str, Any]]) -> Coord:
    """
    Compute the 'true' key location from the first frame (prefer action_index == 1).
    If '+' is not found there, fall back to the very first action.
    """
    if not actions:
        return [-1, -1]

    preferred = None
    for act in actions:
        if isinstance(act, dict) and act.get("action_index") == 1:
            preferred = act
            break

    if preferred is not None:
        grid = preferred.get("map", [])
        pos = find_first(grid, "+")
        if pos != [-1, -1]:
            return pos

    grid0 = actions[0].get("map", [])
    return find_first(grid0, "+")


def to_float_score(x: Any) -> float:
    """Safely convert score to float; default to 0.0 if missing/invalid."""
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def action_to_face(action_str: Any) -> Optional[str]:
    """
    Map an action string to a facing direction.
    Facing changes are applied to the NEXT frame.
    """
    if not isinstance(action_str, str):
        return None
    mapping = {
        "ACTION_LEFT": "LEFT",
        "ACTION_RIGHT": "RIGHT",
        "ACTION_UP": "UP",
        "ACTION_DOWN": "DOWN",
    }
    return mapping.get(action_str)


def annotate_sword_used(actions: List[OrderedDict], sword_sym: Optional[str]) -> None:
    """
    Second pass: add 'sword_used' field to each action.

    Rule:
    - If sword_sym is None: all sword_used = False.
    - Otherwise, scan in order with a cooldown window.
      When we see an ACTION_USE at index i:
        - If i+1 < len(actions) AND next map contains sword_sym:
            actions[i]["sword_used"] = True
            cooldown = 6  (skip detection for the next 6 actions)
        - Else:
            actions[i]["sword_used"] = False
      While cooldown > 0:
        - actions[i]["sword_used"] = False
        - cooldown -= 1
    """
    if not sword_sym:
        for act in actions:
            act["sword_used"] = False
        return

    cooldown = 0
    n = len(actions)

    for i, act in enumerate(actions):
        # If we are inside the 6-frame window after a real sword spawn,
        # no new valid attacks can be triggered due to singleton.
        if cooldown > 0:
            act["sword_used"] = False
            cooldown -= 1
            continue

        used = False
        if act.get("action") == "ACTION_USE":
            # Need a next frame to see whether sword symbol appears
            if i + 1 < n:
                next_map = actions[i + 1].get("map", [])
                # Check whether sword_sym appears in the next map
                found = any(
                    any(cell == sword_sym for cell in row)
                    for row in next_map
                )
                if found:
                    used = True
                    cooldown = 6  # skip next 6 actions from detection

        act["sword_used"] = used


def enrich_actions(data: Dict[str, Any]) -> Dict[str, Any]:
    """Add computed fields to each action."""
    dynamic_mapping = data.get("dynamic_mapping", {}) or {}

    sword_sym = get_dynamic_symbol(dynamic_mapping, "sword")
    withkey_sym = get_dynamic_symbol(dynamic_mapping, "withkey")

    actions = data.get("actions", [])
    initial_key_at = get_initial_key_at(actions)

    new_actions: List[OrderedDict] = []

    prev_score: Optional[float] = None
    prev_action_str: Optional[str] = None

    # face_to is a state. First frame defaults to UP.
    prev_face_to: str = "UP"

    for i, act in enumerate(actions):
        grid = act.get("map", [])

        # Determine face_to for current frame based on PREVIOUS frame action
        if i == 0 or act.get("action_index") == 1:
            face_to = "UP"
        else:
            new_face = action_to_face(prev_action_str)
            face_to = new_face if new_face is not None else prev_face_to

        # Score and score_change
        cur_score = to_float_score(act.get("score", 0.0))
        act_idx = act.get("action_index", None)

        if act_idx == 1 or i == 0 or prev_score is None:
            score_change = 0.0
        else:
            score_change = cur_score - prev_score
        prev_score = cur_score

        # Other fields
        num_of_enemies = count_enemies(grid)
        goal_at = find_first(grid, "g")
        sword_at = find_first(grid, sword_sym) if sword_sym else [-1, -1]

        # Determine with_key from the withkey symbol existence in the current map
        withkey_at = find_first(grid, withkey_sym) if withkey_sym else [-1, -1]
        with_key = (withkey_at != [-1, -1])

        # Key position rule:
        # - While with_key is False, key_at stays the same as the first frame (action_index == 1).
        # - Once with_key is True, key_at must be [-1, -1].
        key_at = [-1, -1] if with_key else initial_key_at

        # Avatar_position rule:
        # - If with_key is True, Avatar_position is the withkey symbol location.
        # - Otherwise, Avatar_position is the 'A' location.
        avatar_pos = withkey_at if with_key else find_first(grid, "A")

        # ---- actual_move: only if face_to matches the move direction ----
        action_str = act.get("action")
        move_dir = action_to_face(action_str)
        if move_dir is not None and move_dir == face_to:
            actual_move = move_dir
        else:
            actual_move = "NO MOVE"

        # Keep original fields (except map, appended last), then append new fields, then map
        out_act: OrderedDict[str, Any] = OrderedDict()
        for k in act.keys():
            if k != "map":
                out_act[k] = act[k]

        out_act["face_to"] = face_to
        out_act["actual_move"] = actual_move  # 新字段
        # sword_used 先留给二次遍历填充
        out_act["score"] = cur_score
        out_act["score_change"] = score_change
        out_act["num_of_enemies"] = num_of_enemies
        out_act["key_at"] = key_at
        out_act["goal_at"] = goal_at
        out_act["sword_at"] = sword_at
        out_act["with_key"] = with_key
        out_act["avatar_position"] = avatar_pos
        out_act["map"] = grid  # map moved to the end

        new_actions.append(out_act)

        # Update previous-state trackers for next iteration
        prev_action_str = action_str if isinstance(act, dict) else None
        prev_face_to = face_to

    # ---- second pass: fill sword_used ----
    annotate_sword_used(new_actions, sword_sym)

    out_data = OrderedDict()
    if "summary" in data:
        out_data["summary"] = data["summary"]
    if "dynamic_mapping" in data:
        out_data["dynamic_mapping"] = data["dynamic_mapping"]
    out_data["actions"] = new_actions

    return out_data


# =========================
# Formatting helpers
# =========================
def format_1d_array(arr: List[Any]) -> str:
    return json.dumps(arr, ensure_ascii=False)


def format_2d_array(arr2d: List[List[Any]], indent: str) -> str:
    """Format 2D array so each row is on its own line."""
    inner_indent = indent + "  "
    lines = ["["]
    for i, row in enumerate(arr2d):
        row_str = format_1d_array(row)
        comma = "," if i != len(arr2d) - 1 else ""
        lines.append(f"{inner_indent}{row_str}{comma}")
    lines.append(f"{indent}]")
    return "\n".join(lines)


def format_action(action_obj: dict, indent: str) -> str:
    """Format one action block with custom field order (map is last)."""
    fields_order = [
        "action_index",
        "action",
        "face_to",
        "actual_move",
        "sword_used",
        "score",
        "score_change",
        "num_of_enemies",
        "key_at",
        "goal_at",
        "sword_at",
        "with_key",
        "avatar_position",
        "map",
    ]

    lines = [f"{indent}{{"]
    for idx, k in enumerate(fields_order):
        if k not in action_obj:
            continue

        key_json = json.dumps(k, ensure_ascii=False)
        prefix = f"{indent}  {key_json}: "

        if k == "map":
            v = action_obj[k]
            v_str = format_2d_array(v, indent + "  ")
            line = prefix + v_str
        else:
            line = prefix + json.dumps(action_obj[k], ensure_ascii=False)

        remaining = [kk for kk in fields_order[idx + 1:] if kk in action_obj]
        comma = "," if remaining else ""
        lines.append(line + comma)

    lines.append(f"{indent}}}")
    return "\n".join(lines)


def format_root(obj: dict) -> str:
    indent1 = "  "
    indent2 = "    "

    lines = ["{"]

    if "summary" in obj:
        lines.append(
            f'{indent1}"summary": {json.dumps(obj["summary"], ensure_ascii=False)},'
        )

    if "dynamic_mapping" in obj:
        lines.append(
            f'{indent1}"dynamic_mapping": {json.dumps(obj["dynamic_mapping"], ensure_ascii=False)},'
        )

    if "actions" in obj:
        lines.append(f'{indent1}"actions": [')
        actions = obj["actions"]
        for i, act in enumerate(actions):
            act_str = format_action(act, indent2)
            comma = "," if i != len(actions) - 1 else ""
            lines.append(act_str + comma)
        lines.append(f"{indent1}]")

    lines.append("}")
    return "\n".join(lines)


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    enriched = enrich_actions(data)
    out = format_root(enriched)

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(out + "\n")

    print(f"✅ Generated {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
