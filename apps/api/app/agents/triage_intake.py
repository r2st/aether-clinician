"""Agent 1: Triage/Intake — decides if enough info exists; asks highest-info-gain questions."""

from __future__ import annotations

from app.agents.cant_miss import match_cant_miss
from app.agents.context import ReasoningContext
from app.agents.prompts import TRIAGE_INTAKE
from app.agents.state import CaseState, IntakeQuestionState
from app.agents.tools import summarize_snapshot
from app.agents.util import call_llm, text_blob

AGENT = "triage_intake"


async def run(state: CaseState, ctx: ReasoningContext) -> None:
    await ctx.emit("agent_start", {"agent": AGENT, "label": "Triage / Intake"})
    state.intake_rounds += 1
    summary = summarize_snapshot(state.patient_graph_snapshot)

    result = await call_llm(
        ctx,
        TRIAGE_INTAKE,
        f"Presenting complaint: {state.presenting_complaint}\n\nPatient record:\n{summary}\n\n"
        f"Questions already answered: "
        f"{[{'q': q.text, 'a': q.answer} for q in state.intake_questions]}",
    )

    if result is None:
        _fallback(state)
    else:
        _apply(state, result)

    # Hard cap on intake rounds/questions regardless of agent output.
    if state.intake_rounds >= 2 or len(state.intake_questions) >= ctx.question_cap:
        unanswered = [q for q in state.intake_questions if q.answer is None]
        if not unanswered:
            state.intake_complete = True
    if state.info_gain_score < ctx.info_gain_threshold:
        state.intake_complete = True

    state.add_trace(
        AGENT,
        "Intake complete" if state.intake_complete else "Generated clarifying questions",
        {"info_gain_score": state.info_gain_score, "round": state.intake_rounds},
    )
    await ctx.emit(
        "intake",
        {
            "agent": AGENT,
            "intake_complete": state.intake_complete,
            "info_gain_score": state.info_gain_score,
            "questions": [
                {"text": q.text, "question_type": q.question_type, "rationale": q.rationale}
                for q in state.intake_questions
                if q.answer is None
            ],
        },
    )
    await ctx.emit("agent_complete", {"agent": AGENT})


def _apply(state: CaseState, result: dict) -> None:
    state.intake_complete = bool(result.get("intake_complete"))
    state.info_gain_score = float(result.get("info_gain_score", state.info_gain_score))
    existing = {q.text.strip().lower() for q in state.intake_questions}
    for q in result.get("questions", []):
        text = (q.get("text") or "").strip()
        if not text or text.lower() in existing:
            continue
        state.intake_questions.append(
            IntakeQuestionState(
                text=text,
                question_type=q.get("question_type", "clarifying"),
                rationale=q.get("rationale"),
                info_gain_score=float(q.get("info_gain_score", 0.5)),
            )
        )


def _fallback(state: CaseState) -> None:
    """Deterministic intake when the LLM is unavailable (degraded mode).

    Round 1: ask red-flag screens derived from can't-miss triggers + a duration question.
    Round 2+: stop (enough to proceed; the engine still runs with a degraded marker).
    """
    state.degraded = True
    if state.intake_rounds >= 2 or state.intake_questions:
        state.intake_complete = True
        state.info_gain_score = 0.1
        return

    blob = text_blob(
        state.presenting_complaint, summarize_snapshot(state.patient_graph_snapshot), []
    )
    questions: list[IntakeQuestionState] = [
        IntakeQuestionState(
            text="How long has the complaint been present, and is it getting worse?",
            question_type="history",
            rationale="Onset and trajectory change the differential and urgency.",
            info_gain_score=0.7,
        ),
        IntakeQuestionState(
            text="Any fever, breathlessness, chest pain, or altered consciousness?",
            question_type="red_flag",
            rationale="Screens for common can't-miss red flags.",
            info_gain_score=0.8,
        ),
    ]
    for rule in match_cant_miss(blob)[:2]:
        questions.append(
            IntakeQuestionState(
                text=f"Any features suggesting {rule.diagnosis.lower()}? ({rule.why})",
                question_type="red_flag",
                rationale=rule.why,
                info_gain_score=0.85,
            )
        )
    state.intake_questions.extend(questions)
    state.info_gain_score = 0.6
    state.intake_complete = False
