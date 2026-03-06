import html
import logging

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

</style>
""", unsafe_allow_html=True)


# ── GOOGLE SHEETS ─────────────────────────────────────────────────────────────

_SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_HEADER = [
    "annotator_name", "paper_id",
    "feedback1_idx", "feedback1",
    "feedback2_idx", "feedback2",
    "llm_name", "match_label",
]


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


def _get_worksheet():
    gc = get_gsheet_client()
    if gc is None:
        return None
    raw = st.secrets["SPREADSHEET_ID"].strip()
    sheet_id = raw.split("/d/")[1].split("/")[0] if "/d/" in raw else raw
    sheet_name = st.secrets.get("SHEET_NAME", "Annotations")
    spreadsheet = gc.open_by_key(sheet_id)
    try:
        return spreadsheet.worksheet(sheet_name)
    except WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
        ws.update([SHEET_HEADER], "A1")
        return ws


def _build_row_data(annotator_name: str, df_idx: int, match_label: int, df: pd.DataFrame) -> list:
    r = df.iloc[df_idx]
    return [
        annotator_name,
        str(r.get("paper_id", "")),
        str(r.get("feedback1_idx", "")),
        str(r.get("feedback1", "")),
        str(r.get("feedback2_idx", "")),
        str(r.get("feedback2", "")),
        str(r.get("llm_name", "") or ""),
        int(match_label),
    ]


def _ensure_header(ws) -> list:
    """Read sheet, write header if blank, return all rows."""
    existing = ws.get_all_values()
    is_blank = not existing or all(
        all(not str(c).strip() for c in row) for row in existing
    )
    if is_blank:
        ws.update([SHEET_HEADER], "A1")
        return [SHEET_HEADER]
    return existing


def load_labels_from_gsheet(annotator_name: str, df: pd.DataFrame) -> tuple[dict, dict]:
    """Read sheet once. Returns (labels, row_cache).
    labels: {df_row_idx: match_label}
    row_cache: {(paper_id, fb1_idx, fb2_idx): sheet_row_number (1-based)}
    """
    try:
        ws = _get_worksheet()
        if ws is None:
            return {}, {}
        existing = _ensure_header(ws)

        df_lookup: dict[tuple, int] = {}
        for i, row in df.iterrows():
            key = (
                str(row.get("paper_id", "")),
                str(row.get("feedback1_idx", "")),
                str(row.get("feedback2_idx", "")),
            )
            df_lookup[key] = int(i)

        labels: dict[int, int] = {}
        row_cache: dict[tuple, int] = {}
        for sheet_row_num, row in enumerate(existing[1:], start=2):
            if len(row) < 5 or str(row[0]).strip() != annotator_name:
                continue
            key = (str(row[1]).strip(), str(row[2]).strip(), str(row[4]).strip())
            row_cache[key] = sheet_row_num
            if key in df_lookup and len(row) >= 8:
                try:
                    labels[df_lookup[key]] = int(row[7])
                except (ValueError, IndexError):
                    pass
        return labels, row_cache
    except Exception as e:
        logging.exception("Load from Google Sheets failed: %s", e)
        return {}, {}


def autosave_row(annotator_name: str, df_idx: int, match_label: int, df: pd.DataFrame) -> bool:
    """Save a single row. Uses cached row positions to avoid reading the whole sheet.
    Returns True on success.
    """
    try:
        ws = _get_worksheet()
        if ws is None:
            return False
        row_data = _build_row_data(annotator_name, df_idx, match_label, df)
        r = df.iloc[df_idx]
        key = (str(r.get("paper_id", "")), str(r.get("feedback1_idx", "")), str(r.get("feedback2_idx", "")))
        cache: dict = st.session_state.get("sheet_row_cache", {})
        if key in cache:
            ws.update([row_data], f"A{cache[key]}")
        else:
            # New row: ensure header exists, then append
            existing = ws.get_all_values()
            is_blank = not existing or all(all(not str(c).strip() for c in row) for row in existing)
            if is_blank:
                ws.update([SHEET_HEADER], "A1")
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
    """Bulk submit all labels (used by the manual Submit button)."""
    try:
        ws = _get_worksheet()
        if ws is None:
            return False, "Google Sheets not configured."

        existing = _ensure_header(ws)
        lookup: dict[tuple, int] = {}
        for i, row in enumerate(existing[1:], start=2):
            if len(row) >= 5 and str(row[0]).strip() == annotator_name:
                key = (str(row[1]).strip(), str(row[2]).strip(), str(row[4]).strip())
                lookup[key] = i

        updated, appended = 0, 0
        for df_idx, match_label in labels.items():
            if df_idx >= len(df):
                continue
            row_data = _build_row_data(annotator_name, df_idx, match_label, df)
            r = df.iloc[df_idx]
            key = (str(r.get("paper_id", "")), str(r.get("feedback1_idx", "")), str(r.get("feedback2_idx", "")))
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
    except Exception as e:
        logging.exception("Load from Google Sheets failed: %s", e)
        return {}


# ── ANNOTATOR ASSIGNMENT ───────────────────────────────────────────────────────
_ANNOTATORS = ["chani", "jimin", "hyunwoo", "xuhui"]
_ASSIGNMENT = {
    "chani":   [0, 1, 2, 4, 5, 6, 8, 9, 10],
    "jimin":   [0, 1, 3, 4, 5, 7, 8, 9, 11],
    "hyunwoo": [0, 2, 3, 4, 6, 7, 8, 10, 11],
    "xuhui":   [1, 2, 3, 5, 6, 7, 9, 10, 11],
}


def get_assigned_rows(annotator_name: str, df_len: int) -> list[int]:
    key = str(annotator_name).strip().lower()
    indices = _ASSIGNMENT.get(key)
    if indices is None:
        return list(range(df_len))
    return [i for i in indices if i < df_len]


# ── DATA ───────────────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent
_DATA_PATH = _PROJECT_ROOT / "data" / "annotation_sheet.csv"


@st.cache_data(ttl=60)
def load_data(path: str, _mtime: float = 0) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df.dropna(subset=["paper_id"]).reset_index(drop=True)


# ── SESSION STATE ──────────────────────────────────────────────────────────────

def init_state():
    if "annotator_name" not in st.session_state:
        q = st.query_params.get("annotator")
        st.session_state.annotator_name = str(q).strip() if q and str(q).strip() else ""
    # Always reload from file so CSV changes are picked up
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
    st.markdown("### 📂 Upload `annotation_sheet.csv` to begin")
    up = st.file_uploader("CSV file", type=["csv"])
    if up:
        st.session_state.df = (
            pd.read_csv(up).dropna(subset=["paper_id"]).reset_index(drop=True)
        )
        st.rerun()
    st.stop()

df: pd.DataFrame = st.session_state.df

# ── ASSIGNED ROWS ──────────────────────────────────────────────────────────────
assigned_rows = get_assigned_rows(annotator_name, len(df))
if not assigned_rows:
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
    # Jump to earliest unlabeled row after loading
    st.session_state.row_nav_idx = next(
        (i for i, df_idx in enumerate(assigned_rows) if df_idx not in st.session_state.labels),
        len(assigned_rows) - 1,
    )

# On first load (no sheets), also land on earliest unlabeled
if not st.session_state.get(f"nav_initialized_{annotator_name}"):
    st.session_state.row_nav_idx = next(
        (i for i, df_idx in enumerate(assigned_rows) if df_idx not in st.session_state.labels),
        len(assigned_rows) - 1,
    )
    st.session_state[f"nav_initialized_{annotator_name}"] = True

# ── CURRENT ROW ───────────────────────────────────────────────────────────────
n_assigned = len(assigned_rows)
nav_idx = min(st.session_state.row_nav_idx, n_assigned - 1)
actual_row_idx = assigned_rows[nav_idx]
row = df.iloc[actual_row_idx]

paper_id    = str(row.get("paper_id", ""))
feedback1   = str(row.get("feedback1", "") or "")
feedback2   = str(row.get("feedback2", "") or "")
feedback1_idx = str(row.get("feedback1_idx", ""))
feedback2_idx = str(row.get("feedback2_idx", ""))
llm_name    = str(row.get("llm_name", "") or "").strip()
title       = str(row.get("title", "") or "").strip()
abstract    = str(row.get("abstract", "") or "").strip()
pdf_url     = str(row.get("pdf_url", "") or "").strip()

n_labeled = sum(1 for i in assigned_rows if i in st.session_state.labels)
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

col_left, col_right = st.columns(2, gap="small")
with col_left:
    st.markdown(f"""
    <div class="feedback-panel {panel_class}">
      <div class="panel-label">Feedback 1</div>
      <div class="panel-idx">#{feedback1_idx}</div>
      <div class="panel-text">{html.escape(feedback1)}</div>
    </div>
    """, unsafe_allow_html=True)

with col_right:
    st.markdown(f"""
    <div class="feedback-panel {panel_class}">
      <div class="panel-label">Feedback 2</div>
      <div class="panel-idx">#{feedback2_idx}</div>
      <div class="panel-text">{html.escape(feedback2)}</div>
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
        st.session_state.row_nav_idx = min(n_assigned - 1, nav_idx + 1)
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
        st.session_state.row_nav_idx = min(n_assigned - 1, nav_idx + 1)
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
