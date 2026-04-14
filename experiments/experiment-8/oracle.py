"""
Oracle constraint evaluators for the MTG-KC structural conflict scenario.

Mirrors the SPARQL oracle queries from experiments 3–4, translated to
Python functions operating on JSON element lists.

  c1-orphaned-properties.rq  →  c1_orphaned_properties()
  c2-boundary-closure.rq     →  c2_boundary_closure()
  c3-complex-membership.rq   →  c3_complex_membership()
  c4-edge-count.rq           →  c4_edge_count()
"""


def _strip_prefix(s):
    """Strip 'mtg:' prefix if present — the REST API strips it from @id but not from values."""
    return s[4:] if s.startswith("mtg:") else s


def _find(elements, element_id):
    bare = _strip_prefix(element_id)
    for e in elements:
        if e["@id"] == element_id or e["@id"] == bare:
            return e
    return None


def _complex(elements):
    return _find(elements, "mtg:_complex")


def _member_set(cplx):
    """Build a normalized set of member IDs (with and without mtg: prefix)."""
    members = set()
    for m in cplx.get("members", []):
        members.add(m)
        members.add(_strip_prefix(m))
    return members


def c1_orphaned_properties(elements):
    """C1: Elements with properties that are NOT in the complex membership list."""
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
    """C2: Elements in the complex whose boundary elements are missing."""
    cplx = _complex(elements)
    if not cplx:
        return {"satisfied": True}
    members = _member_set(cplx)
    violations = []
    for e in elements:
        if e["@id"] not in members:
            continue
        boundary = e.get("boundedBy", [])
        for b in boundary:
            if b not in members and _strip_prefix(b) not in members:
                violations.append({"element": e["@id"], "missingBoundary": b})
    if violations:
        return {"satisfied": False, "violations": violations}
    return {"satisfied": True}


def c3_complex_membership(elements):
    """C3: Count elements by type in the complex."""
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
    """C4: Count edges in the complex."""
    cplx = _complex(elements)
    if not cplx:
        return {"edgeCount": 0}
    members = _member_set(cplx)
    count = sum(1 for e in elements if e["@id"] in members and e.get("@type") == "ColorPair")
    return {"edgeCount": count}


ALL_CONSTRAINTS = [
    ("c1-orphaned-properties", c1_orphaned_properties),
    ("c2-boundary-closure", c2_boundary_closure),
    ("c3-complex-membership", c3_complex_membership),
    ("c4-edge-count", c4_edge_count),
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
                for v in result.get("violations", []):
                    print(f"   {v}")
        else:
            print(f"   {result}")
