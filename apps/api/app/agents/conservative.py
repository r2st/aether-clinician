"""Conservative-resolution node — runs only when the Verifier disagrees (architecture §8.5).

Applies the "conservative output wins" rule deterministically: downgrade confidence bands on
leading hypotheses, force FLAG_FOR_REVIEW, and attach the verifier's caveats. Never relaxes
anything.
"""

from __future__ import annotations

from app.agents.context import ReasoningContext
from app.agents.state import CaseState, downgrade_band, more_conservative_tier

AGENT = "conservative_resolution"


async def run(state: CaseState, ctx: ReasoningContext) -> None:
    await ctx.emit("agent_start", {"agent": AGENT, "label": "Conservative Resolution"})
    state.autonomy_tier = more_conservative_tier(state.autonomy_tier, "flag_for_review")
    # Downgrade the confidence of every leading hypothesis by one band.
    for h in state.leading_hypotheses(3):
        h.probability_band = downgrade_band(h.probability_band)
    caveat = (
        "Verifier disagreed with the reasoning agents; confidence was downgraded and this case "
        "was escalated for active clinician review (conservative resolution)."
    )
    for v in state.verifier_verdicts:
        if caveat not in v.caveats:
            v.caveats.append(caveat)
    state.add_trace(AGENT, "Applied conservative resolution after verifier disagreement", {})
    await ctx.emit(
        "conservative_resolution",
        {"agent": AGENT, "autonomy_tier": state.autonomy_tier, "caveat": caveat},
    )
    await ctx.emit("agent_complete", {"agent": AGENT})
