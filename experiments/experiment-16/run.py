#!/usr/bin/env python3
"""Experiment 16 — Lifecycle Branches: Stage Gates as SHACL Shapes

Key question: When Git branches represent lifecycle stages (structural →
evidence → attestation), can SHACL shapes encode lifecycle gate
prerequisites — and what happens when a late structural change merges
into an attested branch?

The DSG/ADCS-lifecycle-demo enforces gates imperatively in Python
(check_gate()). This experiment makes them declarative SHACL shapes:
  - StructuralCompleteShape: every subsystem req has a satisfy link
  - EvidenceCompleteShape: every subsystem req has evidence addressing it
  - AttestationCompleteShape: every subsystem req has an attestation

Git branches model lifecycle progression:
  main (structural) → evidence → attestation

A second branch 'redesign' from main introduces a structural change
that, when merged into the attested branch, causes lifecycle regression.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from rdflib import Graph, Namespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.git_utils import (
    init_repo, commit_file, commit_files, create_branch,
    checkout, attempt_merge, abort_merge, get_git_log,
)
from lib.rdf_utils import save_graph
from lib.shacl_runner import run_shacl
from lib.experiment_logger import ExperimentLogger

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"

SYSML = Namespace("https://www.omg.org/spec/SysML/2.0/")
RTM   = Namespace("http://example.org/ontology/rtm#")
ADCS  = Namespace("http://example.org/adcs-demo/")
SAT   = Namespace("http://example.org/adcs-demo/satellite/")
PWR   = Namespace("http://example.org/adcs-demo/power/")
BINDINGS = {"sysml": SYSML, "rtm": RTM, "adcs": ADCS, "sat": SAT, "pwr": PWR}

# File groups by lifecycle stage
STRUCTURAL_FILES = [
    "structural/satellite.ttl",
    "structural/adcs.ttl",
    "structural/power.ttl",
    "requirements/satellite.ttl",
    "requirements/adcs.ttl",
    "requirements/power.ttl",
]
EVIDENCE_FILES = [
    "evidence/proofs.ttl",
]
ATTESTATION_FILES = [
    "evidence/attestations.ttl",
]
ONTOLOGY_FILES = [
    "ontology/rtm.ttl",
    "ontology/lifecycle-shapes.ttl",
]
ALL_FILES = STRUCTURAL_FILES + EVIDENCE_FILES + ATTESTATION_FILES + ONTOLOGY_FILES


def load_all_files() -> dict[str, str]:
    files = {}
    for rel_path in ALL_FILES:
        files[rel_path] = (SCRIPT_DIR / rel_path).read_text()
    return files


def load_graph_from_repo(repo_path: Path, file_list: list[str]) -> Graph:
    g = Graph()
    for ns, uri in BINDINGS.items():
        g.bind(ns, uri)
    for rel_path in file_list:
        p = repo_path / rel_path
        if p.exists():
            g.parse(str(p), format="turtle")
    return g


# ── Gate validation ─────────────────────────────────────────────

def check_gates(repo_path: Path, label: str,
                data_files: list[str]) -> dict:
    """Run all three lifecycle gate shapes against the given data files.

    Returns per-gate results and overall compliance.
    """
    data_g = load_graph_from_repo(repo_path, data_files)
    ont_g = load_graph_from_repo(repo_path, ["ontology/rtm.ttl"])
    shapes_g = load_graph_from_repo(repo_path, ["ontology/lifecycle-shapes.ttl"])

    result = run_shacl(data_g, shapes_g, ont_graph=ont_g)

    # Classify violations by gate
    gates = {
        "structural": {"pass": True, "violations": []},
        "evidence": {"pass": True, "violations": []},
        "attestation": {"pass": True, "violations": []},
    }
    for v in result.violations:
        msg = v.message.lower()
        if "structural gate" in msg:
            gates["structural"]["pass"] = False
            gates["structural"]["violations"].append(v.to_dict())
        elif "evidence gate" in msg:
            gates["evidence"]["pass"] = False
            gates["evidence"]["violations"].append(v.to_dict())
        elif "attestation gate" in msg:
            gates["attestation"]["pass"] = False
            gates["attestation"]["violations"].append(v.to_dict())

    # Save report
    report_path = OUTPUT_DIR / "shacl" / f"{label}-report.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(result.report_text)

    return {
        "label": label,
        "gates": gates,
        "total_violations": result.violation_count,
    }


def format_gates(gate_result: dict) -> str:
    """Format gate results as a compact string."""
    parts = []
    for name in ["structural", "evidence", "attestation"]:
        g = gate_result["gates"][name]
        status = "PASS" if g["pass"] else f"FAIL({len(g['violations'])})"
        parts.append(f"{name[0].upper()}:{status}")
    return " | ".join(parts)


# ── Mutations ───────────────────────────────────────────────────

def mutate_remove_star_tracker_satisfy(reqs_adcs_ttl: str) -> str:
    """Redesign: remove StarTracker from REQ-001 satisfy relationship.

    Simulates a late structural change where the pointing requirement's
    allocation is modified — perhaps the team is considering a different
    sensor approach. This breaks the structural gate for REQ-001.
    """
    return reqs_adcs_ttl.replace(
        "sysml:satisfyingElement adcs:PDController , adcs:StarTracker",
        "sysml:satisfyingElement adcs:PDController",
    )


def mutate_remove_req_p01_satisfy(reqs_power_ttl: str) -> str:
    """Redesign: remove satisfy links from REQ-P01 entirely.

    Simulates the power team reconsidering their architecture —
    the solar arrays and PDU are being redesigned, so the satisfy
    relationship is temporarily removed.
    """
    # Remove the ownedRelationship block for REQ-P01
    lines = reqs_power_ttl.split("\n")
    filtered = []
    skip_block = False
    for line in lines:
        if "sysml:ownedRelationship [" in line and not skip_block:
            # Check if this is REQ-P01's block (next few lines)
            # We'll skip until we see the closing ] ;
            skip_block = True
            continue
        if skip_block:
            if "] ;" in line or "] ." in line:
                skip_block = False
                # Replace the closing with just a semicolon to keep syntax valid
                continue
            continue
        filtered.append(line)
    return "\n".join(filtered)


# ── Main ────────────────────────────────────────────────────────

def main():
    logger = ExperimentLogger(
        16,
        "Lifecycle Branches — Stage Gates as SHACL Shapes",
        output_dir=OUTPUT_DIR,
    )
    logger.set_parameters({
        "lifecycle_stages": ["structural", "evidence", "attestation"],
        "gate_shapes": [
            "StructuralCompleteShape: every subsystem req has a satisfy link",
            "EvidenceCompleteShape: every subsystem req has evidence",
            "AttestationCompleteShape: every subsystem req has attestation",
        ],
        "conflict_scenario": "late redesign merged into attested branch",
    })
    logger.begin()

    with logger.step("load_data", "Load model files") as s:
        model_files = load_all_files()
        s.log(f"Loaded {len(model_files)} files across structural, evidence, attestation layers")

    # Create the lifecycle repo
    repo_path = OUTPUT_DIR / "repos" / "lifecycle"
    if repo_path.exists():
        shutil.rmtree(repo_path)
    repo = init_repo(repo_path)

    # ── Stage 1: STRUCTURAL (main branch) ──────────────────────
    with logger.step("stage_structural", "Stage 1: STRUCTURAL — commit model + requirements") as s:
        structural_files = {}
        for f in STRUCTURAL_FILES + ONTOLOGY_FILES:
            structural_files[f] = model_files[f]
        commit_files(repo, structural_files, "stage: STRUCTURAL — model and requirements defined")

        gates = check_gates(repo_path, "structural", STRUCTURAL_FILES)
        s.log(f"  Gates: {format_gates(gates)}")
        s.log(f"  Expected: Structural PASS, Evidence FAIL (no evidence yet), Attestation FAIL")
        s.detail("gates", gates["gates"])

    # ── Stage 2: EVIDENCE (evidence branch) ────────────────────
    with logger.step("stage_evidence", "Stage 2: EVIDENCE — add proof artifacts") as s:
        create_branch(repo, "evidence")
        for f in EVIDENCE_FILES:
            commit_file(repo, f, model_files[f], "stage: EVIDENCE — proof artifacts bound")

        gates = check_gates(repo_path, "evidence", STRUCTURAL_FILES + EVIDENCE_FILES)
        s.log(f"  Gates: {format_gates(gates)}")
        s.log(f"  Expected: Structural PASS, Evidence PASS, Attestation FAIL (no attestations yet)")
        s.detail("gates", gates["gates"])

    # ── Stage 3: ATTESTATION (attestation branch) ──────────────
    with logger.step("stage_attestation", "Stage 3: ATTESTATION — add human attestations") as s:
        create_branch(repo, "attestation")
        for f in ATTESTATION_FILES:
            commit_file(repo, f, model_files[f], "stage: ATTESTATION — human review complete")

        all_data = STRUCTURAL_FILES + EVIDENCE_FILES + ATTESTATION_FILES
        gates = check_gates(repo_path, "attestation", all_data)
        s.log(f"  Gates: {format_gates(gates)}")
        s.log(f"  Expected: All PASS (except REQ-001 has no attestation)")
        s.detail("gates", gates["gates"])
        if not gates["gates"]["attestation"]["pass"]:
            for v in gates["gates"]["attestation"]["violations"]:
                s.log(f"    {v['focus_node']}: {v['message']}")

    attestation_sha = repo.head.commit.hexsha

    # ── Redesign branch (from main) ────────────────────────────
    with logger.step("redesign", "Create redesign branch with structural changes") as s:
        checkout(repo, "main")
        create_branch(repo, "redesign")

        # Mutation 1: remove StarTracker from REQ-001 satisfy
        mutated_adcs_reqs = mutate_remove_star_tracker_satisfy(
            model_files["requirements/adcs.ttl"]
        )
        commit_file(repo, "requirements/adcs.ttl", mutated_adcs_reqs,
                     "redesign: remove StarTracker from REQ-001 allocation (sensor trade study)")

        # Mutation 2: remove REQ-P01 satisfy links
        mutated_power_reqs = mutate_remove_req_p01_satisfy(
            model_files["requirements/power.ttl"]
        )
        commit_file(repo, "requirements/power.ttl", mutated_power_reqs,
                     "redesign: remove REQ-P01 satisfy links (power architecture redesign)")

        s.log("  Applied: remove StarTracker from REQ-001 allocation")
        s.log("  Applied: remove REQ-P01 satisfy links (architecture redesign)")

        # Check gates on redesign branch (structural only)
        gates = check_gates(repo_path, "redesign", STRUCTURAL_FILES)
        s.log(f"  Redesign gates: {format_gates(gates)}")
        s.detail("gates", gates["gates"])

    # ── Merge redesign into attestation ────────────────────────
    with logger.step("merge_regression", "Merge redesign into attestation branch") as s:
        checkout(repo, "attestation")
        merge_result = attempt_merge(repo, "redesign")

        if merge_result.has_conflict:
            s.log(f"  Git CONFLICT: {merge_result.conflict_files}")
            abort_merge(repo)
            s.detail("git_conflict", True)
            merged_gates = None
        else:
            s.log(f"  Git merge: clean (redesign changes don't overlap with evidence/attestation files)")

            all_data = STRUCTURAL_FILES + EVIDENCE_FILES + ATTESTATION_FILES
            merged_gates = check_gates(repo_path, "merged", all_data)
            s.log(f"  Merged gates: {format_gates(merged_gates)}")

            if not merged_gates["gates"]["structural"]["pass"]:
                s.log(f"  LIFECYCLE REGRESSION: structural gate failed on attested branch!")
                for v in merged_gates["gates"]["structural"]["violations"]:
                    s.log(f"    {v['focus_node']}: {v['message']}")

            s.detail("git_conflict", False)
            s.detail("gates", merged_gates["gates"])

            # Save merged graph
            merged_graph = load_graph_from_repo(repo_path, all_data + ONTOLOGY_FILES)
            save_graph(merged_graph, OUTPUT_DIR / "graphs" / "merged.ttl")

    # ── Stage compliance matrix ────────────────────────────────
    with logger.step("compliance_matrix", "Stage-by-branch compliance matrix") as s:
        # Re-check all stages for the matrix display
        # (We already have the results from above, just format them)
        s.log("")
        s.log("  Branch          | Structural | Evidence | Attestation")
        s.log("  ----------------|------------|----------|------------")

        # Reload each branch and check
        branches_data = {
            "main": STRUCTURAL_FILES,
            "evidence": STRUCTURAL_FILES + EVIDENCE_FILES,
            "attestation": STRUCTURAL_FILES + EVIDENCE_FILES + ATTESTATION_FILES,
        }

        matrix_results = {}
        for branch_name, data_files in branches_data.items():
            checkout(repo, branch_name)
            gates = check_gates(repo_path, f"matrix-{branch_name}", data_files)
            matrix_results[branch_name] = gates

            sg = "PASS" if gates["gates"]["structural"]["pass"] else "FAIL"
            eg = "PASS" if gates["gates"]["evidence"]["pass"] else "FAIL"
            ag = "PASS" if gates["gates"]["attestation"]["pass"] else "FAIL"
            s.log(f"  {branch_name:<16s} | {sg:>10s} | {eg:>8s} | {ag}")

        # Show merged state
        if merged_gates:
            checkout(repo, "attestation")  # merged state is on attestation branch
            # Try to get back to the merge result
            # Actually we already have merged_gates from above
            sg = "PASS" if merged_gates["gates"]["structural"]["pass"] else "FAIL"
            eg = "PASS" if merged_gates["gates"]["evidence"]["pass"] else "FAIL"
            ag = "PASS" if merged_gates["gates"]["attestation"]["pass"] else "FAIL"
            s.log(f"  {'merged':16s} | {sg:>10s} | {eg:>8s} | {ag}")
            s.log("")
            s.log(f"  Regression detected: structural gate FAILED on branch that had passed attestation gate")

        s.detail("matrix", {
            name: {g: r["gates"][g]["pass"] for g in ["structural", "evidence", "attestation"]}
            for name, r in matrix_results.items()
        })

    # Save git log
    (OUTPUT_DIR / "git-log.txt").write_text(get_git_log(repo))

    logger.set_findings({
        "stage_compliance": {
            name: {g: r["gates"][g]["pass"] for g in ["structural", "evidence", "attestation"]}
            for name, r in matrix_results.items()
        },
        "merged_compliance": {
            g: merged_gates["gates"][g]["pass"]
            for g in ["structural", "evidence", "attestation"]
        } if merged_gates else None,
        "regression_detected": (
            merged_gates is not None
            and not merged_gates["gates"]["structural"]["pass"]
        ),
    })

    regression = (
        merged_gates is not None
        and not merged_gates["gates"]["structural"]["pass"]
    )
    if regression:
        verdict = "CONFIRMED — lifecycle regression: late structural change broke gate on attested branch"
    else:
        verdict = "NOT CONFIRMED — no regression detected"

    logger.end(verdict)


if __name__ == "__main__":
    main()
