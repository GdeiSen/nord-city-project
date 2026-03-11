#!/usr/bin/env python3
"""
Audit localization keys usage in bot_service.

Collects keys from:
- Python source code (`get_text("key")`, `create_keyboard([...])`)
- Dynamic dialog assets (`assets/*.json`, all `text` fields)

Compares against `locales/localisation_ru.json` and prints:
- missing keys (used but absent in localization)
- unused keys (present in localization but never referenced)
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any

GET_TEXT_PATTERN = re.compile(r'get_text\(\s*["\']([^"\']+)["\']')


def _collect_from_keyboard_arg(node: ast.AST, sink: set[str]) -> None:
    if isinstance(node, ast.Tuple):
        if node.elts and isinstance(node.elts[0], ast.Constant) and isinstance(node.elts[0].value, str):
            sink.add(node.elts[0].value)
    if isinstance(node, (ast.List, ast.Tuple)):
        for child in node.elts:
            _collect_from_keyboard_arg(child, sink)
        return
    if isinstance(node, ast.Dict):
        for child in list(node.keys) + list(node.values):
            if child is not None:
                _collect_from_keyboard_arg(child, sink)


def collect_used_keys_from_python(src_root: Path) -> set[str]:
    used: set[str] = set()

    for py_file in src_root.rglob("*.py"):
        if py_file.name == "localization_audit.py":
            continue
        text = py_file.read_text(encoding="utf-8", errors="ignore")

        for match in GET_TEXT_PATTERN.finditer(text):
            used.add(match.group(1))

        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue

        class Visitor(ast.NodeVisitor):
            def visit_Call(self, node: ast.Call) -> None:
                func_name: str | None = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name == "get_text" and node.args:
                    first = node.args[0]
                    if isinstance(first, ast.Constant) and isinstance(first.value, str):
                        used.add(first.value)

                if func_name == "create_keyboard" and node.args:
                    _collect_from_keyboard_arg(node.args[0], used)

                self.generic_visit(node)

        Visitor().visit(tree)

    return used


def _walk_json_for_text(value: Any, sink: set[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "text" and isinstance(child, str):
                sink.add(child)
            _walk_json_for_text(child, sink)
        return
    if isinstance(value, list):
        for child in value:
            _walk_json_for_text(child, sink)


def collect_used_keys_from_assets(assets_dir: Path) -> set[str]:
    used: set[str] = set()
    if not assets_dir.exists():
        return used

    for json_file in sorted(assets_dir.glob("*.json")):
        try:
            payload = json.loads(json_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        _walk_json_for_text(payload, used)
    return used


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit bot localization keys usage.")
    parser.add_argument(
        "--src-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Path to bot_service/src directory.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    args = parser.parse_args()

    src_root = Path(args.src_root).resolve()
    locale_path = src_root / "locales" / "localisation_ru.json"
    assets_dir = src_root / "assets"

    data = json.loads(locale_path.read_text(encoding="utf-8"))
    locale_data = data.get("RU", {})
    if not isinstance(locale_data, dict):
        raise ValueError("`RU` section in localization file must be an object.")

    all_keys = set(locale_data.keys())
    used_keys = collect_used_keys_from_python(src_root) | collect_used_keys_from_assets(assets_dir)
    used_existing = sorted(all_keys & used_keys)
    unused_keys = sorted(all_keys - used_keys)
    missing_keys = sorted(used_keys - all_keys)

    result = {
        "total_keys": len(all_keys),
        "used_keys": len(used_existing),
        "unused_keys": len(unused_keys),
        "missing_keys": len(missing_keys),
        "unused": unused_keys,
        "missing": missing_keys,
    }

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(f"Source: {src_root}")
    print(f"Localization: {locale_path}")
    print(f"Total keys: {result['total_keys']}")
    print(f"Used keys: {result['used_keys']}")
    print(f"Unused keys: {result['unused_keys']}")
    print(f"Missing keys: {result['missing_keys']}")

    if missing_keys:
        print("\nMissing keys (referenced in code/assets, absent in localization):")
        for key in missing_keys:
            print(f"- {key}")

    if unused_keys:
        print("\nUnused keys (present in localization, not referenced):")
        for key in unused_keys:
            print(f"- {key}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
