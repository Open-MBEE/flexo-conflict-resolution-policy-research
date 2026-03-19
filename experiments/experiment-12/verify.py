#!/usr/bin/env python3
"""
Verification Service (Client-Side)

Standalone verification service that:
  1. Fetches all triples from a Flexo branch via SPARQL CONSTRUCT
  2. Loads modular ontology packages (kc-core + mtg-domain)
  3. Runs SHACL validation (pyshacl)
  4. Runs oracle SPARQL queries (rdflib)
  5. Reports pass/fail with structured output
  6. Exits 0 (pass) or 1 (fail)

This is one of three service concerns identified in Experiment 12
(Storage, Schema, Verification). The verification concern is distinct
from Flexo's architectural layers — it consumes data from storage
(Flexo Layer 0+1) and interprets it using the schema (ontology packages)
to check constraint compliance.

In a production architecture, this would be a hosted service that
optionally gates commits. Here it runs client-side as a proof of concept.

Usage:
    python3 verify.py <branch> [--base-url URL] [--token TOKEN]
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from rdflib import Graph

SCRIPT_DIR = Path(__file__).parent
ONTOLOGY_DIR = SCRIPT_DIR / "ontology"
ORACLE_DIR = SCRIPT_DIR / "oracle"

# Flexo connection defaults
DEFAULT_BASE = "https://try-layer1.starforge.app"
DEFAULT_ORG = "research"
DEFAULT_REPO = "three-layer-demo"
TIMEOUT = 120


def fetch_triples(base_url, token, org, repo, branch):
    """Fetch all triples from a Flexo branch via SPARQL CONSTRUCT."""
    query = "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"
    url = f"{base_url}/orgs/{org}/repos/{repo}/branches/{branch}/query"
    result = subprocess.run(
        [
            "curl", "-s", "-m", str(TIMEOUT),
            "-X", "POST", url,
            "-H", f"Authorization: Bearer {token}",
            "-H", "Content-Type: application/sparql-query",
            "-H", "Accept: text/turtle",
            "--data-binary", query,
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  [verify.py] ERROR: curl failed: {result.stderr}", file=sys.stderr)
        sys.exit(2)
    return result.stdout


def load_ontology_packages():
    """Load all ontology packages into a single rdflib Graph."""
    g = Graph()
    packages = ["kc-core", "mtg-domain"]
    for pkg in packages:
        pkg_dir = ONTOLOGY_DIR / pkg
        ont_file = pkg_dir / "ontology.ttl"
        if ont_file.exists():
            g.parse(str(ont_file), format="turtle")
    return g, packages


def load_shapes():
    """Load all SHACL shapes from ontology packages into a single Graph."""
    g = Graph()
    packages = ["kc-core", "mtg-domain"]
    for pkg in packages:
        shapes_file = ONTOLOGY_DIR / pkg / "shapes.ttl"
        if shapes_file.exists():
            g.parse(str(shapes_file), format="turtle")
    return g


def run_shacl(data_graph, ont_graph, shapes_graph):
    """Run pyshacl validation. Returns (conforms, report_text)."""
    import pyshacl
    conforms, _, report_text = pyshacl.validate(
        data_graph=data_graph,
        shacl_graph=shapes_graph,
        ont_graph=ont_graph,
        inference="rdfs",
        abort_on_first=False,
    )
    return conforms, report_text


def run_oracle_queries(data_graph):
    """Run oracle SPARQL queries against the data graph. Returns list of (name, results)."""
    results = []
    for rq_file in sorted(ORACLE_DIR.glob("*.rq")):
        query_text = rq_file.read_text()
        qresults = data_graph.query(query_text)
        rows = []
        for row in qresults:
            rows.append({str(var): str(row[var]) for var in qresults.vars if row[var] is not None})
        results.append((rq_file.stem, rows))
    return results


def main():
    parser = argparse.ArgumentParser(description="Layer 3 — Verification Service")
    parser.add_argument("branch", help="Flexo branch name to verify")
    parser.add_argument("--base-url", default=os.environ.get("FLEXO_BASE_URL", DEFAULT_BASE))
    parser.add_argument("--org", default=os.environ.get("FLEXO_ORG", DEFAULT_ORG))
    parser.add_argument("--repo", default=os.environ.get("FLEXO_REPO", DEFAULT_REPO))
    parser.add_argument("--token", default=os.environ.get("FLEXO_TOKEN", ""))
    args = parser.parse_args()

    # --- Step 1: Get token ---
    token = args.token
    if not token:
        print("  [verify.py] ERROR: No token provided (set FLEXO_TOKEN or --token)", file=sys.stderr)
        sys.exit(2)

    # --- Step 2: Fetch triples from Layer 1 ---
    print(f"  [verify.py] Fetching state from Layer 1: {args.branch}")
    turtle_data = fetch_triples(args.base_url, token, args.org, args.repo, args.branch)

    if not turtle_data.strip():
        print("  [verify.py] ERROR: Empty response from Layer 1", file=sys.stderr)
        sys.exit(2)

    # Parse into rdflib graph
    data_graph = Graph()
    try:
        data_graph.parse(data=turtle_data, format="turtle")
    except Exception as e:
        # Fallback: try n-triples if turtle fails
        try:
            data_graph.parse(data=turtle_data, format="nt")
        except Exception:
            print(f"  [verify.py] ERROR: Could not parse response as RDF: {e}", file=sys.stderr)
            print(f"  [verify.py] First 500 chars: {turtle_data[:500]}", file=sys.stderr)
            sys.exit(2)

    triple_count = len(data_graph)
    print(f"  [verify.py] Loaded {triple_count} triples from Layer 1")

    # --- Step 3: Load ontology packages ---
    ont_graph, packages = load_ontology_packages()
    print(f"  [verify.py] Loaded ontology packages: {', '.join(packages)}")

    shapes_graph = load_shapes()
    shape_count = len(shapes_graph)
    print(f"  [verify.py] Loaded {shape_count} shape triples")

    # --- Step 4: SHACL validation ---
    print("  [verify.py] Running SHACL validation...")
    conforms, report_text = run_shacl(data_graph, ont_graph, shapes_graph)

    if conforms:
        print("  [verify.py]   SHACL: PASSED (0 violations)")
    else:
        # Count violations from report
        violation_count = report_text.count("Constraint Violation")
        print(f"  [verify.py]   SHACL: FAILED ({violation_count} violation(s))")
        # Print concise violation summary (first few lines of each violation)
        for line in report_text.strip().split("\n"):
            if line.strip() and not line.startswith("@"):
                print(f"  [verify.py]     {line.strip()}")

    # --- Step 5: Oracle SPARQL queries ---
    print("  [verify.py] Running oracle queries (C1-C6)...")
    oracle_results = run_oracle_queries(data_graph)

    # c3, c4, c6 are informational (they return counts, not violations)
    INFORMATIONAL = {"c3-complex-membership", "c4-edge-count", "c6-shape-targets"}

    any_oracle_fail = False
    for name, rows in oracle_results:
        if not rows:
            print(f"  [verify.py]   {name}: PASS (no violations)")
        elif name in INFORMATIONAL:
            print(f"  [verify.py]   {name}: INFO ({len(rows)} result(s))")
            for row in rows[:5]:
                print(f"  [verify.py]     {row}")
        else:
            any_oracle_fail = True
            print(f"  [verify.py]   {name}: FAIL ({len(rows)} result(s))")
            for row in rows[:5]:  # Limit output
                print(f"  [verify.py]     {row}")

    # --- Step 6: Verdict ---
    passed = conforms and not any_oracle_fail
    verdict = "PASS" if passed else "FAIL"
    print(f"  [verify.py] VERDICT: {verdict}")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
