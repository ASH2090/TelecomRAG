from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from app.rag_engine import build_vectordb, query_rag
from app.log_parser import parse_and_analyze

app = FastAPI(
    title="TelecomRAG",
    description="AI-powered telecom call flow diagnostics using RAG",
    version="1.0.0",
)

# Load vector DB once at startup (not on every request)
vectordb = build_vectordb()


# --- Request/Response Models ---
class LogAnalysisRequest(BaseModel):
    """Request body for log analysis."""
    logs: str
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "logs": "2026-06-17 14:32:10 SENT SIP INVITE sip:bob@ims.example.com Call-ID:call-001@ims\n2026-06-17 14:32:10 RECV SIP 100 Trying Call-ID:call-001@ims\n2026-06-17 14:32:15 RECV SIP 408 Request Timeout Call-ID:call-001@ims"
                }
            ]
        }
    }


class QuestionRequest(BaseModel):
    """Request body for direct spec questions."""
    question: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "What does SIP 408 Request Timeout mean?"
                }
            ]
        }
    }


class DiagnosisResponse(BaseModel):
    """Response containing the RAG diagnosis."""
    call_id: Optional[str] = None
    failure_detected: bool
    failure_code: Optional[int] = None
    failure_text: Optional[str] = None
    call_flow_summary: Optional[str] = None
    diagnosis: str
    sources: list


# --- Endpoints ---
@app.get("/")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "TelecomRAG"}


@app.post("/analyze", response_model=DiagnosisResponse)
def analyze_logs(request: LogAnalysisRequest):
    """
    Analyze SIP call logs and diagnose failures.
    
    Paste raw call logs — the system parses them, identifies 
    the failure point, searches telecom specs via RAG, and 
    returns a diagnosis with spec references.
    """
    if not request.logs.strip():
        raise HTTPException(status_code=400, detail="Logs cannot be empty")

    # Step 1: Parse logs and identify failure
    analysis = parse_and_analyze(request.logs)

    if not analysis.messages:
        raise HTTPException(
            status_code=400,
            detail="Could not parse any SIP messages from the provided logs. "
                   "Check the log format."
        )

    # Step 2: Query RAG with auto-generated question
    result = query_rag(vectordb, analysis.rag_question)

    # Step 3: Build response
    return DiagnosisResponse(
        call_id=analysis.call_id,
        failure_detected=analysis.failure_point is not None,
        failure_code=analysis.failure_point.status_code if analysis.failure_point else None,
        failure_text=analysis.failure_point.status_text if analysis.failure_point else None,
        call_flow_summary=analysis.call_flow_summary,
        diagnosis=result["diagnosis"],
        sources=result["sources"],
    )


@app.post("/query")
def query_specs(request: QuestionRequest):
    """
    Ask a direct question about telecom specs.
    
    Ask anything about SIP, MSRP, Diameter, IMS, CPM, or RCS 
    protocols — the system searches the loaded specs and answers 
    based on the actual documentation.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    result = query_rag(vectordb, request.question)

    return {
        "question": request.question,
        "diagnosis": result["diagnosis"],
        "sources": result["sources"],
    }


@app.post("/analyze/file")
async def analyze_log_file(file: UploadFile = File(...)):
    """
    Upload a log file for analysis.
    
    Accepts .txt or .log files containing SIP call logs.
    """
    if not file.filename.endswith((".txt", ".log")):
        raise HTTPException(
            status_code=400,
            detail="Only .txt and .log files are supported"
        )

    content = await file.read()
    logs_text = content.decode("utf-8")

    if not logs_text.strip():
        raise HTTPException(status_code=400, detail="File is empty")

    analysis = parse_and_analyze(logs_text)

    if not analysis.messages:
        raise HTTPException(
            status_code=400,
            detail="Could not parse any SIP messages from the uploaded file"
        )

    result = query_rag(vectordb, analysis.rag_question)

    return DiagnosisResponse(
        call_id=analysis.call_id,
        failure_detected=analysis.failure_point is not None,
        failure_code=analysis.failure_point.status_code if analysis.failure_point else None,
        failure_text=analysis.failure_point.status_text if analysis.failure_point else None,
        call_flow_summary=analysis.call_flow_summary,
        diagnosis=result["diagnosis"],
        sources=result["sources"],
    )