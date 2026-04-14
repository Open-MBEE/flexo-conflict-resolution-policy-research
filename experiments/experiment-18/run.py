#!/usr/bin/env python3
"""Experiment 18 — Evidence Staleness: Provenance Chains Across RDF and Git

Key question: When evidence is hash-bound to a model version and the
model subsequently evolves, can staleness detection be encoded as a
SHACL shape — and can provenance chains span both RDF and Git?

The ADCS-lifecycle-demo binds evidence to model versions via
rtm:modelHash and rtm:gitCommit. But it runs as a single pipeline —
it never tests what happens when the model evolves AFTER evidence
is bound. This experiment introduces model evolution and tests:

  1. Can a SHACL shape detect that evidence is bound to an outdated model?
  2. Can a SPARQL query trace from stale attestation → evidence → model version?
  3. Can Git history identify WHAT changed and WHEN?

The provenance chain spans both:
  - RDF: rtm:modelHash, rtm:addresses, rtm:attests, prov:wasGeneratedBy
  - Git: commit SHAs, diffs, timestamps
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, XSD
from rdflib.namespace import PROV, OWL

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.git_utils import (
    init_repo, commit_file, commit_files, create_branch,
    checkout, get_git_log, get_diff,
)
from lib.rdf_utils import hash_graph, save_graph
from lib.shacl_runner import run_shacl
from lib.experiment_logger import ExperimentLogger

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
ORACLE_DIR = SCRIPT_DIR / "oracle"

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
    """Compute deterministic hash of the structural model only."""
    g = load_graph_from_repo(repo_path, STRUCTURAL_FILES + REQUIREMENT_FILES)
    return hash_graph(g)


# ── Evidence generation ─────────────────────────────────────────

def generate_evidence_ttl(model_hash: str, git_sha: str) -> str:
    """Generate evidence triples bound to a specific model version.

    Produces evidence for all 6 subsystem requirements (ADCS REQ-001..004,
    Power REQ-P01..P02) with model hash and git commit binding.
    """
    now = datetime.now(timezone.utc).isoformat()
    return f"""@prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
@prefix prov:    <http://www.w3.org/ns/prov#> .
@prefix rtm:     <http://example.org/ontology/rtm#> .
@prefix adcs:    <http://example.org/adcs-demo/> .
@prefix pwr:     <http://example.org/adcs-demo/power/> .

# Model version binding
rtm: rtm:currentModelHash "{model_hash}" .

# Computation agents
adcs:SymPyEngine a rtm:ComputationEngine ;
    prov:label "SymPy symbolic engine" .

# Evidence method individuals
rtm:FormalProof a rtm:EvidenceMethod ;
    rdfs:label "Formal Proof" .

rtm:Analysis a rtm:EvidenceMethod ;
    rdfs:label "Analysis" .

# --- ADCS evidence ---

adcs:EV-PROOF-REQ-001 a rtm:ProofArtifact ;
    rtm:addresses adcs:REQ-001 ;
    rtm:modelHash "{model_hash}" ;
    rtm:gitCommit "{git_sha}" ;
    rtm:evidenceMethod rtm:FormalProof ;
    rtm:resultSummary "Steady-state pointing error bounded by 2*tau_gg/Kp" ;
    rtm:sourceFile "analysis/build_proofs.py" ;
    prov:wasGeneratedBy adcs:SA-REQ-001 ;
    prov:generatedAtTime "{now}"^^xsd:dateTime .

adcs:SA-REQ-001 a rtm:SymbolicAnalysis ;
    prov:wasAssociatedWith adcs:SymPyEngine .

adcs:EV-PROOF-REQ-002 a rtm:ProofArtifact ;
    rtm:addresses adcs:REQ-002 ;
    rtm:modelHash "{model_hash}" ;
    rtm:gitCommit "{git_sha}" ;
    rtm:evidenceMethod rtm:FormalProof ;
    rtm:resultSummary "Peak momentum bounded below 4.0 N.m.s" ;
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

# --- Power evidence ---

pwr:EV-ANALYSIS-REQ-P01 a rtm:ProofArtifact ;
    rtm:addresses pwr:REQ-P01 ;
    rtm:modelHash "{model_hash}" ;
    rtm:gitCommit "{git_sha}" ;
    rtm:evidenceMethod rtm:Analysis ;
    rtm:resultSummary "Power budget: 306W available > 300W budget" ;
    prov:wasGeneratedBy pwr:PA-REQ-P01 ;
    prov:generatedAtTime "{now}"^^xsd:dateTime .

pwr:PA-REQ-P01 a rtm:SymbolicAnalysis ;
    prov:wasAssociatedWith adcs:SymPyEngine .

pwr:EV-ANALYSIS-REQ-P02 a rtm:ProofArtifact ;
    rtm:addresses pwr:REQ-P02 ;
    rtm:modelHash "{model_hash}" ;
    rtm:gitCommit "{git_sha}" ;
    rtm:evidenceMethod rtm:Analysis ;
    rtm:resultSummary "Battery 672Wh > 282Wh eclipse need" ;
    prov:wasGeneratedBy pwr:PA-REQ-P02 ;
    prov:generatedAtTime "{now}"^^xsd:dateTime .

pwr:PA-REQ-P02 a rtm:SymbolicAnalysis ;
    prov:wasAssociatedWith adcs:SymPyEngine .
"""


def generate_attestation_ttl(git_sha: str) -> str:
    """Generate attestation triples."""
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

adcs:ATT-REQ-002 a rtm:Attestation ;
    rtm:attests adcs:REQ-002 ;
    rtm:hasEvidence adcs:EV-PROOF-REQ-002 ;
    rtm:modelAdequacy "Energy-based momentum bound is conservative." ;
    rtm:evidenceSufficiency "Peak momentum confirmed below 4.0 N.m.s." ;
    rtm:gitCommit "{git_sha}" ;
    prov:wasAssociatedWith adcs:engineer-mz ;
    prov:generatedAtTime "{now}"^^xsd:dateTime .

adcs:ATT-REQ-003 a rtm:Attestation ;
    rtm:attests adcs:REQ-003 ;
    rtm:hasEvidence adcs:EV-PROOF-REQ-003 ;
    rtm:modelAdequacy "Linearized stability analysis adequate for small angles." ;
    rtm:evidenceSufficiency "All eigenvalues satisfy stability criterion." ;
    rtm:gitCommit "{git_sha}" ;
    prov:wasAssociatedWith adcs:engineer-mz ;
    prov:generatedAtTime "{now}"^^xsd:dateTime .

pwr:ATT-REQ-P01 a rtm:Attestation ;
    rtm:attests pwr:REQ-P01 ;
    rtm:hasEvidence pwr:EV-ANALYSIS-REQ-P01 ;
    rtm:modelAdequacy "Power budget analysis with BOL panel output." ;
    rtm:evidenceSufficiency "306W available exceeds 300W budget." ;
    rtm:gitCommit "{git_sha}" ;
    prov:wasAssociatedWith adcs:engineer-mz ;
    prov:generatedAtTime "{now}"^^xsd:dateTime .
"""


# ── Validation ──────────────────────────────────────────────────

def check_freshness(repo_path: Path, label: str,
                    data_files: list[str]) -> dict:
    """Run freshness SHACL shapes against data."""
    data_g = load_graph_from_repo(repo_path, data_files)
    ont_g = load_graph_from_repo(repo_path, ["ontology/rtm.ttl"])
    shapes_g = load_graph_from_repo(repo_path, ["ontology/freshness-shapes.ttl"])

    result = run_shacl(data_g, shapes_g, ont_graph=ont_g)

    report_path = OUTPUT_DIR / "shacl" / f"{label}-report.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(result.report_text)

    stale_evidence = []
    stale_attestations = []
    for v in result.violations:
        if "STALE EVIDENCE" in v.message:
            stale_evidence.append(v.to_dict())
        elif "STALE ATTESTATION" in v.message:
            stale_attestations.append(v.to_dict())

    return {
        "label": label,
        "conforms": result.conforms,
        "stale_evidence_count": len(stale_evidence),
        "stale_attestation_count": len(stale_attestations),
        "stale_evidence": stale_evidence,
        "stale_attestations": stale_attestations,
    }


def run_staleness_query(repo_path: Path, data_files: list[str]) -> list[dict]:
    """Run the staleness report SPARQL query."""
    g = load_graph_from_repo(repo_path, data_files)
    # Also load ontology for class inference
    for f in ["ontology/rtm.ttl"]:
        p = repo_path / f
        if p.exists():
            g.parse(str(p), format="turtle")

    query_text = (ORACLE_DIR / "staleness-report.rq").read_text()
    try:
        results = g.query(query_text)
        return [
            {str(v): str(r[v]) for v in results.vars if r[v] is not None}
            for r in results
        ]
    except Exception as e:
        return [{"error": str(e)}]


# ── Main ────────────────────────────────────────────────────────

def main():
    logger = ExperimentLogger(
        18,
        "Evidence Staleness — Provenance Chains Across RDF and Git",
        output_dir=OUTPUT_DIR,
    )
    logger.set_parameters({
        "model_evolution": "change reaction wheel max momentum from 4.0 to 8.0 N.m.s",
        "evidence_binding": "SHA-256 hash of structural model at evidence generation time",
        "freshness_check": "SHACL shape comparing rtm:modelHash to rtm:currentModelHash",
    })
    logger.begin()

    # Load source files
    with logger.step("load_data", "Load model files") as s:
        structural_files = load_files(STRUCTURAL_FILES)
        requirement_files = load_files(REQUIREMENT_FILES)
        ontology_files = load_files(ONTOLOGY_FILES)
        s.log(f"Loaded structural ({len(structural_files)}), "
              f"requirements ({len(requirement_files)}), "
              f"ontology ({len(ontology_files)}) files")

    # Set up the lifecycle repo
    repo_path = OUTPUT_DIR / "repos" / "lifecycle"
    if repo_path.exists():
        shutil.rmtree(repo_path)
    repo = init_repo(repo_path)

    all_files = {**structural_files, **requirement_files, **ontology_files}

    # ── Stage 1: Commit structural model ───────────────────────
    with logger.step("stage_structural", "Stage 1: Commit structural model") as s:
        commit_files(repo, all_files, "STRUCTURAL: model and requirements defined")
        structural_sha = repo.head.commit.hexsha

        model_hash_v1 = compute_structural_hash(repo_path)
        s.log(f"  Commit: {structural_sha[:8]}")
        s.log(f"  Model hash v1: {model_hash_v1[:16]}...")
        s.detail("commit", structural_sha)
        s.detail("model_hash", model_hash_v1)

    save_graph(
        load_graph_from_repo(repo_path, STRUCTURAL_FILES + REQUIREMENT_FILES),
        OUTPUT_DIR / "graphs" / "structural-v1.ttl",
    )

    # ── Stage 2: Bind evidence to model v1 ─────────────────────
    with logger.step("stage_evidence", "Stage 2: Bind evidence to model v1") as s:
        evidence_ttl = generate_evidence_ttl(model_hash_v1, structural_sha)
        commit_file(repo, "evidence/proofs.ttl", evidence_ttl,
                     "EVIDENCE: proofs bound to structural model v1")
        evidence_sha = repo.head.commit.hexsha
        s.log(f"  Evidence commit: {evidence_sha[:8]}")
        s.log(f"  All evidence bound to modelHash: {model_hash_v1[:16]}...")
        s.log(f"  All evidence records gitCommit: {structural_sha[:8]}")
        s.detail("commit", evidence_sha)

    # ── Stage 3: Add attestations ──────────────────────────────
    with logger.step("stage_attestation", "Stage 3: Add attestations") as s:
        attestation_ttl = generate_attestation_ttl(evidence_sha)
        commit_file(repo, "evidence/attestations.ttl", attestation_ttl,
                     "ATTESTATION: human review of evidence")
        attestation_sha = repo.head.commit.hexsha
        s.log(f"  Attestation commit: {attestation_sha[:8]}")
        s.detail("commit", attestation_sha)

    # ── Check freshness (should PASS) ──────────────────────────
    with logger.step("freshness_pre", "Check freshness before model change") as s:
        data_files = (STRUCTURAL_FILES + REQUIREMENT_FILES +
                      ["evidence/proofs.ttl", "evidence/attestations.ttl"])
        pre_result = check_freshness(repo_path, "pre-change", data_files)
        s.log(f"  Freshness: {'PASS' if pre_result['conforms'] else 'FAIL'}")
        s.log(f"  Stale evidence: {pre_result['stale_evidence_count']}")
        s.log(f"  Stale attestations: {pre_result['stale_attestation_count']}")
        s.detail("conforms", pre_result["conforms"])

    # ── Stage 4: Evolve the structural model ───────────────────
    with logger.step("model_evolution", "Stage 4: Evolve structural model (design update)") as s:
        s.log("  Change: upgrade reaction wheel max momentum 4.0 -> 8.0 N.m.s")
        s.log("  This invalidates evidence that was bound to the original model.")

        # Modify adcs.ttl
        adcs_ttl = (repo_path / "structural" / "adcs.ttl").read_text()
        adcs_ttl_v2 = adcs_ttl.replace(
            'sysml:value "4.0"^^xsd:double ;\n    sysml:unit "N.m.s" .',
            'sysml:value "8.0"^^xsd:double ;\n    sysml:unit "N.m.s" .',
        )
        commit_file(repo, "structural/adcs.ttl", adcs_ttl_v2,
                     "DESIGN UPDATE: upgrade wheel momentum capacity 4.0 -> 8.0 N.m.s")
        design_sha = repo.head.commit.hexsha

        model_hash_v2 = compute_structural_hash(repo_path)
        s.log(f"  Design commit: {design_sha[:8]}")
        s.log(f"  Model hash v2: {model_hash_v2[:16]}...")
        s.log(f"  Hash changed: {model_hash_v1[:16]} -> {model_hash_v2[:16]}")
        s.detail("commit", design_sha)
        s.detail("model_hash_v2", model_hash_v2)
        s.detail("hash_changed", model_hash_v1 != model_hash_v2)

        # Update currentModelHash in evidence/proofs.ttl
        # (In a real system, this would be updated automatically by the pipeline)
        proofs_ttl = (repo_path / "evidence" / "proofs.ttl").read_text()
        proofs_ttl_updated = proofs_ttl.replace(
            f'rtm:currentModelHash "{model_hash_v1}"',
            f'rtm:currentModelHash "{model_hash_v2}"',
        )
        commit_file(repo, "evidence/proofs.ttl", proofs_ttl_updated,
                     "UPDATE: currentModelHash to reflect structural change")

    save_graph(
        load_graph_from_repo(repo_path, STRUCTURAL_FILES + REQUIREMENT_FILES),
        OUTPUT_DIR / "graphs" / "structural-v2.ttl",
    )

    # ── Check freshness (should FAIL) ──────────────────────────
    with logger.step("freshness_post", "Check freshness after model change") as s:
        post_result = check_freshness(repo_path, "post-change", data_files)
        s.log(f"  Freshness: {'PASS' if post_result['conforms'] else 'FAIL'}")
        s.log(f"  Stale evidence: {post_result['stale_evidence_count']}")
        s.log(f"  Stale attestations: {post_result['stale_attestation_count']}")

        if not post_result["conforms"]:
            s.log("")
            s.log("  Stale evidence artifacts:")
            for v in post_result["stale_evidence"]:
                s.log(f"    {v['focus_node']}")
            s.log("")
            s.log("  Stale attestations:")
            for v in post_result["stale_attestations"]:
                s.log(f"    {v['focus_node']}")

        s.detail("conforms", post_result["conforms"])
        s.detail("stale_evidence", post_result["stale_evidence"])
        s.detail("stale_attestations", post_result["stale_attestations"])

    # ── Staleness provenance query ─────────────────────────────
    with logger.step("staleness_query", "Run staleness provenance query") as s:
        staleness = run_staleness_query(repo_path, data_files)
        s.log(f"  Stale attestation-evidence pairs: {len(staleness)}")
        for row in staleness:
            req = row.get("reqName", "?")
            ev_hash = row.get("evidenceHash", "?")[:12]
            cur_hash = row.get("currentHash", "?")[:12]
            engineer = row.get("engineer", "?")
            s.log(f"    {req}: evidence hash {ev_hash}... != current {cur_hash}... (attested by {engineer})")
        s.detail("staleness_report", staleness)

    # ── Git provenance (temporal dimension) ────────────────────
    with logger.step("git_provenance", "Git provenance — what changed between evidence and design update") as s:
        diff_text = get_diff(repo, evidence_sha, design_sha)
        diff_lines = [l for l in diff_text.split("\n") if l.startswith("+") or l.startswith("-")]
        diff_lines = [l for l in diff_lines if not l.startswith("+++") and not l.startswith("---")]

        s.log(f"  Evidence bound at commit: {evidence_sha[:8]}")
        s.log(f"  Model changed at commit: {design_sha[:8]}")
        s.log(f"  Diff ({len(diff_lines)} changed lines):")
        for line in diff_lines[:10]:
            s.log(f"    {line}")

        s.detail("evidence_commit", evidence_sha)
        s.detail("design_commit", design_sha)
        s.detail("diff_line_count", len(diff_lines))

    # ── Combined report ────────────────────────────────────────
    with logger.step("combined_report", "Combined temporal-spatial staleness report") as s:
        s.log("")
        s.log("  PROVENANCE CHAIN (RDF spatial + Git temporal):")
        s.log("  =============================================")
        s.log("")
        for row in staleness:
            req = row.get("reqName", "?")
            att = row.get("attestation", "?").split("/")[-1]
            ev = row.get("evidence", "?").split("/")[-1]
            ev_hash = row.get("evidenceHash", "?")[:12]
            cur_hash = row.get("currentHash", "?")[:12]
            engineer = row.get("engineer", "?")
            att_time = row.get("attestTime", "?")

            s.log(f"  Requirement: {req}")
            s.log(f"    Attestation: {att}")
            s.log(f"      Attested by: {engineer}")
            s.log(f"      Attested at: {att_time}")
            s.log(f"    Evidence: {ev}")
            s.log(f"      Bound to model: {ev_hash}... (v1)")
            s.log(f"      Current model:  {cur_hash}... (v2)")
            s.log(f"    Git history:")
            s.log(f"      Evidence created: commit {evidence_sha[:8]}")
            s.log(f"      Model changed:   commit {design_sha[:8]}")
            s.log(f"      Change: wheel maxMomentum 4.0 -> 8.0 N.m.s")
            s.log("")

        s.log("  The RDF provenance chain identifies WHICH requirements")
        s.log("  are affected and WHO attested them. The Git history")
        s.log("  identifies WHAT changed and WHEN. Neither alone tells")
        s.log("  the full story.")

    # Save git log
    (OUTPUT_DIR / "git-log.txt").write_text(get_git_log(repo))

    logger.set_findings({
        "model_hash_v1": model_hash_v1,
        "model_hash_v2": model_hash_v2,
        "pre_change_freshness": pre_result,
        "post_change_freshness": post_result,
        "staleness_report": staleness,
        "evidence_commit": evidence_sha,
        "design_commit": design_sha,
    })

    stale = not post_result["conforms"]
    if stale and pre_result["conforms"]:
        verdict = "CONFIRMED — evidence staleness detected after model evolution"
    elif not pre_result["conforms"]:
        verdict = "ERROR — evidence was already stale before model change"
    else:
        verdict = "NOT CONFIRMED — no staleness detected"

    logger.end(verdict)


if __name__ == "__main__":
    main()
