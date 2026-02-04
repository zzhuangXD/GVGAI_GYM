import json
import os
from typing import Dict, List, Any, Set, Optional

INPUT_NAME = "output_formatted_L0.txt"
OUTPUT_NAME = "valid_actions_L0.txt"

# Priority when multiple rules match the same action.
# Note: "turn to ..." is handled specially in pick_type().
TYPE_PRIORITY = ["reach goal", "key taken", "score change", "sword used", "sword using", "actual move"]

TURN_ACTIONS = {"ACTION_UP", "ACTION_DOWN", "ACTION_LEFT", "ACTION_RIGHT"}
BASE_TYPES = {"actual move", "sword used", "sword using", "score change", "reach goal", "key taken"}


def action_to_face(action_str: Any) -> Optional[str]:
    """Map action string to facing direction."""
    if not isinstance(action_str, str):
        return None
    mapping = {
        "ACTION_LEFT": "LEFT",
        "ACTION_RIGHT": "RIGHT",
        "ACTION_UP": "UP",
        "ACTION_DOWN": "DOWN",
    }
    return mapping.get(action_str)


def pick_type(types: Set[str]) -> str:
    """
    Pick final valid_action_type from a set of candidates.

    Rules:
    - First apply fixed priority among base types.
    - Then apply "turn to ..." (if present).
    - Finally fallback.
    """
    for t in TYPE_PRIORITY:
        if t in types:
            return t

    turn_types = [x for x in types if isinstance(x, str) and x.startswith("turn to ")]
    if turn_types:
        return sorted(turn_types)[0]

    return next(iter(types))


def write_valid_actions_pretty(data_object: Dict[str, Any], filename: str) -> None:
    with open(filename, "w", encoding="utf-8") as f:
        summary = data_object.get("summary", {})
        dynamic_mapping = data_object.get("dynamic_mapping", {})
        actions = data_object.get("actions", [])

        f.write("{\n")
        f.write(f'  "summary": {json.dumps(summary, ensure_ascii=False)},\n')
        f.write(f'  "dynamic_mapping": {json.dumps(dynamic_mapping, ensure_ascii=False)},\n')
        f.write('  "actions": [\n')

        for i, a in enumerate(actions):
            f.write("    {\n")

            preferred_order = [
                "action_index",
                "valid_action_index",
                "valid_action_type",
                "action",
                "face_to",
                "actual_move",
                "sword_used",
                "score",
                "score_change",
                "with_key",
                "key_at",
                "avatar_position",
                "num_of_enemies",
                "num_of_aliens",
                "sam_present",
                "map",
            ]

            printed = set()

            def write_kv(key, value, comma=True):
                line = f'      "{key}": {json.dumps(value, ensure_ascii=False)}'
                if comma:
                    line += ","
                f.write(line + "\n")

            # Print preferred keys first (map excluded)
            for key in preferred_order:
                if key not in a or key == "map":
                    continue
                printed.add(key)
                write_kv(key, a.get(key), comma=True)

            # Print remaining keys (except map)
            for key in sorted(k for k in a.keys() if k not in printed and k != "map"):
                write_kv(key, a.get(key), comma=True)

            # Print map with each row on its own line (if present)
            if "map" in a:
                f.write('      "map": [\n')
                for r, row in enumerate(a["map"]):
                    f.write(f"        {json.dumps(row, ensure_ascii=False)}")
                    if r < len(a["map"]) - 1:
                        f.write(",")
                    f.write("\n")
                f.write("      ]\n")
            else:
                f.write('      "map": null\n')

            f.write("    }")
            if i < len(actions) - 1:
                f.write(",\n")
            else:
                f.write("\n")

        f.write("  ]\n")
        f.write("}\n")


def add_turn_to_for_x(
    actions: List[Dict[str, Any]],
    reasons: Dict[int, Set[str]],
    x: int,
) -> None:
    """
    For a kept frame X, find the nearest prior frame Y such that:
      1) Y.action in TURN_ACTIONS
      2) Y.face_to != X.face_to
      3) action_to_face(Y.action) == X.face_to
    Then add Y with type: "turn to m" where m is X.face_to.lower()
    """
    def add_reason(pos: int, reason: str):
        reasons.setdefault(pos, set()).add(reason)

    x_face = actions[x].get("face_to")
    if not isinstance(x_face, str) or x_face not in {"UP", "DOWN", "LEFT", "RIGHT"}:
        return

    for y in range(x - 1, -1, -1):
        y_action = actions[y].get("action")
        if y_action not in TURN_ACTIONS:
            continue

        y_face = actions[y].get("face_to")
        if not isinstance(y_face, str):
            continue

        if y_face == x_face:
            continue

        if action_to_face(y_action) != x_face:
            continue

        add_reason(y, f"turn to {x_face.lower()}")
        return


def extract_valid_actions(data: Dict[str, Any]) -> Dict[str, Any]:
    summary = data.get("summary", {})
    dynamic_mapping = data.get("dynamic_mapping", {})
    actions: List[Dict[str, Any]] = data.get("actions", [])

    reasons: Dict[int, Set[str]] = {}

    def add_reason(pos: int, reason: str):
        reasons.setdefault(pos, set()).add(reason)

    n = len(actions)
    if n == 0:
        return {"summary": summary, "dynamic_mapping": dynamic_mapping, "actions": []}

    # ================= A: True movement (current frame vs next frame) =================
    for pos, a in enumerate(actions):
        if pos == n - 1:
            continue  # Last frame has no next frame

        actual_move = a.get("actual_move")
        if actual_move is None or str(actual_move).upper() == "NO MOVE":
            continue

        cur_pos = a.get("avatar_position")
        next_pos = actions[pos + 1].get("avatar_position")

        if cur_pos is None or next_pos is None:
            continue

        if cur_pos != next_pos:
            add_reason(pos, "actual move")

    # ================= C: score change frame itself =================
    score_change_eq2_positions: Set[int] = set()
    for pos, a in enumerate(actions):
        try:
            sc = float(a.get("score_change", 0))
        except:
            continue

        if sc != 0.0:
            add_reason(pos, "score change")

        # For B trigger: only accept score_change == 2
        if sc == 2.0:
            score_change_eq2_positions.add(pos)

    # ================= E: key taken (ONLY depends on with_key and key_at) =================
    # Trigger on transition: prev.with_key == False -> cur.with_key == True
    # Optionally enforce cur.key_at == [-1, -1] to ensure consistency.
    for pos in range(1, n):
        prev = actions[pos - 1]
        cur = actions[pos]

        prev_with = bool(prev.get("with_key", False))
        cur_with = bool(cur.get("with_key", False))

        if (not prev_with) and cur_with:
            # Optional consistency check with key_at:
            cur_key_at = cur.get("key_at")
            if cur_key_at == [-1, -1]:
                add_reason(pos, "key taken")
            else:
                # If you want to accept even when key_at isn't updated, change this to add_reason(pos, "key taken")
                add_reason(pos, "key taken")

    # ================= B: sword used + next 6 frames
    # ONLY if score_change == 2 exists within next 6 frames =================
    for pos, a in enumerate(actions):
        if bool(a.get("sword_used")) is True:
            window_start = pos + 1
            window_end = min(n - 1, pos + 6)

            has_score_change_eq2_in_next_6 = any(
                k in score_change_eq2_positions for k in range(window_start, window_end + 1)
            )
            if not has_score_change_eq2_in_next_6:
                continue

            add_reason(pos, "sword used")
            for k in range(pos + 1, min(n, pos + 7)):  # pos+1 .. pos+6
                add_reason(k, "sword using")

    # ================= D: Keep the last frame of the whole file =================
    last_pos = n - 1
    add_reason(last_pos, "reach goal")

    # ================= Add "turn to m" frames Y for each kept base frame X (A/B/C/D/E) =================
    base_kept_positions = [p for p, rs in reasons.items() if any(t in rs for t in BASE_TYPES)]
    base_kept_positions = sorted(set(base_kept_positions))

    for x in base_kept_positions:
        add_turn_to_for_x(actions, reasons, x)

    # ================= Build output =================
    extracted = []
    valid_counter = 1

    for pos, a in enumerate(actions):
        if pos not in reasons:
            continue

        a2 = dict(a)
        a2["valid_action_index"] = valid_counter
        a2["valid_action_type"] = pick_type(reasons[pos])

        extracted.append(a2)
        valid_counter += 1

    return {
        "summary": summary,
        "dynamic_mapping": dynamic_mapping,
        "actions": extracted,
    }


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, INPUT_NAME)
    output_path = os.path.join(script_dir, OUTPUT_NAME)

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    out = extract_valid_actions(data)
    write_valid_actions_pretty(out, output_path)

    print(f"Extracted {len(out['actions'])} valid actions → {output_path}")


if __name__ == "__main__":
    main()
