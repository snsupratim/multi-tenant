"""
frontend/app.py – Streamlit frontend for the Multi-Tenant RAG SaaS
Run: streamlit run frontend/app.py
"""
import time
import streamlit as st
from datetime import datetime

# Must be first Streamlit call
st.set_page_config(
    page_title="DocMind · RAG SaaS",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from frontend.api_client import APIClient

# ─── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Root theme ── */
:root {
    --bg: #0a0e1a;
    --surface: #111827;
    --surface2: #1a2236;
    --border: #1e2d45;
    --accent: #3b82f6;
    --accent2: #6366f1;
    --green: #10b981;
    --amber: #f59e0b;
    --red: #ef4444;
    --text: #e2e8f0;
    --muted: #64748b;
}

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}

/* Main area */
.main .block-container {
    padding-top: 1.5rem;
    max-width: 1100px;
}

/* ── Cards ── */
.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}

.card-accent {
    border-left: 3px solid var(--accent);
}

/* ── Metric tiles ── */
.metric-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.75rem;
    margin-bottom: 1.5rem;
}

.metric-tile {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
}

.metric-tile .value {
    font-size: 2rem;
    font-weight: 700;
    color: var(--accent);
    line-height: 1;
}

.metric-tile .label {
    font-size: 0.75rem;
    color: var(--muted);
    margin-top: 0.25rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* ── Status badges ── */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.badge-ready   { background: rgba(16,185,129,.15); color: #10b981; border: 1px solid #10b981; }
.badge-processing { background: rgba(245,158,11,.15); color: #f59e0b; border: 1px solid #f59e0b; }
.badge-error   { background: rgba(239,68,68,.15); color: #ef4444; border: 1px solid #ef4444; }

/* ── Chat bubbles ── */
.chat-user {
    display: flex;
    justify-content: flex-end;
    margin: 0.5rem 0;
}

.chat-user .bubble {
    background: var(--accent2);
    color: white;
    padding: 0.75rem 1rem;
    border-radius: 16px 16px 4px 16px;
    max-width: 75%;
    font-size: 0.92rem;
}

.chat-ai {
    display: flex;
    justify-content: flex-start;
    margin: 0.5rem 0;
}

.chat-ai .bubble {
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 0.75rem 1rem;
    border-radius: 16px 16px 16px 4px;
    max-width: 80%;
    font-size: 0.92rem;
    line-height: 1.6;
}

.chat-meta {
    font-size: 0.7rem;
    color: var(--muted);
    margin-top: 0.25rem;
    font-family: 'JetBrains Mono', monospace;
}

/* ── Source chips ── */
.source-chip {
    display: inline-block;
    background: rgba(59,130,246,.1);
    border: 1px solid rgba(59,130,246,.3);
    color: var(--accent);
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 0.72rem;
    font-family: 'JetBrains Mono', monospace;
    margin: 2px 3px;
}

/* ── Logo ── */
.logo {
    font-size: 1.4rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: var(--text);
}

.logo span { color: var(--accent); }

/* ── Inputs ── */
.stTextInput input, .stTextArea textarea {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 8px !important;
}

.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,.15) !important;
}

/* ── Buttons ── */
.stButton button {
    background: var(--accent) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-family: 'Space Grotesk', sans-serif !important;
    transition: opacity .15s;
}

.stButton button:hover { opacity: 0.88 !important; }

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: var(--surface2) !important;
    border: 1px dashed var(--border) !important;
    border-radius: 10px !important;
}

/* ── Divider ── */
hr { border-color: var(--border) !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid var(--border) !important;
}
.stTabs [data-baseweb="tab"] {
    color: var(--muted) !important;
    font-weight: 500 !important;
}
.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
}

/* Selectbox */
div[data-baseweb="select"] > div {
    background: var(--surface2) !important;
    border-color: var(--border) !important;
}
</style>
""", unsafe_allow_html=True)


# ─── Session state init ───────────────────────────────────────────────────────

def init_session():
    defaults = {
        "access_token": None,
        "username": None,
        "user_id": None,
        "chat_history": [],   # [{"role": "user"|"ai", "content": str, "meta": dict}]
        "page": "chat",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()


def get_client() -> APIClient:
    return APIClient(access_token=st.session_state.access_token)


# ─── Auth pages ───────────────────────────────────────────────────────────────

def render_login():
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown("""
        <div style='text-align:center; padding: 2rem 0 1.5rem;'>
            <div class='logo'>Doc<span>Mind</span></div>
            <p style='color:#64748b; font-size:.9rem; margin-top:.5rem;'>
                Your private AI knowledge base
            </p>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

        with tab_login:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            username = st.text_input("Username", key="login_user", placeholder="your_username")
            password = st.text_input("Password", type="password", key="login_pass", placeholder="••••••••")

            if st.button("Sign In", use_container_width=True):
                if username and password:
                    client = APIClient()
                    data, code = client.login(username, password)
                    if code == 200:
                        st.session_state.access_token = data["access_token"]
                        me, _ = APIClient(data["access_token"]).me()
                        st.session_state.username = me.get("username", username)
                        st.session_state.user_id = me.get("user_id", "")
                        st.success("Signed in!")
                        st.rerun()
                    else:
                        st.error(data.get("detail", "Login failed"))
                else:
                    st.warning("Please fill in all fields")
            st.markdown("</div>", unsafe_allow_html=True)

        with tab_register:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            r_email    = st.text_input("Email",    key="reg_email",    placeholder="you@example.com")
            r_username = st.text_input("Username", key="reg_user",     placeholder="choose_username")
            r_password = st.text_input("Password", key="reg_pass",     type="password", placeholder="min 8 chars")

            if st.button("Create Account", use_container_width=True, key="reg_btn"):
                if r_email and r_username and r_password:
                    client = APIClient()
                    data, code = client.register(r_email, r_username, r_password)
                    if code == 201:
                        st.success("Account created! Please sign in.")
                    else:
                        st.error(data.get("detail", "Registration failed"))
                else:
                    st.warning("All fields required")
            st.markdown("</div>", unsafe_allow_html=True)


# ─── Sidebar ──────────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.markdown(f"<div class='logo'>Doc<span>Mind</span></div>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:#64748b; font-size:.8rem; margin:0 0 1.2rem;'>Signed in as <b>{st.session_state.username}</b></p>", unsafe_allow_html=True)
        st.divider()

        # Nav
        pages = {
            "💬 Chat":      "chat",
            "📁 Documents": "documents",
            "📊 Dashboard": "dashboard",
            "📜 History":   "history",
        }
        for label, key in pages.items():
            active = st.session_state.page == key
            if st.button(
                label,
                use_container_width=True,
                key=f"nav_{key}",
                type="primary" if active else "secondary",
            ):
                st.session_state.page = key
                st.rerun()

        st.divider()

        # Quick stats
        client = get_client()
        stats, code = client.get_stats()
        if code == 200:
            st.markdown(f"""
            <div style='font-size:.78rem; color:#64748b;'>
                <div style='display:flex; justify-content:space-between; margin:.25rem 0;'>
                    <span>Docs indexed</span><b style='color:#e2e8f0'>{stats.get('document_count',0)}</b>
                </div>
                <div style='display:flex; justify-content:space-between; margin:.25rem 0;'>
                    <span>Queries today</span><b style='color:#e2e8f0'>{stats.get('queries_today',0)}</b>
                </div>
                <div style='display:flex; justify-content:space-between; margin:.25rem 0;'>
                    <span>Uploads today</span><b style='color:#e2e8f0'>{stats.get('uploads_today',0)}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()
        if st.button("🚪 Sign Out", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


# ─── Chat page ────────────────────────────────────────────────────────────────

def render_chat():
    st.markdown("## 💬 Chat with your Knowledge Base")

    # Settings expander
    with st.expander("⚙️ Generation settings", expanded=False):
        col_a, col_b = st.columns(2)
        with col_a:
            top_k = st.slider("Retrieved chunks (top_k)", 1, 10, 5)
        with col_b:
            temperature = st.slider("LLM temperature", 0.0, 1.0, 0.3, 0.05)

    # Chat history
    chat_container = st.container()
    with chat_container:
        if not st.session_state.chat_history:
            st.markdown("""
            <div class='card' style='text-align:center; padding:2rem; color:#64748b;'>
                <div style='font-size:2.5rem'>🧠</div>
                <p style='margin:.5rem 0 0;'>Ask anything about your uploaded documents</p>
                <p style='font-size:.8rem; margin:.25rem 0 0;'>Upload files in the <b>Documents</b> tab first</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.markdown(f"""
                    <div class='chat-user'>
                        <div>
                            <div class='bubble'>{msg['content']}</div>
                        </div>
                    </div>""", unsafe_allow_html=True)
                else:
                    sources_html = "".join(
                        f"<span class='source-chip'>{s}</span>"
                        for s in msg.get("meta", {}).get("sources", [])
                    )
                    meta = msg.get("meta", {})
                    st.markdown(f"""
                    <div class='chat-ai'>
                        <div>
                            <div class='bubble'>{msg['content']}</div>
                            <div class='chat-meta'>
                                ⚡ {meta.get('latency_ms','?')}ms &nbsp;·&nbsp;
                                🔢 {meta.get('tokens_used','?')} tokens
                                &nbsp;{sources_html}
                            </div>
                        </div>
                    </div>""", unsafe_allow_html=True)

    st.divider()

    # Input
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        user_input = st.text_input(
            "Message",
            key="chat_input",
            placeholder="Ask about your documents...",
            label_visibility="collapsed",
        )
    with col_btn:
        send = st.button("Send →", use_container_width=True)

    if send and user_input.strip():
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        with st.spinner("Thinking..."):
            client = get_client()
            data, code = client.query(user_input, top_k=top_k, temperature=temperature)

        if code == 200:
            st.session_state.chat_history.append({
                "role": "ai",
                "content": data["answer"],
                "meta": {
                    "sources": data.get("sources", []),
                    "latency_ms": data.get("latency_ms", 0),
                    "tokens_used": data.get("tokens_used", 0),
                },
            })
        elif code == 429:
            st.warning(data.get("detail", "Rate limit hit. Please wait."))
        else:
            st.error(data.get("detail", "Query failed"))

        st.rerun()

    if st.session_state.chat_history:
        if st.button("🗑️ Clear chat"):
            st.session_state.chat_history = []
            st.rerun()


# ─── Documents page ───────────────────────────────────────────────────────────

def render_documents():
    st.markdown("## 📁 Knowledge Base Documents")

    # Upload section
    st.markdown("<div class='card card-accent'>", unsafe_allow_html=True)
    st.markdown("**Upload Documents**")
    uploaded = st.file_uploader(
        "Drop files here",
        type=["pdf", "txt", "docx"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    if uploaded:
        if st.button(f"Upload {len(uploaded)} file(s)", type="primary"):
            client = get_client()
            for f in uploaded:
                with st.spinner(f"Uploading {f.name}..."):
                    data, code = client.upload_document(f.read(), f.name)
                if code == 202:
                    st.success(f"✓ {f.name} queued for processing")
                elif code == 429:
                    st.warning(f"⚠️ Daily upload limit reached")
                    break
                else:
                    st.error(f"✗ {f.name}: {data.get('detail', 'Upload failed')}")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # Document list
    client = get_client()
    docs, code = client.list_documents()

    if code != 200:
        st.error("Failed to load documents")
        return

    if not docs:
        st.info("No documents yet. Upload your first file above.")
        return

    st.markdown(f"**{len(docs)} document(s) in your knowledge base**")
    st.divider()

    for doc in docs:
        status = doc.get("status", "unknown")
        badge_cls = {
            "ready": "badge-ready",
            "processing": "badge-processing",
            "error": "badge-error",
        }.get(status, "badge-processing")

        col_name, col_meta, col_del = st.columns([3, 2, 1])
        with col_name:
            icon = {"pdf": "📄", "docx": "📝", "txt": "📃"}.get(doc.get("file_type",""), "📄")
            st.markdown(f"{icon} **{doc['filename']}**")
        with col_meta:
            st.markdown(
                f"<span class='badge {badge_cls}'>{status}</span> "
                f"<span style='color:#64748b; font-size:.8rem;'>{doc.get('chunk_count',0)} chunks</span>",
                unsafe_allow_html=True,
            )
        with col_del:
            if st.button("🗑️", key=f"del_{doc['doc_id']}", help="Delete document"):
                code = client.delete_document(doc["doc_id"])
                if code == 204:
                    st.success("Deleted")
                    st.rerun()
                else:
                    st.error("Delete failed")
        st.divider()


# ─── Dashboard page ───────────────────────────────────────────────────────────

def render_dashboard():
    st.markdown("## 📊 Usage Dashboard")

    client = get_client()
    stats, s_code = client.get_stats()
    ns_stats, n_code = client.get_namespace_stats()

    if s_code == 200:
        st.markdown(f"""
        <div class='metric-row'>
            <div class='metric-tile'>
                <div class='value'>{stats.get('document_count', 0)}</div>
                <div class='label'>Documents</div>
            </div>
            <div class='metric-tile'>
                <div class='value'>{stats.get('queries_today', 0)}</div>
                <div class='label'>Queries Today</div>
            </div>
            <div class='metric-tile'>
                <div class='value'>{stats.get('total_queries', 0)}</div>
                <div class='label'>Total Queries</div>
            </div>
            <div class='metric-tile'>
                <div class='value'>{stats.get('total_uploads', 0)}</div>
                <div class='label'>Total Uploads</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if n_code == 200:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("**Pinecone Namespace**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Vectors indexed", ns_stats.get("vector_count", 0))
        with col2:
            st.metric("Queries left (this min)", ns_stats.get("queries_remaining_this_minute", "?"))
        with col3:
            st.metric("Plan", ns_stats.get("plan", "free").upper())
        st.markdown(f"<p style='font-size:.78rem; color:#64748b; margin-top:.5rem;'>Namespace: <code>{ns_stats.get('namespace','')}</code></p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


# ─── History page ─────────────────────────────────────────────────────────────

def render_history():
    st.markdown("## 📜 Query History")

    client = get_client()
    history, code = client.query_history(limit=50)

    if code != 200:
        st.error("Failed to load history")
        return

    if not history:
        st.info("No query history yet.")
        return

    for item in history:
        with st.expander(f"🔍 {item['query'][:80]}...", expanded=False):
            st.markdown(f"**Answer:** {item['answer']}")
            if item.get("sources"):
                sources_html = "".join(f"<span class='source-chip'>{s}</span>" for s in item["sources"])
                st.markdown(f"**Sources:** {sources_html}", unsafe_allow_html=True)
            st.markdown(
                f"<span style='font-size:.75rem; color:#64748b;'>"
                f"⚡ {item['latency_ms']}ms · 🔢 {item['tokens_used']} tokens · "
                f"🕐 {item['created_at'][:16].replace('T',' ')}"
                f"</span>",
                unsafe_allow_html=True,
            )


# ─── App router ───────────────────────────────────────────────────────────────

def main():
    if not st.session_state.access_token:
        render_login()
    else:
        render_sidebar()
        page = st.session_state.page
        if page == "chat":
            render_chat()
        elif page == "documents":
            render_documents()
        elif page == "dashboard":
            render_dashboard()
        elif page == "history":
            render_history()


if __name__ == "__main__":
    main()
