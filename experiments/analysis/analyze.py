#!/usr/bin/env python3
"""Cross-experiment analysis — loads all results.json files and produces
comparison tables, signal effectiveness summaries, and the core
temporal-vs-spatial thesis table.

Designed to run after any subset of experiments — gracefully handles
missing results.json files.

Usage:
    cd experiments
    uv run python analysis/analyze.py
"""

from __future__ import annotations

import json
import csv
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENTS_DIR = SCRIPT_DIR.parent
TABLES_DIR = SCRIPT_DIR / "tables"
TABLES_DIR.mkdir(exist_ok=True)

EXPERIMENT_IDS = [14, 15, 16, 17, 18]


def load_results() -> dict[int, dict]:
    """Load results.json from each experiment that has one."""
    results = {}
    for exp_id in EXPERIMENT_IDS:
        path = EXPERIMENTS_DIR / f"experiment-{exp_id}" / "output" / "results.json"
        if path.exists():
            results[exp_id] = json.loads(path.read_text())
    return results


# ── Table 1: Conflict Detection Comparison ──────────────────────

def conflict_detection_table(results: dict[int, dict]) -> str:
    """Compare what Git, SHACL, and oracle detected across all scenarios."""
    rows = []

    # Exp 14: confusion matrix scenarios
    if 14 in results:
        for sc in results[14]["findings"]["scenarios"]:
            for o in sc["orderings"]:
                gc = o["git_conflict"]
                sv = o["semantically_valid"]
                rows.append({
                    "experiment": 14,
                    "scenario": sc["scenario"],
                    "ordering": o["ordering"],
                    "git_conflict": gc,
                    "shacl_fail": (
                        o.get("validation", {}).get("shacl_violation_count", 0) > 0
                        if o.get("validation") else None
                    ),
                    "oracle_fail": (
                        o.get("validation", {}).get("oracle_violation_count", 0) > 0
                        if o.get("validation") else None
                    ),
                    "semantically_valid": sv,
                })

    # Exp 15: composition scenarios
    if 15 in results:
        for sc in results[15]["findings"]["scenarios"]:
            d = sc["detection"]
            rows.append({
                "experiment": 15,
                "scenario": sc["scenario"],
                "ordering": "composed",
                "git_conflict": d["git"],
                "shacl_fail": d["composed_shacl"],
                "oracle_fail": d["composition_gate"],
                "semantically_valid": not (d["composed_shacl"] or d["composition_gate"]),
            })

    # Exp 17: classification scenarios
    if 17 in results:
        for sc in results[17]["findings"]["scenarios"]:
            for o in sc["orderings"]:
                gc = o["git_conflict"]
                sv = o["semantically_valid"]
                rows.append({
                    "experiment": 17,
                    "scenario": sc["scenario"],
                    "ordering": o["ordering"],
                    "git_conflict": gc,
                    "shacl_fail": (
                        o.get("validation", {}).get("shacl_violation_count", 0) > 0
                        if o.get("validation") else None
                    ),
                    "oracle_fail": (
                        o.get("validation", {}).get("oracle_violation_count", 0) > 0
                        if o.get("validation") else None
                    ),
                    "semantically_valid": sv,
                })

    # Write CSV
    csv_path = TABLES_DIR / "conflict-detection.csv"
    if rows:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    # Write markdown
    md_lines = [
        "# Conflict Detection Comparison",
        "",
        "| Exp | Scenario | Ordering | Git | SHACL | Oracle | Valid |",
        "|:---:|----------|----------|:---:|:-----:|:------:|:----:|",
    ]
    for r in rows:
        def fmt(v):
            if v is None: return "—"
            if isinstance(v, bool): return "yes" if v else "no"
            return str(v)
        md_lines.append(
            f"| {r['experiment']} | {r['scenario'][:25]} | {r['ordering'][:15]} | "
            f"{fmt(r['git_conflict'])} | {fmt(r['shacl_fail'])} | "
            f"{fmt(r['oracle_fail'])} | {fmt(r['semantically_valid'])} |"
        )

    md = "\n".join(md_lines) + "\n"
    (TABLES_DIR / "conflict-detection.md").write_text(md)
    return md


# ── Table 2: Signal Effectiveness ───────────────────────────────

def signal_effectiveness(results: dict[int, dict]) -> str:
    """For each signal type, report catch rate and miss rate."""
    signals = {
        "git_textual": {"catches": 0, "misses": 0, "false_positives": 0, "total": 0},
        "shacl_shapes": {"catches": 0, "misses": 0, "false_positives": 0, "total": 0},
        "oracle_queries": {"catches": 0, "misses": 0, "false_positives": 0, "total": 0},
    }

    # Exp 14 confusion matrix is the cleanest source
    if 14 in results:
        cm = results[14]["findings"]["confusion_matrix"]
        signals["git_textual"]["catches"] = cm["true_positive"]
        signals["git_textual"]["misses"] = cm["false_negative"]
        signals["git_textual"]["false_positives"] = cm["false_positive"]
        signals["git_textual"]["total"] = cm["total"]

    # Count SHACL and oracle across exp 14 scenarios
    if 14 in results:
        for sc in results[14]["findings"]["scenarios"]:
            for o in sc["orderings"]:
                val = o.get("validation")
                if val is None:
                    continue
                has_real_conflict = not val["semantically_valid"]
                shacl_fired = val["shacl_violation_count"] > 0
                oracle_fired = val["oracle_violation_count"] > 0

                for sig_name, fired in [("shacl_shapes", shacl_fired), ("oracle_queries", oracle_fired)]:
                    signals[sig_name]["total"] += 1
                    if fired and has_real_conflict:
                        signals[sig_name]["catches"] += 1
                    elif fired and not has_real_conflict:
                        signals[sig_name]["false_positives"] += 1
                    elif not fired and has_real_conflict:
                        signals[sig_name]["misses"] += 1

    md_lines = [
        "# Signal Effectiveness",
        "",
        "| Signal | Catches | Misses | False Positives | Total |",
        "|--------|:-------:|:------:|:---------------:|:-----:|",
    ]
    for name, s in signals.items():
        md_lines.append(
            f"| {name} | {s['catches']} | {s['misses']} | {s['false_positives']} | {s['total']} |"
        )

    md = "\n".join(md_lines) + "\n"
    csv_path = TABLES_DIR / "signal-effectiveness.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["signal", "catches", "misses", "false_positives", "total"])
        writer.writeheader()
        for name, s in signals.items():
            writer.writerow({"signal": name, **s})

    (TABLES_DIR / "signal-effectiveness.md").write_text(md)
    return md


# ── Table 3: Temporal vs Spatial Signal Matrix ──────────────────

def temporal_spatial_matrix(results: dict[int, dict]) -> str:
    """Core thesis table: what requires temporal, spatial, or both signals."""
    findings = [
        {
            "finding": "Cross-file coupling conflicts (power budget)",
            "experiment": 14,
            "temporal_git": "no — Git merges cleanly (different files)",
            "spatial_rdf": "YES — oracle detects budget violation",
            "requires_both": "Spatial alone sufficient for detection; Git identifies who diverged",
        },
        {
            "finding": "Serialization-order false positives",
            "experiment": 14,
            "temporal_git": "YES — Git conflicts on reordered text",
            "spatial_rdf": "no — graphs are semantically identical",
            "requires_both": "Both needed: Git flags it, RDF confirms it's spurious",
        },
        {
            "finding": "Ontology composition conflicts (property rename)",
            "experiment": 15,
            "temporal_git": "no — different files",
            "spatial_rdf": "YES — composed SHACL detects missing property",
            "requires_both": "Spatial alone sufficient; Git shows who renamed",
        },
        {
            "finding": "Schema + data composition conflicts",
            "experiment": 15,
            "temporal_git": "no — different files",
            "spatial_rdf": "YES — composed SHACL detects new violation",
            "requires_both": "Spatial alone sufficient; Git shows which team added what",
        },
        {
            "finding": "Lifecycle gate regression",
            "experiment": 16,
            "temporal_git": "no — Git merges cleanly (different files)",
            "spatial_rdf": "YES — lifecycle SHACL shape detects broken gate",
            "requires_both": "Spatial detects regression; Git branch topology shows lifecycle ordering",
        },
        {
            "finding": "Four-way conflict classification",
            "experiment": 17,
            "temporal_git": "partial — distinguishes 2 classes (clean/conflict)",
            "spatial_rdf": "partial — distinguishes ordering but not textual",
            "requires_both": "YES — only combination distinguishes all 4 classes",
        },
        {
            "finding": "Non-commutative ordering artifacts",
            "experiment": 17,
            "temporal_git": "YES — identifies which branch was applied when",
            "spatial_rdf": "YES — shows which ordering violates constraints",
            "requires_both": "YES — both needed to detect and explain",
        },
        {
            "finding": "Evidence staleness after model evolution",
            "experiment": 18,
            "temporal_git": "partial — shows what changed between commits",
            "spatial_rdf": "YES — SHACL detects hash mismatch",
            "requires_both": "YES — RDF identifies affected requirements; Git identifies the change",
        },
    ]

    md_lines = [
        "# Temporal vs. Spatial Signal Matrix",
        "",
        "Core thesis: RDF excels at the spatial dimension (how things relate),",
        "Git excels at the temporal dimension (how things evolve).",
        "",
        "| Finding | Exp | Temporal (Git) | Spatial (RDF/SHACL) | Requires Both? |",
        "|---------|:---:|----------------|---------------------|----------------|",
    ]
    for f in findings:
        md_lines.append(
            f"| {f['finding']} | {f['experiment']} | "
            f"{f['temporal_git']} | {f['spatial_rdf']} | {f['requires_both']} |"
        )

    md = "\n".join(md_lines) + "\n"
    (TABLES_DIR / "temporal-vs-spatial.md").write_text(md)
    return md


# ── Main ────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Cross-Experiment Analysis")
    print("=" * 60)
    print()

    results = load_results()
    print(f"Loaded results from {len(results)} experiments: {sorted(results.keys())}")
    missing = [i for i in EXPERIMENT_IDS if i not in results]
    if missing:
        print(f"Missing: {missing}")
    print()

    # Table 1
    print("─" * 60)
    print("Table 1: Conflict Detection Comparison")
    print("─" * 60)
    md1 = conflict_detection_table(results)
    print(md1)

    # Table 2
    print("─" * 60)
    print("Table 2: Signal Effectiveness")
    print("─" * 60)
    md2 = signal_effectiveness(results)
    print(md2)

    # Table 3
    print("─" * 60)
    print("Table 3: Temporal vs. Spatial Signal Matrix")
    print("─" * 60)
    md3 = temporal_spatial_matrix(results)
    print(md3)

    print("─" * 60)
    print(f"Tables written to: {TABLES_DIR}")
    print("  - conflict-detection.md / .csv")
    print("  - signal-effectiveness.md / .csv")
    print("  - temporal-vs-spatial.md")
    print("─" * 60)


if __name__ == "__main__":
    main()
