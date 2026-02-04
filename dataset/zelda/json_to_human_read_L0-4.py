#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os

LEVELS = range(5)  # L0-L4

def convert_one(level: int, script_dir: str) -> None:
    input_json = f"zelda_dataset_L{level}.json"
    output_txt = f"zelda_dataset_readable_L{level}.txt"

    in_path = os.path.join(script_dir, input_json)
    out_path = os.path.join(script_dir, output_txt)

    if not os.path.exists(in_path):
        print(f"[WARN] {input_json} not found, skipped.")
        return

    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"{input_json} 顶层应为 list")

    with open(out_path, "w", encoding="utf-8") as f:
        for idx, sample in enumerate(data):
            inp = sample.get("input", "")
            out = sample.get("output", "")

            f.write(f"===== Sample {idx} (L{level}) =====\n")
            f.write("INPUT:\n")
            f.write(inp)
            f.write("\n\nOUTPUT:\n")
            f.write(out)
            f.write("\n\n" + "=" * 78 + "\n\n")

    print(f"[INFO] Wrote {out_path}")


def main() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))

    for level in LEVELS:
        convert_one(level, script_dir)


if __name__ == "__main__":
    main()
