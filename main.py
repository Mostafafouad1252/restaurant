from __future__ import annotations

import argparse
import sys

from dealership.inventory import Inventory
from dealership.models import Car


def _money(value: float) -> str:
    return f"${value:,.2f}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="car-dealership",
        description="Car dealership inventory (price, type, color).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Add a car to inventory")
    p_add.add_argument("--type", required=True, dest="car_type", help="Car type (e.g., Sedan)")
    p_add.add_argument("--color", required=True, help="Car color (e.g., Red)")
    p_add.add_argument("--price", required=True, type=float, help="Car price (e.g., 25000)")

    sub.add_parser("list", help="List all cars")

    p_search = sub.add_parser("search", help="Search cars by filters")
    p_search.add_argument("--type", dest="car_type", help="Filter by type")
    p_search.add_argument("--color", help="Filter by color")
    p_search.add_argument("--min-price", type=float, help="Minimum price")
    p_search.add_argument("--max-price", type=float, help="Maximum price")

    sub.add_parser("reset", help="Clear inventory (dangerous)")

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    inv = Inventory.default()

    if args.command == "add":
        if args.price < 0:
            print("Price must be >= 0.", file=sys.stderr)
            return 2
        car = Car(price=args.price, car_type=args.car_type, color=args.color, id=inv.next_id())
        inv.add(car)
        inv.save()
        print(f"Added: {car.car_type} | {car.color} | {_money(car.price)} (id={car.id})")
        return 0

    if args.command == "list":
        cars = inv.list_all()
        if not cars:
            print("Inventory is empty. Add cars with: python main.py add --type ... --color ... --price ...")
            return 0
        for c in cars:
            print(f"{c.id} | {c.car_type} | {c.color} | {_money(c.price)}")
        return 0

    if args.command == "search":
        cars = inv.search(
            car_type=args.car_type,
            color=args.color,
            min_price=args.min_price,
            max_price=args.max_price,
        )
        if not cars:
            print("No matches.")
            return 0
        for c in cars:
            print(f"{c.id} | {c.car_type} | {c.color} | {_money(c.price)}")
        return 0

    if args.command == "reset":
        inv.clear()
        inv.save()
        print("Inventory cleared.")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

