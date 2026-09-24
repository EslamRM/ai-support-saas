"""Unit tests for the bounded conversation history strategy -- no DB,
constructed Message objects directly."""
from app.modules.conversations.context import build_bounded_history
from app.modules.conversations.models import Message, MessageRole


def _msg(role: MessageRole, content: str) -> Message:
    m = Message(role=role, content=content)
    return m


def test_empty_history_returns_empty_list():
    assert build_bounded_history([]) == []


def test_short_history_is_returned_in_full_and_in_order():
    messages = [
        _msg(MessageRole.USER, "Hi"),
        _msg(MessageRole.ASSISTANT, "Hello! How can I help?"),
        _msg(MessageRole.USER, "What are your hours?"),
    ]

    result = build_bounded_history(messages, max_tokens=1000)

    assert result == [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello! How can I help?"},
        {"role": "user", "content": "What are your hours?"},
    ]


def test_long_history_is_trimmed_to_the_most_recent_messages():
    # Each message is long enough that only a few fit in a small budget.
    messages = [_msg(MessageRole.USER, " ".join(["word"] * 50)) for _ in range(20)]

    result = build_bounded_history(messages, max_tokens=100)

    assert len(result) < len(messages)
    # The LAST message in the trimmed result must be the most recent
    # original message -- trimming drops from the front (oldest), never
    # the back (most recent).
    assert result[-1]["content"] == messages[-1].content


def test_a_single_oversized_message_is_still_returned_alone():
    """Better to return one over-budget message than an empty history --
    see the docstring in context.py."""
    huge_message = _msg(MessageRole.USER, " ".join(["word"] * 10000))

    result = build_bounded_history([huge_message], max_tokens=10)

    assert len(result) == 1
    assert result[0]["content"] == huge_message.content


def test_history_preserves_role_information():
    messages = [
        _msg(MessageRole.USER, "question one"),
        _msg(MessageRole.ASSISTANT, "answer one"),
    ]
    result = build_bounded_history(messages, max_tokens=1000)
    assert result[0]["role"] == "user"
    assert result[1]["role"] == "assistant"
