import os
import pytest

GROQ_KEY_PRESENT = bool(os.getenv("GROQ_API_KEY"))


@pytest.fixture(autouse=True)
def skip_if_no_api_key():
    if not GROQ_KEY_PRESENT:
        pytest.skip("GROQ_API_KEY not set")


def test_build_vectordb():
    from tests.create_test_spec import create_test_spec
    create_test_spec()
    from app.rag_engine import build_vectordb
    db = build_vectordb(force_rebuild=True)
    assert db is not None


def test_query_rag():
    from app.rag_engine import build_vectordb, query_rag
    db = build_vectordb()
    result = query_rag(db, "What does SIP 408 Request Timeout mean?")
    assert "diagnosis" in result
    assert "sources" in result
    assert len(result["diagnosis"]) > 0


def test_query_rag_481():
    from app.rag_engine import build_vectordb, query_rag
    db = build_vectordb()
    result = query_rag(db, "What does a 481 response mean for a BYE request?")
    assert "diagnosis" in result
    assert len(result["sources"]) > 0