"""
Module: agent
File responsibility (llm.py): thin wrapper around the chat LLM call --
the ONLY place in the codebase that calls the LLM's chat/completion API.
Mirrors core/ai/embeddings.py's role for embeddings. Centralizing this
makes provider-swapping (docs/adr/ADR-009, added later) and cost/latency
instrumentation (docs/observability.md, Phase 9) a one-file change.
"""
import json
import time

import structlog
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.config import settings
from app.core.exceptions import AIOutputError, AIProviderUnavailableError
from app.core.reliability import retry_call

logger = structlog.get_logger(__name__)


@dataclass
class AgentAnswer:
    answer: str
    grounded: bool
    confidence: float
    latency_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass
class TicketSummary:
    title: str
    description: str


SYSTEM_PROMPT = (
    "You are a customer support assistant. Answer the user's question using ONLY the "
    "provided context. If the context does not contain enough information to answer "
    "confidently, say you don't know rather than guessing or inventing information -- "
    "this matters more than sounding helpful. If there is no context because the user "
    "is just greeting you or making small talk, respond naturally and briefly; that is "
    "not a case where you need to say you don't know. If prior conversation turns are "
    "provided, use them to understand what the user is referring to (e.g. \"it\" or "
    "\"that\" may refer to something discussed earlier), but still answer ONLY from the "
    "provided context -- prior turns give you conversational continuity, not new facts "
    "to draw on. Respond as a JSON object with exactly these keys: \"answer\" (string), "
    "\"grounded\" (boolean -- true only if your answer is fully supported by the "
    "provided context; for small talk with no context, use false), and \"confidence\" "
    "(float from 0 to 1)."
)


TICKET_SUMMARY_SYSTEM_PROMPT = (
    "You are writing a support ticket on behalf of a customer whose question the automated "
    "assistant could not confidently answer. Given the customer's question, the assistant's "
    "(insufficient) answer, and any prior conversation, write a concise ticket title (under "
    "80 characters, no trailing punctuation) and a clear description a human support agent "
    "can use to pick up the conversation without re-reading the whole transcript. Do not "
    "invent facts the customer didn't state. Respond as a JSON object with exactly these "
    "keys: \"title\" (string) and \"description\" (string)."
)


class ChatModel(ABC):
    @abstractmethod
    def answer_from_context(
        self, *, question: str, context_chunks: list[str], history: list[dict] | None = None
    ) -> AgentAnswer:
        """context_chunks may be empty (small talk, or retrieval found
        nothing) -- implementations must handle that without erroring.
        history is prior conversation turns, oldest-first, already
        bounded by modules/conversations/context.py -- may be None/empty
        for a single-turn call or the first message of a conversation."""

    @abstractmethod
    def summarize_for_ticket(
        self, *, question: str, answer: str, history: list[dict] | None = None
    ) -> TicketSummary:
        """Called only when quality_check has already decided (
        deterministically) to hand off -- this method's job is narrowly
        to write a good title/description from the conversation, NOT to
        decide whether a ticket should exist at all. See docs/tickets.md
        for why that decision boundary matters."""


class OpenAIChatModel(ChatModel):
    """Production provider. Kept deliberately thin -- one API call, no
    branching logic -- so there's as little as possible hiding behind the
    one part of this class the test suite can't exercise (this sandbox
    has no network access to api.openai.com)."""

    def __init__(self) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

    def answer_from_context(
        self, *, question: str, context_chunks: list[str], history: list[dict] | None = None
    ) -> AgentAnswer:
        context_text = "\n\n---\n\n".join(context_chunks) if context_chunks else "(no context retrieved)"
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        # Prior turns are passed as real chat messages (not flattened into
        # the prompt text) so the model's native multi-turn handling
        # applies -- this is exactly what chat-completion history is for.
        messages.extend(history or [])
        messages.append(
            {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {question}"}
        )
        started = time.perf_counter()
        try:
            response = retry_call(
                "llm.chat.completions",
            lambda: self._client.chat.completions.create(
                model=settings.llm_model,
                response_format={"type": "json_object"},
                messages=messages,
                timeout=settings.llm_timeout_seconds,
            ),
                max_attempts=settings.ai_max_attempts,
                base_delay=settings.ai_retry_base_delay_seconds,
                max_delay=settings.ai_retry_max_delay_seconds,
            )
        except Exception as exc:
            raise AIProviderUnavailableError("AI provider is temporarily unavailable") from exc
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        usage = getattr(response, "usage", None)
        logger.info(
            "ai.llm.call.completed",
            provider="openai",
            model=settings.llm_model,
            latency_ms=latency_ms,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
        )
        try:
            payload = json.loads(response.choices[0].message.content)
            answer = str(payload["answer"])
            grounded = bool(payload.get("grounded", False))
            confidence = float(payload.get("confidence", 0.0))
        except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise AIOutputError("AI returned an invalid structured response") from exc
        return AgentAnswer(
            answer=answer,
            grounded=grounded,
            confidence=confidence,
            latency_ms=latency_ms,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
        )

    def summarize_for_ticket(
        self, *, question: str, answer: str, history: list[dict] | None = None
    ) -> TicketSummary:
        messages = [{"role": "system", "content": TICKET_SUMMARY_SYSTEM_PROMPT}]
        messages.extend(history or [])
        messages.append(
            {
                "role": "user",
                "content": f"Customer's question: {question}\n\nAssistant's answer: {answer}",
            }
        )
        started = time.perf_counter()
        response = retry_call(
            "llm.chat.completions",
            lambda: self._client.chat.completions.create(
                model=settings.llm_model,
                response_format={"type": "json_object"},
                messages=messages,
                timeout=settings.llm_timeout_seconds,
            ),
            max_attempts=settings.ai_max_attempts,
            base_delay=settings.ai_retry_base_delay_seconds,
            max_delay=settings.ai_retry_max_delay_seconds,
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        usage = getattr(response, "usage", None)
        logger.info(
            "ai.llm.call.completed",
            provider="openai",
            model=settings.llm_model,
            latency_ms=latency_ms,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
        )
        logger.info(
            "ai.llm.ticket_summary.completed",
            provider="openai",
            model=settings.llm_model,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        try:
            payload = json.loads(response.choices[0].message.content)
            title = str(payload["title"]).strip()
            description = str(payload["description"]).strip()
            if not title or not description:
                raise ValueError("empty ticket summary")
        except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise AIOutputError("AI returned an invalid ticket summary") from exc
        return TicketSummary(title=title, description=description)


class FakeChatModel(ChatModel):
    """Deterministic, fully offline stand-in for tests and local dev
    without an API key. This is NOT a language model -- it's a keyword-
    overlap heuristic, only good enough to exercise the graph's ROUTING
    logic (grounded vs. not, high vs. low confidence) without a network
    call. It cannot evaluate real answer quality -- that needs the real
    provider (see docs/evaluation.md, Phase 12).

    history is accepted (to satisfy the ChatModel interface and let
    tests assert it was passed through correctly) but does NOT influence
    the fake's answer -- genuinely using conversation context to resolve
    something like "what about that?" requires real language
    understanding, which is exactly the part this fake can't provide."""

    def answer_from_context(
        self, *, question: str, context_chunks: list[str], history: list[dict] | None = None
    ) -> AgentAnswer:
        if not context_chunks:
            return AgentAnswer(
                answer="I don't have enough information in the knowledge base to answer that.",
                grounded=False,
                confidence=0.0,
            )

        # strip() removes trailing punctuation ("policy?" -> "policy") so a
        # question word actually matches its occurrence in the context --
        # without this, EVERY question ending in punctuation undercounts
        # overlap by at least one word. Found via a failing integration
        # test, not by inspection.
        question_words = {w.strip(".,!?;:\"'") for w in question.lower().split()}
        question_words = {w for w in question_words if len(w) > 2}
        combined_context = " ".join(context_chunks).lower()
        overlap = sum(1 for w in question_words if w in combined_context)

        if overlap >= 2:
            snippet = context_chunks[0][:200]
            return AgentAnswer(
                answer=f"Based on the knowledge base: {snippet}",
                grounded=True,
                confidence=min(1.0, 0.5 + 0.1 * overlap),
            )
        return AgentAnswer(
            answer="I don't have enough information in the knowledge base to answer that confidently.",
            grounded=False,
            confidence=0.2,
        )

    def summarize_for_ticket(
        self, *, question: str, answer: str, history: list[dict] | None = None
    ) -> TicketSummary:
        title = question.strip()[:80] or "Customer inquiry"
        description = (
            f"Customer asked: {question}\n\n"
            f"Automated assistant's response (could not resolve): {answer}"
        )
        return TicketSummary(title=title, description=description)


def get_chat_model() -> ChatModel:
    if settings.openai_api_key:
        return OpenAIChatModel()
    return FakeChatModel()
