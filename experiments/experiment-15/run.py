#!/usr/bin/env python3
"""Experiment 15 — Ontology Package Versioning: Composition Conflicts

Key question: When composable ontology packages evolve independently on
separate Git branches, can their composition produce semantic conflicts
that neither Git nor per-package validation detects alone?

The satellite model uses two ontology/schema packages:
  ontology/rtm.ttl     — RTM vocabulary (classes, properties)
  ontology/shapes.ttl   — SHACL validation shapes

Instance data references both packages. When a team renames a property
across the vocabulary + instance files, another team's new shapes may
reference the old name. Git sees no conflict (different files). Each
branch validates in isolation. Only the composed result fails.

Three scenarios:
  1. Benign — orthogonal additions to vocabulary and shapes
  2. Property rename — rtm:derivedFrom → rtm:tracesTo across vocabulary
     and instance data; shapes team adds constraint using old name
  3. New constraint + new data — shapes team adds power-draw validation;
     ADCS team adds a component without declaring its power draw
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
from lib.rdf_utils import load_graph, save_graph
from lib.shacl_runner import run_shacl, load_shapes
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
    "ontology/shapes.ttl",
]
ALL_FILES = STRUCTURAL_FILES + REQUIREMENT_FILES + ONTOLOGY_FILES


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


# ── Mutations ───────────────────────────────────────────────────

# Scenario 1: Benign

def mutate_rtm_add_class(rtm_ttl: str) -> str:
    """V&V team adds new evidence subclass (orthogonal)."""
    return rtm_ttl.rstrip() + """

# --- Added by V&V methodology team ---
rtm:TestResult a owl:Class ;
    rdfs:subClassOf rtm:Evidence ;
    rdfs:label "Test Result" ;
    rdfs:comment "Physical test evidence (hardware-in-the-loop, thermal vacuum)." .
"""


def mutate_shapes_add_name_check(shapes_ttl: str) -> str:
    """Quality team requires every PartUsage to have a name (orthogonal)."""
    return shapes_ttl.rstrip() + """

shapes:PartUsageNameShape a sh:NodeShape ;
    rdfs:label "PartUsageNameShape" ;
    sh:targetClass sysml:PartUsage ;
    sh:property [
        sh:path sysml:declaredName ;
        sh:minCount 1 ;
        sh:message "PartUsage is missing a declaredName."
    ] .
"""


# Scenario 2: Property rename

def mutate_rtm_rename_derivedFrom(rtm_ttl: str) -> str:
    """RTM team renames rtm:derivedFrom → rtm:tracesTo in vocabulary."""
    return rtm_ttl.replace("rtm:derivedFrom", "rtm:tracesTo").replace(
        '"derived from"', '"traces to"'
    )


def mutate_reqs_rename_derivedFrom(reqs_ttl: str) -> str:
    """RTM team also renames rtm:derivedFrom → rtm:tracesTo in instance data.

    This is realistic: a team renames consistently across all files they own.
    """
    return reqs_ttl.replace("rtm:derivedFrom", "rtm:tracesTo")


def mutate_shapes_add_derivation_check(shapes_ttl: str) -> str:
    """Traceability team adds a shape requiring valid rtm:derivedFrom chains.

    Uses the OLD property name — they wrote this against the ancestor.
    """
    return shapes_ttl.rstrip() + """

shapes:DerivationChainShape a sh:NodeShape ;
    rdfs:label "DerivationChainShape" ;
    rdfs:comment "Every subsystem requirement must trace to a valid parent." ;
    sh:targetClass sysml:RequirementDefinition ;
    sh:sparql [
        a sh:SPARQLConstraint ;
        sh:message "Requirement uses rtm:derivedFrom but the target is not a RequirementDefinition." ;
        sh:select \"\"\"
            PREFIX sysml: <https://www.omg.org/spec/SysML/2.0/>
            PREFIX rtm:   <http://example.org/ontology/rtm#>
            SELECT $this WHERE {
                $this rtm:derivedFrom ?parent .
                FILTER NOT EXISTS {
                    ?parent a sysml:RequirementDefinition .
                }
            }
        \"\"\"
    ] ;
    sh:sparql [
        a sh:SPARQLConstraint ;
        sh:message "Subsystem requirement is missing rtm:derivedFrom traceability link." ;
        sh:select \"\"\"
            PREFIX sysml: <https://www.omg.org/spec/SysML/2.0/>
            PREFIX rtm:   <http://example.org/ontology/rtm#>
            PREFIX sat:   <http://example.org/adcs-demo/satellite/>
            SELECT $this WHERE {
                $this a sysml:RequirementDefinition ;
                      sysml:declaredName ?name .
                FILTER(!STRSTARTS(?name, "SAT-"))
                FILTER NOT EXISTS {
                    $this rtm:derivedFrom ?parent .
                }
            }
        \"\"\"
    ] .
"""


# Scenario 3: New constraint + new data

def mutate_shapes_add_unit_check(shapes_ttl: str) -> str:
    """Standards team adds a shape requiring every AttributeUsage to have a unit."""
    return shapes_ttl.rstrip() + """

shapes:AttributeUnitShape a sh:NodeShape ;
    rdfs:label "AttributeUnitShape" ;
    rdfs:comment "Every AttributeUsage must declare its unit." ;
    sh:targetClass sysml:AttributeUsage ;
    sh:property [
        sh:path sysml:unit ;
        sh:minCount 1 ;
        sh:message "AttributeUsage is missing sysml:unit declaration."
    ] .
"""


def mutate_adcs_add_component(adcs_ttl: str) -> str:
    """ADCS team adds a second star tracker (redundancy upgrade).

    The new component has attributes but one attribute is missing
    its unit declaration — a realistic oversight on a new addition.
    """
    # Add new component to ownedPart list
    result = adcs_ttl.replace(
        "adcs:PDController ;",
        "adcs:PDController ;\n"
        "    sysml:ownedPart adcs:StarTracker_2 ;",
    )
    # Add component definition at the end
    result = result.rstrip() + """

# --- Added by ADCS team: redundant star tracker ---

adcs:StarTracker_2 a sysml:PartUsage ;
    sysml:declaredName "StarTracker_2" ;
    sysml:type adcs:StarTrackerDef ;
    rdfs:comment "Redundant star tracker for fault tolerance." .

adcs:attr_st2_fov a sysml:AttributeUsage ;
    sysml:declaredName "st2FieldOfView" ;
    rdfs:comment "Star tracker 2 field of view." ;
    sysml:value "12.0"^^xsd:double .
"""
    return result


# ── Validation ──────────────────────────────────────────────────

def validate_shacl(repo_path: Path, label: str,
                   instance_files: list[str] | None = None) -> dict:
    """Run SHACL validation and return structured results."""
    if instance_files is None:
        instance_files = STRUCTURAL_FILES + REQUIREMENT_FILES

    instance_g = load_graph_from_repo(repo_path, instance_files)
    ont_g = load_graph_from_repo(repo_path, ["ontology/rtm.ttl"])
    shapes_g = load_graph_from_repo(repo_path, ["ontology/shapes.ttl"])

    result = run_shacl(instance_g, shapes_g, ont_graph=ont_g)

    report_path = OUTPUT_DIR / "shacl" / f"{label}-report.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(result.report_text)

    return {
        "label": label,
        "conforms": result.conforms,
        "violation_count": result.violation_count,
        "violations": [v.to_dict() for v in result.violations],
    }


def run_composition_gate(repo_path: Path) -> list[dict]:
    """Run composition gate SPARQL query."""
    full_graph = load_graph_from_repo(repo_path, ALL_FILES)
    query_text = (ORACLE_DIR / "composition-gate.rq").read_text()
    try:
        results = full_graph.query(query_text)
        return [
            {str(var): str(row[var]) for var in results.vars if row[var] is not None}
            for row in results
        ]
    except Exception as e:
        return [{"error": str(e)}]


# ── Scenario runner ─────────────────────────────────────────────

def run_scenario(
    logger: ExperimentLogger,
    name: str,
    model_files: dict[str, str],
    branch_a_name: str,
    branch_a_mutations: dict[str, object],
    branch_b_name: str,
    branch_b_mutations: dict[str, object],
) -> dict:
    repo_path = OUTPUT_DIR / "repos" / name
    if repo_path.exists():
        shutil.rmtree(repo_path)

    repo = init_repo(repo_path)
    ancestor_sha = commit_files(repo, model_files, "ancestor: satellite model")

    # Branch A
    create_branch(repo, branch_a_name)
    for filepath, mutator in branch_a_mutations.items():
        original = model_files[filepath]
        commit_file(repo, filepath, mutator(original), f"{branch_a_name}: {filepath}")

    # Validate Branch A in isolation
    branch_a_val = validate_shacl(repo_path, f"{name}-branch-a")
    logger.log(f"  Branch A ({branch_a_name}): "
               f"{'PASS' if branch_a_val['conforms'] else 'FAIL'} "
               f"({branch_a_val['violation_count']} violations)")

    # Branch B
    checkout(repo, "main")
    create_branch(repo, branch_b_name)
    for filepath, mutator in branch_b_mutations.items():
        original = model_files[filepath]
        commit_file(repo, filepath, mutator(original), f"{branch_b_name}: {filepath}")

    branch_b_val = validate_shacl(repo_path, f"{name}-branch-b")
    logger.log(f"  Branch B ({branch_b_name}): "
               f"{'PASS' if branch_b_val['conforms'] else 'FAIL'} "
               f"({branch_b_val['violation_count']} violations)")

    # Merge
    checkout(repo, "main")
    create_branch(repo, "merge-result", branch_a_name)
    merge = attempt_merge(repo, branch_b_name)

    result = {
        "scenario": name,
        "branch_a": branch_a_name,
        "branch_b": branch_b_name,
        "branch_a_validation": branch_a_val,
        "branch_b_validation": branch_b_val,
        "git_conflict": merge.has_conflict,
        "conflict_files": merge.conflict_files,
    }

    if merge.has_conflict:
        logger.log(f"  Git CONFLICT: {merge.conflict_files}")
        abort_merge(repo)
        result["composed_validation"] = None
        result["composition_gate"] = None
    else:
        logger.log(f"  Git merge: clean")

        composed_val = validate_shacl(repo_path, f"{name}-composed")
        logger.log(f"  Composed SHACL: "
                   f"{'PASS' if composed_val['conforms'] else 'FAIL'} "
                   f"({composed_val['violation_count']} violations)")
        if not composed_val["conforms"]:
            for v in composed_val["violations"][:5]:
                logger.log(f"    {v['shape']}: {v['message']}")

        gate = run_composition_gate(repo_path)
        if gate:
            logger.log(f"  Composition gate: {len(gate)} issue(s)")
            for r in gate[:3]:
                logger.log(f"    {r}")
        else:
            logger.log(f"  Composition gate: PASS")

        result["composed_validation"] = composed_val
        result["composition_gate"] = gate

        merged_graph = load_graph_from_repo(repo_path, ALL_FILES)
        save_graph(merged_graph, OUTPUT_DIR / "graphs" / f"{name}-merged.ttl")

    # Classify
    git_det = merge.has_conflict
    pkg_det = not branch_a_val["conforms"] or not branch_b_val["conforms"]
    if result["composed_validation"]:
        composed_det = not result["composed_validation"]["conforms"]
    else:
        composed_det = None
    gate_det = bool(result.get("composition_gate"))

    result["detection"] = {
        "git": git_det,
        "per_package_shacl": pkg_det,
        "composed_shacl": composed_det,
        "composition_gate": gate_det,
    }

    logger.log(f"  Detection — Git: {'yes' if git_det else 'no'} | "
               f"Per-pkg: {'yes' if pkg_det else 'no'} | "
               f"Composed: {'yes' if composed_det else ('no' if composed_det is not None else 'N/A')} | "
               f"Gate: {'yes' if gate_det else 'no'}")

    (OUTPUT_DIR / f"git-log-{name}.txt").write_text(get_git_log(repo))
    return result


# ── Main ────────────────────────────────────────────────────────

def main():
    logger = ExperimentLogger(
        15,
        "Ontology Package Versioning — Composition Conflicts",
        output_dir=OUTPUT_DIR,
    )
    logger.set_parameters({
        "ontology_packages": ["ontology/rtm.ttl", "ontology/shapes.ttl"],
        "scenarios": [
            "benign: orthogonal additions (new class + new shape)",
            "property-rename: rtm:derivedFrom → rtm:tracesTo in vocab+data; new shape uses old name",
            "new-constraint-new-data: unit-check shape + component missing unit declaration",
        ],
    })
    logger.begin()

    with logger.step("load_data", "Load model files") as s:
        model_files = load_all_files()
        s.log(f"Loaded {len(model_files)} files")

    # Validate ancestor
    with logger.step("validate_ancestor", "Validate ancestor composition") as s:
        repo_path_anc = OUTPUT_DIR / "repos" / "_ancestor"
        if repo_path_anc.exists():
            shutil.rmtree(repo_path_anc)
        repo_anc = init_repo(repo_path_anc)
        commit_files(repo_anc, model_files, "ancestor")
        anc_val = validate_shacl(repo_path_anc, "ancestor")
        s.log(f"Ancestor: {'PASS' if anc_val['conforms'] else 'FAIL'}")

    all_scenarios = []

    # ── Scenario 1: Benign ─────────────────────────────────────
    with logger.step("scenario_benign", "Scenario 1: Benign — orthogonal changes") as s:
        s.log("Branch A: add rtm:TestResult class to rtm.ttl")
        s.log("Branch B: add PartUsageNameShape to shapes.ttl")
        result = run_scenario(
            logger, "benign", model_files,
            "rtm-add-class",
            {"ontology/rtm.ttl": mutate_rtm_add_class},
            "shapes-add-name-check",
            {"ontology/shapes.ttl": mutate_shapes_add_name_check},
        )
        all_scenarios.append(result)

    # ── Scenario 2: Property rename ────────────────────────────
    with logger.step("scenario_rename", "Scenario 2: Property rename — derivedFrom → tracesTo") as s:
        s.log("Branch A: rename rtm:derivedFrom → rtm:tracesTo in rtm.ttl + requirements/*.ttl")
        s.log("Branch B: add DerivationChainShape using rtm:derivedFrom in shapes.ttl")
        s.log("Git clean (different files). Each branch valid. Composed: shape fires on all subsystem reqs.")
        result = run_scenario(
            logger, "property-rename", model_files,
            "rtm-rename-property",
            {
                "ontology/rtm.ttl": mutate_rtm_rename_derivedFrom,
                "requirements/adcs.ttl": mutate_reqs_rename_derivedFrom,
                "requirements/power.ttl": mutate_reqs_rename_derivedFrom,
            },
            "shapes-derivation-check",
            {"ontology/shapes.ttl": mutate_shapes_add_derivation_check},
        )
        all_scenarios.append(result)

    # ── Scenario 3: New constraint + new data ──────────────────
    with logger.step("scenario_constraint_data", "Scenario 3: New constraint meets new data") as s:
        s.log("Branch A: add AttributeUnitShape (every attribute must have a unit) to shapes.ttl")
        s.log("Branch B: add StarTracker_2 with attr missing unit to adcs.ttl")
        s.log("Git clean. Each valid alone (shape doesn't see new attr; attr doesn't know about shape).")
        result = run_scenario(
            logger, "constraint-data", model_files,
            "shapes-unit-check",
            {"ontology/shapes.ttl": mutate_shapes_add_unit_check},
            "adcs-add-component",
            {"structural/adcs.ttl": mutate_adcs_add_component},
        )
        all_scenarios.append(result)

    # ── Summary ────────────────────────────────────────────────
    with logger.step("classification", "Detection classification") as s:
        s.log("")
        s.log("  Scenario               | Git | Per-pkg | Composed | Gate")
        s.log("  -----------------------|-----|---------|----------|-----")
        for sc in all_scenarios:
            d = sc["detection"]
            def yn(v):
                if v is None: return "N/A"
                return "YES" if v else " no"
            s.log(f"  {sc['scenario']:<23s} | {yn(d['git'])} | {yn(d['per_package_shacl']):>7s} | "
                  f"{yn(d['composed_shacl']):>8s} | {yn(d['composition_gate'])}")
        s.log("")

        composition_only = sum(
            1 for sc in all_scenarios
            if not sc["detection"]["git"]
            and not sc["detection"]["per_package_shacl"]
            and (sc["detection"]["composed_shacl"] or sc["detection"]["composition_gate"])
        )
        s.log(f"  Conflicts detectable ONLY by composition: {composition_only}")
        s.detail("composition_only_count", composition_only)

    logger.set_findings({
        "scenarios": all_scenarios,
        "detection_summary": {sc["scenario"]: sc["detection"] for sc in all_scenarios},
    })

    if composition_only > 0:
        verdict = f"CONFIRMED — {composition_only} composition conflict(s) invisible to Git and per-package SHACL"
    else:
        verdict = "NOT CONFIRMED"

    logger.end(verdict)


if __name__ == "__main__":
    main()
