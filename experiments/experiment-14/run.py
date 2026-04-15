#!/usr/bin/env python3
"""Experiment 14 — Git as RDF Conflict Detector: Confusion Matrix

Key question: When RDF graphs are split across team-owned files under Git,
does Git's textual merge produce meaningful conflict signals for semantic
(constraint-violating) conflicts — or does it miss them?

The satellite model is split by team ownership:
  structural/satellite.ttl  — systems engineering (GeoSat, interface params)
  structural/adcs.ttl       — ADCS team (components, power draw)
  structural/power.ttl      — power team (solar arrays, battery, PDU)
  requirements/satellite.ttl — system-level requirements
  requirements/adcs.ttl      — ADCS requirements + satisfy links
  requirements/power.ttl     — power requirements + satisfy links
  ontology/rtm.ttl           — shared RTM ontology
  ontology/shapes.ttl        — SHACL structural constraints

Four scenarios test each cell of the confusion matrix:
  1. True negative  — ADCS tunes gains, Power tunes battery — no coupling
  2. False negative — ADCS increases wheel power, Power reduces panels —
                      different files, Git clean, but power budget violated
  3. True positive  — both teams edit the same ADCS power draw attribute
  4. False positive — same structural content, reordered serialization
"""

from __future__ import annotations

import random
import re
import shutil
import sys
from pathlib import Path

from rdflib import Graph

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.git_utils import (
    init_repo, commit_file, commit_files, create_branch,
    checkout, attempt_merge, abort_merge, get_git_log,
)
from lib.rdf_utils import load_graph, save_graph, hash_graph, STANDARD_BINDINGS
from lib.shacl_runner import run_shacl, load_shapes
from lib.experiment_logger import ExperimentLogger

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
ORACLE_DIR = SCRIPT_DIR / "oracle"

RANDOM_SEED = 42

# All model files, by relative path within the experiment repo
MODEL_FILES = [
    "structural/satellite.ttl",
    "structural/adcs.ttl",
    "structural/power.ttl",
    "requirements/satellite.ttl",
    "requirements/adcs.ttl",
    "requirements/power.ttl",
    "ontology/rtm.ttl",
    "ontology/shapes.ttl",
]

# Namespaces for the ADCS model
from rdflib import Namespace
SYSML = Namespace("https://www.omg.org/spec/SysML/2.0/")
RTM   = Namespace("http://example.org/ontology/rtm#")
ADCS  = Namespace("http://example.org/adcs-demo/")
SAT   = Namespace("http://example.org/adcs-demo/satellite/")
PWR   = Namespace("http://example.org/adcs-demo/power/")

ADCS_BINDINGS = {
    "sysml": SYSML, "rtm": RTM, "adcs": ADCS, "sat": SAT, "pwr": PWR,
}


# ── Model loading ───────────────────────────────────────────────

def load_model_files() -> dict[str, str]:
    """Load all model files as raw text, keyed by relative path."""
    files = {}
    for rel_path in MODEL_FILES:
        src = SCRIPT_DIR / rel_path
        files[rel_path] = src.read_text()
    return files


def load_full_graph_from_repo(repo_path: Path) -> Graph:
    """Load all model .ttl files from a repo working dir into one graph."""
    g = Graph()
    for ns, uri in ADCS_BINDINGS.items():
        g.bind(ns, uri)
    for rel_path in MODEL_FILES:
        p = repo_path / rel_path
        if p.exists():
            g.parse(str(p), format="turtle")
    return g


def load_full_graph_from_source() -> Graph:
    """Load all model files from the experiment source directory."""
    g = Graph()
    for ns, uri in ADCS_BINDINGS.items():
        g.bind(ns, uri)
    for rel_path in MODEL_FILES:
        g.parse(str(SCRIPT_DIR / rel_path), format="turtle")
    return g


def load_ontology_graph() -> Graph:
    """Load the RTM ontology (for SHACL inference)."""
    return load_graph(SCRIPT_DIR / "ontology" / "rtm.ttl")


def load_shapes_graph() -> Graph:
    """Load SHACL shapes."""
    return load_shapes(SCRIPT_DIR / "ontology" / "shapes.ttl")


# ── Mutations ───────────────────────────────────────────────────
# Each mutation is a function: str -> str (file content -> mutated content)

def mutate_adcs_tune_gains(adcs_ttl: str) -> str:
    """ADCS team tunes PD controller gains (no interface impact)."""
    result = adcs_ttl.replace(
        'sysml:value "1.0"^^xsd:double ;\n    sysml:unit "N.m/rad"',
        'sysml:value "1.5"^^xsd:double ;\n    sysml:unit "N.m/rad"',
    )
    result = result.replace(
        'sysml:value "10.0"^^xsd:double ;\n    sysml:unit "N.m.s/rad"',
        'sysml:value "15.0"^^xsd:double ;\n    sysml:unit "N.m.s/rad"',
    )
    return result


def mutate_power_tune_battery(power_ttl: str) -> str:
    """Power team adjusts battery DOD limit (no interface impact)."""
    return power_ttl.replace(
        'sysml:value "0.60"^^xsd:double ;\n    sysml:unit "dimensionless" .',
        'sysml:value "0.70"^^xsd:double ;\n    sysml:unit "dimensionless" .',
    )


def mutate_adcs_upgrade_wheels(adcs_ttl: str) -> str:
    """ADCS team upgrades to larger reaction wheels — higher power draw.

    Increases per-wheel power from 12W to 22W and updates total ADCS draw
    from 50W to 80W (3×22W + 8W + 3W + 3W).
    """
    result = adcs_ttl.replace(
        'sysml:value "12.0"^^xsd:double ;\n    sysml:unit "W" .',
        'sysml:value "22.0"^^xsd:double ;\n    sysml:unit "W" .',
    )
    result = result.replace(
        'sysml:value "50.0"^^xsd:double ;\n    sysml:unit "W" .',
        'sysml:value "80.0"^^xsd:double ;\n    sysml:unit "W" .',
    )
    # Also upgrade torque and momentum (justification for bigger wheels)
    result = result.replace(
        'sysml:value "0.1"^^xsd:double ;\n    sysml:unit "N.m" .',
        'sysml:value "0.2"^^xsd:double ;\n    sysml:unit "N.m" .',
    )
    result = result.replace(
        'sysml:value "4.0"^^xsd:double ;\n    sysml:unit "N.m.s" .',
        'sysml:value "8.0"^^xsd:double ;\n    sysml:unit "N.m.s" .',
    )
    return result


def mutate_power_reduce_panels(power_ttl: str) -> str:
    """Power team reduces solar panel output (cost/mass optimization).

    Reduces per-panel power from 180W to 150W and updates available
    power from 306W to 255W (2×150×0.85).
    """
    result = power_ttl.replace(
        'sysml:value "180.0"^^xsd:double ;\n    sysml:unit "W" .',
        'sysml:value "150.0"^^xsd:double ;\n    sysml:unit "W" .',
    )
    result = result.replace(
        'sysml:value "306.0"^^xsd:double ;\n    sysml:unit "W" .',
        'sysml:value "255.0"^^xsd:double ;\n    sysml:unit "W" .',
    )
    return result


def mutate_adcs_change_power_draw(adcs_ttl: str) -> str:
    """ADCS team updates their total power draw value (for TP scenario)."""
    return adcs_ttl.replace(
        'sysml:value "50.0"^^xsd:double ;\n    sysml:unit "W" .',
        'sysml:value "55.0"^^xsd:double ;\n    sysml:unit "W" .',
    )


def mutate_power_change_adcs_view(adcs_ttl: str) -> str:
    """A different team edits the same ADCS power draw attribute (for TP).

    Simulates a systems engineer correcting what they think is the
    ADCS power draw based on independent analysis.
    """
    return adcs_ttl.replace(
        'sysml:value "50.0"^^xsd:double ;\n    sysml:unit "W" .',
        'sysml:value "48.0"^^xsd:double ;\n    sysml:unit "W" .',
    )


def shuffle_turtle(turtle_text: str, seed: int) -> str:
    """Shuffle non-prefix blocks to simulate serialization nondeterminism."""
    lines = turtle_text.split("\n")
    prefix_lines = []
    body_lines = []
    in_prefixes = True
    for line in lines:
        if in_prefixes and (line.startswith("@prefix") or line.strip() == ""):
            prefix_lines.append(line)
        else:
            in_prefixes = False
            body_lines.append(line)

    blocks: list[list[str]] = []
    current: list[str] = []
    for line in body_lines:
        if line.strip() == "" and current:
            blocks.append(current)
            current = []
        else:
            current.append(line)
    if current:
        blocks.append(current)

    rng = random.Random(seed)
    rng.shuffle(blocks)

    result = prefix_lines + [""]
    for block in blocks:
        result.extend(block)
        result.append("")
    return "\n".join(result)


# ── Validation ──────────────────────────────────────────────────

def run_oracle_queries(data_graph: Graph) -> list[dict]:
    """Run oracle SPARQL queries."""
    informational = {"c3-requirement-allocation"}
    results = []
    for rq_file in sorted(ORACLE_DIR.glob("*.rq")):
        query_text = rq_file.read_text()
        try:
            qresults = data_graph.query(query_text)
            rows = []
            for row in qresults:
                rows.append({
                    str(var): str(row[var])
                    for var in qresults.vars
                    if row[var] is not None
                })
        except Exception as e:
            rows = [{"error": str(e)}]
        results.append({
            "query": rq_file.stem,
            "rows": rows,
            "has_violations": len(rows) > 0 and rq_file.stem not in informational,
        })
    return results


def validate(data_graph: Graph, ont_graph: Graph, shapes_graph: Graph,
             label: str) -> dict:
    """Full SHACL + oracle validation. Returns summary dict."""
    shacl_result = run_shacl(data_graph, shapes_graph, ont_graph=ont_graph)

    report_path = OUTPUT_DIR / "shacl" / f"{label}-report.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(shacl_result.report_text)

    oracle_results = run_oracle_queries(data_graph)
    oracle_violations = [r for r in oracle_results if r["has_violations"]]

    return {
        "label": label,
        "shacl_conforms": shacl_result.conforms,
        "shacl_violation_count": shacl_result.violation_count,
        "shacl_violations": [v.to_dict() for v in shacl_result.violations],
        "oracle_results": oracle_results,
        "oracle_violation_count": len(oracle_violations),
        "semantically_valid": shacl_result.conforms and len(oracle_violations) == 0,
    }


# ── Scenario runner ─────────────────────────────────────────────

def run_scenario(
    logger: ExperimentLogger,
    name: str,
    ont_graph: Graph,
    shapes_graph: Graph,
    model_files: dict[str, str],
    branch_a_name: str,
    branch_a_mutations: dict[str, object],
    branch_b_name: str,
    branch_b_mutations: dict[str, object],
) -> dict:
    """Run a single scenario: create repo, branch, mutate, merge, validate."""
    repo_path = OUTPUT_DIR / "repos" / name
    if repo_path.exists():
        shutil.rmtree(repo_path)

    repo = init_repo(repo_path)

    # Commit ancestor state
    ancestor_sha = commit_files(repo, model_files, "ancestor: satellite model (ADCS + Power)")

    # Branch A
    create_branch(repo, branch_a_name)
    for filepath, mutator in branch_a_mutations.items():
        original = model_files[filepath]
        mutated = mutator(original)
        commit_file(repo, filepath, mutated, f"{branch_a_name}: {filepath}")
    branch_a_sha = repo.head.commit.hexsha

    # Branch B (from main)
    checkout(repo, "main")
    create_branch(repo, branch_b_name)
    for filepath, mutator in branch_b_mutations.items():
        original = model_files[filepath]
        mutated = mutator(original)
        commit_file(repo, filepath, mutated, f"{branch_b_name}: {filepath}")
    branch_b_sha = repo.head.commit.hexsha

    result = {
        "scenario": name,
        "branch_a": branch_a_name,
        "branch_b": branch_b_name,
        "ancestor_sha": ancestor_sha,
        "branch_a_sha": branch_a_sha,
        "branch_b_sha": branch_b_sha,
        "orderings": [],
    }

    for ordering, target_br, source_br in [
        ("a-into-b", branch_b_name, branch_a_name),
        ("b-into-a", branch_a_name, branch_b_name),
    ]:
        checkout(repo, "main")
        merge_br = f"merge-{ordering}"
        create_branch(repo, merge_br, target_br)

        merge_result = attempt_merge(repo, source_br)

        ordering_result = {
            "ordering": ordering,
            "target": target_br,
            "source": source_br,
            "git_conflict": merge_result.has_conflict,
            "conflict_files": merge_result.conflict_files,
        }

        if merge_result.has_conflict:
            ordering_result["validation"] = None
            ordering_result["semantically_valid"] = None
            abort_merge(repo)
            logger.log(f"  [{ordering}] Git CONFLICT on: {merge_result.conflict_files}")
        else:
            merged_graph = load_full_graph_from_repo(repo_path)
            graph_label = f"{name}-{ordering}"
            save_graph(merged_graph, OUTPUT_DIR / "graphs" / f"{graph_label}.ttl")

            val = validate(merged_graph, ont_graph, shapes_graph, graph_label)
            ordering_result["validation"] = val
            ordering_result["semantically_valid"] = val["semantically_valid"]

            shacl_s = "PASS" if val["shacl_conforms"] else "FAIL"
            oracle_detail = ""
            for oq in val["oracle_results"]:
                if oq["has_violations"]:
                    oracle_detail += f" [{oq['query']}: {oq['rows'][0]}]"
            logger.log(
                f"  [{ordering}] Git clean | "
                f"SHACL {shacl_s} ({val['shacl_violation_count']}) | "
                f"Oracle {val['oracle_violation_count']} violations"
                f"{oracle_detail}"
            )

        result["orderings"].append(ordering_result)

    git_log = get_git_log(repo)
    (OUTPUT_DIR / f"git-log-{name}.txt").write_text(git_log)

    return result


# ── Confusion matrix ────────────────────────────────────────────

def build_confusion_matrix(scenarios: list[dict]) -> dict:
    tp = tn = fp = fn = 0
    for scenario in scenarios:
        for o in scenario["orderings"]:
            gc = o["git_conflict"]
            sv = o["semantically_valid"]
            if sv is None:
                if gc:
                    tp += 1
                continue
            if gc and not sv:
                tp += 1
            elif not gc and sv:
                tn += 1
            elif gc and sv:
                fp += 1
            elif not gc and not sv:
                fn += 1

    total = tp + tn + fp + fn
    return {
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "total": total,
        "accuracy": round((tp + tn) / total, 3) if total > 0 else 0,
        "false_negative_rate": round(fn / (fn + tp), 3) if (fn + tp) > 0 else 0,
        "false_positive_rate": round(fp / (fp + tn), 3) if (fp + tn) > 0 else 0,
    }


# ── Main ────────────────────────────────────────────────────────

def main():
    logger = ExperimentLogger(
        14,
        "Git as RDF Conflict Detector — Confusion Matrix",
        output_dir=OUTPUT_DIR,
    )
    logger.set_parameters({
        "model_files": MODEL_FILES,
        "model_domain": "GeoSat (ADCS + Power subsystems)",
        "random_seed": RANDOM_SEED,
        "scenarios": [
            "TN: ADCS tunes gains, Power tunes battery — no coupling",
            "FN: ADCS upgrades wheels (+30W), Power reduces panels (-51W) — budget violated",
            "TP: two teams edit same ADCS power draw attribute — textual conflict",
            "FP: same structural content with reordered serialization",
        ],
    })
    logger.begin()

    # Load shared data
    with logger.step("load_data", "Load model, ontology, and shapes") as s:
        model_files = load_model_files()
        ont_graph = load_ontology_graph()
        shapes_graph = load_shapes_graph()
        ancestor_graph = load_full_graph_from_source()
        s.detail("model_files", MODEL_FILES)
        s.detail("ancestor_triples", len(ancestor_graph))
        s.log(f"Model files: {len(MODEL_FILES)} files")
        s.log(f"Ancestor model: {len(ancestor_graph)} triples")
        s.log(f"Ancestor hash: {hash_graph(ancestor_graph)[:12]}...")

    save_graph(ancestor_graph, OUTPUT_DIR / "graphs" / "ancestor.ttl")

    # Validate ancestor
    with logger.step("validate_ancestor", "Validate ancestor model (baseline)") as s:
        ancestor_val = validate(ancestor_graph, ont_graph, shapes_graph, "ancestor")
        status = "PASS" if ancestor_val["semantically_valid"] else "FAIL"
        s.detail("valid", ancestor_val["semantically_valid"])
        s.detail("shacl_conforms", ancestor_val["shacl_conforms"])
        s.detail("oracle_violations", ancestor_val["oracle_violation_count"])
        s.log(f"Ancestor: {status}")
        if not ancestor_val["semantically_valid"]:
            s.log("  SHACL violations:")
            for v in ancestor_val["shacl_violations"]:
                s.log(f"    {v['shape']}: {v['message']}")
            for oq in ancestor_val["oracle_results"]:
                if oq["has_violations"]:
                    s.log(f"  Oracle {oq['query']}: {oq['rows']}")

    all_scenarios = []

    # ── Scenario 1: True Negative ──────────────────────────────
    with logger.step("scenario_tn", "Scenario 1: True Negative — disjoint, uncoupled changes") as s:
        s.log("Branch A (ADCS): tune PD gains Kp=1.5, Kd=15 in adcs.ttl")
        s.log("Branch B (Power): relax battery DOD to 0.70 in power.ttl")
        s.log("Different files, no shared constraint affected.")
        result = run_scenario(
            logger, "true-negative", ont_graph, shapes_graph, model_files,
            branch_a_name="adcs-tune-gains",
            branch_a_mutations={"structural/adcs.ttl": mutate_adcs_tune_gains},
            branch_b_name="power-tune-battery",
            branch_b_mutations={"structural/power.ttl": mutate_power_tune_battery},
        )
        all_scenarios.append(result)

    # ── Scenario 2: False Negative ─────────────────────────────
    with logger.step("scenario_fn", "Scenario 2: False Negative — coupled across files") as s:
        s.log("Branch A (ADCS): upgrade wheels, power draw 50W → 80W in adcs.ttl")
        s.log("Branch B (Power): reduce panels 180W → 150W, available 306W → 255W in power.ttl")
        s.log("Different files → Git clean. But total draw (80+15+120+40+10=265W) > 255W available.")
        result = run_scenario(
            logger, "false-negative", ont_graph, shapes_graph, model_files,
            branch_a_name="adcs-upgrade-wheels",
            branch_a_mutations={"structural/adcs.ttl": mutate_adcs_upgrade_wheels},
            branch_b_name="power-reduce-panels",
            branch_b_mutations={"structural/power.ttl": mutate_power_reduce_panels},
        )
        all_scenarios.append(result)

    # ── Scenario 3: True Positive ──────────────────────────────
    with logger.step("scenario_tp", "Scenario 3: True Positive — same attribute, same file") as s:
        s.log("Branch A (ADCS): update own power draw 50W → 55W in adcs.ttl")
        s.log("Branch B (SysEng): independently sets ADCS draw to 48W in adcs.ttl")
        s.log("Same line → Git textual conflict.")
        result = run_scenario(
            logger, "true-positive", ont_graph, shapes_graph, model_files,
            branch_a_name="adcs-update-power",
            branch_a_mutations={"structural/adcs.ttl": mutate_adcs_change_power_draw},
            branch_b_name="syseng-correct-power",
            branch_b_mutations={"structural/adcs.ttl": mutate_power_change_adcs_view},
        )
        all_scenarios.append(result)

    # ── Scenario 4: False Positive ─────────────────────────────
    with logger.step("scenario_fp", "Scenario 4: False Positive — reordered serialization") as s:
        s.log(f"Both branches reorder adcs.ttl blocks (seeds {RANDOM_SEED}, {RANDOM_SEED+1})")
        s.log("Semantically identical content. Git may conflict on textual diff.")

        adcs_ttl = model_files["structural/adcs.ttl"]
        shuffled_a = shuffle_turtle(adcs_ttl, RANDOM_SEED)
        shuffled_b = shuffle_turtle(adcs_ttl, RANDOM_SEED + 1)

        result = run_scenario(
            logger, "false-positive", ont_graph, shapes_graph, model_files,
            branch_a_name="serialize-order-a",
            branch_a_mutations={"structural/adcs.ttl": lambda _: shuffled_a},
            branch_b_name="serialize-order-b",
            branch_b_mutations={"structural/adcs.ttl": lambda _: shuffled_b},
        )
        all_scenarios.append(result)

    # ── Confusion matrix ───────────────────────────────────────
    with logger.step("confusion_matrix", "Build confusion matrix") as s:
        matrix = build_confusion_matrix(all_scenarios)
        s.detail("matrix", matrix)
        s.log("")
        s.log("                Sem. Valid    Sem. Invalid")
        s.log(f"  Git clean     {matrix['true_negative']:>5d}         {matrix['false_negative']:>5d}   ← false negatives")
        s.log(f"  Git conflict  {matrix['false_positive']:>5d}         {matrix['true_positive']:>5d}")
        s.log("")
        s.log(f"  False negative rate: {matrix['false_negative_rate']:.1%}")
        s.log(f"  False positive rate: {matrix['false_positive_rate']:.1%}")

    # ── Summary ────────────────────────────────────────────────
    with logger.step("summary", "Per-scenario summary") as s:
        for sc in all_scenarios:
            s.log(f"\n  {sc['scenario']}:")
            for o in sc["orderings"]:
                gc = "CONFLICT" if o["git_conflict"] else "clean"
                if o["semantically_valid"] is None:
                    sv = "N/A"
                elif o["semantically_valid"]:
                    sv = "valid"
                else:
                    sv = "INVALID"
                s.log(f"    {o['ordering']:>12s}: Git {gc:>8s} | Semantic {sv}")

    logger.set_findings({
        "confusion_matrix": matrix,
        "scenarios": all_scenarios,
        "ancestor_validation": ancestor_val,
    })

    has_fn = matrix["false_negative"] > 0
    has_fp = matrix["false_positive"] > 0
    if has_fn and has_fp:
        verdict = "MIXED — Git has both false negatives and false positives for RDF"
    elif has_fn:
        verdict = "MIXED — Git misses semantic conflicts (false negatives)"
    elif has_fp:
        verdict = "MIXED — Git produces spurious conflicts (false positives)"
    else:
        verdict = "PASS"

    logger.end(verdict)


if __name__ == "__main__":
    main()
