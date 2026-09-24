"""
Node: generate_answer

Calls the LLM (via ChatModel, modules/agent/llm.py) with whatever context
was retrieved -- possibly none, for small talk or a failed retrieval --
and produces a structured (answer, grounded, confidence) result. This
node ALWAYS runs (see graph.py); it's quality_check, downstream, that
decides what to do with a low-confidence or ungrounded result.
"""
from app.modules.agent.llm import ChatModel, get_chat_model
from app.modules.agent.state import AgentState


def make_generate_answer(chat_model: ChatModel | None = None):
    def generate_answer(state: AgentState) -> dict:
        model = chat_model or get_chat_model()
        context_texts = [c["content"] for c in state.get("retrieved_chunks", [])]
        result = model.answer_from_context(
            question=state["question"],
            context_chunks=context_texts,
            history=state.get("history"),
        )
        output = {
            "answer": result.answer,
            "grounded": result.grounded,
            "confidence": result.confidence,
        }
        if result.latency_ms is not None:
            output["llm_latency_ms"] = result.latency_ms
        if result.prompt_tokens is not None:
            output["prompt_tokens"] = result.prompt_tokens
        if result.completion_tokens is not None:
            output["completion_tokens"] = result.completion_tokens
        if result.total_tokens is not None:
            output["total_tokens"] = result.total_tokens
        return output

    return generate_answer
