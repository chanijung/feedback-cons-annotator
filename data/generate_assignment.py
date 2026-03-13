"""
Generate pairs_assignment.json from human_human and human_llm embedding similarity results.

Distribution strategy:
  - 280 human-human pairs + 280 human-llm pairs = 560 total pairs
  - Pairs are interleaved: even global_id → human-human, odd global_id → human-llm
  - 4 annotators: chani, jimin, hyunwoo, xuhui
  - Each pair is assigned to exactly 3 annotators (one excluded per block of 140)
  - Block 0 (global_id  0–139): exclude chani   → jimin, hyunwoo, xuhui
  - Block 1 (global_id 140–279): exclude jimin   → chani, hyunwoo, xuhui
  - Block 2 (global_id 280–419): exclude hyunwoo → chani, jimin,   xuhui
  - Block 3 (global_id 420–559): exclude xuhui   → chani, jimin,   hyunwoo
  Each annotator ends up with 420 pairs (210 human-human + 210 human-llm).
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

ANNOTATORS = ["chani", "jimin", "hyunwoo", "xuhui"]
BLOCK_SIZE = 140  # 4 blocks × 140 = 560 total


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


def assign_annotators(global_id: int) -> list:
    block = global_id // BLOCK_SIZE  # 0–3
    excluded = ANNOTATORS[block]
    return [a for a in ANNOTATORS if a != excluded]


def main():
    hh_data = load_json(DATA / "human_human-emb_sim_results.json")
    hl_data = load_json(DATA / "human_llm-emb_sim_results.json")
    papers = load_json(DATA / "sample_50_papers-consensus_human_annot.json")
    paper_lookup = build_paper_lookup(papers)

    # Flatten all pairs from each source
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

    assert len(hh_pairs) == 280, f"Expected 280 human-human pairs, got {len(hh_pairs)}"
    assert len(hl_pairs) == 280, f"Expected 280 human-llm pairs, got {len(hl_pairs)}"

    # Interleave: even global_id → hh, odd global_id → hl
    assignments = []
    for i in range(280):
        for source_pairs, src_i in [(hh_pairs[i], 2 * i), (hl_pairs[i], 2 * i + 1)]:
            entry = dict(source_pairs)
            entry["global_id"] = src_i
            entry["annotators"] = assign_annotators(src_i)
            assignments.append(entry)

    # Sort by global_id for clarity
    assignments.sort(key=lambda x: x["global_id"])

    assert len(assignments) == 560

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
