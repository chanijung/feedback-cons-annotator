import html
import logging
import re

import streamlit as st
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

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
    --match-bg: rgba(34,197,94,0.1);
    --match-border: #16a34a;
    --nonmatch-bg: rgba(239,68,68,0.1);
    --nonmatch-border: #dc2626;
    --radius: 10px;
}

html, body, .stApp {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'IBM Plex Sans', sans-serif;
}

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

/* ── Feedback panels ── */
.feedback-panel {
    background: var(--surface);
    border: 1.5px solid var(--border);
    border-radius: var(--radius);
    padding: 1.2rem;
    min-height: 200px;
}
.feedback-panel.match {
    border-color: var(--match-border);
    background: var(--match-bg);
}
.feedback-panel.nonmatch {
    border-color: var(--nonmatch-border);
    background: var(--nonmatch-bg);
}
.panel-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 0.4rem;
    font-weight: 600;
}
.panel-idx {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.75rem;
    color: var(--text-dim);
    margin-bottom: 0.5rem;
}
.panel-text {
    font-size: 1rem;
    line-height: 1.65;
    color: var(--text);
}

/* ── Label heading ── */
.label-heading {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.4rem;
}

/* ── Paper info ── */
.paper-info {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem;
    margin-top: 0.8rem;
    max-height: 180px;
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
    font-size: 0.9rem;
    line-height: 1.55;
    color: var(--text);
    margin-bottom: 0.5rem;
}
.paper-pdf-link a {
    color: var(--accent);
    font-size: 0.85rem;
    text-decoration: none;
}
.paper-pdf-link a:hover { text-decoration: underline; }

/* ── Go to # label ── */
.stNumberInput label {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    color: var(--text) !important;
    white-space: nowrap;
}
.stNumberInput > div {
    gap: 0.3rem !important;
}

/* ── Buttons (default) ── */
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

/* ── Match / Non-match label buttons (bigger, centered) ── */
.label-btn-row + div button,
.label-btn-row ~ div button {
    font-size: 1.15rem !important;
    padding: 0.8rem 1rem !important;
    min-height: 3.2rem !important;
    font-weight: 600 !important;
}
/* Simpler: all primary/secondary kind buttons get bigger */
[data-testid="baseButton-primary"],
[data-testid="baseButton-secondary"] {
    font-size: 1.15rem !important;
    padding: 0.8rem 1.2rem !important;
    min-height: 3.2rem !important;
    font-weight: 600 !important;
}

/* ── Radio buttons for labeling ── */
.stRadio > div {
    gap: 0.5rem !important;
}
.stRadio label {
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.9rem !important;
}

/* ── Word overlap highlight ── */
.word-hl {
    background: rgba(250, 204, 21, 0.45);
    border-radius: 3px;
    padding: 0 2px;
    color: inherit;
    font-weight: 600;
}

</style>
""", unsafe_allow_html=True)


# ── GOOGLE SHEETS ─────────────────────────────────────────────────────────────

_SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HH_HEADER = [
    "annotator_name", "paper_id", "global_id",
    "feedback1_idx", "feedback1",
    "feedback2_idx", "feedback2",
    "match_label",
]

HL_HEADER = [
    "annotator_name", "paper_id", "global_id",
    "feedback1_idx", "feedback1",
    "feedback2_idx", "feedback2",
    "llm_name", "match_label",
]

_SHEET_NAMES = {
    "human_human": "HumanHuman",
    "human_llm":   "HumanLLM",
}


def _source_to_sheet_name(source: str) -> str:
    return _SHEET_NAMES.get(source, "HumanHuman")


def _get_header(sheet_name: str) -> list:
    return HL_HEADER if sheet_name == "HumanLLM" else HH_HEADER


def get_gsheet_client():
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


def _get_worksheet(sheet_name: str):
    gc = get_gsheet_client()
    if gc is None:
        return None
    raw = st.secrets["SPREADSHEET_ID"].strip()
    sheet_id = raw.split("/d/")[1].split("/")[0] if "/d/" in raw else raw
    spreadsheet = gc.open_by_key(sheet_id)
    header = _get_header(sheet_name)
    try:
        return spreadsheet.worksheet(sheet_name)
    except WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=sheet_name, rows=2000, cols=20)
        ws.update([header], "A1")
        return ws


def _build_row_data(annotator_name: str, df_idx: int, match_label: int, df: pd.DataFrame) -> list:
    r = df.iloc[df_idx]
    source = str(r.get("source", ""))
    base = [
        annotator_name,
        str(r.get("paper_id", "")),
        int(r.get("global_id", df_idx)),
        str(r.get("feedback1_idx", "")),
        str(r.get("feedback1", "")),
        str(r.get("feedback2_idx", "")),
        str(r.get("feedback2", "")),
    ]
    if source == "human_llm":
        return base + [str(r.get("llm_name", "") or ""), int(match_label)]
    else:
        return base + [int(match_label)]


def _ensure_header(ws, header: list) -> list:
    """Read sheet, write header if blank, return all rows."""
    existing = ws.get_all_values()
    is_blank = not existing or all(
        all(not str(c).strip() for c in row) for row in existing
    )
    if is_blank:
        ws.update([header], "A1")
        return [header]
    return existing


def load_labels_from_gsheet(annotator_name: str, df: pd.DataFrame) -> tuple[dict, dict]:
    """Read both sheets. Returns (labels, row_cache).
    labels:    {df_row_idx: match_label}
    row_cache: {(sheet_name, paper_id, fb1_idx, fb2_idx): sheet_row_number (1-based)}
    """
    try:
        gc = get_gsheet_client()
        if gc is None:
            return {}, {}

        df_lookup: dict[tuple, int] = {}
        for i, row in df.iterrows():
            sname = _source_to_sheet_name(str(row.get("source", "")))
            key = (
                sname,
                str(row.get("paper_id", "")),
                str(row.get("feedback1_idx", "")),
                str(row.get("feedback2_idx", "")),
            )
            df_lookup[key] = int(i)

        labels: dict[int, int] = {}
        row_cache: dict[tuple, int] = {}

        for sheet_name in _SHEET_NAMES.values():
            ws = _get_worksheet(sheet_name)
            if ws is None:
                continue
            header = _get_header(sheet_name)
            existing = _ensure_header(ws, header)
            
            label_idx = 7 if sheet_name == "HumanHuman" else 8
            
            for sheet_row_num, row in enumerate(existing[1:], start=2):
                if len(row) < 5 or str(row[0]).strip() != annotator_name:
                    continue
                # key: (sheet_name, paper_id, fb1_idx, fb2_idx)
                # row[1]: paper_id, row[3]: feedback1_idx, row[5]: feedback2_idx
                key = (sheet_name, str(row[1]).strip(), str(row[3]).strip(), str(row[5]).strip())
                row_cache[key] = sheet_row_num
                if key in df_lookup and len(row) > label_idx:
                    try:
                        labels[df_lookup[key]] = int(row[label_idx])
                    except (ValueError, IndexError):
                        pass

        return labels, row_cache
    except Exception as e:
        logging.exception("Load from Google Sheets failed: %s", e)
        return {}, {}


def autosave_row(annotator_name: str, df_idx: int, match_label: int, df: pd.DataFrame) -> bool:
    """Save a single row to the appropriate sheet based on source type.
    Uses cached row positions to avoid reading the whole sheet.
    Returns True on success.
    """
    try:
        r = df.iloc[df_idx]
        sheet_name = _source_to_sheet_name(str(r.get("source", "")))
        ws = _get_worksheet(sheet_name)
        if ws is None:
            return False
        row_data = _build_row_data(annotator_name, df_idx, match_label, df)
        key = (
            sheet_name,
            str(r.get("paper_id", "")),
            str(r.get("feedback1_idx", "")),
            str(r.get("feedback2_idx", "")),
        )
        cache: dict = st.session_state.get("sheet_row_cache", {})
        if key in cache:
            ws.update([row_data], f"A{cache[key]}")
        else:
            header = _get_header(sheet_name)
            existing = ws.get_all_values()
            is_blank = not existing or all(all(not str(c).strip() for c in row) for row in existing)
            if is_blank:
                ws.update([header], "A1")
                next_row = 2
            else:
                next_row = len(existing) + 1
            ws.append_row(row_data)
            cache[key] = next_row
            st.session_state.sheet_row_cache = cache
        return True
    except Exception as e:
        logging.exception("Auto-save failed: %s", e)
        return False


def submit_to_gsheet(annotator_name: str, labels: dict, df: pd.DataFrame) -> tuple[bool, str]:
    """Bulk submit all labels to the appropriate sheets based on source type."""
    try:
        gc = get_gsheet_client()
        if gc is None:
            return False, "Google Sheets not configured."

        # Build per-sheet lookups of existing rows
        ws_map: dict[str, object] = {}
        lookup: dict[tuple, int] = {}
        for sheet_name in _SHEET_NAMES.values():
            ws = _get_worksheet(sheet_name)
            if ws is None:
                continue
            ws_map[sheet_name] = ws
            header = _get_header(sheet_name)
            existing = _ensure_header(ws, header)
            for i, row in enumerate(existing[1:], start=2):
                if len(row) >= 6 and str(row[0]).strip() == annotator_name:
                    # key: (sheet_name, paper_id, fb1_idx, fb2_idx)
                    # row[1]: paper_id, row[3]: feedback1_idx, row[5]: feedback2_idx
                    key = (sheet_name, str(row[1]).strip(), str(row[3]).strip(), str(row[5]).strip())
                    lookup[key] = i

        updated, appended = 0, 0
        for df_idx, match_label in labels.items():
            if df_idx >= len(df):
                continue
            r = df.iloc[df_idx]
            sheet_name = _source_to_sheet_name(str(r.get("source", "")))
            ws = ws_map.get(sheet_name)
            if ws is None:
                continue
            row_data = _build_row_data(annotator_name, df_idx, match_label, df)
            key = (
                sheet_name,
                str(r.get("paper_id", "")),
                str(r.get("feedback1_idx", "")),
                str(r.get("feedback2_idx", "")),
            )
            if key in lookup:
                ws.update([row_data], f"A{lookup[key]}")
                updated += 1
            else:
                ws.append_row(row_data)
                appended += 1

        if updated + appended == 0:
            return False, "No labels to submit."
        return True, f"Submitted {updated + appended} annotations ({updated} updated, {appended} new)."
    except Exception as e:
        logging.exception("Google Sheets submit failed: %s", e)
        return False, str(e)


# ── WORD OVERLAP HIGHLIGHT ────────────────────────────────────────────────────

_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "it", "its",
    "this", "that", "these", "those", "i", "we", "you", "he", "she",
    "they", "me", "us", "him", "her", "them", "my", "our", "your", "his",
    "their", "what", "which", "who", "when", "where", "why", "how",
    "all", "each", "every", "both", "some", "such", "no", "not", "only",
    "own", "same", "so", "than", "too", "very", "just", "also", "any",
    "as", "if", "then", "there", "about", "after", "before", "into",
    "more", "other", "well", "s", "t",
})


def _overlap_words(text_a: str, text_b: str) -> frozenset:
    """Return lowercase words present in both texts, excluding short tokens and stopwords."""
    def tokens(t: str) -> set:
        return {
            w for w in re.findall(r"\b[a-z]{3,}\b", t.lower())
            if w not in _STOPWORDS
        }
    return frozenset(tokens(text_a) & tokens(text_b))


def _highlight_text(text: str, words: frozenset) -> str:
    """Return HTML with words-in-overlap wrapped in <span class='word-hl'>.
    All other content is HTML-escaped."""
    if not words:
        return html.escape(text)
    parts = re.split(r"(\b\w+\b)", text)
    result = []
    for part in parts:
        if part.lower() in words:
            result.append(f'<span class="word-hl">{html.escape(part)}</span>')
        else:
            result.append(html.escape(part))
    return "".join(result)


# ── NAV HELPERS ───────────────────────────────────────────────────────────────

def _next_nav_idx(current_nav: int, assigned_pairs: list[tuple[int, bool]], labels: dict, n_assigned: int) -> int:
    """After labeling current_nav, return the next nav index to show.
    Priority: (1) next unlabeled row after current, (2) earliest unlabeled row,
    (3) stay at current if everything is labeled.
    """
    for i in range(current_nav + 1, n_assigned):
        if assigned_pairs[i][0] not in labels:
            return i
    for i in range(0, current_nav):
        if assigned_pairs[i][0] not in labels:
            return i
    return min(n_assigned - 1, current_nav + 1)


# ── ANNOTATOR ASSIGNMENT ───────────────────────────────────────────────────────
_ANNOTATORS = ["chani", "jimin", "hyunwoo", "xuhui"]


def compute_assigned_pairs(annotator_name: str, df: pd.DataFrame) -> list[tuple[int, bool]]:
    """Return ordered list of (df_idx, swap) for this annotator.

    Ordering:
    1. Group by paper_id (papers in order of first appearance in df)
    2. Within each paper:
       - Count how many pairs each feedback_idx appears in
       - Put the higher-frequency feedback on the left (swap=True if feedback2 is more frequent)
         Ties → keep original order (swap=False)
       - Sort pairs by (left_feedback_idx, right_feedback_idx) so same-anchor pairs
         appear consecutively
    swap=True means feedback2 is shown on the left and feedback1 on the right.
    """
    from collections import defaultdict, Counter

    key = str(annotator_name).strip().lower()
    if "annotators" in df.columns:
        raw_indices = [
            i for i, row in df.iterrows()
            if key in (row["annotators"] if isinstance(row["annotators"], list) else [])
        ]
    else:
        raw_indices = list(range(len(df)))

    # Group by paper_id, preserving order of first occurrence
    paper_order: list[str] = []
    paper_groups: dict[str, list[int]] = defaultdict(list)
    seen_papers: set[str] = set()
    for idx in raw_indices:
        pid = str(df.iloc[idx].get("paper_id", ""))
        if pid not in seen_papers:
            paper_order.append(pid)
            seen_papers.add(pid)
        paper_groups[pid].append(idx)

    result: list[tuple[int, bool]] = []

    for paper_id in paper_order:
        indices = paper_groups[paper_id]
        if len(indices) == 1:
            result.append((indices[0], False))
            continue

        # Count how many times each feedback_idx appears across this paper's assigned pairs
        freq: Counter = Counter()
        for idx in indices:
            row = df.iloc[idx]
            freq[str(row.get("feedback1_idx", ""))] += 1
            freq[str(row.get("feedback2_idx", ""))] += 1

        # Decide orientation per pair: higher-freq feedback goes left
        oriented: list[tuple[int, bool]] = []
        for idx in indices:
            row = df.iloc[idx]
            f1k = str(row.get("feedback1_idx", ""))
            f2k = str(row.get("feedback2_idx", ""))
            # swap only when feedback2 is strictly more frequent than feedback1
            swap = freq[f2k] > freq[f1k]
            oriented.append((idx, swap))

        # Sort so same-anchor (left) feedback pairs are consecutive
        def _sort_key(item: tuple[int, bool]) -> tuple[str, str]:
            idx, swap = item
            row = df.iloc[idx]
            f1k = str(row.get("feedback1_idx", ""))
            f2k = str(row.get("feedback2_idx", ""))
            left_k  = f2k if swap else f1k
            right_k = f1k if swap else f2k
            return (left_k, right_k)

        oriented.sort(key=_sort_key)
        result.extend(oriented)

    return result


# ── DATA ───────────────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent
_DATA_PATH = _PROJECT_ROOT / "data" / "pairs_assignment.json"


@st.cache_data(ttl=60)
def load_data(path: str, _mtime: float = 0) -> pd.DataFrame:
    import json as _json
    with open(path, encoding="utf-8") as f:
        records = _json.load(f)
    df = pd.DataFrame(records)
    return df.dropna(subset=["paper_id"]).reset_index(drop=True)


# ── SESSION STATE ──────────────────────────────────────────────────────────────

def init_state():
    if "annotator_name" not in st.session_state:
        q = st.query_params.get("annotator")
        st.session_state.annotator_name = str(q).strip() if q and str(q).strip() else ""
    # Always reload from file so data changes are picked up
    if _DATA_PATH.exists():
        mtime = _DATA_PATH.stat().st_mtime
        st.session_state.df = load_data(str(_DATA_PATH), mtime)
    elif "df" not in st.session_state:
        st.session_state.df = None
    if "row_nav_idx" not in st.session_state:
        st.session_state.row_nav_idx = 0
    if "labels" not in st.session_state:
        # {df_row_idx: 0 (non-match) or 1 (match)}
        st.session_state.labels = {}


init_state()

# ── ANNOTATOR NAME GATE ────────────────────────────────────────────────────────
if not st.session_state.annotator_name:
    st.markdown("### 👤 Enter your name to begin")
    st.caption("This will be recorded with your annotations when you submit.")
    name = st.text_input("Annotator name", placeholder="e.g. chani", label_visibility="collapsed")
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

# ── FILE UPLOAD FALLBACK ───────────────────────────────────────────────────────
if st.session_state.df is None:
    st.error("`data/pairs_assignment.json` not found. Please run `data/generate_assignment.py` first.")
    st.stop()

df: pd.DataFrame = st.session_state.df

# ── ASSIGNED PAIRS ─────────────────────────────────────────────────────────────
assigned_pairs = compute_assigned_pairs(annotator_name, df)
if not assigned_pairs:
    st.warning(
        f"Annotator '{annotator_name}' is not in the assignment list "
        f"({', '.join(_ANNOTATORS)}). No rows assigned."
    )
    st.stop()

# ── LOAD FROM GOOGLE SHEETS (once per session) ────────────────────────────────
_sheets_loaded_key = f"sheets_loaded_{annotator_name}"
if not st.session_state.get(_sheets_loaded_key) and get_gsheet_client():
    loaded, row_cache = load_labels_from_gsheet(annotator_name, df)
    if loaded:
        st.session_state.labels.update(loaded)
    st.session_state.sheet_row_cache = row_cache
    st.session_state[_sheets_loaded_key] = True
    st.session_state.row_nav_idx = next(
        (i for i, (df_idx, _) in enumerate(assigned_pairs) if df_idx not in st.session_state.labels),
        len(assigned_pairs) - 1,
    )

# On first load (no sheets), also land on earliest unlabeled
if not st.session_state.get(f"nav_initialized_{annotator_name}"):
    st.session_state.row_nav_idx = next(
        (i for i, (df_idx, _) in enumerate(assigned_pairs) if df_idx not in st.session_state.labels),
        len(assigned_pairs) - 1,
    )
    st.session_state[f"nav_initialized_{annotator_name}"] = True

# ── CURRENT ROW ───────────────────────────────────────────────────────────────
n_assigned = len(assigned_pairs)
nav_idx = min(st.session_state.row_nav_idx, n_assigned - 1)
actual_row_idx, swap_display = assigned_pairs[nav_idx]
row = df.iloc[actual_row_idx]

paper_id    = str(row.get("paper_id", ""))
llm_name    = str(row.get("llm_name", "") or "").strip()
title       = str(row.get("title", "") or "").strip()
abstract    = str(row.get("abstract", "") or "").strip()
pdf_url     = str(row.get("pdf_url", "") or "").strip()
pair_source = str(row.get("source", "") or "").strip()
global_id   = row.get("global_id", actual_row_idx)

# Apply left/right orientation based on swap_display
if swap_display:
    feedback_left  = str(row.get("feedback2", "") or "")
    feedback_right = str(row.get("feedback1", "") or "")
else:
    feedback_left  = str(row.get("feedback1", "") or "")
    feedback_right = str(row.get("feedback2", "") or "")

n_labeled = sum(1 for df_idx, _ in assigned_pairs if df_idx in st.session_state.labels)
pct = int(n_labeled / n_assigned * 100) if n_assigned else 0
current_label = st.session_state.labels.get(actual_row_idx)

# ── TOP BAR ───────────────────────────────────────────────────────────────────
c1, c2 = st.columns([6, 1])
with c1:
    st.markdown(f"""
    <div class="top-bar">
      <h1>⬡ Feedback Consensus Annotator</h1>
      <span class="progress-info">
        <span style="color:var(--accent); margin-right:0.8rem;">👤 {annotator_name}</span>
        Labeled: {n_labeled} / {n_assigned}
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

# ── NAVIGATION ROW: ← Prev | Go to # [input] | Next → ───────────────────────
_jump_key = f"jump_row_{annotator_name}"
st.session_state[_jump_key] = nav_idx

def _on_jump():
    new_val = int(st.session_state[_jump_key])
    if 0 <= new_val < n_assigned:
        st.session_state.row_nav_idx = new_val

label_badge = (
    "✅ Match" if current_label == 1
    else ("❌ Non-match" if current_label == 0 else "⬜ Unlabeled")
)

prev_col, pos_col, goto_col, next_col = st.columns([3, 2, 2, 3])
with prev_col:
    do_prev = st.button("← Prev", use_container_width=True)
with pos_col:
    st.markdown(
        f"<div style='text-align:center; font-family:IBM Plex Mono,monospace; "
        f"font-size:0.85rem; color:var(--text-dim); padding-top:0.55rem; line-height:1.3'>"
        f"{nav_idx + 1} / {n_assigned}<br>"
        f"<span style='font-size:0.8rem'>{label_badge}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
with goto_col:
    st.number_input(
        "Go to #",
        min_value=0,
        max_value=n_assigned - 1,
        step=1,
        format="%d",
        key=_jump_key,
        on_change=_on_jump,
    )
with next_col:
    do_next = st.button("Next →", use_container_width=True)

if do_prev:
    st.session_state.row_nav_idx = max(0, nav_idx - 1)
    st.rerun()
if do_next:
    st.session_state.row_nav_idx = min(n_assigned - 1, nav_idx + 1)
    st.rerun()

# ── FEEDBACK PANELS: feedback1 | feedback2 (side by side, no gap) ─────────────
panel_class = ""
if current_label == 1:
    panel_class = "match"
elif current_label == 0:
    panel_class = "nonmatch"

_src_badge = (
    "human ↔ human" if pair_source == "human_human"
    else ("human ↔ LLM")
)

_overlap = _overlap_words(feedback_left, feedback_right)
_html_left  = _highlight_text(feedback_left,  _overlap)
_html_right = _highlight_text(feedback_right, _overlap)

col_left, col_right = st.columns(2, gap="small")
with col_left:
    st.markdown(f"""
    <div class="feedback-panel {panel_class}">
      <div class="panel-label">Feedback A &nbsp;<span style="font-weight:400;color:var(--text-dim)">[{_src_badge}] pair #{global_id}</span></div>
      <div class="panel-text">{_html_left}</div>
    </div>
    """, unsafe_allow_html=True)

with col_right:
    st.markdown(f"""
    <div class="feedback-panel {panel_class}">
      <div class="panel-label">Feedback B &nbsp;<span style="font-weight:400;color:var(--text-dim)">[{_src_badge}] pair #{global_id}</span></div>
      <div class="panel-text">{_html_right}</div>
    </div>
    """, unsafe_allow_html=True)

# ── LABEL THIS PAIR (full width below feedbacks) ─────────────────────────────
st.markdown("<div style='margin-top:0.8rem'></div>", unsafe_allow_html=True)
st.markdown("<div class='label-heading'>Label this pair</div>", unsafe_allow_html=True)
st.markdown("<div class='label-btn-row'>", unsafe_allow_html=True)

match_active    = current_label == 1
nonmatch_active = current_label == 0

label_col1, label_col2 = st.columns(2)
with label_col1:
    if st.button(
        "✅  Match",
        key=f"btn_match_{actual_row_idx}",
        use_container_width=True,
        type="primary" if match_active else "secondary",
    ):
        st.session_state.labels[actual_row_idx] = 1
        if get_gsheet_client():
            autosave_row(annotator_name, actual_row_idx, 1, df)
        st.session_state.row_nav_idx = _next_nav_idx(nav_idx, assigned_pairs, st.session_state.labels, n_assigned)
        st.rerun()
with label_col2:
    if st.button(
        "❌  Non-match",
        key=f"btn_nonmatch_{actual_row_idx}",
        use_container_width=True,
        type="primary" if nonmatch_active else "secondary",
    ):
        st.session_state.labels[actual_row_idx] = 0
        if get_gsheet_client():
            autosave_row(annotator_name, actual_row_idx, 0, df)
        st.session_state.row_nav_idx = _next_nav_idx(nav_idx, assigned_pairs, st.session_state.labels, n_assigned)
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<hr style='margin:0.8rem 0'>", unsafe_allow_html=True)


# ── PAPER INFO (full width) ───────────────────────────────────────────────────
if abstract or pdf_url:
    abstract_escaped = html.escape(abstract) if abstract else ""
    title_escaped = html.escape(title) if title else ""
    pdf_link_html = (
        f'<a href="{html.escape(pdf_url)}" target="_blank" rel="noopener">📄 Open PDF</a>'
        if pdf_url else ""
    )
    st.markdown(f"""
    <div class="paper-info">
      <div class="paper-info-title">Paper{f': {title_escaped}' if title_escaped else ''}</div>
      {f'<div class="paper-abstract">{abstract_escaped}</div>' if abstract_escaped else ''}
      {f'<div class="paper-pdf-link">{pdf_link_html}</div>' if pdf_link_html else ''}
    </div>
    """, unsafe_allow_html=True)
