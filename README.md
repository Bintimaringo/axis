# Axis — Financial Decision Stabilization Layer

AI-native decision support for high-stakes financial choices. Axis turns a decision narrative into structured variables, a trade-off model, a volatility/contradiction report, scenario simulations, and a human-boundary gate. Privacy-first: no database, no auth, no external storage.

> **Not financial advice. Decision support only.**

---

## Setup

### 1. Clone / navigate

```bash
cd axis
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key:

```
CLAUDE_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-6
```

`CLAUDE_MODEL` is optional — defaults to `claude-sonnet-4-6` if omitted.

### 5. Run

```bash
uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000).

---

## Usage

1. **Enter a decision narrative** — describe the financial decision in plain language.
2. **Optionally provide numeric context** — monthly burn, runway months, income delta.
3. **Declare your risk tolerance** — check the box, select a level, and set a downside limit. If you don't confirm, the analysis still runs but the Human Boundary Gate will flag "AI must stop here."
4. **Optionally upload a prior decision log** — drag in a previous Axis JSON export to get a drift comparison.
5. **Click Analyze** — 5–6 API calls run (~30–60 seconds).
6. **Export** — download as Decision Summary (JSON), Full Decision Log (JSON), or Markdown (.md).

### Longitudinal tracking

Axis has no database. Persistence is explicit: export a log after each analysis, then upload it when you return. This is intentional — you own your decision history.

To try the drift feature, click **Download sample prior log** and upload it alongside a new analysis.

---

## Architecture

```
axis/
├── app/
│   ├── main.py                  FastAPI app and endpoints
│   ├── models.py                Pydantic schemas
│   ├── prompts.py               Claude prompt templates
│   ├── claude_client.py         API call + JSON retry logic
│   ├── sample_prior_log.json    Demo prior decision log
│   └── static/
│       └── index.html           Single-page UI
├── .env.example
├── requirements.txt
└── README.md
```

**Endpoints:**

| Method | Path               | Description                              |
|--------|--------------------|------------------------------------------|
| GET    | `/`                | Main UI                                  |
| POST   | `/api/analyze`     | Run full analysis, returns DecisionLog   |
| GET    | `/api/sample_prior`| Download demo prior log JSON             |

**API call sequence:**

1. Extraction (sequential)
2. Trade-off model, Volatility report, Scenario simulation (parallel)
3. Final summary + optional drift comparison (parallel)

---

## DecisionLog schema version: 1.1

The exported JSON conforms to the schema defined in `app/models.py`. Fields:

- `meta` — schema version, timestamp, model, disclaimer
- `input` — raw narrative + provided numeric fields
- `extraction` — variables, constraints, unknowns, clarifying questions
- `tradeoff_model` — dimensions, options with scores, opportunity costs
- `volatility_report` — score (0–100), biases, contradictions, stabilizing moves
- `scenario_simulation` — conservative / base / optimistic
- `human_boundary_gate` — risk declaration, confirmation status
- `final_summary` — actionable next steps, AI responsibilities, where AI stops

---

## Privacy

- No data is stored server-side
- No authentication required
- The only external calls made are to the Anthropic API with the text you submit
- Logs exist only in your browser/downloads until you choose to save them
