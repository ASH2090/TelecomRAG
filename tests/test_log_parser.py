"""Tests for the SIP log parser."""
from app.log_parser import parse_and_analyze, parse_sip_logs

def test_parse_sip_request():
    logs = "2026-06-17 14:32:10 SENT SIP INVITE sip:bob@ims.example.com Call-ID:call-001@ims"
    messages = parse_sip_logs(logs)
    assert len(messages) == 1
    assert messages[0].method == "INVITE"
    assert messages[0].direction == "SENT"
    assert messages[0].call_id == "call-001@ims"


def test_parse_sip_response():
    logs = "2026-06-17 14:32:10 RECV SIP 200 OK Call-ID:call-001@ims"
    messages = parse_sip_logs(logs)
    assert len(messages) == 1
    assert messages[0].status_code == 200
    assert messages[0].status_text == "OK"


def test_parse_error_response():
    logs = "2026-06-17 14:32:15 RECV SIP 408 Request Timeout Call-ID:call-001@ims"
    messages = parse_sip_logs(logs)
    assert len(messages) == 1
    assert messages[0].status_code == 408


def test_detect_failure():
    logs = """2026-06-17 14:32:10 SENT SIP INVITE sip:bob@ims.example.com Call-ID:call-001@ims
2026-06-17 14:32:10 RECV SIP 100 Trying Call-ID:call-001@ims
2026-06-17 14:32:15 RECV SIP 408 Request Timeout Call-ID:call-001@ims"""
    analysis = parse_and_analyze(logs)
    assert analysis.failure_point is not None
    assert analysis.failure_point.status_code == 408
    assert "408" in analysis.rag_question


def test_no_failure_on_success():
    logs = """2026-06-17 14:32:10 SENT SIP INVITE sip:bob@ims.example.com Call-ID:call-001@ims
2026-06-17 14:32:10 RECV SIP 100 Trying Call-ID:call-001@ims
2026-06-17 14:32:11 RECV SIP 200 OK Call-ID:call-001@ims"""
    analysis = parse_and_analyze(logs)
    assert analysis.failure_point is None


def test_empty_logs():
    analysis = parse_and_analyze("")
    assert len(analysis.messages) == 0


def test_call_flow_summary():
    logs = """2026-06-17 14:32:10 SENT SIP INVITE sip:bob@ims.example.com Call-ID:call-001@ims
2026-06-17 14:32:10 RECV SIP 100 Trying Call-ID:call-001@ims
2026-06-17 14:32:11 RECV SIP 180 Ringing Call-ID:call-001@ims
2026-06-17 14:32:15 RECV SIP 408 Request Timeout Call-ID:call-001@ims"""
    analysis = parse_and_analyze(logs)
    assert "INVITE" in analysis.call_flow_summary
    assert "FAILURE" in analysis.call_flow_summary
    assert analysis.call_id == "call-001@ims"