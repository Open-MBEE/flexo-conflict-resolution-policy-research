#!/usr/bin/env python3
"""Experiment 20 — The Attestation Gap: Human Judgment Under Model Evolution

Key question: After programmatic reverification restores evidence freshness
(Experiment 19), what is the irreducible human role? What can attestation
shapes detect, and what decisions must remain with engineers?

This experiment picks up where Experiment 19 leaves off:
  - Evidence is fresh (bound to model v2)
  - Attestations are stale or absent (they cite evidence from v1,
    or they don't exist because they were never re-issued)

The experiment walks through three attestation scenarios:
  1. Re-attestation with unchanged conclusion — engineer reviews fresh
     evidence, confirms same judgment. Attestation freshness restored.
  2. Re-attestation with changed judgment — engineer reviews evidence
     for the changed proof (REQ-002 margin doubled) and issues a
     revised statement. Shows that even when proofs pass, the human
     judgment may need updating.
  3. Declined re-attestation — engineer reviews but declines to attest
     because the model change raises questions about assumptions not
     captured in the proof. Shows the irreducible human role: the
     pipeline says "proof passes" but the engineer says "I need to
     think about this more."

Core principle from the ADCS demo: "Evidence does not verify
requirements; evidence supports a human judgment that requirements
are satisfied."
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from rdflib import Graph, Namespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.git_utils import init_repo, commit_file, commit_files, get_git_log
from lib.rdf_utils import hash_graph, save_graph
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

STRUCTURAL_FILES = [
    "structural/satellite.ttl",
    "structural/adcs.ttl",
    "structural/power.ttl",
]
REQUIREMENT_FILES = [
    "requirements/satellite.ttl",
    "requirements/adcs.ttl",
    "requirements/power.ttl",
]
ONTOLOGY_FILES = [
    "ontology/rtm.ttl",
    "ontology/lifecycle-shapes.ttl",
    "ontology/freshness-shapes.ttl",
]


def load_files(file_list: list[str]) -> dict[str, str]:
    return {f: (SCRIPT_DIR / f).read_text() for f in file_list}


def load_graph_from_repo(repo_path: Path, file_list: list[str]) -> Graph:
    g = Graph()
    for ns, uri in BINDINGS.items():
        g.bind(ns, uri)
    for f in file_list:
        p = repo_path / f
        if p.exists():
            g.parse(str(p), format="turtle")
    return g


def compute_structural_hash(repo_path: Path) -> str:
    g = load_graph_from_repo(repo_path, STRUCTURAL_FILES + REQUIREMENT_FILES)
    return hash_graph(g)


def check_shapes(repo_path: Path, label: str, data_files: list[str],
                 shape_files: list[str]) -> dict:
    data_g = load_graph_from_repo(repo_path, data_files)
    ont_g = load_graph_from_repo(repo_path, ["ontology/rtm.ttl"])
    shapes_g = load_graph_from_repo(repo_path, shape_files)
    result = run_shacl(data_g, shapes_g, ont_graph=ont_g)

    report_path = OUTPUT_DIR / "shacl" / f"{label}-report.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(result.report_text)

    violations_by_gate = {"structural": [], "evidence": [], "attestation": [],
                          "stale_evidence": [], "stale_attestation": []}
    for v in result.violations:
        msg = v.message
        if "STRUCTURAL GATE" in msg:
            violations_by_gate["structural"].append(v.to_dict())
        elif "EVIDENCE GATE" in msg:
            violations_by_gate["evidence"].append(v.to_dict())
        elif "ATTESTATION GATE" in msg:
            violations_by_gate["attestation"].append(v.to_dict())
        elif "STALE EVIDENCE" in msg:
            violations_by_gate["stale_evidence"].append(v.to_dict())
        elif "STALE ATTESTATION" in msg:
            violations_by_gate["stale_attestation"].append(v.to_dict())

    return {
        "label": label,
        "conforms": result.conforms,
        "violation_count": result.violation_count,
        "by_gate": violations_by_gate,
    }


def format_gate_summary(result: dict) -> str:
    parts = []
    for gate in ["structural", "evidence", "attestation", "stale_evidence", "stale_attestation"]:
        count = len(result["by_gate"][gate])
        if count > 0:
            parts.append(f"{gate}:{count}")
    if not parts:
        return "ALL PASS"
    return " | ".join(parts)


# ── Evidence generation (fresh, from Exp 19) ───────────────────

def generate_fresh_evidence(model_hash: str, git_sha: str) -> str:
    """Fresh evidence bound to model v2 (output of reverification pipeline)."""
    now = datetime.now(timezone.utc).isoformat()
    return f"""@prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
@prefix prov:    <http://www.w3.org/ns/prov#> .
@prefix rtm:     <http://example.org/ontology/rtm#> .
@prefix adcs:    <http://example.org/adcs-demo/> .
@prefix pwr:     <http://example.org/adcs-demo/power/> .

rtm: rtm:currentModelHash "{model_hash}" .

adcs:SymPyEngine a rtm:ComputationEngine ;
    prov:label "SymPy symbolic engine" .

rtm:FormalProof a rtm:EvidenceMethod ; rdfs:label "Formal Proof" .
rtm:Analysis a rtm:EvidenceMethod ; rdfs:label "Analysis" .

adcs:EV-PROOF-REQ-001 a rtm:ProofArtifact ;
    rtm:addresses adcs:REQ-001 ;
    rtm:modelHash "{model_hash}" ;
    rtm:gitCommit "{git_sha}" ;
    rtm:evidenceMethod rtm:FormalProof ;
    rtm:resultSummary "Steady-state pointing error bounded by 2*tau_gg/Kp" ;
    prov:wasGeneratedBy adcs:SA-REQ-001 ;
    prov:generatedAtTime "{now}"^^xsd:dateTime .

adcs:SA-REQ-001 a rtm:SymbolicAnalysis ;
    prov:wasAssociatedWith adcs:SymPyEngine .

adcs:EV-PROOF-REQ-002 a rtm:ProofArtifact ;
    rtm:addresses adcs:REQ-002 ;
    rtm:modelHash "{model_hash}" ;
    rtm:gitCommit "{git_sha}" ;
    rtm:evidenceMethod rtm:FormalProof ;
    rtm:resultSummary "Peak momentum bounded below 4.0 N.m.s (margin increased: capacity now 8.0)" ;
    prov:wasGeneratedBy adcs:SA-REQ-002 ;
    prov:generatedAtTime "{now}"^^xsd:dateTime .

adcs:SA-REQ-002 a rtm:SymbolicAnalysis ;
    prov:wasAssociatedWith adcs:SymPyEngine .

adcs:EV-PROOF-REQ-003 a rtm:ProofArtifact ;
    rtm:addresses adcs:REQ-003 ;
    rtm:modelHash "{model_hash}" ;
    rtm:gitCommit "{git_sha}" ;
    rtm:evidenceMethod rtm:FormalProof ;
    rtm:resultSummary "Routh-Hurwitz: all eigenvalues Re < -0.010 rad/s" ;
    prov:wasGeneratedBy adcs:SA-REQ-003 ;
    prov:generatedAtTime "{now}"^^xsd:dateTime .

adcs:SA-REQ-003 a rtm:SymbolicAnalysis ;
    prov:wasAssociatedWith adcs:SymPyEngine .

adcs:EV-PROOF-REQ-004 a rtm:ProofArtifact ;
    rtm:addresses adcs:REQ-004 ;
    rtm:modelHash "{model_hash}" ;
    rtm:gitCommit "{git_sha}" ;
    rtm:evidenceMethod rtm:FormalProof ;
    rtm:resultSummary "Gravity gradient torques micro-Nm, below actuator capacity" ;
    prov:wasGeneratedBy adcs:SA-REQ-004 ;
    prov:generatedAtTime "{now}"^^xsd:dateTime .

adcs:SA-REQ-004 a rtm:SymbolicAnalysis ;
    prov:wasAssociatedWith adcs:SymPyEngine .

pwr:EV-ANALYSIS-REQ-P01 a rtm:ProofArtifact ;
    rtm:addresses pwr:REQ-P01 ;
    rtm:modelHash "{model_hash}" ;
    rtm:gitCommit "{git_sha}" ;
    rtm:evidenceMethod rtm:Analysis ;
    rtm:resultSummary "306W available > 300W budget" ;
    prov:wasGeneratedBy pwr:PA-REQ-P01 ;
    prov:generatedAtTime "{now}"^^xsd:dateTime .

pwr:PA-REQ-P01 a rtm:SymbolicAnalysis ;
    prov:wasAssociatedWith adcs:SymPyEngine .

pwr:EV-ANALYSIS-REQ-P02 a rtm:ProofArtifact ;
    rtm:addresses pwr:REQ-P02 ;
    rtm:modelHash "{model_hash}" ;
    rtm:gitCommit "{git_sha}" ;
    rtm:evidenceMethod rtm:Analysis ;
    rtm:resultSummary "672Wh > 282Wh eclipse need" ;
    prov:wasGeneratedBy pwr:PA-REQ-P02 ;
    prov:generatedAtTime "{now}"^^xsd:dateTime .

pwr:PA-REQ-P02 a rtm:SymbolicAnalysis ;
    prov:wasAssociatedWith adcs:SymPyEngine .
"""


# ── Attestation generation ──────────────────────────────────────

def generate_attestations_partial(model_hash: str, git_sha: str) -> str:
    """Generate attestations for the re-attestation scenarios.

    - REQ-003: re-attested with same conclusion (stability unaffected)
    - REQ-002: re-attested with revised statement (margin doubled)
    - REQ-004: re-attested (disturbance unaffected by momentum change)
    - REQ-P01, REQ-P02: re-attested (power unaffected)
    - REQ-001: DECLINED — engineer flags that larger wheels may change
      thermal/vibration characteristics not captured in the pointing proof
    """
    now = datetime.now(timezone.utc).isoformat()
    return f"""@prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
@prefix prov:    <http://www.w3.org/ns/prov#> .
@prefix rtm:     <http://example.org/ontology/rtm#> .
@prefix adcs:    <http://example.org/adcs-demo/> .
@prefix pwr:     <http://example.org/adcs-demo/power/> .

adcs:engineer-mz a rtm:Engineer ;
    rdfs:label "Dr. Michael Zargham" .

# --- REQ-002: re-attested with REVISED statement ---
# The proof passes with increased margin (capacity doubled) but the
# engineer updates their adequacy statement to reflect the change.

adcs:ATT-REQ-002-v2 a rtm:Attestation ;
    rtm:attests adcs:REQ-002 ;
    rtm:hasEvidence adcs:EV-PROOF-REQ-002 ;
    rtm:modelAdequacy "Energy-based momentum bound remains conservative. Wheel capacity doubled to 8.0 N.m.s — margin is now 2x. Model adequate." ;
    rtm:evidenceSufficiency "Proof confirms peak momentum well below both the 4.0 N.m.s requirement and the new 8.0 N.m.s hardware capacity." ;
    rtm:gitCommit "{git_sha}" ;
    prov:wasAssociatedWith adcs:engineer-mz ;
    prov:generatedAtTime "{now}"^^xsd:dateTime .

# --- REQ-003: re-attested, conclusion unchanged ---

adcs:ATT-REQ-003-v2 a rtm:Attestation ;
    rtm:attests adcs:REQ-003 ;
    rtm:hasEvidence adcs:EV-PROOF-REQ-003 ;
    rtm:modelAdequacy "Linearized stability analysis unaffected by momentum capacity change. Model adequate." ;
    rtm:evidenceSufficiency "Routh-Hurwitz criterion still satisfied for all positive J, Kp, Kd." ;
    rtm:gitCommit "{git_sha}" ;
    prov:wasAssociatedWith adcs:engineer-mz ;
    prov:generatedAtTime "{now}"^^xsd:dateTime .

# --- REQ-004: re-attested, conclusion unchanged ---

adcs:ATT-REQ-004-v2 a rtm:Attestation ;
    rtm:attests adcs:REQ-004 ;
    rtm:hasEvidence adcs:EV-PROOF-REQ-004 ;
    rtm:modelAdequacy "Disturbance rejection depends on torque capacity, not momentum capacity. Model adequate." ;
    rtm:evidenceSufficiency "Gravity gradient torques remain micro-Nm. Unchanged." ;
    rtm:gitCommit "{git_sha}" ;
    prov:wasAssociatedWith adcs:engineer-mz ;
    prov:generatedAtTime "{now}"^^xsd:dateTime .

# --- Power requirements: re-attested, unchanged ---

pwr:ATT-REQ-P01-v2 a rtm:Attestation ;
    rtm:attests pwr:REQ-P01 ;
    rtm:hasEvidence pwr:EV-ANALYSIS-REQ-P01 ;
    rtm:modelAdequacy "Power budget unaffected by wheel momentum change." ;
    rtm:evidenceSufficiency "306W available still exceeds 300W budget." ;
    rtm:gitCommit "{git_sha}" ;
    prov:wasAssociatedWith adcs:engineer-mz ;
    prov:generatedAtTime "{now}"^^xsd:dateTime .

pwr:ATT-REQ-P02-v2 a rtm:Attestation ;
    rtm:attests pwr:REQ-P02 ;
    rtm:hasEvidence pwr:EV-ANALYSIS-REQ-P02 ;
    rtm:modelAdequacy "Eclipse analysis unaffected by wheel momentum change." ;
    rtm:evidenceSufficiency "Battery capacity unchanged." ;
    rtm:gitCommit "{git_sha}" ;
    prov:wasAssociatedWith adcs:engineer-mz ;
    prov:generatedAtTime "{now}"^^xsd:dateTime .

# --- REQ-001: DECLINED ---
# The engineer notes that larger wheels may have different vibration
# characteristics that could affect star tracker accuracy. The
# pointing proof doesn't model vibration coupling. The proof PASSES
# but the engineer's judgment is that the model is no longer adequate
# for this requirement without additional analysis.
#
# NO attestation triple is generated for REQ-001.
# This is the attestation gap: the pipeline says "pass" but the
# human says "not yet."
"""


# ── Main ────────────────────────────────────────────────────────

def main():
    logger = ExperimentLogger(
        20,
        "The Attestation Gap — Human Judgment Under Model Evolution",
        output_dir=OUTPUT_DIR,
    )
    logger.set_parameters({
        "starting_state": "Experiment 19 output (fresh evidence, no attestations)",
        "attestation_scenarios": [
            "REQ-002: re-attested with revised statement (margin doubled)",
            "REQ-003, REQ-004, REQ-P01, REQ-P02: re-attested unchanged",
            "REQ-001: DECLINED — engineer flags vibration coupling concern",
        ],
    })
    logger.begin()

    with logger.step("load_data", "Load model files") as s:
        structural_files = load_files(STRUCTURAL_FILES)
        requirement_files = load_files(REQUIREMENT_FILES)
        ontology_files = load_files(ONTOLOGY_FILES)
        s.log(f"Loaded {len(structural_files) + len(requirement_files) + len(ontology_files)} files")

    repo_path = OUTPUT_DIR / "repos" / "attestation-gap"
    if repo_path.exists():
        shutil.rmtree(repo_path)
    repo = init_repo(repo_path)

    all_files = {**structural_files, **requirement_files, **ontology_files}

    # ── Set up: model v2 with fresh evidence (Exp 19 output) ──
    with logger.step("setup", "Set up: model v2 + fresh evidence (Exp 19 state)") as s:
        # Commit model v2 (with upgraded wheels)
        adcs_v2 = structural_files["structural/adcs.ttl"].replace(
            'sysml:value "4.0"^^xsd:double ;\n    sysml:unit "N.m.s" .',
            'sysml:value "8.0"^^xsd:double ;\n    sysml:unit "N.m.s" .',
        )
        all_files_v2 = {**all_files, "structural/adcs.ttl": adcs_v2}
        commit_files(repo, all_files_v2, "MODEL v2: wheel momentum 8.0 N.m.s")
        v2_sha = repo.head.commit.hexsha
        model_hash_v2 = compute_structural_hash(repo_path)

        # Add fresh evidence
        evidence_ttl = generate_fresh_evidence(model_hash_v2, v2_sha)
        commit_file(repo, "evidence/proofs.ttl", evidence_ttl,
                    "EVIDENCE: fresh proofs bound to model v2 (from reverification pipeline)")
        s.log(f"  Model v2 hash: {model_hash_v2[:16]}...")
        s.log(f"  Fresh evidence: 6 artifacts bound to v2")

    # ── Check state: evidence fresh, no attestations ───────────
    with logger.step("pre_attestation", "Check state before attestation") as s:
        data_files = STRUCTURAL_FILES + REQUIREMENT_FILES + ["evidence/proofs.ttl"]
        all_shapes = ["ontology/lifecycle-shapes.ttl", "ontology/freshness-shapes.ttl"]

        pre = check_shapes(repo_path, "pre-attestation", data_files, all_shapes)
        s.log(f"  Gates: {format_gate_summary(pre)}")
        s.log(f"  Evidence fresh: {len(pre['by_gate']['stale_evidence']) == 0}")
        s.log(f"  Attestation gap: {len(pre['by_gate']['attestation'])} requirements unattested")
        for v in pre["by_gate"]["attestation"]:
            s.log(f"    {v['focus_node']}")

    # ── Engineer reviews and attests (partially) ───────────────
    with logger.step("attestation", "Engineer reviews evidence and attests") as s:
        s.log("")
        s.log("  Engineer reviews each requirement against fresh evidence:")
        s.log("")
        s.log("  REQ-001 (pointing): DECLINED")
        s.log("    Proof passes, but larger wheels may have different vibration")
        s.log("    characteristics affecting star tracker accuracy. The pointing")
        s.log("    proof does not model vibration coupling. Engineer requests")
        s.log("    additional analysis before attesting.")
        s.log("")
        s.log("  REQ-002 (momentum): RE-ATTESTED with revised statement")
        s.log("    Proof passes with doubled margin (capacity 4.0 -> 8.0 N.m.s).")
        s.log("    Engineer updates adequacy statement to reflect new margin.")
        s.log("")
        s.log("  REQ-003 (stability): RE-ATTESTED, unchanged conclusion")
        s.log("  REQ-004 (disturbance): RE-ATTESTED, unchanged conclusion")
        s.log("  REQ-P01 (power budget): RE-ATTESTED, unchanged conclusion")
        s.log("  REQ-P02 (eclipse): RE-ATTESTED, unchanged conclusion")

        att_sha = repo.head.commit.hexsha
        attestation_ttl = generate_attestations_partial(model_hash_v2, att_sha)
        commit_file(repo, "evidence/attestations.ttl", attestation_ttl,
                    "ATTESTATION: 5 of 6 requirements attested; REQ-001 declined")

    # ── Check state after partial attestation ──────────────────
    with logger.step("post_attestation", "Check state after partial attestation") as s:
        data_files_full = (STRUCTURAL_FILES + REQUIREMENT_FILES +
                           ["evidence/proofs.ttl", "evidence/attestations.ttl"])

        post = check_shapes(repo_path, "post-attestation", data_files_full, all_shapes)
        s.log(f"  Gates: {format_gate_summary(post)}")
        s.log(f"  Evidence fresh: {len(post['by_gate']['stale_evidence']) == 0}")
        s.log(f"  Attestation gap: {len(post['by_gate']['attestation'])} requirements still unattested")
        for v in post["by_gate"]["attestation"]:
            s.log(f"    {v['focus_node']}")

    # ── The attestation gap analysis ───────────────────────────
    with logger.step("analysis", "The attestation gap") as s:
        s.log("")
        s.log("  ATTESTATION GAP ANALYSIS")
        s.log("  ════════════════════════")
        s.log("")
        s.log("  After programmatic reverification (Exp 19) + human review (this exp):")
        s.log("")
        s.log("  ┌──────────────┬─────────┬──────────┬─────────────┐")
        s.log("  │ Requirement  │ Evidence│ Attested │ Status      │")
        s.log("  ├──────────────┼─────────┼──────────┼─────────────┤")

        req_status = [
            ("REQ-001", "fresh", "DECLINED", "GAP — needs vibration analysis"),
            ("REQ-002", "fresh", "revised", "CLOSED — margin noted"),
            ("REQ-003", "fresh", "confirmed", "CLOSED"),
            ("REQ-004", "fresh", "confirmed", "CLOSED"),
            ("REQ-P01", "fresh", "confirmed", "CLOSED"),
            ("REQ-P02", "fresh", "confirmed", "CLOSED"),
        ]

        for req, ev, att, status in req_status:
            s.log(f"  │ {req:<12s} │ {ev:<7s} │ {att:<8s}  │ {status:<11s} │")
        s.log("  └──────────────┴─────────┴──────────┴─────────────┘")

        s.log("")
        s.log("  The pipeline automated 100% of evidence regeneration.")
        s.log("  The engineer attested 5 of 6 requirements (83%).")
        s.log("  1 requirement (REQ-001) has an attestation gap:")
        s.log("    - The PROOF passes (pointing error bounded by 2*tau_gg/Kp)")
        s.log("    - But the MODEL may be inadequate (vibration not modeled)")
        s.log("    - This is the distinction the ADCS demo makes:")
        s.log('      "Evidence does not verify requirements; evidence supports')
        s.log('       a human judgment that requirements are satisfied."')
        s.log("")
        s.log("  The attestation gap is detectable by SHACL (AttestationCompleteShape")
        s.log("  fires on REQ-001) but CANNOT be resolved by automation.")
        s.log("  It requires either:")
        s.log("    a) Additional analysis (vibration coupling model)")
        s.log("    b) Engineering judgment that vibration is negligible")
        s.log("    c) Hardware testing to validate the assumption")

    (OUTPUT_DIR / "git-log.txt").write_text(get_git_log(repo))

    unattested = len(post["by_gate"]["attestation"])
    evidence_fresh = len(post["by_gate"]["stale_evidence"]) == 0

    logger.set_findings({
        "model_hash_v2": model_hash_v2,
        "evidence_fresh": evidence_fresh,
        "total_requirements": 6,
        "attested": 5,
        "declined": 1,
        "declined_requirements": ["REQ-001"],
        "decline_reason": "Model adequacy concern: larger wheels may change vibration characteristics not captured in pointing proof",
        "pre_attestation_gates": {g: len(v) for g, v in pre["by_gate"].items()},
        "post_attestation_gates": {g: len(v) for g, v in post["by_gate"].items()},
        "attestation_gap": {
            "requirement": "REQ-001",
            "evidence_status": "fresh (proof passes)",
            "attestation_status": "declined",
            "reason": "model inadequacy — vibration coupling not modeled",
            "resolution_options": [
                "additional analysis (vibration coupling model)",
                "engineering judgment (vibration negligible)",
                "hardware testing (validate assumption)",
            ],
        },
    })

    if unattested > 0 and evidence_fresh:
        verdict = (f"CONFIRMED — attestation gap: {unattested} requirement(s) have fresh evidence "
                   f"but no attestation. Human judgment is irreducible.")
    else:
        verdict = "NOT CONFIRMED"

    logger.end(verdict)


if __name__ == "__main__":
    main()
