from __future__ import annotations

import datetime as dt
import re

from flask import Flask, jsonify, render_template_string, request, url_for
from flask_cors import CORS

from budget_manager import clear_records, normalize_category, parse_expense_input_smart, read_records, save_record

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

PAGE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Budget Manager</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2rem; background: #f7f8fb; color: #1f2937; }
    .container { max-width: 860px; margin: 0 auto; background: #fff; padding: 1.25rem; border-radius: 12px; }
    h1 { margin-top: 0; }
    form { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
    input[type=text] { flex: 1; padding: 0.65rem; border: 1px solid #d1d5db; border-radius: 8px; }
    button { padding: 0.65rem 1rem; border: none; background: #2563eb; color: #fff; border-radius: 8px; cursor: pointer; }
    .msg { padding: 0.65rem; border-radius: 8px; margin-bottom: 1rem; }
    .ok { background: #ecfdf3; color: #166534; }
    .err { background: #fef2f2; color: #991b1b; }
    table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
    th, td { border-bottom: 1px solid #e5e7eb; text-align: left; padding: 0.6rem; }
    .small { font-size: 0.92rem; color: #4b5563; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Budget Manager</h1>
    <p class="small">Step 1: enter one line, e.g. <code>30 GBP food</code></p>

    {% if message %}
      <div class="msg ok">{{ message }}</div>
    {% endif %}
    {% if error %}
      <div class="msg err">{{ error }}</div>
    {% endif %}

    <form method="post" action="{{ url_for('preview_expense') }}">
      <input type="text" name="expense_text" placeholder="e.g. 30 GBP shopping" required />
      <button type="submit">Classify with AI</button>
    </form>

    {% if preview %}
    <h3>Step 2: Review and confirm</h3>
    <form method="post" action="{{ url_for('confirm_expense') }}">
      <input type="hidden" name="raw_input" value="{{ preview.raw_input }}" />
      <input type="hidden" name="source" value="{{ preview.source }}" />
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;margin-bottom:0.5rem;">
        <input type="text" name="amount" value="{{ preview.amount }}" required />
        <input type="text" name="currency" value="{{ preview.currency }}" required />
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;">
        <input type="text" name="category" value="{{ preview.category }}" required />
        <input type="text" name="description" value="{{ preview.description }}" required />
      </div>
      <div style="margin-top:0.6rem;">
        <button type="submit">Confirm and Save</button>
      </div>
      <p class="small">Parsed by: <strong>{{ preview.source }}</strong></p>
    </form>
    {% endif %}

    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Amount</th>
          <th>Currency</th>
          <th>Category</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        {% for row in records %}
        <tr>
          <td>{{ row.date }}</td>
          <td>{{ row.amount }}</td>
          <td>{{ row.currency }}</td>
          <td>{{ row.category }}</td>
          <td>{{ row.description }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</body>
</html>
"""


@app.get("/")
def index():
    records = read_records()
    return render_template_string(PAGE_TEMPLATE, records=records, message="", error="", preview=None)


@app.get("/api/health")
def api_health():
    return jsonify({"ok": True})


@app.get("/api/records")
def api_records():
    return jsonify(read_records())


@app.post("/preview")
def preview_expense():
    text = request.form.get("expense_text", "")
    try:
        record, source = parse_expense_input_smart(text)
        preview = {
            "amount": record["amount"],
            "currency": record["currency"],
            "category": record["category"],
            "description": record["description"],
            "raw_input": record["raw_input"],
            "source": source,
        }
        message = (
            f"Classification ready ({source} parser). "
            "Review amount/category then confirm."
        )
        return render_template_string(
            PAGE_TEMPLATE,
            records=read_records(),
            message=message,
            error="",
            preview=preview,
        )
    except ValueError as exc:
        return render_template_string(
            PAGE_TEMPLATE,
            records=read_records(),
            message="",
            error=str(exc),
            preview=None,
        )


@app.post("/confirm")
def confirm_expense():
    amount = request.form.get("amount", "").strip()
    currency = request.form.get("currency", "GBP").strip().upper()
    category = normalize_category(request.form.get("category", "Lifestyle"))
    description = request.form.get("description", "General expense").strip() or "General expense"
    raw_input = request.form.get("raw_input", "").strip()
    source = request.form.get("source", "rule").strip()

    if not amount:
        return render_template_string(
            PAGE_TEMPLATE,
            records=read_records(),
            message="",
            error="Amount is required.",
            preview=None,
        )

    try:
        float(amount)
    except ValueError:
        return render_template_string(
            PAGE_TEMPLATE,
            records=read_records(),
            message="",
            error="Amount must be a valid number.",
            preview=None,
        )

    record = {
        "date": dt.date.today().isoformat(),
        "amount": amount,
        "currency": currency,
        "category": category,
        "description": description,
        "raw_input": raw_input or f"{amount} {currency} {description}",
    }
    save_record(record)

    message = (
        f"Saved: {record['date']} | {record['amount']} {record['currency']} | "
        f"{record['category']} | {record['description']} (classified by {source} parser)"
    )
    return render_template_string(
        PAGE_TEMPLATE,
        records=read_records(),
        message=message,
        error="",
        preview=None,
    )


@app.post("/api/preview")
def api_preview_expense():
    data = request.get_json(silent=True) or {}
    text = str(data.get("expense_text", "")).strip()
    preferred_currency = str(data.get("preferred_currency", "GBP")).strip().upper()
    if not text:
        return jsonify({"error": "expense_text is required"}), 400

    try:
        record, source = parse_expense_input_smart(text)
        if preferred_currency in {"GBP", "KRW"} and not re.search(r"\b(GBP|KRW)\b", text, flags=re.IGNORECASE):
            record["currency"] = preferred_currency
        return jsonify(
            {
                "date": record["date"],
                "amount": record["amount"],
                "currency": record["currency"],
                "category": record["category"],
                "description": record["description"],
                "raw_input": record["raw_input"],
                "source": source,
            }
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/confirm")
def api_confirm_expense():
    data = request.get_json(silent=True) or {}
    amount = str(data.get("amount", "")).strip()
    currency = str(data.get("currency", "GBP")).strip().upper()
    category = normalize_category(str(data.get("category", "Lifestyle")))
    description = str(data.get("description", "General expense")).strip() or "General expense"
    raw_input = str(data.get("raw_input", "")).strip()
    source = str(data.get("source", "rule")).strip()

    if not amount:
        return jsonify({"error": "Amount is required."}), 400

    try:
        float(amount)
    except ValueError:
        return jsonify({"error": "Amount must be a valid number."}), 400

    record = {
        "date": dt.date.today().isoformat(),
        "amount": amount,
        "currency": currency,
        "category": category,
        "description": description,
        "raw_input": raw_input or f"{amount} {currency} {description}",
    }
    save_record(record)
    return jsonify(
        {
            "saved": True,
            "source": source,
            "record": record,
        }
    )


@app.post("/api/reset")
def api_reset_records():
    clear_records()
    return jsonify({"reset": True})


@app.get("/health")
def health():
    return {"ok": True}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
