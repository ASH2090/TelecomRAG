import os
from pathlib import Path
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq

load_dotenv()

# --- Configuration ---
SPECS_DIR = Path("data/specs")
VECTORDB_DIR = Path("vectordb")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
LLM_MODEL = "llama-3.1-8b-instant"


def load_specs() -> list:
    """Load all PDF files from the specs directory."""
    all_docs = []
    pdf_files = list(SPECS_DIR.glob("*.pdf"))

    if not pdf_files:
        print("WARNING: No PDF files found in data/specs/")
        return []

    for pdf_path in pdf_files:
        print(f"Loading: {pdf_path.name}")
        loader = PyPDFLoader(str(pdf_path))
        docs = loader.load()

        for doc in docs:
            doc.metadata["source_file"] = pdf_path.name

        all_docs.extend(docs)
        print(f"  Loaded {len(docs)} pages from {pdf_path.name}")

    print(f"Total pages loaded: {len(all_docs)}")
    return all_docs


def chunk_documents(docs: list) -> list:
    """Split documents into smaller chunks for better retrieval."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    print(f"Split into {len(chunks)} chunks")
    return chunks


def get_embeddings():
    """Initialize the local embedding model (free, no API calls)."""
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def build_vectordb(force_rebuild: bool = False) -> Chroma:
    """Build or load the Chroma vector database."""
    embeddings = get_embeddings()

    if VECTORDB_DIR.exists() and not force_rebuild:
        print("Loading existing vector database...")
        return Chroma(
            persist_directory=str(VECTORDB_DIR),
            embedding_function=embeddings,
        )

    print("Building vector database from specs...")
    docs = load_specs()

    if not docs:
        raise ValueError("No documents loaded. Add PDF files to data/specs/")

    chunks = chunk_documents(docs)

    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(VECTORDB_DIR),
    )

    print(f"Vector database built with {len(chunks)} chunks")
    return vectordb


def get_llm():
    """Initialize Groq LLM."""
    return ChatGroq(
        model=LLM_MODEL,
        api_key=GROQ_API_KEY,
        temperature=0,
    )


TELECOM_PROMPT = """You are a senior telecom engineer specializing in IMS, SIP, MSRP, 
Diameter, CPM, and RCS protocols.

You are given relevant sections from telecom protocol specifications (RFCs, 3GPP docs)
and a question about a call flow issue or log analysis.

Use ONLY the provided spec sections to answer. If the answer is not in the provided 
context, say so — do not make up information.

Always include:
1. What went wrong (the specific failure)
2. Why it happened (root cause based on the specs)
3. Which spec section is relevant (document name + section number if visible)
4. Suggested fix

Relevant spec sections:
{context}

Question:
{question}

Diagnosis:"""


def query_rag(vectordb: Chroma, question: str) -> dict:
    """
    The complete RAG pipeline in one function:
    1. Search vector DB for relevant spec chunks (RETRIEVAL)
    2. Combine question + chunks into one prompt (AUGMENTED)
    3. Send to LLM to generate diagnosis (GENERATION)
    """
    # Step 1: RETRIEVAL — find the 5 most relevant spec sections
    retriever = vectordb.as_retriever(search_kwargs={"k": 5})
    retrieved_docs = retriever.invoke(question)

    # Step 2: AUGMENTED — combine retrieved sections into context
    context = "\n\n---\n\n".join(
        f"[Source: {doc.metadata.get('source_file', 'Unknown')}, "
        f"Page: {doc.metadata.get('page', '?')}]\n{doc.page_content}"
        for doc in retrieved_docs
    )

    # Build the full prompt with context + question
    prompt = TELECOM_PROMPT.format(context=context, question=question)

    # Step 3: GENERATION — LLM generates diagnosis based on context
    llm = get_llm()
    response = llm.invoke(prompt)

    # Extract source info for transparency
    sources = []
    for doc in retrieved_docs:
        sources.append({
            "file": doc.metadata.get("source_file", "Unknown"),
            "page": doc.metadata.get("page", "Unknown"),
            "content_preview": doc.page_content[:200] + "...",
        })

    return {
        "diagnosis": response.content,
        "sources": sources,
    }


# --- Quick standalone test ---
if __name__ == "__main__":
    print("=" * 60)
    print("  TelecomRAG — Building Vector Database")
    print("=" * 60)

    vectordb = build_vectordb(force_rebuild=True)

    test_question = "What does a SIP 408 Request Timeout response mean and when is it sent?"

    print("\n" + "=" * 60)
    print("  Test Query")
    print("=" * 60)
    print(f"Question: {test_question}\n")

    result = query_rag(vectordb, test_question)

    print("--- Diagnosis ---")
    print(result["diagnosis"])

    print("\n--- Sources Used ---")
    for src in result["sources"]:
        print(f"  File: {src['file']}, Page: {src['page']}")