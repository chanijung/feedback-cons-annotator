import html
import logging

import streamlit as st
import pandas as pd
import json
import re
import ast
from datetime import datetime, timezone
from pathlib import Path

# Google Sheets integration (gspread + Service Account)
import gspread
from google.oauth2 import service_account

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Feedback Consensus Annotator",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

:root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #22263a;
    --border: #2e3250;
    --accent: #5b8dee;
    --accent2: #e05b8d;
    --text: #d4d8f0;
    --text-dim: #7a7f9a;
    --highlight: rgba(91, 141, 238, 0.25);
    --checked-bg: rgba(91, 141, 238, 0.12);
    --checked-border: #5b8dee;
    --radius: 10px;
}

html, body, .stApp {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'IBM Plex Sans', sans-serif;
}

/* Hide default streamlit chrome */
#MainMenu, footer, header { display: none !important; }
.block-container { padding: 1.2rem 1.5rem !important; max-width: 100% !important; }

/* ── Top bar ── */
.top-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.6rem 1rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    margin-bottom: 1rem;
}
.top-bar h1 {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--accent);
    margin: 0;
    letter-spacing: 0.02em;
}
.progress-info {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem;
    color: var(--text-dim);
}

/* ── Progress bar ── */
.progress-wrap {
    background: var(--border);
    border-radius: 4px;
    height: 5px;
    width: 160px;
    display: inline-block;
    vertical-align: middle;
    margin-left: 0.5rem;
}
.progress-fill {
    height: 100%;
    background: var(--accent);
    border-radius: 4px;
    transition: width 0.4s ease;
}

/* ── Paper selector ── */
.stSelectbox > div > div {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    color: var(--text) !important;
    font-family: 'IBM Plex Sans', sans-serif;
}

/* ── Anchor panel ── */
.anchor-panel {
    background: var(--surface);
    border: 1.5px solid var(--accent);
    border-radius: var(--radius);
    padding: 1.2rem;
    position: sticky;
    top: 0.5rem;
    box-shadow: 0 0 20px rgba(91, 141, 238, 0.1);
}
.anchor-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 0.5rem;
    font-weight: 600;
}
.anchor-idx {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem;
    color: var(--text-dim);
    margin-bottom: 0.5rem;
}
.anchor-text {
    font-size: 0.92rem;
    line-height: 1.65;
    color: var(--text);
}

/* ── Feedback card ── */
.feedback-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.9rem 1rem;
    margin-bottom: 0.6rem;
    transition: border-color 0.2s, background 0.2s;
}
.feedback-card.checked {
    background: var(--checked-bg);
    border-color: var(--checked-border);
}
.feedback-card.anchor-self {
    opacity: 0.35;
    pointer-events: none;
}
.card-idx {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    color: var(--text-dim);
    margin-bottom: 0.35rem;
}
.card-text {
    font-size: 0.88rem;
    line-height: 1.6;
    color: var(--text);
}
.highlight-word {
    background: rgba(91,141,238,0.28);
    color: #a8c4ff;
    border-radius: 3px;
    padding: 0 2px;
    font-weight: 500;
}

/* ── Basket ── */
.basket-wrap {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem;
    margin-top: 0.8rem;
}
.basket-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    color: var(--accent2);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.6rem;
    font-weight: 600;
}
.pair-tag {
    display: inline-block;
    background: rgba(224,91,141,0.15);
    border: 1px solid rgba(224,91,141,0.4);
    color: #f0a8c4;
    border-radius: 6px;
    padding: 0.2rem 0.55rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    margin: 0.15rem;
}

/* ── Paper info ── */
.paper-info {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem;
    margin-top: 1rem;
    max-height: 200px;
    overflow-y: auto;
}
.paper-info-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.5rem;
}
.paper-abstract {
    font-size: 0.95rem;
    line-height: 1.55;
    color: #ffffff;
    margin-bottom: 0.6rem;
}
.paper-pdf-link {
    font-size: 0.85rem;
}
.paper-pdf-link a {
    color: var(--accent);
    text-decoration: none;
}
.paper-pdf-link a:hover {
    text-decoration: underline;
}

/* ── Buttons ── */
.stButton > button {
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.83rem !important;
    border-radius: 8px !important;
    border: 1px solid var(--border) !important;
    background: var(--surface2) !important;
    color: var(--text) !important;
    transition: all 0.15s !important;
    padding: 0.4rem 1rem !important;
    font-weight: 500 !important;
}
.stButton > button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}

/* search box */
.stTextInput > div > div > input {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.82rem !important;
}

/* ── Sticky left panel, scrollable right panel ── */
[data-testid="stHorizontalBlock"]:has(.anchor-panel) {
    align-items: flex-start !important;
    max-height: calc(100vh - 180px) !important;
}
[data-testid="stHorizontalBlock"]:has(.anchor-panel) > div:first-child {
    position: sticky !important;
    top: 0.5rem !important;
    align-self: flex-start !important;
    flex-shrink: 0 !important;
}
[data-testid="stHorizontalBlock"]:has(.anchor-panel) > div:last-child {
    overflow-y: auto !important;
    max-height: calc(100vh - 180px) !important;
    flex: 1 !important;
    min-width: 0 !important;
}

/* save result area */
.save-result {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    color: var(--text-dim);
    white-space: pre-wrap;
    word-break: break-all;
}
</style>
""", unsafe_allow_html=True)

# ── STOPWORDS ─────────────────────────────────────────────────────────────────
STOPWORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of","with",
    "is","are","was","were","be","been","being","have","has","had","do","does",
    "did","will","would","could","should","may","might","shall","can","this",
    "that","these","those","it","its","by","from","as","if","into","than",
    "then","also","not","no","so","very","more","most","some","any","all",
    "each","both","such","through","about","which","what","when","where","who",
    "how","their","they","them","there","he","she","we","i","you","my","our",
    "your","his","her","its","up","out","just","been","only","over","after",
    "before","since","while","although","though","even","within","between",
    "among","during","without","whether","because","however","therefore",
    "thus","hence","while","whereas","despite","although","further","since",
    "first","second","third"
}

# ── UTILS ─────────────────────────────────────────────────────────────────────

def parse_feedbacks(raw) -> list[tuple[int, str]]:
    """Parse newline-separated numbered feedbacks → [(idx, text), ...]"""
    if pd.isna(raw) or not str(raw).strip():
        return []
    items = []
    pattern = re.compile(r'^(\d+)\.\s+(.+)', re.DOTALL)
    for line in str(raw).split('\n'):
        line = line.strip()
        m = pattern.match(line)
        if m:
            items.append((int(m.group(1)), m.group(2).strip()))
    return items


def get_keywords(text: str) -> set[str]:
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    return {w for w in words if w not in STOPWORDS}


def highlight(text: str, keywords: set[str]) -> str:
    """Wrap matching keywords in <span class='highlight-word'>"""
    if not keywords:
        return text
    pattern = re.compile(
        r'\b(' + '|'.join(re.escape(k) for k in sorted(keywords, key=len, reverse=True)) + r')\b',
        re.IGNORECASE
    )
    return pattern.sub(r"<span class='highlight-word'>\1</span>", text)


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df


def parse_existing_pairs(val) -> list[list[int]]:
    if pd.isna(val) or not str(val).strip():
        return []
    try:
        parsed = ast.literal_eval(str(val))
        if isinstance(parsed, list):
            return [list(p) for p in parsed]
    except Exception:
        pass
    return []


# ── GOOGLE SHEETS ─────────────────────────────────────────────────────────────

_SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_gsheet_client():
    """Build gspread client from Streamlit secrets. Returns None if not configured."""
    try:
        if "gcp_service_account" not in st.secrets or "SPREADSHEET_ID" not in st.secrets:
            return None
        sa = st.secrets["gcp_service_account"]
        creds_dict = dict(sa) if hasattr(sa, "keys") else sa
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=_SHEETS_SCOPES
        )
        return gspread.authorize(creds)
    except Exception:
        return None


def submit_to_gsheet(annotator_name: str) -> tuple[bool, str]:
    """Submit/update {annotator_name, paper_id, pairs, timestamp} in Google Sheet.
    If a row with same annotator_name+paper_id exists, update it; else append.
    Returns (success, message)."""
    gc = get_gsheet_client()
    if gc is None:
        return False, "Google Sheets not configured. Add gcp_service_account and SPREADSHEET_ID to Streamlit secrets."
    try:
        raw = st.secrets["SPREADSHEET_ID"].strip()
        if "/d/" in raw:
            sheet_id = raw.split("/d/")[1].split("/")[0]
        else:
            sheet_id = raw
        sheet_name = st.secrets.get("SHEET_NAME", "Sheet1")
        spreadsheet = gc.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        existing = worksheet.get_all_values()
        header = ["annotator_name", "paper_id", "pairs", "timestamp"]
        # Consider sheet "blank" if empty or all rows have only empty cells
        is_blank = not existing or all(
            all(not str(c).strip() for c in (row if isinstance(row, (list, tuple)) else [row]))
            for row in existing
        )
        if is_blank:
            worksheet.update("A1:D1", [header])
            existing = [header]
        # Find row indices: skip header (row 0), data rows start at index 1
        def find_row(ann: str, pid: str) -> int | None:
            for i in range(1, len(existing)):
                row = existing[i]
                if len(row) >= 2 and str(row[0]).strip() == ann and str(row[1]).strip() == pid:
                    return i
            return None

        timestamp = datetime.now(timezone.utc).isoformat()
        updated, appended = 0, 0
        for pid, ps in st.session_state.pairs.items():
            if not ps:
                continue
            pairs_str = json.dumps(sorted([sorted(list(p)) for p in ps]))
            row_data = [annotator_name, pid, pairs_str, timestamp]
            idx = find_row(annotator_name, pid)
            if idx is not None:
                # 1-based row number for gspread
                worksheet.update(f"A{idx + 1}:D{idx + 1}", [row_data])
                updated += 1
            else:
                worksheet.append_row(row_data)
                appended += 1
        total = updated + appended
        if total == 0:
            return False, "No annotations to submit. Mark at least one duplicate pair."
        msg_parts = []
        if updated:
            msg_parts.append(f"{updated} updated")
        if appended:
            msg_parts.append(f"{appended} added")
        return True, f"Submitted to Google Sheets: {', '.join(msg_parts)}."
    except Exception as e:
        logging.exception("Google Sheets submit failed: %s", e)
        return False, str(e)


def load_pairs_from_gsheet(annotator_name: str) -> dict:
    """Load annotations from Google Sheet for the given annotator.
    Returns {paper_id: set of frozensets} or empty dict on error."""
    gc = get_gsheet_client()
    if gc is None:
        return {}
    try:
        raw = st.secrets["SPREADSHEET_ID"].strip()
        sheet_id = raw.split("/d/")[1].split("/")[0] if "/d/" in raw else raw
        sheet_name = st.secrets.get("SHEET_NAME", "Sheet1")
        spreadsheet = gc.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        rows = worksheet.get_all_values()
        if not rows or len(rows) < 2:
            return {}
        # Skip header; rows: [annotator_name, paper_id, pairs_json, timestamp]
        result = {}
        ann = str(annotator_name).strip()
        for row in rows[1:]:
            if len(row) < 3:
                continue
            if str(row[0]).strip() != ann:
                continue
            pid = str(row[1]).strip()
            pairs_str = str(row[2]).strip()
            if not pid or not pairs_str:
                continue
            parsed = parse_existing_pairs(pairs_str)
            if parsed:
                result[pid] = set(frozenset(p) for p in parsed if len(p) == 2)
        return result
    except Exception as e:
        logging.exception("Load from Google Sheets failed: %s", e)
        return {}


# ── SESSION STATE ─────────────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent
DATA_PATH = _PROJECT_ROOT / "data" / "inter_human_annotation_sheet.csv"

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    return load_csv(path)


def init_state():
    # Restore annotator name from URL query param or session
    if "annotator_name" not in st.session_state:
        q = st.query_params.get("annotator")
        if q and str(q).strip():
            st.session_state.annotator_name = str(q).strip()
        else:
            st.session_state.annotator_name = ""
    if "df" not in st.session_state:
        # Try default path, else require upload
        if DATA_PATH.exists():
            st.session_state.df = load_data(str(DATA_PATH))
        else:
            st.session_state.df = None
    if "paper_idx" not in st.session_state:
        st.session_state.paper_idx = 0
    if "anchor_idx" not in st.session_state:
        st.session_state.anchor_idx = 0
    if "pairs" not in st.session_state:
        # { paper_id: set of frozensets }
        st.session_state.pairs = {}
    if "search_query" not in st.session_state:
        st.session_state.search_query = ""
    if "submit_success" not in st.session_state:
        st.session_state.submit_success = None


init_state()

# ── ANNOTATOR NAME (required) ──────────────────────────────────────────────────
if not st.session_state.annotator_name or not str(st.session_state.annotator_name).strip():
    st.markdown("### 👤 Enter your name to begin")
    st.caption("This will be recorded with your annotations when you submit.")
    name = st.text_input("Annotator name", placeholder="e.g. Chani Jung", label_visibility="collapsed")
    if st.button("Continue"):
        if name and str(name).strip():
            name_clean = str(name).strip()
            st.session_state.annotator_name = name_clean
            st.query_params["annotator"] = name_clean
            st.rerun()
        else:
            st.warning("Please enter your name.")
    st.stop()

annotator_name = st.session_state.annotator_name

# ── LOAD FROM GOOGLE SHEETS (on refresh / fresh session) ──────────────────────
if not st.session_state.pairs and get_gsheet_client():
    loaded = load_pairs_from_gsheet(annotator_name)
    if loaded:
        st.session_state.pairs = loaded

# ── FILE UPLOAD (if no CSV found) ─────────────────────────────────────────────
if st.session_state.df is None:
    st.markdown("### 📂 Upload `inter_human_annotation_sheet.csv` to begin")
    up = st.file_uploader("CSV file", type=["csv"])
    if up:
        st.session_state.df = pd.read_csv(up)
        st.rerun()
    st.stop()

df = st.session_state.df

# ── PAPER SELECTION ───────────────────────────────────────────────────────────
paper_ids = df["paper_id"].tolist()
paper_labels = []
for _, row in df.iterrows():
    pid = row["paper_id"]
    title = str(row.get("title", "")).strip()
    label = title[:55] + "…" if len(title) > 55 else title if title else str(pid)
    is_annotated = pid in st.session_state.pairs and len(st.session_state.pairs[pid]) > 0
    if is_annotated:
        label = f"✓ {label}"
    paper_labels.append(label)

# Progress across all papers
total_papers = len(paper_ids)
reviewed_papers = sum(
    1 for pid in paper_ids
    if pid in st.session_state.pairs and len(st.session_state.pairs[pid]) > 0
)

pct = int(reviewed_papers / total_papers * 100) if total_papers else 0

c1, c2 = st.columns([6, 1])
with c1:
    st.markdown(f"""
    <div class="top-bar">
      <h1>⬡ Feedback Consensus Annotator</h1>
      <span class="progress-info">
        <span style="color:var(--accent); margin-right:0.8rem;">👤 {annotator_name}</span>
        Papers annotated: {reviewed_papers} / {total_papers}
        <span class="progress-wrap"><span class="progress-fill" style="width:{pct}%"></span></span>
      </span>
    </div>
    """, unsafe_allow_html=True)
with c2:
    if st.button("Change name", help="Use a different annotator name"):
        del st.session_state.annotator_name
        params = dict(st.query_params)
        params.pop("annotator", None)
        st.query_params = params
        st.rerun()

sel_label = st.selectbox(
    "Select Paper",
    options=paper_labels,
    index=st.session_state.paper_idx,
    label_visibility="collapsed",
)
paper_idx = paper_labels.index(sel_label)
if paper_idx != st.session_state.paper_idx:
    st.session_state.paper_idx = paper_idx
    st.session_state.anchor_idx = 0
    st.rerun()

current_row = df.iloc[paper_idx]
paper_id = current_row["paper_id"]
feedbacks = parse_feedbacks(current_row.get("human_feedback_list", ""))

# Init pairs for this paper
if paper_id not in st.session_state.pairs:
    existing = parse_existing_pairs(current_row.get("duplicated_feedback_pairs", ""))
    st.session_state.pairs[paper_id] = set(frozenset(p) for p in existing if len(p) == 2)

current_pairs: set = st.session_state.pairs[paper_id]

if not feedbacks:
    st.warning("No feedbacks found for this paper.")
    st.stop()

n = len(feedbacks)
anchor_i = min(st.session_state.anchor_idx, n - 1)
anchor_feedback_idx, anchor_text = feedbacks[anchor_i]
anchor_keywords = get_keywords(anchor_text)

# ── SEARCH FILTER ─────────────────────────────────────────────────────────────
search_q = st.text_input("🔍  Filter feedbacks by keyword", value=st.session_state.search_query, placeholder="e.g. experiment, baseline ...")
st.session_state.search_query = search_q

def matches_search(text: str, q: str) -> bool:
    if not q.strip():
        return True
    return q.strip().lower() in text.lower()

# ── LAYOUT: anchor | scroll list ─────────────────────────────────────────────
col_anchor, col_list = st.columns([2, 3], gap="large")

# ─── Anchor panel ────────────────────────────────────────────────────────────
with col_anchor:
    st.markdown(f"""
    <div class="anchor-panel">
      <div class="anchor-label">🔒 Anchor — Reviewing</div>
      <div class="anchor-idx">#{anchor_feedback_idx} &nbsp;·&nbsp; {anchor_i} / {n - 1}</div>
      <div class="anchor-text">{anchor_text}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Jump to specific feedback (0-based index to match #0, #1, ...)
    jump_c1, jump_c2 = st.columns([1, 3])
    with jump_c1:
        st.caption("Go to #")
    with jump_c2:
        jump_to = st.number_input(
            "Jump to feedback",
            min_value=0,
            max_value=n - 1,
            value=anchor_i,
            step=1,
            format="%d",
            key=f"jump_{paper_id}",
            label_visibility="collapsed",
        )
    if jump_to != anchor_i:
        st.session_state.anchor_idx = int(jump_to)
        st.rerun()

    nav_c1, nav_c2 = st.columns(2)
    with nav_c1:
        if st.button("← Prev", use_container_width=True):
            st.session_state.anchor_idx = max(0, anchor_i - 1)
            st.rerun()
    with nav_c2:
        if st.button("Next →", use_container_width=True):
            if anchor_i >= n - 1 and paper_idx < total_papers - 1:
                # At last feedback of current paper → move to next paper
                st.session_state.paper_idx = paper_idx + 1
                st.session_state.anchor_idx = 0
            else:
                st.session_state.anchor_idx = min(n - 1, anchor_i + 1)
            st.rerun()

    # ── Basket ───────────────────────────────────────────────────────────────
    pairs_list = sorted([sorted(list(p)) for p in current_pairs])
    pair_tags = "".join(f"<span class='pair-tag'>({a}, {b})</span>" for a, b in pairs_list)
    empty_msg = "<span style='color:var(--text-dim); font-size:0.8rem;'>No pairs marked yet.</span>"

    st.markdown(f"""
    <div class="basket-wrap">
      <div class="basket-title">🛒 Duplicate Pairs — {len(pairs_list)} saved</div>
      {pair_tags if pair_tags else empty_msg}
    </div>
    """, unsafe_allow_html=True)

    # ── Submit to Google Sheets ───────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    if get_gsheet_client():
        if st.button("📤 Submit to Google Sheets", use_container_width=True, type="primary"):
            ok, msg = submit_to_gsheet(annotator_name)
            st.session_state.submit_success = ok
            st.session_state.submit_message = msg
            st.rerun()
        if st.session_state.submit_success is True:
            st.success(st.session_state.get("submit_message", "Submitted."))
        elif st.session_state.submit_success is False:
            st.error(st.session_state.get("submit_message", "Submit failed."))
    else:
        st.caption("Google Sheets not configured. Add secrets to enable Submit.")
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 Copy result as JSON", use_container_width=True):
        result = {
            pid: sorted([sorted(list(p)) for p in ps])
            for pid, ps in st.session_state.pairs.items()
            if ps
        }
        st.markdown(f"<div class='save-result'>{json.dumps(result, indent=2)}</div>", unsafe_allow_html=True)

    # ── Paper info (Abstract, PDF) ─────────────────────────────────────────────
    abstract_raw = str(current_row.get("abstract", "") or "").strip()
    pdf_url = str(current_row.get("pdf_url", "") or "").strip()
    if abstract_raw or pdf_url:
        abstract_escaped = html.escape(abstract_raw) if abstract_raw else ""
        pdf_link_html = f'<a href="{html.escape(pdf_url)}" target="_blank" rel="noopener">📄 Open PDF</a>' if pdf_url else ""
        st.markdown(f"""
        <div class="paper-info">
          <div class="paper-info-title">Paper</div>
          {f'<div class="paper-abstract">{abstract_escaped}</div>' if abstract_escaped else ''}
          {f'<div class="paper-pdf-link">{pdf_link_html}</div>' if pdf_link_html else ''}
        </div>
        """, unsafe_allow_html=True)

# ─── Scroll list panel ───────────────────────────────────────────────────────
with col_list:
    st.markdown(f"""
    <div style='font-family:IBM Plex Mono,monospace; font-size:0.7rem; color:var(--text-dim);
                text-transform:uppercase; letter-spacing:0.1em; margin-bottom:0.6rem;'>
        All feedbacks &nbsp;·&nbsp; {n} items
    </div>
    """, unsafe_allow_html=True)

    for fb_i, (fb_idx, fb_text) in enumerate(feedbacks):
        if not matches_search(fb_text, search_q):
            continue

        pair_key = frozenset([anchor_feedback_idx, fb_idx])
        is_self = (fb_i == anchor_i)
        is_checked = pair_key in current_pairs and not is_self

        # highlight common words
        display_text = highlight(fb_text, anchor_keywords) if not is_self else fb_text

        card_class = "feedback-card"
        if is_self:
            card_class += " anchor-self"
        elif is_checked:
            card_class += " checked"

        check_icon = "✅ Duplicate" if is_checked else "Mark duplicate"
        check_icon_self = "← This is the anchor" if is_self else check_icon

        st.markdown(f"""
        <div class="{card_class}">
          <div class="card-idx">#{fb_idx}</div>
          <div class="card-text">{display_text if not is_self else fb_text}</div>
        </div>
        """, unsafe_allow_html=True)

        if not is_self:
            btn_label = f"{'✅ Marked' if is_checked else '☐ Mark'} — #{anchor_feedback_idx} ↔ #{fb_idx}"
            if st.button(btn_label, key=f"btn_{paper_id}_{anchor_i}_{fb_i}"):
                if is_checked:
                    current_pairs.discard(pair_key)
                else:
                    current_pairs.add(pair_key)
                st.session_state.pairs[paper_id] = current_pairs
                st.rerun()
