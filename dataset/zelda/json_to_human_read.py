#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from typing import List, Dict, Any

INPUT_JSON = "zelda_dataset_L0.json"
OUTPUT_TXT = "zelda_dataset_readable_L0.txt"


def main() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    in_path = os.path.join(script_dir, INPUT_JSON)
    out_path = os.path.join(script_dir, OUTPUT_TXT)

    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("输入 JSON 顶层应为一个样本列表(list)。")

    with open(out_path, "w", encoding="utf-8") as f:
        for idx, sample in enumerate(data):
            inp = sample.get("input", "")
            out = sample.get("output", "")

            f.write(f"===== Sample {idx} =====\n")
            f.write("INPUT:\n")
            f.write(inp)
            f.write("\n\nOUTPUT:\n")
            f.write(out)
            f.write("\n\n" + "=" * 78 + "\n\n")

    print(f"[INFO] Wrote human-readable dataset to {out_path}")


if __name__ == "__main__":
    main()
