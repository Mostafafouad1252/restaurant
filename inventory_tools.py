from __future__ import annotations

import argparse
import json
from pathlib import Path


def data_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "inventory.json"


def load_inventory(p: Path) -> dict:
    if not p.exists():
        return {"cars": []}
    raw = p.read_text(encoding="utf-8").strip()
    if not raw:
        return {"cars": []}
    parsed = json.loads(raw)
    cars = parsed.get("cars", [])
    return {"cars": cars if isinstance(cars, list) else []}


def cmd_validate(p: Path) -> int:
    inv = load_inventory(p)
    errors: list[str] = []
    for i, c in enumerate(inv["cars"]):
        if not isinstance(c, dict):
            errors.append(f"cars[{i}] is not an object")
            continue
        for k in ("id", "type", "color", "price"):
            if k not in c:
                errors.append(f"cars[{i}] missing '{k}'")
        price = c.get("price")
        try:
            price_f = float(price)
            if price_f < 0:
                errors.append(f"cars[{i}] price is negative")
        except Exception:
            errors.append(f"cars[{i}] price is not a number")

    if errors:
        print("INVALID inventory.json")
        for e in errors:
            print(f"- {e}")
        return 1
    print("OK inventory.json")
    return 0


def cmd_summary(p: Path) -> int:
    inv = load_inventory(p)
    cars = inv["cars"]
    total = len(cars)
    by_type: dict[str, int] = {}
    by_color: dict[str, int] = {}
    prices: list[float] = []

    for c in cars:
        if not isinstance(c, dict):
            continue
        by_type[str(c.get("type", "Unknown"))] = by_type.get(str(c.get("type", "Unknown")), 0) + 1
        by_color[str(c.get("color", "Unknown"))] = by_color.get(str(c.get("color", "Unknown")), 0) + 1
        try:
            prices.append(float(c.get("price")))
        except Exception:
            pass

    print(f"Cars: {total}")
    if prices:
        print(f"Min price: {min(prices):,.2f}")
        print(f"Max price: {max(prices):,.2f}")
        print(f"Avg price: {sum(prices)/len(prices):,.2f}")

    if by_type:
        print("\nBy type:")
        for k in sorted(by_type):
            print(f"- {k}: {by_type[k]}")

    if by_color:
        print("\nBy color:")
        for k in sorted(by_color):
            print(f"- {k}: {by_color[k]}")

    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Python tools for data/inventory.json")
    parser.add_argument("--path", default=str(data_path()), help="Path to inventory.json")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate", help="Validate inventory.json schema")
    sub.add_parser("summary", help="Print inventory summary")

    args = parser.parse_args(argv)
    p = Path(args.path)

    if args.cmd == "validate":
        return cmd_validate(p)
    if args.cmd == "summary":
        return cmd_summary(p)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))

