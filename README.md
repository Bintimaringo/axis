# Axis — Financial Decision Stabilization Layer

> **Not financial advice. Decision support only.**

**Live demo:** [axis-jiyo.onrender.com](https://axis-jiyo.onrender.com)

---

## What it does

Axis takes a high-stakes financial decision narrative and runs it through a structured 6-call AI pipeline: variable extraction, trade-off modeling, volatility and bias analysis, scenario simulation, executive snapshot, and final summary. The result is a structured DecisionLog — a legible, exportable record of how a decision was analyzed, what assumptions were made explicit, and where human judgment is required. It is not an advisor. It is a stabilization layer between a person and a consequential decision.

---

## What the human can now do that they couldn't before

- Externalize a high-stakes decision into structured form without a financial advisor or consultant
- See their own cognitive biases named and explained in plain language, not jargon
- Have implicit assumptions surfaced before acting on them
- Run three realistic scenarios (conservative, base, optimistic) without spreadsheet expertise
- Compare a current decision against a prior one to detect drift in values or risk tolerance over time
- Leave with a structured, exportable record of the decision process — not just the outcome

---

## What AI is responsible for

- Extracting variables, constraints, and unknowns from an unstructured narrative
- Building a weighted trade-off model across four dimensions: stability, upside, trajectory alignment, and optionality
- Identifying cognitive biases and logical contradictions in the user's stated reasoning
- Simulating three scenario outcomes with concrete failure points
- Synthesizing an executive snapshot in plain language for non-expert readers
- Generating specific, actionable next steps the human can take

---

## Where AI must stop

- Making the final decision — that belongs entirely to the user
- Evaluating whether the goal itself is worth pursuing
- Weighing personal values, identity, or what matters to the person
- Acting on the analysis in any way
- Replacing the Human Boundary Gate with a recommendation

The `HumanBoundaryGate` is not a disclaimer. It is load-bearing. The system is designed so the AI's output cannot be mistaken for a decision.

---

## What breaks first at scale

**Human boundary erosion**
At scale, users will treat structured AI output as recommendation rather than reflection. The confirmation gate risks becoming ritual rather than pause. The integrity of the system depends on preserving human accountability — and that cannot be enforced technically.

**Schema reliability under narrative diversity**
The structured JSON pipeline works under controlled inputs. At scale, ambiguous or adversarial narratives increase extraction drift. Without validation layers or confidence scoring, silent degradation becomes likely.

**Input quality collapse**
Axis is context-dependent. As user input quality declines, output quality declines — but the system currently lacks input validation or completeness scoring to warn users when their narrative is too thin to analyze reliably.

**Volatility score misuse**
A single number invites shortcut behavior. Over time, users may anchor on the score rather than interrogate assumptions. The metric could unintentionally become a decision proxy.

---

## How to run it locally

```bash
git clone https://github.com/Bintimaringo/axis.git
cd axis
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add your Anthropic API key to .env
uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000).

---

## Architecture

```
axis/
├── app/
│   ├── main.py                  FastAPI app — orchestrates 6-call pipeline
│   ├── models.py                Pydantic schemas — DecisionLog and all sub-models
│   ├── prompts.py               Claude prompt templates — one per analysis step
│   ├── claude_client.py         API call + JSON retry logic
│   ├── sample_prior_log.json    Demo prior decision log for drift testing
│   └── static/
│       └── index.html           Single-page UI — no framework
├── .env.example
├── requirements.txt
└── README.md
```

**API call sequence:**

1. Extraction — sequential, outputs structured variables
2. Trade-off model + Volatility report + Scenario simulation — parallel
3. Final summary + Executive snapshot + Drift comparison (if prior log uploaded) — parallel

**Stack:** FastAPI · Pydantic · Claude API (claude-sonnet-4-6) · Vanilla JS · No frontend framework · No database

---

## Privacy

- No data stored server-side
- No authentication required
- The only external calls made are to the Anthropic API with the text you submit
- Decision logs exist only in your browser or downloads — never on our servers
