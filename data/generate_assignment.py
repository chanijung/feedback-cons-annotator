"""
Generate pairs_assignment.json from human_human and human_llm embedding similarity results.

Distribution strategy:
  - 140 human-human pairs + 140 human-llm pairs = 280 total pairs
  - Pairs are interleaved: even global_id → human-human, odd global_id → human-llm
  - 4 annotators: chani, jimin, hyunwoo, xuhui
  - Each pair is assigned to exactly 3 annotators.
  - xuhui is assigned only to pairs that were assigned to xuhui in the old 280-sample
    assignment (data/old-280_samples/pairs_assignment.json); no newly assigned samples.
  - Among xuhui-eligible pairs, pairs xuhui already annotated (in old CSV files) are
    prioritised first, then remaining slots are filled by global_id order.
  - 210 pairs include xuhui; 70 pairs → chani, jimin, hyunwoo only.
  Each annotator ends up with 210 pairs (105 human-human + 105 human-llm).
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OLD_SAMPLES_DIR = DATA / "old-280_samples"

ANNOTATORS = ["chani", "jimin", "hyunwoo", "xuhui"]
OTHER_ANNOTATORS = ["chani", "jimin", "hyunwoo"]
TOTAL_PAIRS = 280  # 140 HH + 140 HL
PAIRS_PER_SOURCE = 140
XUHUI_TARGET = 210  # pairs assigned to xuhui (subset of old assignment)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_paper_lookup(papers):
    return {p["paper_id"]: p for p in papers}


def pairs_from_hh(paper_id, pairs, paper_info):
    """Flatten human-human pairs into normalized dicts."""
    result = []
    for p in pairs:
        result.append({
            "source": "human_human",
            "paper_id": paper_id,
            "feedback1_idx": p["unit_key_a"],
            "feedback1": p["text_a"],
            "feedback2_idx": p["unit_key_b"],
            "feedback2": p["text_b"],
            "llm_name": "",
            "title": paper_info.get("title", ""),
            "abstract": paper_info.get("abstract", ""),
            "pdf_url": paper_info.get("pdf_url", ""),
        })
    return result


def pairs_from_hl(paper_id, pairs, paper_info, model_name):
    """Flatten human-llm pairs into normalized dicts."""
    result = []
    for p in pairs:
        result.append({
            "source": "human_llm",
            "paper_id": paper_id,
            "feedback1_idx": p["human_unit_key"],
            "feedback1": p["human_text"],
            "feedback2_idx": p["llm_unit_key"],
            "feedback2": p["llm_text"],
            "llm_name": model_name,
            "title": paper_info.get("title", ""),
            "abstract": paper_info.get("abstract", ""),
            "pdf_url": paper_info.get("pdf_url", ""),
        })
    return result


def pair_key(entry: dict) -> tuple:
    """Stable key for matching pairs across old/new assignment (paper_id, feedback1_idx, feedback2_idx, source)."""
    return (
        entry["paper_id"],
        entry["feedback1_idx"],
        entry["feedback2_idx"],
        entry["source"],
    )


def load_xuhui_old_assignment_keys() -> set:
    """Load old pairs_assignment and return set of pair keys that were assigned to xuhui."""
    path = OLD_SAMPLES_DIR / "pairs_assignment.json"
    if not path.exists():
        return set()
    data = load_json(path)
    return {
        pair_key(e)
        for e in data
        if "xuhui" in e.get("annotators", [])
    }


def load_xuhui_annotated_keys() -> set:
    """Return pair keys xuhui has already annotated, from the old CSV files.

    Key format matches pair_key(): (paper_id, feedback1_idx, feedback2_idx, source)
    """
    import csv as _csv
    source_map = {
        OLD_SAMPLES_DIR / "Feedback consensus annotation - HumanHuman.csv": "human_human",
        OLD_SAMPLES_DIR / "Feedback consensus annotation - HumanLLM.csv":   "human_llm",
    }
    keys: set = set()
    for csv_path, source in source_map.items():
        if not csv_path.exists():
            continue
        with open(csv_path, encoding="utf-8", newline="") as f:
            rows = list(_csv.reader(f))
        if not rows:
            continue
        header = rows[0]
        try:
            paper_col = header.index("paper_id")
            f1_col    = header.index("feedback1_idx")
            f2_col    = header.index("feedback2_idx")
        except ValueError:
            continue
        for row in rows[1:]:
            if not row or str(row[0]).strip().lower() != "xuhui":
                continue
            # Same order as pair_key(): (paper_id, fb1, fb2, source)
            keys.add((
                str(row[paper_col]).strip(),
                str(row[f1_col]).strip(),
                str(row[f2_col]).strip(),
                source,
            ))
    return keys


def main():
    hh_data = load_json(DATA / "human_human-emb_sim_results.json")
    hl_data = load_json(DATA / "human_llm-emb_sim_results.json")
    papers = load_json(DATA / "sample_50_papers-consensus_human_annot.json")
    paper_lookup = build_paper_lookup(papers)
    xuhui_old_keys      = load_xuhui_old_assignment_keys()
    xuhui_annotated_keys = load_xuhui_annotated_keys()

    # Flatten all pairs from each source (140 per source)
    hh_pairs = []
    for entry in hh_data:
        pid = entry["paper_id"]
        info = paper_lookup.get(pid, {})
        hh_pairs.extend(pairs_from_hh(pid, entry["pairs"], info))

    hl_pairs = []
    for entry in hl_data:
        pid = entry["paper_id"]
        info = paper_lookup.get(pid, {})
        hl_pairs.extend(pairs_from_hl(pid, entry["pairs"], info, entry.get("model_name", "")))

    assert len(hh_pairs) == PAIRS_PER_SOURCE, f"Expected {PAIRS_PER_SOURCE} human-human pairs, got {len(hh_pairs)}"
    assert len(hl_pairs) == PAIRS_PER_SOURCE, f"Expected {PAIRS_PER_SOURCE} human-llm pairs, got {len(hl_pairs)}"

    # Interleave: even global_id → hh, odd global_id → hl (global_id 0..279)
    raw_entries = []
    for i in range(PAIRS_PER_SOURCE):
        for source_pairs, src_i in [(hh_pairs[i], 2 * i), (hl_pairs[i], 2 * i + 1)]:
            entry = dict(source_pairs)
            entry["global_id"] = src_i
            raw_entries.append(entry)

    raw_entries.sort(key=lambda x: x["global_id"])
    assert len(raw_entries) == TOTAL_PAIRS

    # Mark which pairs can get xuhui (must be in old xuhui assignment)
    for e in raw_entries:
        e["_key"] = pair_key(e)
        e["_xuhui_eligible"]  = e["_key"] in xuhui_old_keys
        e["_xuhui_annotated"] = e["_key"] in xuhui_annotated_keys

    xuhui_eligible_indices = [i for i, e in enumerate(raw_entries) if e["_xuhui_eligible"]]
    if len(xuhui_eligible_indices) < XUHUI_TARGET:
        raise SystemExit(
            f"Only {len(xuhui_eligible_indices)} of {TOTAL_PAIRS} new pairs were in xuhui's old assignment; "
            f"need at least {XUHUI_TARGET} for target 210. Check data/old-280_samples/pairs_assignment.json."
        )

    # Select XUHUI_TARGET pairs: already-annotated ones first, then fill by global_id order
    annotated_eligible   = [i for i in xuhui_eligible_indices if raw_entries[i]["_xuhui_annotated"]]
    unannotated_eligible = [i for i in xuhui_eligible_indices if not raw_entries[i]["_xuhui_annotated"]]
    # Sort each group by global_id
    annotated_eligible.sort(key=lambda i: raw_entries[i]["global_id"])
    unannotated_eligible.sort(key=lambda i: raw_entries[i]["global_id"])

    selected = annotated_eligible + unannotated_eligible
    selected = selected[:XUHUI_TARGET]

    print(f"xuhui 선택: 이미 annotation한 pair {len(annotated_eligible)}개 우선 포함, "
          f"추가 {len(selected) - len(annotated_eligible)}개 (global_id 순)")

    xuhui_assign_global_ids = {raw_entries[i]["global_id"] for i in selected}

    # Assign annotators: 210 with xuhui (split 70/70/70 for other two), 70 without xuhui
    # Groups for xuhui pairs: (xuhui, chani, jimin), (xuhui, chani, hyunwoo), (xuhui, jimin, hyunwoo)
    other_combos = [
        ["xuhui", "chani", "jimin"],
        ["xuhui", "chani", "hyunwoo"],
        ["xuhui", "jimin", "hyunwoo"],
    ]
    no_xuhui_combo = ["chani", "jimin", "hyunwoo"]

    assignments = []
    xuhui_pair_idx = 0
    no_xuhui_count = 0
    for e in raw_entries:
        gid = e["global_id"]
        if gid in xuhui_assign_global_ids:
            annotators = other_combos[xuhui_pair_idx % 3]
            xuhui_pair_idx += 1
        else:
            annotators = no_xuhui_combo
            no_xuhui_count += 1
        entry = {k: v for k, v in e.items() if not k.startswith("_")}
        entry["annotators"] = annotators
        assignments.append(entry)

    assert no_xuhui_count == 70, f"Expected 70 pairs without xuhui, got {no_xuhui_count}"
    assert xuhui_pair_idx == XUHUI_TARGET

    # Verify distribution
    counts = {a: 0 for a in ANNOTATORS}
    src_counts = {a: {"human_human": 0, "human_llm": 0} for a in ANNOTATORS}
    for entry in assignments:
        for a in entry["annotators"]:
            counts[a] += 1
            src_counts[a][entry["source"]] += 1

    print("Annotator distribution:")
    for a in ANNOTATORS:
        print(f"  {a}: {counts[a]} total "
              f"({src_counts[a]['human_human']} human-human, "
              f"{src_counts[a]['human_llm']} human-llm)")

    out_path = DATA / "pairs_assignment.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(assignments, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(assignments)} pairs → {out_path}")


if __name__ == "__main__":
    main()
