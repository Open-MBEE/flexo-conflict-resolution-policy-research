#!/usr/bin/env python3
"""Findings report generator — synthesizes results from all experiments
into a single markdown report.

Usage:
    cd experiments
    uv run python analysis/report.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENTS_DIR = SCRIPT_DIR.parent
REPORT_PATH = SCRIPT_DIR / "report.md"

EXPERIMENT_IDS = [14, 15, 16, 17, 18]

EXPERIMENT_META = {
    14: {
        "title": "Git as RDF Conflict Detector — Confusion Matrix",
        "question": "Does Git's textual merge produce meaningful conflict signals for RDF?",
    },
    15: {
        "title": "Ontology Package Versioning — Composition Conflicts",
        "question": "Can independently-evolved ontology packages produce composition conflicts invisible to both Git and per-package SHACL?",
    },
    16: {
        "title": "Lifecycle Branches — Stage Gates as SHACL Shapes",
        "question": "Can SHACL shapes encode lifecycle gate prerequisites, and what happens when a late structural change causes regression?",
    },
    17: {
        "title": "Dual-Signal Conflict Classification (Git + SHACL)",
        "question": "Does combining Git + SHACL signals produce a richer conflict classification than either alone?",
    },
    18: {
        "title": "Evidence Staleness — Provenance Chains Across RDF and Git",
        "question": "Can evidence staleness be detected as a SHACL shape, with provenance chains spanning both RDF and Git?",
    },
}


def load_results() -> dict[int, dict]:
    results = {}
    for exp_id in EXPERIMENT_IDS:
        path = EXPERIMENTS_DIR / f"experiment-{exp_id}" / "output" / "results.json"
        if path.exists():
            results[exp_id] = json.loads(path.read_text())
    return results


def generate_report(results: dict[int, dict]) -> str:
    """Generate the full synthesis report."""
    sections = []

    # ── Header ─────────────────────────────────────────────────
    sections.append(f"""# RDF + Git Mixed Model — Experiment Synthesis Report

*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*

## Executive Summary

These five experiments test the thesis that **RDF and Git are complementary tools** for modeling complex composable engineering systems. RDF excels at the spatial dimension — how things relate, compose, and satisfy constraints. Git excels at the temporal dimension — how things evolve, who changed what, and when.

Using a refactored satellite model (ADCS + Power subsystems, adapted from [BlockScience/ADCS-lifecycle-demo](https://github.com/BlockScience/ADCS-lifecycle-demo)), the experiments demonstrate that:

1. **Git misses 33% of semantic conflicts** when teams modify different files that are coupled through shared constraints (Exp 14)
2. **Ontology composition conflicts** are invisible to both Git and per-package validation — only composed SHACL catches them (Exp 15)
3. **Lifecycle gate compliance is not monotonic** — a late structural change can break an earlier gate on an attested branch (Exp 16)
4. **A four-way conflict classification** (benign, coupling, ordering, textual) requires both Git and SHACL signals to distinguish (Exp 17)
5. **Evidence staleness** is a joint temporal-spatial property that spans both RDF provenance and Git commit history (Exp 18)

The mixed model is not about choosing between RDF and Git — it is about using each where it is strongest and composing their signals for richer conflict detection than either provides alone.
""")

    # ── Per-Experiment Findings ────────────────────────────────
    sections.append("## Per-Experiment Findings\n")

    for exp_id in EXPERIMENT_IDS:
        meta = EXPERIMENT_META[exp_id]
        sections.append(f"### Experiment {exp_id}: {meta['title']}\n")
        sections.append(f"**Question:** {meta['question']}\n")

        if exp_id not in results:
            sections.append("*Results not available — experiment has not been run.*\n")
            continue

        r = results[exp_id]
        sections.append(f"**Verdict:** {r['verdict']}\n")

        if exp_id == 14:
            cm = r["findings"]["confusion_matrix"]
            sections.append(f"""
|                | Sem. Valid | Sem. Invalid |
|----------------|:---------:|:------------:|
| **Git clean**   | {cm['true_negative']} (TN) | {cm['false_negative']} (FN) |
| **Git conflict**| {cm['false_positive']} (FP) | {cm['true_positive']} (TP) |

False negative rate: **{cm['false_negative_rate']:.0%}** — Git misses semantic conflicts spanning different files.
""")

        elif exp_id == 15:
            det = r["findings"]["detection_summary"]
            sections.append("\n| Scenario | Git | Per-package | Composed | Gate |")
            sections.append("|----------|:---:|:----------:|:--------:|:----:|")
            for name, d in det.items():
                def yn(v):
                    if v is None: return "—"
                    return "YES" if v else "no"
                sections.append(f"| {name} | {yn(d['git'])} | {yn(d['per_package_shacl'])} | {yn(d['composed_shacl'])} | {yn(d['composition_gate'])} |")
            sections.append("")

        elif exp_id == 16:
            f = r["findings"]
            sections.append("\n| Branch | Structural | Evidence | Attestation |")
            sections.append("|--------|:----------:|:--------:|:-----------:|")
            for branch, gates in f["stage_compliance"].items():
                sg = "PASS" if gates["structural"] else "FAIL"
                eg = "PASS" if gates["evidence"] else "FAIL"
                ag = "PASS" if gates["attestation"] else "FAIL"
                sections.append(f"| {branch} | {sg} | {eg} | {ag} |")
            if f["merged_compliance"]:
                mc = f["merged_compliance"]
                sg = "PASS" if mc["structural"] else "**FAIL**"
                eg = "PASS" if mc["evidence"] else "FAIL"
                ag = "PASS" if mc["attestation"] else "FAIL"
                sections.append(f"| merged | {sg} | {eg} | {ag} |")
            sections.append(f"\nRegression detected: **{f['regression_detected']}**\n")

        elif exp_id == 17:
            ct = r["findings"]["classification_table"]
            sections.append("\n| Scenario | Git | SHACL(a→b) | SHACL(b→a) | Class |")
            sections.append("|----------|:---:|:----------:|:----------:|-------|")
            for name, d in ct.items():
                def fmt(v):
                    if v is None: return "N/A"
                    return "pass" if v else "FAIL"
                gc = "CONFLICT" if d["git_conflict"] else "clean"
                sections.append(f"| {name} | {gc} | {fmt(d['sem_valid_uv'])} | {fmt(d['sem_valid_vu'])} | {d['class']} |")
            sections.append(f"\nClasses found: **{', '.join(r['findings']['classes_found'])}**\n")

        elif exp_id == 18:
            f = r["findings"]
            pre = f["pre_change_freshness"]
            post = f["post_change_freshness"]
            sections.append(f"""
| State | Stale Evidence | Stale Attestations |
|-------|:--------------:|:------------------:|
| Before model change | {pre['stale_evidence_count']} | {pre['stale_attestation_count']} |
| **After model change** | **{post['stale_evidence_count']}** | **{post['stale_attestation_count']}** |

Model hash changed: `{f['model_hash_v1'][:12]}...` → `{f['model_hash_v2'][:12]}...`
""")

    # ── Cross-Experiment Synthesis ─────────────────────────────
    sections.append("""## Cross-Experiment Synthesis

### The Four-Way Conflict Classification

Experiment 17 formalized a four-way taxonomy. Each earlier experiment demonstrated specific classes:

| Class | Signal Pattern | Demonstrated By |
|-------|---------------|-----------------|
| Benign Divergence | Git clean, both orderings valid | Exp 14 (scenario 1), Exp 17 (scenario 1) |
| Coupling Conflict | Git clean, both orderings invalid | Exp 14 (scenario 2), Exp 15 (scenarios 2-3), Exp 16 (merge regression), Exp 17 (scenario 2) |
| Ordering Artifact | Git conflict, orderings disagree | Exp 17 (scenario 3) — sequential application only |
| Textual Conflict | Git conflict, SHACL N/A | Exp 14 (scenarios 3-4), Exp 17 (scenario 4) |

**Coupling conflicts are the most dangerous class.** They are invisible to Git, symmetric in their SHACL signal, and only caught by domain-specific constraints (power budget, lifecycle gates, composition checks, evidence freshness).

### The Three-Layer Architecture Extended

Experiment 12 (from the original series) identified three layers: Storage, Schema, Verification. Experiments 14-18 extend this:

| Layer | Original (Exp 12) | Extended (Exp 14-18) |
|-------|-------------------|----------------------|
| Storage | Flexo quadstore (accepts any valid RDF) | Git (accepts any valid text files) |
| Schema | OWL ontology packages | RTM ontology + SysMLv2 vocabulary |
| Verification | SHACL shapes + SPARQL oracles | SHACL shapes + SPARQL oracles + Git merge signal + content hashing |

The key extension: **Git's merge signal is a verification input**, not just a storage mechanism. Whether Git reports a conflict or a clean merge is informative — but it is only one of several signals needed for full conflict detection.

### Evidence Freshness as Composed Gate

Experiments 16 and 18 produce shapes that compose naturally:

| Shape | Question | Layer |
|-------|----------|-------|
| StructuralCompleteShape | Has the requirement been allocated? | Lifecycle |
| EvidenceCompleteShape | Has evidence been produced? | Lifecycle |
| AttestationCompleteShape | Has a human attested? | Lifecycle |
| EvidenceFreshnessShape | Is the evidence still valid? | Freshness |
| AttestationFreshnessShape | Is the attestation citing current evidence? | Freshness |

Running all five shapes against a merged state checks both lifecycle completeness AND temporal validity — something no single tool (Git or SHACL alone) can do.
""")

    # ── Design Principles ──────────────────────────────────────
    sections.append("""## Design Principles Validated and Refined

### Validated

1. **RDF is primarily spatial; Git is primarily temporal.** This heuristic held across all five experiments. RDF/SHACL detected constraint violations in the merged state (spatial). Git tracked who made what change when (temporal). Neither substituted for the other.

2. **Multi-file model decomposition by team ownership is realistic and reveals coupling.** Splitting the satellite model by subsystem team (ADCS, Power, Systems Engineering) is how real engineering organizations work. It also exposes exactly the coupling conflicts that matter most — cross-team budget violations, interface mismatches, lifecycle regressions.

3. **Declarative constraints (SHACL) compose better than imperative checks.** The ADCS demo's `check_gate()` is Python code. The lifecycle gate shapes from Experiment 16 compose with the freshness shapes from Experiment 18. Composability is a property of the declarative representation, not the constraint content.

### Refined

1. **Git's commutativity is a feature, not a limitation.** Git's 3-way merge is commutative for non-overlapping changes — both merge directions produce the same state. This eliminates ordering artifacts that exist in sequential commit application (Flexo's SPARQL UPDATE). Whether this is desirable depends on context: commutativity reduces false positives but also eliminates a signal (non-commutativity) that can indicate structural coupling.

2. **The "composition gate" (static cross-package check) is less powerful than composed SHACL validation.** Experiment 15's composition gate query didn't fire because the renamed property was embedded in SPARQL strings inside SHACL constraints — invisible to static analysis. Running the composed SHACL shapes against instance data is more reliable because it tests actual behavior, not declared structure.

3. **Evidence staleness is conservative by design.** All 6 evidence artifacts became stale from a single parameter change (Experiment 18). This is correct: any structural change could invalidate any proof's assumptions. A more granular approach (per-requirement model dependency tracking) would reduce false staleness but requires explicit dependency declarations that the current model doesn't have.
""")

    # ── Comparison with Experiments 1-13 ───────────────────────
    sections.append("""## Comparison with Experiments 1-13

| Aspect | Experiments 1-13 (Flexo) | Experiments 14-18 (Git + RDF) |
|--------|--------------------------|-------------------------------|
| VCS | Flexo MMS (RDF-native) | Git (text-oriented) |
| Conflict detection | Server-side SPARQL + client-side pyshacl | Client-side SHACL + SPARQL + Git merge signal |
| Commit format | SPARQL UPDATE patches | File-level text diffs |
| Ordering sensitivity | Non-commutative (DELETE then INSERT ≠ INSERT then DELETE) | Commutative for non-overlapping files; non-commutative only for sequential application |
| Model domain | MTG Knowledge Complex (simplicial complex) | Satellite ADCS + Power (SysMLv2 engineering model) |
| Key finding (shared) | Conflicts are model-semantic, not API-dependent | Same: conflicts are model-semantic, not VCS-dependent |
| Key finding (new) | Three-layer architecture (storage, schema, verification) | Git's merge signal is an additional verification input; evidence freshness as joint temporal-spatial property |
""")

    # ── Open Questions ─────────────────────────────────────────
    sections.append("""## Open Questions

1. **Granular staleness tracking.** Can per-requirement model dependencies reduce false staleness without requiring explicit dependency declarations? Could SHACL path expressions or SPARQL property chains infer which requirements are affected by a specific structural change?

2. **Automated conflict resolution.** Experiments 14-18 detect conflicts but don't resolve them. The constrained optimization formalism from the original research (Lagrange duality, shadow prices) could be applied to the Git + RDF setting — but the merge operation would need to produce RDF-aware diffs, not text diffs.

3. **CI/CD integration.** The lifecycle gate shapes (Experiment 16) and freshness shapes (Experiment 18) are natural CI gate checks. How should they be wired into a Git-based CI pipeline? Should they run pre-merge (blocking) or post-merge (advisory)?

4. **Scaling to larger models.** The satellite model has ~500 triples across 6 files. Real SysMLv2 models can have millions of triples across hundreds of files. How does the multi-file decomposition strategy scale? Does SHACL validation become a bottleneck?

5. **Canonical serialization.** Experiment 14 showed that Turtle serialization nondeterminism causes Git false positives. Should engineering models enforce canonical serialization (sorted N-Triples, deterministic Turtle)? What are the tooling implications?
""")

    return "\n".join(sections)


def main():
    results = load_results()
    print(f"Loaded results from {len(results)} experiments")

    report = generate_report(results)
    REPORT_PATH.write_text(report)
    print(f"Report written to: {REPORT_PATH}")
    print(f"Report length: {len(report)} characters, {report.count(chr(10))} lines")


if __name__ == "__main__":
    main()
