import streamlit as st
from app.rag_engine import build_vectordb, query_rag
from app.log_parser import parse_and_analyze

# Page config
st.set_page_config(
    page_title="TelecomRAG",
    layout="wide",
)

st.title("📡 TelecomRAG")
st.markdown("Telecom call flow diagnostics")


@st.cache_resource
def load_db():
    """Load vector DB once, cache it across all users/sessions."""
    return build_vectordb()


vectordb = load_db()

tab1, tab2, tab3, tab4 = st.tabs(["Overview", " Log Analysis", " Spec Query", " About"])

# --- Tab 1: Overview ---
with tab1:
    st.subheader("Welcome to TelecomRAG")
    st.markdown("""
    **TelecomRAG** is an AI-powered tool for diagnosing telecom call flow issues 
    using Retrieval-Augmented Generation (RAG). It automatically analyzes SIP/MSRP 
    call logs, identifies failures, and generates root cause analysis by searching 
    telecom protocol specifications.
    
    **How it works:**
    1. Paste your call logs or upload a log file
    2. The system parses the logs to identify the call flow and any failures
    3. It generates a question based on the failure and searches telecom specs
    4. An LLM generates a diagnosis with references to relevant spec sections
    
    **Use Cases:**
    - Debugging failed SIP/MSRP calls without manually reading RFCs
    - Quickly understanding what specific SIP responses mean in context
    - Learning about telecom protocols through interactive Q&A
    
    **Get Started:**
    Navigate to the "Log Analysis" tab to analyze your call logs or the "Spec Query" tab to ask direct questions about telecom protocols.
    """)


# --- Tab 2: Log Analysis ---
with tab2:
    st.subheader("Paste Call Logs")
    st.markdown("Paste your SIP/MSRP call logs below. The system will "
                "identify the failure and diagnose it using telecom specs.")

    sample_logs = """2026-06-17 14:32:10 SENT SIP INVITE sip:bob@ims.example.com Call-ID:call-001@ims From:<alice@ims.example.com> To:<bob@ims.example.com>
2026-06-17 14:32:10 RECV SIP 100 Trying Call-ID:call-001@ims
2026-06-17 14:32:11 RECV SIP 180 Ringing Call-ID:call-001@ims
2026-06-17 14:32:15 RECV SIP 408 Request Timeout Call-ID:call-001@ims"""

    logs_input = st.text_area(
        "Call Logs",
        value="",
        height=200,
        placeholder=sample_logs,
    )

    # File upload option
    uploaded_file = st.file_uploader(
        "Or upload a log file",
        type=["txt", "log"],
    )

    if uploaded_file:
        logs_input = uploaded_file.read().decode("utf-8")
        st.text_area("File contents", value=logs_input, height=150, disabled=True)

    if st.button("🔍 Analyze Logs", type="primary", disabled=not logs_input.strip()):
        with st.spinner("Parsing logs and searching specs..."):
            # Step 1: Parse
            analysis = parse_and_analyze(logs_input)

            if not analysis.messages:
                st.error("Could not parse any SIP messages. Check the log format.")
            else:
                # Show call flow
                st.subheader("Call Flow")
                st.code(analysis.call_flow_summary)

                # Show failure if detected
                if analysis.failure_point:
                    st.error(
                        f"**Failure Detected:** {analysis.failure_point.status_code} "
                        f"{analysis.failure_point.status_text}"
                    )
                else:
                    st.success("No failure detected in the call flow.")

                # Step 2: RAG diagnosis
                result = query_rag(vectordb, analysis.rag_question)

                st.subheader("Diagnosis")
                st.markdown(result["diagnosis"])

                # Show sources
                st.subheader("Spec References")
                for src in result["sources"]:
                    st.markdown(
                        f"- **{src['file']}**, Page {src['page']}"
                    )

# --- Tab 3: Direct Spec Query ---
with tab3:
    st.subheader("Ask a Question")
    st.markdown("Ask anything about SIP, MSRP, Diameter, IMS, CPM, or RCS protocols.")

    question = st.text_input(
        "Your question",
        placeholder="What does a SIP 486 Busy Here response mean?",
    )

    if st.button("🔍 Search Specs", type="primary", disabled=not question.strip()):
        with st.spinner("Searching telecom specs..."):
            result = query_rag(vectordb, question)

            st.subheader("Answer")
            st.markdown(result["diagnosis"])

            st.subheader("Spec References")
            for src in result["sources"]:
                st.markdown(
                    f"- **{src['file']}**, Page {src['page']}"
                )

# --- Tab 4: About ---
with tab4:
    st.subheader("About the Developer")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### Harsathabinav Anusuya Suresh")
        st.markdown("[GitHub](https://github.com/ASH2090?tab=repositories) · [LinkedIn](https://www.linkedin.com/in/harsathabinav-a-s-b57b64179/)")
    
    with col2:
        st.markdown("""
        MS Computer Science graduate from Governors State University 
        with 4+ years of production experience in telecom software engineering 
        at Mavenir Systems.
                    
        **Why I built TelecomRAG:**  
        After spending years manually debugging SIP/MSRP call flows by 
        cross-referencing RFC specs line by line, I built the tool I wish 
        I had when I started. TelecomRAG uses RAG (Retrieval-Augmented Generation) 
        to automatically diagnose call failures by searching telecom protocol 
        specifications and generating root cause analysis with spec references.
        
        **Other Projects:**
        - **NetTriage AI** — Multi-agent log triage system using LangGraph 
          with conditional routing for automated incident reporting
        - **SentraNET AI** — AI-powered network intrusion detection system 
          using hybrid rule engine + Llama 3.1
        
        **Tech Stack:**  
        Python, FastAPI, LangChain, Chroma, HuggingFace, Groq/Llama 3.1, 
        Docker, Kubernetes, GitHub Actions, SIP, MSRP, Diameter, IMS
        """)
    
    st.markdown("---")
    st.markdown(
        "<center><small>TelecomRAG v1.0 — Built by Harsathabinav A.S.</small></center>",
        unsafe_allow_html=True,
    )