import json
from typing import Any

INDENT = 2  # 缩进空格数

def is_scalar(x: Any) -> bool:
    return x is None or isinstance(x, (str, int, float, bool))

def is_1d_scalar_list(arr: list) -> bool:
    return all(is_scalar(x) for x in arr)

def is_2d_scalar_list(arr: list) -> bool:
    return all(isinstance(row, list) and is_1d_scalar_list(row) for row in arr)

def dumps_scalar(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False)

def dumps_1d(arr: list) -> str:
    return "[" + ",".join(dumps_scalar(x) for x in arr) + "]"

def dumps_custom(obj: Any, level: int = 0) -> str:
    sp = " " * (INDENT * level)
    sp_in = " " * (INDENT * (level + 1))

    if is_scalar(obj):
        return dumps_scalar(obj)

    if isinstance(obj, dict):
        if not obj:
            return "{}"
        lines = ["{"]
        items = list(obj.items())
        for i, (k, v) in enumerate(items):
            key_str = json.dumps(k, ensure_ascii=False)
            val_str = dumps_custom(v, level + 1)
            comma = "," if i < len(items) - 1 else ""
            lines.append(f"{sp_in}{key_str}: {val_str}{comma}")
        lines.append(f"{sp}}}")
        return "\n".join(lines)

    if isinstance(obj, list):
        if not obj:
            return "[]"

        if is_1d_scalar_list(obj):          # 一维数组 → 一行
            return dumps_1d(obj)

        if is_2d_scalar_list(obj):          # 二维数组 → 每行一个子数组
            lines = ["["]
            for i, row in enumerate(obj):
                comma = "," if i < len(obj) - 1 else ""
                lines.append(f"{sp_in}{dumps_1d(row)}{comma}")
            lines.append(f"{sp}]")
            return "\n".join(lines)

        # 其他 list（如 actions 列表）→ 每个元素单独一行
        lines = ["["]
        for i, item in enumerate(obj):
            comma = "," if i < len(obj) - 1 else ""
            lines.append(f"{sp_in}{dumps_custom(item, level + 1)}{comma}")
        lines.append(f"{sp}]")
        return "\n".join(lines)

    return json.dumps(obj, ensure_ascii=False)

def main():
    input_path = "output.txt"
    output_path = "output.txt"  # 仍然是 txt

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    text = dumps_custom(data) + "\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    print("Done →", output_path)

if __name__ == "__main__":
    main()
