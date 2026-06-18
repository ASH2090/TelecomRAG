from app.rag_engine import build_vectordb, query_rag
from app.log_parser import parse_and_analyze

# Load existing vector DB (instant, already built)
db = build_vectordb()

# Simulate a failed call's logs
failed_call_logs = """2026-06-17 14:32:10 SENT SIP INVITE sip:bob@ims.example.com Call-ID:call-001@ims From:<alice@ims.example.com> To:<bob@ims.example.com>
2026-06-17 14:32:10 RECV SIP 100 Trying Call-ID:call-001@ims
2026-06-17 14:32:11 RECV SIP 180 Ringing Call-ID:call-001@ims
2026-06-17 14:32:15 RECV SIP 408 Request Timeout Call-ID:call-001@ims"""

print("=" * 60)
print("  TelecomRAG — Full Pipeline Test")
print("  Logs → Parser → RAG → Diagnosis")
print("=" * 60)

# Step 1: Parse the logs
print("\n--- Step 1: Parsing Logs ---")
analysis = parse_and_analyze(failed_call_logs)
print(f"Call-ID: {analysis.call_id}")
print(f"Failure: {analysis.failure_point.status_code} {analysis.failure_point.status_text}")

# Step 2: Feed auto-generated question to RAG
print("\n--- Step 2: Querying RAG ---")
print("(Searching specs for relevant sections...)\n")
result = query_rag(db, analysis.rag_question)

# Step 3: Display the diagnosis
print("--- Diagnosis ---")
print(result["diagnosis"])

print("\n--- Spec References ---")
for src in result["sources"]:
    print(f"  {src['file']}, Page {src['page']}")