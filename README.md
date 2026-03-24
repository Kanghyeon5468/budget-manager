# Budget Manager

A lightweight expense tracker that parses one-line input like `30 GBP shopping` and automatically stores date and category.

The app supports a hybrid parser:
- AI parser (if `OPENAI_API_KEY` is set)
- Rule parser fallback (always available)

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

To enable AI parsing:

```bash
export OPENAI_API_KEY="your_api_key"
```

If the key is missing or AI parsing fails, the app automatically falls back to the rule parser.

## Deploy (Render)

1. Push this repository to GitHub.
2. Go to [Render](https://render.com) and create a new **Web Service** from the repo.
3. Render will detect `requirements.txt` and `Procfile`.
4. Deploy, then open the generated URL.

## Deploy with Cloudflare Tunnel

This option exposes your app through a Cloudflare URL/domain and keeps traffic behind Cloudflare.

### 1) Run app server

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

### 2) Install and login cloudflared

```bash
brew install cloudflared
cloudflared tunnel login
```

### 3) Create tunnel and DNS route

```bash
cloudflared tunnel create budget-manager
cloudflared tunnel route dns budget-manager budget.yourdomain.com
```

### 4) Configure tunnel

Copy `cloudflared-config.yml.example` to `~/.cloudflared/config.yml` and update:
- `YOUR_TUNNEL_ID`
- `credentials-file`
- `budget.yourdomain.com`

### 5) Start tunnel

```bash
cloudflared tunnel run budget-manager
```

Now your app is available at `https://budget.yourdomain.com`.

### macOS note about Gunicorn

On macOS, Gunicorn workers can crash with Objective-C fork errors like:
`objc[...] initialize ... when fork() was called`.

For local tunnel usage on macOS, use:

```bash
python3 app.py
```

If you still want Gunicorn on macOS (not recommended for local use), try:

```bash
OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES gunicorn app:app --workers 1 --bind 0.0.0.0:8000
```

## Cloudflare Zero Trust (optional)

You can protect the app with Cloudflare Access:
- Zero Trust Dashboard -> Access -> Applications -> Add application
- Set policy to allow only your email/domain
- Keep app private while still reachable on the internet

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
- `Health`
- `Shopping`
- `PersonalCare`
- `Bills`
- `Household`
- `Subscription`
- `Leisure`
- fallback: `Shopping`

## Flutter App (MVP)

A Flutter client is available in `mobile_app` and uses this backend API flow:
- `POST /api/preview` -> classify input with AI/rule parser
- `POST /api/confirm` -> save final amount/category/description
- `GET /api/records` -> fetch saved records

### Run backend

```bash
source .venv/bin/activate
python3 app.py
```

### Run Flutter app

```bash
cd mobile_app
../flutter/bin/flutter pub get
../flutter/bin/flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

For Android emulator, use:

```bash
../flutter/bin/flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```
