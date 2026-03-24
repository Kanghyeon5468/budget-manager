from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
from pathlib import Path


DATA_FILE = Path("expenses.csv")

CATEGORY_KEYWORDS = {
    "Food": ["shopping", "grocery", "food", "restaurant", "cafe", "coffee", "delivery", "lunch", "dinner"],
    "Transport": ["bus", "subway", "taxi", "train", "fuel", "parking"],
    "Lifestyle": ["toiletries", "pharmacy", "hospital", "beauty", "clothes"],
    "Subscription": ["netflix", "spotify", "youtube", "subscription", "membership"],
    "Leisure": ["movie", "game", "travel", "concert", "hobby"],
}


def ensure_data_file() -> None:
    if DATA_FILE.exists():
        return
    with DATA_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["date", "amount", "currency", "category", "description", "raw_input"],
        )
        writer.writeheader()


def parse_expense_input(text: str) -> dict[str, str]:
    """
    Parse text like:
      - 30 GBP shopping
      - 12.5 GBP coffee
      - 20000 KRW lunch
    """
    cleaned = text.strip()
    if not cleaned:
        raise ValueError('Input is empty. Example: 30 GBP shopping')

    pattern = r"^\s*(\d+(?:\.\d+)?)\s*(GBP|gbp|KRW|krw)?\s*(.*)$"
    match = re.match(pattern, cleaned)
    if not match:
        raise ValueError('Invalid format. Example: 30 GBP shopping')

    amount, currency_raw, description = match.groups()
    currency = normalize_currency(currency_raw)
    description = description.strip() or "Misc"
    category = infer_category(description)

    return {
        "date": dt.date.today().isoformat(),
        "amount": amount,
        "currency": currency,
        "category": category,
        "description": description,
        "raw_input": cleaned,
    }


def normalize_currency(currency_raw: str | None) -> str:
    if currency_raw is None:
        return "GBP"
    normalized = currency_raw.lower()
    if normalized in {"gbp"}:
        return "GBP"
    if normalized in {"krw"}:
        return "KRW"
    return currency_raw.upper()


def infer_category(description: str) -> str:
    lower_desc = description.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in lower_desc:
                return category
    return "Misc"


def save_record(record: dict[str, str]) -> None:
    ensure_data_file()
    with DATA_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["date", "amount", "currency", "category", "description", "raw_input"],
        )
        writer.writerow(record)


def read_records() -> list[dict[str, str]]:
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def print_records(records: list[dict[str, str]]) -> None:
    if not records:
        print("No expense records found.")
        return

    print("Date       | Amount    | Curr | Category    | Description")
    print("-" * 58)
    for row in records:
        amount_text = f"{row['amount']:<8}"
        print(
            f"{row['date']} | {amount_text} | {row['currency']:<4} | "
            f"{row['category']:<8} | {row['description']}"
        )


def print_summary(records: list[dict[str, str]]) -> None:
    if not records:
        print("No data available for summary.")
        return

    summary: dict[tuple[str, str], float] = {}
    for row in records:
        key = (row["currency"], row["category"])
        summary[key] = summary.get(key, 0.0) + float(row["amount"])

    print("Totals by category")
    print("-" * 30)
    for (currency, category), total in sorted(summary.items()):
        print(f"{currency} {category:<8}: {total:.2f}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="One-line expense input manager")
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help='Example: add "30 GBP shopping"')
    add_parser.add_argument("text", type=str, help='Example: "30 GBP shopping"')

    subparsers.add_parser("list", help="Show saved records")
    subparsers.add_parser("summary", help="Show totals by category")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "add":
        record = parse_expense_input(args.text)
        save_record(record)
        print(
            f"Saved: {record['date']} | {record['amount']} {record['currency']} | "
            f"{record['category']} | {record['description']}"
        )
        return

    if args.command == "list":
        records = read_records()
        print_records(records)
        return

    if args.command == "summary":
        records = read_records()
        print_summary(records)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
