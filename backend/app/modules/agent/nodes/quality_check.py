"""
Node: quality_check

Deterministic gate -- no LLM call. Decides whether the generated answer
is good enough to return directly ("answered") or whether this should be
routed to a human ("handoff"). This is where "avoid building an
unnecessarily autonomous agent" is most concrete: the LLM does not decide
whether to hand off, this function does, from signals (grounded,
confidence, whether retrieval found anything) the LLM itself produced.
Ticket creation from a "handoff" route is Phase 7's job -- this node only
decides the route, it doesn't act on it.
"""
from app.modules.agent.state import AgentState

# Below this confidence, treat the answer as too uncertain to return
# directly even if the model claimed it was "grounded". A magic number
# for v1 -- see docs/evaluation.md (Phase 12) for how this should
# eventually be tuned against real evaluation data instead of guessed.
CONFIDENCE_HANDOFF_THRESHOLD = 0.4


def quality_check(state: AgentState) -> dict:
    if not state.get("needs_retrieval", False):
        # Small talk / no knowledge lookup was needed -- never route this
        # to a human, since there was no knowledge-base question to fail
        # to answer in the first place.
        return {"route": "answered"}

    if not state.get("retrieved_chunks"):
        # Retrieval ran but found literally nothing above the similarity
        # threshold -- generate_answer almost certainly said "I don't
        # know" already, but handing off explicitly (rather than
        # returning that as if it were a satisfying answer) is the
        # correct product behavior for a support agent.
        return {"route": "handoff"}

    grounded = state.get("grounded", False)
    confidence = state.get("confidence", 0.0)
    if not grounded or confidence < CONFIDENCE_HANDOFF_THRESHOLD:
        return {"route": "handoff"}

    return {"route": "answered"}
