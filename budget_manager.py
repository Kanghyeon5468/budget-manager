from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:  # Optional dependency for AI parsing.
    OpenAI = None

DATA_FILE = Path("expenses.csv")

CATEGORY_KEYWORDS = {
    "Food": ["food", "restaurant", "cafe", "coffee", "delivery", "lunch", "dinner", "breakfast", "brunch"],
    "Transport": ["bus", "subway", "taxi", "train", "fuel", "parking"],
    "Health": ["pharmacy", "hospital", "clinic", "medicine", "doctor", "dental", "therapy", "gym", "fitness", "workout"],
    "Shopping": ["shopping", "mall", "store", "online", "amazon", "electronics", "gift"],
    "PersonalCare": ["beauty", "hair", "barber", "salon", "cosmetic", "toiletries", "skincare"],
    "Bills": ["rent", "electricity", "water", "gas", "internet", "phone", "utility", "insurance"],
    "Household": ["detergent", "cleaning", "furniture", "home", "kitchen", "supplies"],
    "Subscription": ["netflix", "spotify", "youtube", "subscription", "membership"],
    "Leisure": ["movie", "game", "travel", "concert", "hobby", "pub", "bar", "drinks", "beer"],
}
VALID_CATEGORIES = ["Food", "Transport", "Health", "Shopping", "PersonalCare", "Bills", "Household", "Subscription", "Leisure"]
DEFAULT_CATEGORY = "Shopping"


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
    description = description.strip() or "General expense"
    category = infer_category(description)

    return {
        "date": dt.date.today().isoformat(),
        "amount": amount,
        "currency": currency,
        "category": category,
        "description": description,
        "raw_input": cleaned,
    }


def parse_expense_input_with_ai(text: str) -> dict[str, str] | None:
    """
    Try AI-based parsing first. Returns None when AI is unavailable or fails.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return None

    client = OpenAI(api_key=api_key)
    today = dt.date.today().isoformat()
    prompt = (
        "Extract expense data from one-line user input.\n"
        "Return only valid JSON with keys: amount, currency, description, category.\n"
        "Rules:\n"
        "- amount must be a number as string\n"
        "- currency must be GBP or KRW (default GBP when unknown)\n"
        "- description must be concise text\n"
        "- category must be one of: Food, Transport, Health, Shopping, PersonalCare, Bills, Household, Subscription, Leisure\n"
        "- never use Misc or Other; choose the closest category\n"
        f"- today's date is {today} (do not return date key)\n"
        f"Input: {text}"
    )

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            temperature=0,
        )
        content = response.output_text.strip()
        parsed = json.loads(content)
        description = str(parsed.get("description", "General expense")).strip() or "General expense"
        return {
            "date": today,
            "amount": str(parsed["amount"]),
            "currency": normalize_currency(str(parsed.get("currency", "GBP"))),
            "category": normalize_category(str(parsed.get("category", DEFAULT_CATEGORY)), description),
            "description": description,
            "raw_input": text.strip(),
        }
    except Exception:
        return None


def parse_expense_input_smart(text: str) -> tuple[dict[str, str], str]:
    """
    Parse with AI agent if available, else fallback to rule parser.
    Returns (record, source).
    """
    ai_record = parse_expense_input_with_ai(text)
    if ai_record is not None:
        return ai_record, "ai"
    return parse_expense_input(text), "rule"


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
    return DEFAULT_CATEGORY


def is_ai_available() -> bool:
    return bool(os.getenv("OPENAI_API_KEY")) and OpenAI is not None


def classify_category_with_ai(description: str, hinted_category: str = "") -> str | None:
    if not is_ai_available():
        return None

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = (
        "Choose exactly one category for this expense.\n"
        f"Allowed categories: {', '.join(VALID_CATEGORIES)}.\n"
        "Return only the category name, no extra text.\n"
        f"Hinted category: {hinted_category}\n"
        f"Description: {description}"
    )
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            temperature=0,
        )
        choice = response.output_text.strip()
        for category in VALID_CATEGORIES:
            if category.lower() == choice.lower():
                return category
        return None
    except Exception:
        return None


def normalize_category(category_raw: str, description: str | None = None) -> str:
    normalized = category_raw.strip().lower()
    for category in VALID_CATEGORIES:
        if category.lower() == normalized:
            return category

    if description:
        ai_category = classify_category_with_ai(description, category_raw)
        if ai_category:
            return ai_category
    if description:
        return infer_category(description)
    return DEFAULT_CATEGORY


def save_record(record: dict[str, str]) -> None:
    ensure_data_file()
    with DATA_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["date", "amount", "currency", "category", "description", "raw_input"],
        )
        writer.writerow(record)


def clear_records() -> None:
    with DATA_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["date", "amount", "currency", "category", "description", "raw_input"],
        )
        writer.writeheader()


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
