from app.rag_engine import build_vectordb, query_rag

db = build_vectordb()

questions = [
    "If one user is not reg and the sip invite is sent and stored in DB and later when the user comes online what does SIP do",]

for q in questions:
    print("=" * 60)
    print(f"Q: {q}\n")
    result = query_rag(db, q)
    print(result["diagnosis"])
    print("\nSources:")
    for s in result["sources"]:
        print(f"  {s['file']}, Page {s['page']}")
    print()