from __future__ import annotations

from flask import Flask, redirect, render_template_string, request, url_for

from budget_manager import parse_expense_input, read_records, save_record

app = Flask(__name__)

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
    <p class="small">Enter one line like: <code>30 GBP shopping</code></p>

    {% if message %}
      <div class="msg ok">{{ message }}</div>
    {% endif %}
    {% if error %}
      <div class="msg err">{{ error }}</div>
    {% endif %}

    <form method="post" action="{{ url_for('add_expense') }}">
      <input type="text" name="expense_text" placeholder="e.g. 30 GBP shopping" required />
      <button type="submit">Save</button>
    </form>

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
    return render_template_string(PAGE_TEMPLATE, records=records, message="", error="")


@app.post("/add")
def add_expense():
    text = request.form.get("expense_text", "")
    try:
        record = parse_expense_input(text)
        save_record(record)
        message = (
            f"Saved: {record['date']} | {record['amount']} {record['currency']} | "
            f"{record['category']} | {record['description']}"
        )
        return render_template_string(PAGE_TEMPLATE, records=read_records(), message=message, error="")
    except ValueError as exc:
        return render_template_string(PAGE_TEMPLATE, records=read_records(), message="", error=str(exc))


@app.get("/health")
def health():
    return {"ok": True}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
