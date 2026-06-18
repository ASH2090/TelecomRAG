import re
from dataclasses import dataclass


@dataclass
class SIPMessage:
    """One parsed SIP message from the logs."""
    timestamp: str
    direction: str       # SENT or RECEIVED
    method: str          # INVITE, BYE, REGISTER, etc. (for requests)
    status_code: int     # 200, 408, 481, etc. (for responses, 0 for requests)
    status_text: str     # "OK", "Request Timeout", etc.
    call_id: str
    from_uri: str
    to_uri: str
    raw_text: str        # Original log text for this message


@dataclass
class CallFlowAnalysis:
    """Result of parsing a complete call's logs."""
    call_id: str
    messages: list               # List of SIPMessage objects
    failure_point: SIPMessage    # The message where it went wrong (None if no failure)
    call_flow_summary: str       # Human-readable summary of the flow
    rag_question: str            # Auto-generated question for RAG


# SIP response codes that indicate failures
ERROR_CODES = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    408: "Request Timeout",
    480: "Temporarily Unavailable",
    481: "Call/Transaction Does Not Exist",
    486: "Busy Here",
    487: "Request Terminated",
    488: "Not Acceptable Here",
    500: "Server Internal Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Server Timeout",
}


def parse_sip_logs(raw_logs: str) -> list:
    """
    Parse raw SIP log text into a list of SIPMessage objects.

    Expected log format (common IMS format):
    2026-06-17 14:32:10 SENT SIP INVITE sip:bob@ims.example.com Call-ID:abc123 From:<alice@ims.example.com> To:<bob@ims.example.com>
    2026-06-17 14:32:10 RECV SIP 100 Trying Call-ID:abc123
    2026-06-17 14:32:11 RECV SIP 200 OK Call-ID:abc123

    This format is a placeholder — update the regex patterns when you
    get the actual log format from your senior.
    """
    messages = []

    # Pattern for SIP requests (INVITE, BYE, REGISTER, etc.)
    request_pattern = re.compile(
        r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+"
        r"(?P<direction>SENT|RECV)\s+SIP\s+"
        r"(?P<method>INVITE|ACK|BYE|CANCEL|REGISTER|OPTIONS|PRACK|UPDATE|REFER|SUBSCRIBE|NOTIFY|MESSAGE|INFO)\s+"
        r"(?P<uri>\S+)\s+"
        r"Call-ID:(?P<call_id>\S+)"
        r"(?:\s+From:<?(?P<from_uri>[^>]+)>?)?"
        r"(?:\s+To:<?(?P<to_uri>[^>]+)>?)?",
        re.IGNORECASE
    )

    # Pattern for SIP responses (100, 200, 408, etc.)
    response_pattern = re.compile(
        r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+"
        r"(?P<direction>SENT|RECV)\s+SIP\s+"
        r"(?P<status_code>\d{3})\s+(?P<status_text>[^\n]+?)\s+"
        r"Call-ID:(?P<call_id>\S+)",
        re.IGNORECASE
    )

    for line in raw_logs.strip().splitlines():
        line = line.strip()
        if not line:
            continue

        # Try matching as a response first (has status code)
        match = response_pattern.match(line)
        if match:
            messages.append(SIPMessage(
                timestamp=match.group("timestamp"),
                direction=match.group("direction").upper(),
                method="",
                status_code=int(match.group("status_code")),
                status_text=match.group("status_text").strip(),
                call_id=match.group("call_id"),
                from_uri="",
                to_uri="",
                raw_text=line,
            ))
            continue

        # Try matching as a request (has method name)
        match = request_pattern.match(line)
        if match:
            messages.append(SIPMessage(
                timestamp=match.group("timestamp"),
                direction=match.group("direction").upper(),
                method=match.group("method").upper(),
                status_code=0,
                status_text="",
                call_id=match.group("call_id"),
                from_uri=match.group("from_uri") or "",
                to_uri=match.group("to_uri") or "",
                raw_text=line,
            ))
            continue

    return messages


def analyze_call_flow(messages: list) -> CallFlowAnalysis:
    """
    Analyze a list of SIP messages to identify the call flow
    and find where it failed (if it did).
    """
    if not messages:
        return CallFlowAnalysis(
            call_id="unknown",
            messages=[],
            failure_point=None,
            call_flow_summary="No SIP messages found in logs.",
            rag_question="No messages to analyze.",
        )

    call_id = messages[0].call_id

    # Find the first error response (4xx or 5xx)
    failure_point = None
    for msg in messages:
        if msg.status_code >= 400:
            failure_point = msg
            break

    # Build human-readable call flow summary
    summary_lines = []
    for i, msg in enumerate(messages, 1):
        if msg.method:
            summary_lines.append(
                f"Step {i}: {msg.direction} {msg.method} "
                f"({msg.timestamp})"
            )
        else:
            status_marker = " *** FAILURE ***" if msg.status_code >= 400 else ""
            summary_lines.append(
                f"Step {i}: {msg.direction} {msg.status_code} "
                f"{msg.status_text} ({msg.timestamp}){status_marker}"
            )

    call_flow_summary = "\n".join(summary_lines)

    # Auto-generate a targeted question for RAG
    if failure_point:
        rag_question = (
            f"A SIP call with Call-ID {call_id} failed. "
            f"The call flow was:\n{call_flow_summary}\n\n"
            f"The failure occurred at step where a "
            f"{failure_point.status_code} {failure_point.status_text} "
            f"response was received. "
            f"What does this error mean in the context of this call flow, "
            f"what is the likely root cause, and how should it be fixed?"
        )
    else:
        rag_question = (
            f"A SIP call with Call-ID {call_id} completed. "
            f"The call flow was:\n{call_flow_summary}\n\n"
            f"Does this call flow look correct according to the SIP "
            f"specification? Are there any missing steps or potential issues?"
        )

    return CallFlowAnalysis(
        call_id=call_id,
        messages=messages,
        failure_point=failure_point,
        call_flow_summary=call_flow_summary,
        rag_question=rag_question,
    )


def parse_and_analyze(raw_logs: str) -> CallFlowAnalysis:
    """Convenience function: parse logs and analyze in one call."""
    messages = parse_sip_logs(raw_logs)
    return analyze_call_flow(messages)


# --- Quick standalone test ---
if __name__ == "__main__":
    sample_logs = """2026-06-17 14:32:10 SENT SIP INVITE sip:bob@ims.example.com Call-ID:call-001@ims From:<alice@ims.example.com> To:<bob@ims.example.com>
2026-06-17 14:32:10 RECV SIP 100 Trying Call-ID:call-001@ims
2026-06-17 14:32:11 RECV SIP 180 Ringing Call-ID:call-001@ims
2026-06-17 14:32:15 RECV SIP 408 Request Timeout Call-ID:call-001@ims"""

    print("=" * 60)
    print("  Log Parser Test")
    print("=" * 60)

    analysis = parse_and_analyze(sample_logs)

    print(f"\nCall-ID: {analysis.call_id}")
    print(f"\n--- Call Flow ---")
    print(analysis.call_flow_summary)

    if analysis.failure_point:
        print(f"\n--- Failure Detected ---")
        print(f"Error: {analysis.failure_point.status_code} "
              f"{analysis.failure_point.status_text}")

    print(f"\n--- Auto-generated RAG Question ---")
    print(analysis.rag_question)