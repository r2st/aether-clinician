"""Agent 5: Investigation Strategist — the single most discriminating next test."""

from __future__ import annotations

from app.agents.context import ReasoningContext
from app.agents.prompts import INVESTIGATION_STRATEGIST
from app.agents.state import CaseState, Investigation
from app.agents.tools import compute_discriminating_test
from app.agents.util import call_llm, norm_band

AGENT = "investigation_strategist"
_TIERS = {"phc", "chc", "district_hospital", "referral"}


async def run(state: CaseState, ctx: ReasoningContext) -> None:
    await ctx.emit("agent_start", {"agent": AGENT, "label": "Investigation Strategist"})
    leaders = state.leading_hypotheses(5)
    result = await call_llm(
        ctx,
        INVESTIGATION_STRATEGIST,
        "Leading hypotheses: "
        + ", ".join(f"{h.diagnosis_name} ({h.probability_band})" for h in leaders),
    )
    investigations: list[Investigation] = []
    if result:
        for inv in result.get("investigations", []):
            name = (inv.get("name") or "").strip()
            if not name:
                continue
            tier = inv.get("availability_tier", "phc")
            investigations.append(
                Investigation(
                    name=name,
                    rationale=inv.get("rationale", ""),
                    expected_information_gain=norm_band(
                        inv.get("expected_information_gain"), "moderate"
                    ),
                    cost_estimate=inv.get("cost_estimate"),
                    availability_tier=tier if tier in _TIERS else "phc",
                )
            )
    if not investigations:
        state.degraded = state.degraded or not ctx.llm_available()
        investigations = compute_discriminating_test(leaders)

    state.recommended_investigations.extend(investigations)
    state.add_trace(AGENT, f"Recommended {len(investigations)} discriminating tests", {})
    await ctx.emit(
        "investigations",
        {
            "agent": AGENT,
            "investigations": [
                {
                    "name": i.name,
                    "rationale": i.rationale,
                    "expected_information_gain": i.expected_information_gain,
                    "cost_estimate": i.cost_estimate,
                    "availability_tier": i.availability_tier,
                }
                for i in investigations
            ],
        },
    )
    await ctx.emit("agent_complete", {"agent": AGENT})
