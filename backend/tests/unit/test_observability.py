from app.core.logging import get_request_id, set_request_id


def test_request_id_context_is_available_to_logging():
    set_request_id("test-request")
    assert get_request_id() == "test-request"
