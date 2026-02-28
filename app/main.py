import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from app.claude_client import call_claude
from app.models import (
    AnalysisResponse,
    DecisionLog,
    DriftReport,
    ExecutiveSnapshot,
    ExtractionOutput,
    FinalSummaryOutput,
    HumanBoundaryGate,
    InputData,
    MetaInfo,
    ScenarioOutput,
    TradeoffOutput,
    VolatilityOutput,
)
from app.prompts import (
    DRIFT_SYSTEM,
    EXECUTIVE_SNAPSHOT_SYSTEM,
    EXTRACTION_SYSTEM,
    FINAL_SUMMARY_SYSTEM,
    SCENARIO_SYSTEM,
    TRADEOFF_SYSTEM,
    VOLATILITY_SYSTEM,
)

load_dotenv()

BASE_DIR = Path(__file__).parent
DISCLAIMER = "Not financial advice. Decision support only."

app = FastAPI(title="Axis — Financial Decision Stabilization Layer")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def get_volatility_label(score: float) -> str:
    """Deterministic mapping — code-generated, not AI-generated."""
    if score <= 30:
        return "Low instability"
    elif score <= 60:
        return "Moderate instability"
    elif score <= 80:
        return "Elevated instability"
    else:
        return "High instability"


@app.get("/")
async def index():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/sample_prior")
async def sample_prior():
    path = BASE_DIR / "sample_prior_log.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Sample file not found")
    return FileResponse(path, media_type="application/json", filename="axis_sample_prior_log.json")


@app.post("/api/analyze")
async def analyze(
    decision_narrative: str = Form(...),
    monthly_burn: Optional[float] = Form(None),
    runway_months: Optional[float] = Form(None),
    income_delta: Optional[float] = Form(None),
    risk_tolerance_level: str = Form("Medium"),
    downside_limit: float = Form(0.0),
    prior_log_file: Optional[UploadFile] = File(None),
):
    api_key = os.getenv("CLAUDE_API_KEY", "").strip()
    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

    if not api_key:
        raise HTTPException(status_code=500, detail="CLAUDE_API_KEY is not set in environment.")

    # Parse prior log if provided
    prior_log: Optional[dict] = None
    if prior_log_file and prior_log_file.filename:
        raw = await prior_log_file.read()
        if raw:
            try:
                prior_log = json.loads(raw)
            except json.JSONDecodeError:
                raise HTTPException(status_code=422, detail="Prior log file is not valid JSON.")

    # Build narrative context
    numeric_lines = []
    if monthly_burn is not None:
        numeric_lines.append(f"Monthly expenses: ${monthly_burn:,.2f}/month")
    if runway_months is not None:
        numeric_lines.append(f"Financial runway: {runway_months} months")
    if income_delta is not None:
        sign = "+" if income_delta >= 0 else ""
        numeric_lines.append(f"Income change: {sign}${income_delta:,.2f}/year")

    narrative_with_context = decision_narrative
    if numeric_lines:
        narrative_with_context += "\n\nUser-provided numeric context:\n" + "\n".join(numeric_lines)

    # ── Call 1: Extraction (sequential) ───────────────────────────────────
    try:
        extraction_raw = await call_claude(EXTRACTION_SYSTEM, narrative_with_context, model, api_key)
        extraction = ExtractionOutput(**extraction_raw)
    except (ValueError, ValidationError) as e:
        raise HTTPException(status_code=502, detail=f"Extraction step failed: {e}")

    # User-provided values take precedence over AI-extracted
    if monthly_burn is not None:
        extraction.variables.monthly_burn = monthly_burn
    if runway_months is not None:
        extraction.variables.runway_months = runway_months
    if income_delta is not None:
        extraction.variables.income_delta = income_delta

    extraction_dict = extraction.model_dump()

    # ── Calls 2, 3, 4: Parallel ───────────────────────────────────────────
    enriched_context = (
        f"{narrative_with_context}\n\n"
        f"Extracted variables:\n{json.dumps(extraction_dict, indent=2)}"
    )

    try:
        tradeoff_raw, volatility_raw, scenario_raw = await asyncio.gather(
            call_claude(TRADEOFF_SYSTEM, enriched_context, model, api_key),
            call_claude(VOLATILITY_SYSTEM, enriched_context, model, api_key),
            call_claude(SCENARIO_SYSTEM, enriched_context, model, api_key),
        )
        tradeoff = TradeoffOutput(**tradeoff_raw)
        volatility = VolatilityOutput(**volatility_raw)
        scenario = ScenarioOutput(**scenario_raw)
    except (ValueError, ValidationError) as e:
        raise HTTPException(status_code=502, detail=f"Analysis step failed: {e}")

    # ── Build human boundary gate (gate confirmed client-side after render) ──
    gate = HumanBoundaryGate(
        required=True,
        user_declared_risk_tolerance=risk_tolerance_level,
        user_declared_downside_limit=downside_limit,
        ai_must_stop_reason="All final judgment belongs to you.",
        confirmed_by_user=False,  # always false until user confirms in UI
    )

    # ── Full context for final calls ───────────────────────────────────────
    full_context = (
        f"{enriched_context}\n\n"
        f"Trade-off model:\n{json.dumps(tradeoff.model_dump(), indent=2)}\n\n"
        f"Volatility report:\n{json.dumps(volatility.model_dump(), indent=2)}\n\n"
        f"Scenario simulation:\n{json.dumps(scenario.model_dump(), indent=2)}"
    )

    # Snapshot context — pass scenario what_breaks_first values explicitly
    snapshot_context = (
        f"{full_context}\n\n"
        f"For what_breaks_first in the snapshot, derive from these scenario values:\n"
        f"Conservative: {scenario.conservative.what_breaks_first}\n"
        f"Base: {scenario.base.what_breaks_first}\n"
        f"Optimistic: {scenario.optimistic.what_breaks_first}"
    )

    # ── Calls 5, 6, [7]: Final summary + Executive snapshot + [Drift] in parallel ──
    tasks = [
        call_claude(FINAL_SUMMARY_SYSTEM, full_context, model, api_key),
        call_claude(EXECUTIVE_SNAPSHOT_SYSTEM, snapshot_context, model, api_key),
    ]

    if prior_log:
        current_partial = {
            "executive_snapshot": {},  # not yet assembled
            "extraction": extraction_dict,
            "tradeoff_model": tradeoff.model_dump(),
            "volatility_report": volatility.model_dump(),
            "scenario_simulation": scenario.model_dump(),
            "human_boundary_gate": gate.model_dump(),
        }
        drift_context = (
            f"Prior decision log:\n{json.dumps(prior_log, indent=2)}\n\n"
            f"Current decision analysis:\n{json.dumps(current_partial, indent=2)}"
        )
        tasks.append(call_claude(DRIFT_SYSTEM, drift_context, model, api_key))

    try:
        results = await asyncio.gather(*tasks)
    except (ValueError, ValidationError) as e:
        raise HTTPException(status_code=502, detail=f"Summary/snapshot step failed: {e}")

    summary_raw = results[0]
    snapshot_raw = results[1]
    drift_raw = results[2] if prior_log else None

    # ── Assemble executive snapshot (code adds deterministic fields) ───────
    try:
        snapshot_raw["volatility_score"] = volatility.volatility_score_0_to_100
        snapshot_raw["volatility_label"] = get_volatility_label(volatility.volatility_score_0_to_100)
        executive_snapshot = ExecutiveSnapshot(**snapshot_raw)
        final_summary = FinalSummaryOutput(**summary_raw)
    except ValidationError as e:
        raise HTTPException(status_code=502, detail=f"Snapshot/summary validation failed: {e}")

    drift_report: Optional[DriftReport] = None
    if drift_raw:
        try:
            drift_report = DriftReport(**drift_raw)
        except ValidationError as e:
            raise HTTPException(status_code=502, detail=f"Drift report validation failed: {e}")

    # ── Assemble full DecisionLog ──────────────────────────────────────────
    decision_log = DecisionLog(
        meta=MetaInfo(
            schema_version="1.1",
            created_at=datetime.now(timezone.utc).isoformat(),
            system_name="Axis",
            model=model,
            disclaimer=DISCLAIMER,
        ),
        input=InputData(
            decision_narrative=decision_narrative,
            provided_fields={
                "monthly_burn": monthly_burn,
                "runway_months": runway_months,
                "income_delta": income_delta,
            },
        ),
        executive_snapshot=executive_snapshot,
        extraction=extraction,
        tradeoff_model=tradeoff,
        volatility_report=volatility,
        scenario_simulation=scenario,
        human_boundary_gate=gate,
        final_summary=final_summary,
    )

    return AnalysisResponse(decision_log=decision_log, drift_report=drift_report)
