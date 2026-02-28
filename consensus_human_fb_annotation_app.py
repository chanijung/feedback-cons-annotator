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
from gspread.exceptions import WorksheetNotFound
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
    --bg: #f5f6f8;
    --surface: #ffffff;
    --surface2: #eef0f4;
    --border: #d1d5dc;
    --accent: #2563eb;
    --accent2: #c026d3;
    --text: #1e293b;
    --text-dim: #64748b;
    --highlight: rgba(37, 99, 235, 0.15);
    --checked-bg: rgba(37, 99, 235, 0.08);
    --checked-border: #2563eb;
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
    font-size: 1rem;
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
    font-size: 0.96rem;
    line-height: 1.6;
    color: var(--text);
}
.highlight-word {
    background: rgba(37,99,235,0.2);
    color: #1d4ed8;
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
    color: #1e293b;
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
    scrollbar-width: thin;
    scrollbar-color: var(--border) var(--surface);
}
[data-testid="stHorizontalBlock"]:has(.anchor-panel) > div:last-child::-webkit-scrollbar {
    width: 10px;
}
[data-testid="stHorizontalBlock"]:has(.anchor-panel) > div:last-child::-webkit-scrollbar-track {
    background: var(--surface);
    border-radius: 5px;
}
[data-testid="stHorizontalBlock"]:has(.anchor-panel) > div:last-child::-webkit-scrollbar-thumb {
    background: var(--border);
    border-radius: 5px;
    border: 2px solid var(--surface);
}
[data-testid="stHorizontalBlock"]:has(.anchor-panel) > div:last-child::-webkit-scrollbar-thumb:hover {
    background: var(--text-dim);
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


def count_word_overlap(anchor_keywords: set[str], text: str) -> int:
    """Count overlapping words between anchor and text. Used for sorting."""
    return len(anchor_keywords & get_keywords(text))


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


def _submit_pairs_to_sheet(worksheet, annotator_name: str, pairs_dict: dict, is_hl: bool) -> tuple[int, int]:
    """Submit pairs to worksheet. Returns (updated, appended) counts."""
    existing = worksheet.get_all_values()
    header = ["annotator_name", "paper_id", "pairs", "timestamp"]
    is_blank = not existing or all(
        all(not str(c).strip() for c in (row if isinstance(row, (list, tuple)) else [row]))
        for row in existing
    )
    if is_blank:
        worksheet.update([header], "A1:D1")
        existing = [header]

    def find_row(ann: str, pid: str) -> int | None:
        for i in range(1, len(existing)):
            row = existing[i]
            if len(row) >= 2 and str(row[0]).strip() == ann and str(row[1]).strip() == pid:
                return i
        return None

    timestamp = datetime.now(timezone.utc).isoformat()
    updated, appended = 0, 0
    for pid, data in pairs_dict.items():
        if is_hl:
            ps = data if isinstance(data, set) else set(tuple(p) for p in data)
            if not ps:
                continue
            pairs_str = json.dumps(sorted([list(p) for p in ps]))
        else:
            ps = data
            if not ps:
                continue
            pairs_str = json.dumps(sorted([sorted(list(p)) for p in ps]))
        row_data = [annotator_name, pid, pairs_str, timestamp]
        idx = find_row(annotator_name, pid)
        if idx is not None:
            worksheet.update([row_data], f"A{idx + 1}:D{idx + 1}")
            updated += 1
        else:
            worksheet.append_row(row_data)
            appended += 1
    return updated, appended


def submit_to_gsheet(annotator_name: str) -> tuple[bool, str]:
    """Submit both human-human and human-llm pairs to Google Sheets."""
    gc = get_gsheet_client()
    if gc is None:
        return False, "Google Sheets not configured."
    try:
        raw = st.secrets["SPREADSHEET_ID"].strip()
        sheet_id = raw.split("/d/")[1].split("/")[0] if "/d/" in raw else raw
        sheet_name = st.secrets.get("SHEET_NAME", "HumanHuman")
        sheet_hl = st.secrets.get("SHEET_NAME_HL", "HumanLLM")
        spreadsheet = gc.open_by_key(sheet_id)

        msg_parts = []
        try:
            ws_main = spreadsheet.worksheet(sheet_name)
        except WorksheetNotFound:
            return False, f"Worksheet '{sheet_name}' not found. Create a tab with that name, or set SHEET_NAME in secrets to match your tab."
        u1, a1 = _submit_pairs_to_sheet(
            ws_main, annotator_name, st.session_state.pairs, is_hl=False
        )
        if u1 or a1:
            msg_parts.append(f"Human-Human: {u1 + a1}")

        try:
            ws_hl = spreadsheet.worksheet(sheet_hl)
            u2, a2 = _submit_pairs_to_sheet(
                ws_hl, annotator_name, st.session_state.pairs_hl, is_hl=True
            )
            if u2 or a2:
                msg_parts.append(f"Human-LLM: {u2 + a2}")
        except WorksheetNotFound:
            if msg_parts:
                msg_parts.append(f"(Human-LLM tab '{sheet_hl}' not found—create it or set SHEET_NAME_HL)")
            else:
                return False, f"Worksheet '{sheet_hl}' not found. Create a tab named '{sheet_hl}', or set SHEET_NAME_HL in secrets."

        if not msg_parts:
            return False, "No annotations to submit."
        return True, f"Submitted: {', '.join(msg_parts)}."
    except Exception as e:
        logging.exception("Google Sheets submit failed: %s", e)
        return False, str(e)


def load_pairs_from_gsheet(annotator_name: str) -> tuple[dict, dict]:
    """Load human-human and human-llm annotations. Returns (pairs, pairs_hl)."""
    gc = get_gsheet_client()
    if gc is None:
        return {}, {}
    pairs, pairs_hl = {}, {}
    ann = str(annotator_name).strip()
    try:
        raw = st.secrets["SPREADSHEET_ID"].strip()
        sheet_id = raw.split("/d/")[1].split("/")[0] if "/d/" in raw else raw
        spreadsheet = gc.open_by_key(sheet_id)

        # Human-Human
        sheet_name = st.secrets.get("SHEET_NAME", "HumanHuman")
        try:
            ws = spreadsheet.worksheet(sheet_name)
        except WorksheetNotFound:
            logging.warning("Sheet '%s' not found, trying first tab", sheet_name)
            try:
                ws = spreadsheet.sheet1
            except Exception:
                ws = None
        rows = ws.get_all_values() if ws else []
        for row in (rows[1:] if rows else []):
            if len(row) < 3 or str(row[0]).strip() != ann:
                continue
            pid, pairs_str = str(row[1]).strip(), str(row[2]).strip()
            if pid and pairs_str:
                parsed = parse_existing_pairs(pairs_str)
                if parsed:
                    pairs[pid] = set(frozenset(p) for p in parsed if len(p) == 2)

        # Human-LLM
        try:
            ws_hl = spreadsheet.worksheet(st.secrets.get("SHEET_NAME_HL", "HumanLLM"))
            rows_hl = ws_hl.get_all_values()
            for row in (rows_hl[1:] if rows_hl else []):
                if len(row) < 3 or str(row[0]).strip() != ann:
                    continue
                pid, pairs_str = str(row[1]).strip(), str(row[2]).strip()
                if pid and pairs_str:
                    parsed = parse_existing_pairs(pairs_str)
                    if parsed:
                        pairs_hl[pid] = set(tuple(p) for p in parsed if len(p) == 2)
        except Exception:
            pass
    except Exception as e:
        logging.exception("Load from Google Sheets failed: %s", e)
    return pairs, pairs_hl


# ── ANNOTATOR ASSIGNMENT (12 papers × 3 annotators each, 4 people) ───────────────
# Each paper: 3 annotators. Each person: 9 papers.
_ANNOTATORS = ["chani", "jimin", "hyunwoo", "xuhui"]
_ASSIGNMENT = {
    "chani": [0, 1, 2, 4, 5, 6, 8, 9, 10],
    "jimin": [0, 1, 3, 4, 5, 7, 8, 9, 11],
    "hyunwoo": [0, 2, 3, 4, 6, 7, 8, 10, 11],
    "xuhui": [1, 2, 3, 5, 6, 7, 9, 10, 11],
}


def get_assigned_paper_indices(annotator_name: str) -> list[int] | None:
    """Return list of paper indices for this annotator, or None if not assigned."""
    key = str(annotator_name).strip().lower()
    return _ASSIGNMENT.get(key)


# ── SESSION STATE ─────────────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent
# Prefer annotation_sheet.csv (has human + llm); fallback to inter_human
_DATA_ANNOTATION = _PROJECT_ROOT / "data" / "annotation_sheet.csv"
_DATA_INTER_HUMAN = _PROJECT_ROOT / "data" / "inter_human_annotation_sheet.csv"
DATA_PATH = _DATA_ANNOTATION if _DATA_ANNOTATION.exists() else _DATA_INTER_HUMAN

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
    if "annotation_mode" not in st.session_state:
        st.session_state.annotation_mode = "human_human"  # or "human_llm"
    if "pairs_hl" not in st.session_state:
        # {(paper_id, human_idx): set of llm_idx} or {paper_id: {(h,l), ...}}
        st.session_state.pairs_hl = {}

def _paper_has_llm(row) -> bool:
    """Check if row has valid llm_feedback."""
    fb = row.get("llm_feedback", "")
    return pd.notna(fb) and str(fb).strip() != ""


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
    loaded_pairs, loaded_hl = load_pairs_from_gsheet(annotator_name)
    if loaded_pairs:
        st.session_state.pairs = loaded_pairs
    if loaded_hl:
        st.session_state.pairs_hl = loaded_hl

# ── FILE UPLOAD (if no CSV found) ─────────────────────────────────────────────
if st.session_state.df is None:
    st.markdown("### 📂 Upload `inter_human_annotation_sheet.csv` to begin")
    up = st.file_uploader("CSV file", type=["csv"])
    if up:
        st.session_state.df = pd.read_csv(up)
        st.rerun()
    st.stop()

df = st.session_state.df

# ── FILTER BY ANNOTATOR ASSIGNMENT ────────────────────────────────────────────
assigned_indices = get_assigned_paper_indices(annotator_name)
if assigned_indices is not None:
    df = df.iloc[assigned_indices].reset_index(drop=True)
else:
    st.warning(
        f"Annotator '{annotator_name}' is not in the assignment list ({', '.join(_ANNOTATORS)}). "
        "Showing all papers."
    )

# ── PAPER SELECTION (H-H and H-L separate entries) ─────────────────────────────
paper_ids = df["paper_id"].tolist()
if st.session_state.paper_idx >= len(paper_ids):
    st.session_state.paper_idx = 0

# Build nav options: each (paper_idx, mode) gets its own dropdown entry
nav_options: list[tuple[int, str]] = []  # (paper_idx, "human_human"|"human_llm")
nav_labels: list[str] = []
for i, row in df.iterrows():
    pid = row["paper_id"]
    title = str(row.get("title", "")).strip()
    short = title[:48] + "…" if len(title) > 48 else title if title else str(pid)
    pid_short = str(pid)[:12] if pid else ""
    has_llm_row = _paper_has_llm(row) and len(parse_feedbacks(row.get("llm_feedback", ""))) > 0

    # Human-Human
    has_hh = pid in st.session_state.pairs and len(st.session_state.pairs[pid]) > 0
    lbl_hh = f"[H-H] {short} ({pid_short})" + (" ✓" if has_hh else "")
    nav_options.append((i, "human_human"))
    nav_labels.append(lbl_hh)

    # Human-LLM (only if paper has llm feedback)
    if has_llm_row:
        has_hl = pid in st.session_state.pairs_hl and len(st.session_state.pairs_hl[pid]) > 0
        lbl_hl = f"[H-L] {short} ({pid_short})" + (" ✓" if has_hl else "")
        nav_options.append((i, "human_llm"))
        nav_labels.append(lbl_hl)

# Progress across all papers
total_papers = len(paper_ids)
reviewed_papers = sum(
    1 for pid in paper_ids
    if (pid in st.session_state.pairs and len(st.session_state.pairs[pid]) > 0)
    or (pid in st.session_state.pairs_hl and len(st.session_state.pairs_hl[pid]) > 0)
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

# Find current nav index
current_nav_idx = 0
for k, (pi, m) in enumerate(nav_options):
    if pi == st.session_state.paper_idx and m == st.session_state.annotation_mode:
        current_nav_idx = k
        break

sel_label = st.selectbox(
    "Select Paper & Mode",
    options=nav_labels,
    index=current_nav_idx,
    label_visibility="collapsed",
)
sel_idx = nav_labels.index(sel_label) if sel_label in nav_labels else 0
new_paper_idx, new_mode = nav_options[sel_idx]
if new_paper_idx != st.session_state.paper_idx or new_mode != st.session_state.annotation_mode:
    st.session_state.paper_idx = new_paper_idx
    st.session_state.annotation_mode = new_mode
    st.session_state.anchor_idx = 0
    st.rerun()

paper_idx = st.session_state.paper_idx

current_row = df.iloc[paper_idx]
paper_id = current_row["paper_id"]
feedbacks = parse_feedbacks(current_row.get("human_feedback_list", ""))
llm_feedbacks = parse_feedbacks(current_row.get("llm_feedback", ""))
has_llm = _paper_has_llm(current_row) and len(llm_feedbacks) > 0
llm_name = str(current_row.get("llm_name", "LLM")).strip()

# Init pairs for this paper
if paper_id not in st.session_state.pairs:
    existing = parse_existing_pairs(current_row.get("duplicated_feedback_pairs", ""))
    st.session_state.pairs[paper_id] = set(frozenset(p) for p in existing if len(p) == 2)

current_pairs: set = st.session_state.pairs[paper_id]

# Init pairs_hl for human-llm: {(human_idx, llm_idx), ...}
if paper_id not in st.session_state.pairs_hl:
    st.session_state.pairs_hl[paper_id] = set()
pairs_hl_paper: set = st.session_state.pairs_hl[paper_id]

if not feedbacks:
    st.warning("No feedbacks found for this paper.")
    st.stop()

# If in human_llm mode but no llm data, switch back to human_human
if st.session_state.annotation_mode == "human_llm" and not has_llm:
    st.session_state.annotation_mode = "human_human"
    st.rerun()

n = len(feedbacks)
n_llm = len(llm_feedbacks)
anchor_i = min(st.session_state.anchor_idx, n - 1)
anchor_feedback_idx, anchor_text = feedbacks[anchor_i]
anchor_keywords = get_keywords(anchor_text)
mode = st.session_state.annotation_mode

# ── SEARCH FILTER ─────────────────────────────────────────────────────────────
search_q = st.text_input("🔍  Filter feedbacks by keyword", value=st.session_state.search_query, placeholder="e.g. experiment, baseline ...")
st.session_state.search_query = search_q

def matches_search(text: str, q: str) -> bool:
    if not q.strip():
        return True
    return q.strip().lower() in text.lower()

# ── MODE LABEL + PREV/NEXT NAV ───────────────────────────────────────────────
mode_label = "Human ↔ LLM Consensus" if mode == "human_llm" else "Human ↔ Human Duplicates"
st.caption(f"📌 {mode_label}")

# Prev / Next / 맨위로 - above right panel (same 2:3 split as main layout)
_nav_left, nav_right = st.columns([2, 3], gap="large")
with nav_right:
    prev_col, next_col, scroll_col = st.columns([1, 1, 1])
    with prev_col:
        do_prev = st.button("← Prev", key="nav_prev", use_container_width=True)
    with next_col:
        do_next = st.button("Next →", key="nav_next", use_container_width=True)
    with scroll_col:
        st.html(
            """<button type="button" id="scroll-to-top-btn" style="
                font-size: 0.75rem; padding: 0.3rem 0.5rem;
                background: var(--surface2); border: 1px solid var(--border); border-radius: 8px;
                color: var(--text); cursor: pointer; font-family: inherit; width: 100%;
            ">Scroll to top</button>
            <script>
            (function(){
                function scrollRightToTop(){
                    var d = document;
                    try { if (window.parent && window.parent !== window) d = window.parent.document; } catch(e) {}
                    var blocks = d.querySelectorAll('[data-testid=\"stHorizontalBlock\"]');
                    for (var i = 0; i < blocks.length; i++) {
                        if (blocks[i].querySelector('.anchor-panel')) {
                            var right = blocks[i].lastElementChild;
                            if (right) { right.scrollTop = 0; break; }
                        }
                    }
                }
                var btn = document.getElementById('scroll-to-top-btn');
                if (btn) btn.addEventListener('click', scrollRightToTop);
            })();
            </script>""",
            unsafe_allow_javascript=True,
        )

if do_prev:
    if anchor_i <= 0 and mode == "human_llm":
        st.session_state.annotation_mode = "human_human"
        st.session_state.anchor_idx = n - 1
    else:
        st.session_state.anchor_idx = max(0, anchor_i - 1)
    st.rerun()
if do_next:
    if anchor_i >= n - 1:
        if mode == "human_human" and has_llm:
            st.session_state.annotation_mode = "human_llm"
            st.session_state.anchor_idx = 0
        else:
            st.session_state.annotation_mode = "human_human"
            st.session_state.anchor_idx = 0
            if paper_idx < total_papers - 1:
                st.session_state.paper_idx = paper_idx + 1
    else:
        st.session_state.anchor_idx = min(n - 1, anchor_i + 1)
    st.rerun()

# ── LAYOUT: anchor | scroll list ─────────────────────────────────────────────
col_anchor, col_list = st.columns([2, 3], gap="large")

# ─── Anchor panel ────────────────────────────────────────────────────────────
with col_anchor:
    anchor_title = "Human Anchor" if mode == "human_llm" else "Anchor"
    st.markdown(f"""
    <div class="anchor-panel">
      <div class="anchor-label">🔒 {anchor_title} — Reviewing</div>
      <div class="anchor-idx">#{anchor_feedback_idx} &nbsp;·&nbsp; {anchor_i} / {n - 1}</div>
      <div class="anchor-text">{anchor_text}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Jump to specific feedback (0-based index)
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
            key=f"jump_{paper_id}_{mode}",
            label_visibility="collapsed",
        )
    if jump_to != anchor_i:
        st.session_state.anchor_idx = int(jump_to)
        st.rerun()

    # ── Basket ───────────────────────────────────────────────────────────────
    if mode == "human_human":
        pairs_list = sorted([sorted(list(p)) for p in current_pairs])
        pair_tags = "".join(f"<span class='pair-tag'>({a}, {b})</span>" for a, b in pairs_list)
        basket_title = "🛒 Duplicate Pairs"
    else:
        # human_llm: show (human_i, llm_j) for current anchor
        hl_pairs = [(anchor_i, l) for (h, l) in pairs_hl_paper if h == anchor_i]
        pairs_list = sorted(hl_pairs)
        pair_tags = "".join(f"<span class='pair-tag'>(H{anchor_i}, L{j})</span>" for _, j in pairs_list)
        basket_title = "🛒 Consensus Pairs (Human ↔ LLM)"
    empty_msg = "<span style='color:var(--text-dim); font-size:0.8rem;'>No pairs marked yet.</span>"

    st.markdown(f"""
    <div class="basket-wrap">
      <div class="basket-title">{basket_title} — {len(pairs_list)} saved</div>
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
            "human_human": {pid: sorted([sorted(list(p)) for p in ps]) for pid, ps in st.session_state.pairs.items() if ps},
            "human_llm": {pid: sorted([list(p) for p in ps]) for pid, ps in st.session_state.pairs_hl.items() if ps},
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
    if mode == "human_human":
        list_feedbacks = feedbacks
        list_n = n
        list_title = f"All feedbacks &nbsp;·&nbsp; {n} items"
    else:
        list_feedbacks = llm_feedbacks
        list_n = n_llm
        list_title = f"LLM feedbacks ({llm_name}) &nbsp;·&nbsp; {n_llm} items"

    st.markdown(f"""
    <div style='font-family:IBM Plex Mono,monospace; font-size:0.7rem; color:var(--text-dim);
                text-transform:uppercase; letter-spacing:0.1em; margin-bottom:0.6rem;'>
        {list_title} · sorted by word overlap ↓
    </div>
    """, unsafe_allow_html=True)

    # Filter by search, then sort by word overlap (desc) so high-overlap feedbacks appear first
    items = [
        (fb_i, fb_idx, fb_text)
        for fb_i, (fb_idx, fb_text) in enumerate(list_feedbacks)
        if matches_search(fb_text, search_q)
    ]
    items.sort(key=lambda x: count_word_overlap(anchor_keywords, x[2]), reverse=True)

    for fb_i, fb_idx, fb_text in items:

        if mode == "human_human":
            pair_key = frozenset([anchor_feedback_idx, fb_idx])
            is_self = (fb_i == anchor_i)
            is_checked = pair_key in current_pairs and not is_self
        else:
            # human_llm: (human_anchor_i, llm_idx)
            is_self = False
            is_checked = (anchor_i, fb_i) in pairs_hl_paper

        # highlight common words
        display_text = highlight(fb_text, anchor_keywords)

        card_class = "feedback-card"
        if is_self:
            card_class += " anchor-self"
        elif is_checked:
            card_class += " checked"

        if mode == "human_human":
            check_icon_self = "← This is the anchor" if is_self else ("✅ Duplicate" if is_checked else "Mark duplicate")
        else:
            check_icon_self = "✅ Consensus" if is_checked else "Mark consensus"

        st.markdown(f"""
        <div class="{card_class}">
          <div class="card-idx">#{fb_idx}</div>
          <div class="card-text">{display_text}</div>
        </div>
        """, unsafe_allow_html=True)

        if mode == "human_human":
            if not is_self:
                btn_label = f"{'✅ Marked' if is_checked else '☐ Mark'} — #{anchor_feedback_idx} ↔ #{fb_idx}"
                if st.button(btn_label, key=f"btn_hh_{paper_id}_{anchor_i}_{fb_i}"):
                    if is_checked:
                        current_pairs.discard(pair_key)
                    else:
                        current_pairs.add(pair_key)
                    st.session_state.pairs[paper_id] = current_pairs
                    st.rerun()
        else:
            btn_label = f"{'✅ Marked' if is_checked else '☐ Mark'} — Human #{anchor_feedback_idx} ↔ LLM #{fb_idx}"
            if st.button(btn_label, key=f"btn_hl_{paper_id}_{anchor_i}_{fb_i}"):
                hl_pair = (anchor_i, fb_i)
                if is_checked:
                    pairs_hl_paper.discard(hl_pair)
                else:
                    pairs_hl_paper.add(hl_pair)
                st.session_state.pairs_hl[paper_id] = pairs_hl_paper
                st.rerun()
