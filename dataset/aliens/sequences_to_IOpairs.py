#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from typing import Any, Dict, List, Tuple, Optional

INPUT_FILE = "action_sequences_L4.json"
OUTPUT_FILE = "aliens_dataset_L4.json"


def load_data(path: str) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    返回 (sequences, dynamic_mapping)
    - sequences: list of dict
    - dynamic_mapping: dict[str, str]，例如 {"alienBlue": "B", "bomb": "D", "sam": "C"}
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    dynamic_mapping: Dict[str, str] = {}

    if isinstance(data, dict):
        # summary / dynamic_mapping / sequences
        if "sequences" in data:
            sequences = data["sequences"]
        else:
            # 容错：dict 中找一个 list-of-dicts 当做 sequences
            sequences = None
            for v in data.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    sequences = v
                    break
            if sequences is None:
                raise ValueError("无法在 dict 里找到 'sequences' 列表，请检查文件结构。")

        if isinstance(data.get("dynamic_mapping"), dict):
            dynamic_mapping = data["dynamic_mapping"]
    elif isinstance(data, list):
        # 旧格式：顶层就是 sequences
        sequences = data
    else:
        raise ValueError("action_sequences.json 顶层既不是 list 也不是 dict。")

    return sequences, dynamic_mapping


def find_avatar_position(game_map: List[List[str]]) -> Optional[Tuple[int, int]]:
    """找到 'A' 的 (row, col)，0-based；找不到则返回 None。"""
    for r, row in enumerate(game_map):
        for c, cell in enumerate(row):
            if cell == "A":
                return r, c
    return None


def map_to_text(game_map: List[List[str]]) -> str:
    """把 2D map 转成多行字符串。"""
    return "\n".join("".join(row) for row in game_map)


def format_score(score: Any) -> str:
    if isinstance(score, (int, float)):
        if isinstance(score, float) and score.is_integer():
            return str(int(score))
        return str(score)
    return str(score)


def build_state_description_section(
    title: str,
    game_map: List[List[str]],
    dynamic_mapping: Dict[str, str],
    add_avatar_sam_note: bool = True,
) -> List[str]:
    """
    构造一个状态描述段落：

    === <title> ===
    <ASCII map>

    Each line below shows a non-background entity at (row, col).
    row=..., col=... -> X (meaning)
    ...
    [可选] Note that A (avatar) shares its position with C (sam) at row=..., col=...

    用于：
    - input 里的 "=== Current State ==="
    - output <think> 末尾的 "=== State When Firing The Missile ==="
    """
    lines: List[str] = []

    # 1) 标题 + 符号地图
    map_text = map_to_text(game_map)
    lines.append(title)
    lines.append(map_text)
    lines.append("")  # 与下面自然语言描述空一行

    # 2) symbol -> 语义名
    symbol_to_name: Dict[str, str] = {
        ".": "background",
        "0": "base",
        "A": "avatar",
    }
    for sprite_name, symbol in dynamic_mapping.items():
        symbol_to_name.setdefault(symbol, sprite_name)

    # 3) 列出所有非背景实体
    entries: List[Tuple[int, int, str, str]] = []
    for r, row in enumerate(game_map):
        for c, cell in enumerate(row):
            if cell in (".", "", None):
                continue
            meaning = symbol_to_name.get(cell, f"sprite '{cell}'")
            entries.append((r, c, cell, meaning))

    MAX_ENTRIES = 80

    lines.append("Each line below shows a non-background entity at (row, col).")
    for (r, c, sym, meaning) in entries[:MAX_ENTRIES]:
        lines.append(f"row={r}, col={c} -> {sym} ({meaning})")

    if len(entries) > MAX_ENTRIES:
        lines.append(f"... ({len(entries) - MAX_ENTRIES} more entities omitted)")

    # 4) 如果 map 中没有 'A'，补充 A 和 sam 重合的说明
    if add_avatar_sam_note:
        has_avatar = any("A" in row for row in ["".join(r) for r in game_map])
        if not has_avatar:
            sam_symbol = dynamic_mapping.get("sam")
            if sam_symbol:
                found_sam_pos: Optional[Tuple[int, int]] = None
                for r, row in enumerate(game_map):
                    for c, cell in enumerate(row):
                        if cell == sam_symbol:
                            found_sam_pos = (r, c)
                            break
                    if found_sam_pos is not None:
                        break
                if found_sam_pos is not None:
                    r, c = found_sam_pos
                    lines.append(
                        f"Note that A (avatar) shares its position with {sam_symbol} (sam) at row={r}, col={c}."
                    )

    return lines


# ---------- 构造一个样本的 input / output ----------

def build_input_from_sequence(
    seq: Dict[str, Any],
    vgdl_rules_text: str,
    dynamic_mapping: Dict[str, str],
) -> str:
    """
    构造 input 字符串，结构为：

    === Game Rules in VGDL ===
    ...

    === Game Rules in Natural Language ===
    ...

    === Available Actions ===
    ...

    === Important Mechanics Notice ===
    ...

    === Sprite Mapping ===
    ...

    === Current State ===
    <ASCII map>
    Each line below shows ...
    row=..., col=... -> X (meaning)
    ...
    [Optional] Note that A (avatar) shares its position with C (sam) at ...
    """
    initial_map = seq.get("initial_map", [])
    init_num_aliens = seq.get("init_num_of_aliens", 0)
    score_change = seq.get("score_change", 0)
    score_str = format_score(score_change)

    init_pos = seq.get("init_avatar_pos", None)
    avatar_r, avatar_c = (init_pos if init_pos and len(init_pos) == 2 else (None, None))

    actions = seq.get("action_sequence", [])
    num_steps = len(actions)

    # 行列仅用于 Game Rules 里提到“grid size”的那一部分（如果需要用的话）
    rows = len(initial_map)
    cols = len(initial_map[0]) if rows > 0 else 0

    # === Game Rules in VGDL ===
    vgdl_clean = vgdl_rules_text.strip() if vgdl_rules_text is not None else "VGDL rules for Aliens are unavailable."
    part_vgdl = [
        "=== Game Rules in VGDL ===",
        vgdl_clean,
    ]

    # === Game Rules in Natural Language ===
    part_nl_rules = [
        "=== Game Rules in Natural Language ===",
        "This is a fixed-shooter arcade game.",
        "You control a spaceship at the bottom of the screen and must shoot down alien ships.",
        "Aliens march in rows, sweeping left and right across the grid; whenever they reach the edge, they drop down closer to the avatar, reverse direction, and keep moving while periodically dropping bombs that can destroy the avatar or bases.",
        "You win by eliminating all aliens. You lose if the avatar is destroyed.",
    ]

    # === Available Actions ===
    part_actions = [
        "=== Available Actions ===",
        "0: ACTION_LEFT",
        "1: ACTION_RIGHT",
        "2: ACTION_USE",
    ]

    # === Important Mechanics Notice ===
    part_notice = [
        "=== Important Mechanics Notice ===",
        "Sam, the bullet fired by the avatar travels straight upward from the avatar's current column.",
        "Sam and bombs can destroy bases as well as alien ships.",
        "Each alien ship occupies at most a 2x2 block of tiles on the grid.",
        "The avatar moves horizontally along the bottom row and must avoid bombs while shooting aliens.",
    ]

    # === Sprite Mapping ===

    part_mapping = [
        "=== Sprite Mapping ===",
        ". > background",
        "0 > base",
        "A > avatar",
    ]
    # dynamic_mapping: spriteName -> symbol，例如 {"alienBlue": "B", "bomb": "D", "sam": "C"}
    # 这里输出 symbol > spriteName
    for sprite_name, symbol in sorted(dynamic_mapping.items(), key=lambda kv: kv[1]):
        part_mapping.append(f"{symbol} > {sprite_name}")

    # === Current State ===
    part_state = build_state_description_section(
        title="=== Current State ===",
        game_map=initial_map,
        dynamic_mapping=dynamic_mapping,
        add_avatar_sam_note=True,
    )

    # ---------- 拼接 ----------
    sections = [
        "\n".join(part_vgdl),
        "\n".join(part_nl_rules),
        "\n".join(part_actions),
        "\n".join(part_notice),
        "\n".join(part_mapping),
        "\n".join(part_state),
    ]

    input_text = "\n\n".join(sections)
    return input_text


def build_output_from_sequence(
    seq: Dict[str, Any],
    dynamic_mapping: Dict[str, str],
) -> str:

    init_num_aliens = seq.get("init_num_of_aliens", 0)
    end_num_aliens = seq.get("end_num_of_aliens", 0)
    score_change = seq.get("score_change", 0)
    score_str = format_score(score_change)

    init_pos = seq.get("init_avatar_pos", None)
    avatar_r, avatar_c = (init_pos if init_pos and len(init_pos) == 2 else (None, None))

    end_pos = seq.get("end_avatar_pos", None)
    end_avatar_r, end_avatar_c = (end_pos if end_pos and len(end_pos) == 2 else (None, None))

    base_destroyed = seq.get("base_destroyed", 0)
    alien_eliminated = seq.get("alien_eliminated", 0)

    actions = seq.get("action_sequence", [])
    num_steps = len(actions)

    end_map = seq.get("end_map", [])

    think_lines: List[str] = []

    if avatar_r is not None and avatar_c is not None:
        think_lines.append(
            f"The avatar starts at row {avatar_r}, column {avatar_c} with {init_num_aliens} alien(s) remaining."
        )
    else:
        think_lines.append(
            f"The avatar position is not explicitly visible, but there are {init_num_aliens} alien(s) remaining at the start."
        )

    think_lines.append(
        f"To win the game, the agent decides to execute the following {num_steps} action step(s)."
    )

    # 逐步解释每个 action
    for i, act in enumerate(actions, start=1):
        if act == "ACTION_LEFT":
            think_lines.append(
                f"Action {i} is ACTION_LEFT, moving one cell left to adjust the avatar's position before firing."
            )
        elif act == "ACTION_RIGHT":
            think_lines.append(
                f"Action {i} is ACTION_RIGHT, moving one cell right to adjust the avatar's position before firing."
            )
        elif act == "ACTION_USE":
            # 非最后一步：尝试发射，但 sam 是 singleton
            if i < num_steps:
                think_lines.append(
                    f"Action {i} is ACTION_USE, which tries to fire a missile in the current column, "
                    f"but because the missile 'sam' is singleton, this attempt does not create a new missile."
                )
            else:
                # 最后一发真正生效的子弹
                think_lines.append(
                    f"Action {i} is ACTION_USE, firing a missile 'sam' from the current position. "
                    f"This missile will eliminate {alien_eliminated} alien(s) and destroy {base_destroyed} base tile(s), "
                    f"the score is expected to be increased by {score_str}."
                )
        else:
            think_lines.append(
                f"Action {i} is {act}, which affects the state according to the game rules."
            )

    # 末尾追加“发射子弹时的状态”
    if end_map:
        think_lines.append("")
        state_fire_section = build_state_description_section(
            title="=== State When Firing The Missile ===",
            game_map=end_map,
            dynamic_mapping=dynamic_mapping,
            add_avatar_sam_note=True,
        )
        think_lines.extend(state_fire_section)
        if end_avatar_r is not None and end_avatar_c is not None:
            think_lines.append(
                f"When the missile is fired, the avatar is at row {end_avatar_r}, column {end_avatar_c}, "
                f"with {end_num_aliens} alien(s) remaining."
            )
        else:
            think_lines.append(
                f"When the missile is fired, there are {end_num_aliens} alien(s) remaining, "
                f"but the avatar's exact grid position is not explicitly visible."
            )

    # 拼成 <think>...</think><answer>...</answer>
    think_text = "<think>\n" + "\n".join(think_lines) + "\n</think>"
    actions_str = json.dumps(actions, ensure_ascii=False)
    answer_text = "<answer>\n" + actions_str + "\n</answer>"

    return think_text + answer_text


def build_sample(
    seq: Dict[str, Any],
    vgdl_rules_text: str,
    dynamic_mapping: Dict[str, str],
) -> Dict[str, str]:
    return {
        "input": build_input_from_sequence(seq, vgdl_rules_text, dynamic_mapping),
        "output": build_output_from_sequence(seq, dynamic_mapping),
    }


def main() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. 读取 action_sequences.json
    in_path = os.path.join(script_dir, INPUT_FILE)

    # 2. 定位 aliens.txt：../../gym_gvgai/envs/games/aliens_v0/aliens.txt
    vgdl_path = os.path.normpath(
        os.path.join(
            script_dir,
            "..", "..",
            "gym_gvgai", "envs", "games", "aliens_v0", "aliens.txt",
        )
    )

    try:
        with open(vgdl_path, "r", encoding="utf-8") as f_v:
            vgdl_rules_text = f_v.read()
    except FileNotFoundError:
        print(f"[WARN] Could not find aliens VGDL file at: {vgdl_path}")
        vgdl_rules_text = "VGDL rules for Aliens are unavailable."

    sequences, dynamic_mapping = load_data(in_path)

    samples = [
        build_sample(seq, vgdl_rules_text, dynamic_mapping)
        for seq in sequences
    ]

    out_path = os.path.join(script_dir, OUTPUT_FILE)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, ensure_ascii=False, indent=2)

    print(f"[INFO] Loaded VGDL rules from: {vgdl_path}")
    print(f"[INFO] dynamic_mapping keys: {list(dynamic_mapping.keys())}")
    print(f"[INFO] Wrote {len(samples)} pairs to {out_path}")


if __name__ == "__main__":
    main()
