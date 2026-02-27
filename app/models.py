from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class MetaInfo(BaseModel):
    schema_version: str = "1.1"
    created_at: str
    system_name: str = "Axis"
    model: str
    disclaimer: str


class InputData(BaseModel):
    decision_narrative: str
    provided_fields: Dict[str, Optional[float]]


class ExtractionVariables(BaseModel):
    monthly_burn: Optional[float] = None
    runway_months: Optional[float] = None
    income_delta: Optional[float] = None
    liquidity_need_months: Optional[float] = None


class ExtractionOutput(BaseModel):
    decision_type: str
    time_horizon_months: Optional[float] = None
    declared_goal: str
    constraints: List[str]
    assumptions_made_explicit: List[str]
    variables: ExtractionVariables
    unknowns: List[str]
    questions_to_clarify: List[str]


class TradeoffDimension(BaseModel):
    name: str
    weight: float
    notes: str


class TradeoffOption(BaseModel):
    option_name: str
    pros: List[str]
    cons: List[str]
    dimension_scores: Dict[str, float]
    summary: str


class TradeoffOutput(BaseModel):
    dimensions: List[TradeoffDimension]
    options: List[TradeoffOption]
    opportunity_costs: List[str]
    recommendation_style_note: str


class Contradiction(BaseModel):
    statement_a: str
    statement_b: str
    why_it_matters: str


class HumanDecision(BaseModel):
    decision: str
    why_human: str


class BiasHuman(BaseModel):
    name: str          # canonical analyst name — preserved, not replaced
    plain_language: str  # second-person, jargon-free explanation


class VolatilityOutput(BaseModel):
    volatility_score_0_to_100: float
    detected_biases: List[str]          # canonical names — unchanged
    detected_biases_human: List[BiasHuman]  # human-readable layer added alongside
    contradictions: List[Contradiction]
    pressure_signals: List[str]
    stabilizing_moves: List[str]
    human_must_decide: List[HumanDecision]


class ScenarioDetail(BaseModel):
    assumptions: List[str]
    runway_impact: str
    trajectory_impact: str
    primary_risks: List[str]
    what_breaks_first: str


class ScenarioOutput(BaseModel):
    conservative: ScenarioDetail
    base: ScenarioDetail
    optimistic: ScenarioDetail


class ExecutiveSnapshot(BaseModel):
    volatility_score: float          # code-pulled from volatility_report
    volatility_label: str            # code-generated deterministic mapping
    primary_tension: str
    highest_optionality_path: str
    most_dangerous_assumption: str
    what_breaks_first: str
    what_this_means_in_plain_language: List[str]  # 3–5 bullet points, max 150 words


class FinalSummaryOutput(BaseModel):
    what_human_can_do_now: List[str]   # bullet list, actionable
    what_ai_is_responsible_for: List[str]
    where_ai_must_stop: List[str]      # plain language, not regulatory phrasing
    what_breaks_at_scale_first: List[str]


class HumanBoundaryGate(BaseModel):
    required: bool = True
    user_declared_risk_tolerance: str
    user_declared_downside_limit: float
    ai_must_stop_reason: str
    confirmed_by_user: bool


class DriftChange(BaseModel):
    field: str
    before: Any
    after: Any
    risk: str


class DriftReport(BaseModel):
    drift_detected: bool
    changes: List[DriftChange]
    value_weight_shift: List[str]
    risk_tolerance_shift: str
    volatility_shift: str
    new_contradictions: List[str]
    stabilization_advice: List[str]


class DecisionLog(BaseModel):
    meta: MetaInfo
    input: InputData
    executive_snapshot: ExecutiveSnapshot   # compression layer — first in schema
    extraction: ExtractionOutput
    tradeoff_model: TradeoffOutput
    volatility_report: VolatilityOutput
    scenario_simulation: ScenarioOutput
    human_boundary_gate: HumanBoundaryGate
    final_summary: FinalSummaryOutput


class AnalysisResponse(BaseModel):
    decision_log: DecisionLog
    drift_report: Optional[DriftReport] = None
