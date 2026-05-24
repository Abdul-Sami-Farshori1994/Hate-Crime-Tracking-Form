import json
import logging

from logging_config import JsonLogFormatter, RedactSensitiveFilter, request_id_ctx


def test_json_formatter_includes_request_id():
    token = request_id_ctx.set("test-req-id")
    try:
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="hello",
            args=(),
            exc_info=None,
        )
        record.request_id = request_id_ctx.get()  # type: ignore[attr-defined]
        line = JsonLogFormatter().format(record)
        data = json.loads(line)
        assert data["message"] == "hello"
        assert data["request_id"] == "test-req-id"
    finally:
        request_id_ctx.reset(token)


def test_redact_sensitive_filter():
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="login failed password=supersecret",
        args=(),
        exc_info=None,
    )
    assert RedactSensitiveFilter().filter(record) is True
    assert "supersecret" not in record.getMessage()
