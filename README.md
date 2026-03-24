# Budget Manager

A lightweight expense tracker that parses one-line input like `30 GBP shopping` and automatically stores date and category.

## CLI Usage

Run in the project directory:

```bash
python3 budget_manager.py add "30 GBP shopping"
python3 budget_manager.py add "12.5 GBP coffee"
python3 budget_manager.py add "20000 KRW lunch"
```

Show saved records:

```bash
python3 budget_manager.py list
```

Show category totals:

```bash
python3 budget_manager.py summary
```

## Web App Usage

Install dependencies and run locally:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Open: `http://localhost:8000`

## Deploy (Render)

1. Push this repository to GitHub.
2. Go to [Render](https://render.com) and create a new **Web Service** from the repo.
3. Render will detect `requirements.txt` and `Procfile`.
4. Deploy, then open the generated URL.

## Data Format

Data is stored in `expenses.csv` with these columns:

- `date`
- `amount`
- `currency`
- `category`
- `description`
- `raw_input`

## Auto Categorization

Categories are inferred from description keywords:

- `Food`
- `Transport`
- `Lifestyle`
- `Subscription`
- `Leisure`
- fallback: `Misc`
