"""
Oracle for Experiment 6 — hybrid constraint evaluation.

Runs the same C1–C4 checks as Experiment 5 (Python), PLUS:
- C5: SHACL validation via pyshacl (through the KC bridge)
- C6: SPARQL boundary-closure query executed on client-side RDF graph

This demonstrates that RDF-native validation tools can operate on data
retrieved from the JSON REST API, bridging the two worlds.
"""

from bridge import validate_with_shacl, run_sparql_on_elements


def _strip(s):
    return s[4:] if s.startswith("mtg:") else s


def _complex(elements):
    for e in elements:
        if e["@id"] in ("mtg:_complex", "_complex"):
            return e
    return None


def _member_set(cplx):
    members = set()
    for m in cplx.get("members", []):
        members.add(m)
        members.add(_strip(m))
    return members


def c1_orphaned_properties(elements):
    """C1: Elements with properties not in complex membership (Python)."""
    cplx = _complex(elements)
    if not cplx:
        return {"satisfied": True}
    members = _member_set(cplx)
    orphans = []
    for e in elements:
        eid = e["@id"]
        if eid in ("mtg:_complex", "_complex"):
            continue
        if eid not in members:
            props = {k: v for k, v in e.items() if k not in ("@id", "@type")}
            if props:
                orphans.append({"element": eid, "properties": props})
    if orphans:
        return {"satisfied": False, "violations": orphans}
    return {"satisfied": True}


def c2_boundary_closure(elements):
    """C2: Boundary closure check (Python)."""
    cplx = _complex(elements)
    if not cplx:
        return {"satisfied": True}
    members = _member_set(cplx)
    violations = []
    for e in elements:
        if e["@id"] not in members:
            continue
        for b in e.get("boundedBy", []):
            if b not in members and _strip(b) not in members:
                violations.append({"element": e["@id"], "missingBoundary": b})
    if violations:
        return {"satisfied": False, "violations": violations}
    return {"satisfied": True}


def c3_complex_membership(elements):
    """C3: Count elements by type in complex (Python)."""
    cplx = _complex(elements)
    if not cplx:
        return {}
    members = _member_set(cplx)
    counts = {}
    for e in elements:
        if e["@id"] in members:
            t = e.get("@type", "Unknown")
            counts[t] = counts.get(t, 0) + 1
    return counts


def c4_edge_count(elements):
    """C4: Count edges in complex (Python)."""
    cplx = _complex(elements)
    if not cplx:
        return {"edgeCount": 0}
    members = _member_set(cplx)
    return {"edgeCount": sum(1 for e in elements if e["@id"] in members and e.get("@type") == "ColorPair")}


def c5_shacl_validation(elements):
    """C5: SHACL validation via pyshacl (through KC bridge).

    Converts JSON elements to RDF, loads KC schema, runs pyshacl.
    This is the key test: can RDF-native validation work on REST API data?
    """
    conforms, report = validate_with_shacl(elements)
    if conforms:
        return {"satisfied": True}
    # Extract violation count from report
    lines = report.strip().split("\n")
    violation_lines = [l for l in lines if "Constraint Violation" in l]
    return {
        "satisfied": False,
        "violationCount": len(violation_lines),
        "summary": report[:500] if len(report) > 500 else report,
    }


def c6_sparql_boundary_closure(elements):
    """C6: Boundary closure via SPARQL on client-side RDF graph (through KC bridge).

    Same query as experiments 3–4's c2-boundary-closure.rq, but executed
    on an rdflib graph built from JSON elements.
    """
    query = """
    PREFIX kc: <https://example.org/kc#>
    PREFIX mtg: <https://example.org/mtg#>

    SELECT ?element ?missingBoundary
    WHERE {
      mtg:_complex kc:hasElement ?element .
      ?element kc:boundedBy ?missingBoundary .
      FILTER NOT EXISTS {
        mtg:_complex kc:hasElement ?missingBoundary .
      }
    }
    ORDER BY ?element
    """
    results = run_sparql_on_elements(elements, query)
    if results:
        return {"satisfied": False, "violations": results}
    return {"satisfied": True}


ALL_CONSTRAINTS = [
    ("c1-orphaned-properties (Python)", c1_orphaned_properties),
    ("c2-boundary-closure (Python)", c2_boundary_closure),
    ("c3-complex-membership (Python)", c3_complex_membership),
    ("c4-edge-count (Python)", c4_edge_count),
    ("c5-shacl-validation (pyshacl via bridge)", c5_shacl_validation),
    ("c6-sparql-boundary-closure (rdflib via bridge)", c6_sparql_boundary_closure),
]


def run_oracle(elements, label):
    """Run all constraints and print results."""
    print(f"\n=== Oracle evaluation: {label} ===")
    for name, fn in ALL_CONSTRAINTS:
        print(f"--- {name} ---")
        result = fn(elements)
        if isinstance(result, dict) and "satisfied" in result:
            if result["satisfied"]:
                print("   (no results — constraint satisfied)")
            else:
                violations = result.get("violations", [])
                summary = result.get("summary", "")
                count = result.get("violationCount")
                if count is not None:
                    print(f"   {count} SHACL violation(s)")
                    if summary:
                        for line in summary.split("\n")[:8]:
                            print(f"   {line}")
                else:
                    for v in violations:
                        print(f"   {v}")
        else:
            print(f"   {result}")
