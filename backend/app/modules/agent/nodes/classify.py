"""
Node: classify_intent

Decides whether this question needs a knowledge-base lookup at all.
Deliberately a cheap deterministic heuristic, not an LLM call -- see
docs/agent.md "when an agent is unnecessary". Classifying "is this a
greeting/thanks" vs. "is this a real question" doesn't need a language
model, and every LLM call avoided here is latency and cost saved on the
share of real traffic that's just "hi" / "thanks, bye".
"""
from app.modules.agent.state import AgentState

_SMALL_TALK = {"hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "bye", "goodbye"}


def classify_intent(state: AgentState) -> dict:
    question = state["question"].strip().lower().rstrip("!.?")
    needs_retrieval = bool(question) and question not in _SMALL_TALK
    return {"needs_retrieval": needs_retrieval}
