#!/usr/bin/env python3
"""
Verification Service — KC Python API

Reconstructs a Flexo branch's model state using the mtg-kc Python API,
then detects conflicts as the gap between what Flexo stores and what
the KC framework accepts.

This is a proxy for how a KerML or SysML v2 verification service would
work: domain-typed validation through a Pythonic API, with SHACL/SPARQL
abstracted away as implementation details.

Steps:
  1. Fetch all triples from a Flexo branch via SPARQL CONSTRUCT
  2. Extract structured element data (complex membership, types, boundaries, attributes)
  3. Reconstruct using KC API: build_mtg_schema() → KnowledgeComplex → add_vertex/add_edge/add_face
  4. Detect orphans: triples in Flexo for elements NOT in the complex
  5. Run named queries for domain analysis
  6. Report pass/fail with domain concepts (not SHACL violation text)

Usage:
    python3 verify.py <branch> [--base-url URL] [--token TOKEN]
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# mtg-kc sibling repo
_MTG_KC_PATH = Path(__file__).resolve().parents[2].parent / "mtg-kc"
sys.path.insert(0, str(_MTG_KC_PATH))

from rdflib import Graph, Namespace, RDF  # ONLY for parsing Flexo response

from models.mtg import build_mtg_schema, QUERIES_DIR
from kc import KnowledgeComplex, ValidationError

KC = Namespace("https://example.org/kc#")
MTG = Namespace("https://example.org/mtg#")

# Map RDF type IRIs to KC API type names
TYPE_MAP = {
    str(MTG.Color): "Color",
    str(MTG.ColorPair): "ColorPair",
    str(MTG.ColorTriple): "ColorTriple",
}

# Attributes that are structural (handled separately), not passed as kwargs
STRUCTURAL_PROPS = {"boundedBy", "hasElement"}
# Properties in the kc: namespace (not domain attributes)
KC_PROPS = {str(KC.boundedBy), str(KC.hasElement)}
# RDF/OWL/RDFS properties to skip
SKIP_PROPS = {str(RDF.type)}

DEFAULT_BASE = "https://try-layer1.starforge.app"
DEFAULT_ORG = "research"
TIMEOUT = 120


def _local_id(iri: str) -> str:
    """Extract local ID from a full IRI (e.g., 'https://example.org/mtg#White' → 'White')."""
    return iri.rsplit("#", 1)[-1] if "#" in iri else iri.rsplit("/", 1)[-1]


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


def parse_flexo_graph(turtle_data):
    """Parse Turtle data into an rdflib Graph."""
    g = Graph()
    try:
        g.parse(data=turtle_data, format="turtle")
    except Exception:
        try:
            g.parse(data=turtle_data, format="nt")
        except Exception as e:
            print(f"  [verify.py] ERROR: Could not parse response: {e}", file=sys.stderr)
            sys.exit(2)
    return g


def extract_elements(g):
    """Extract structured element data from the Flexo graph.

    Returns:
        members: set of local IDs in the complex
        vertices: dict of {id: {attr: value, ...}}
        edges: dict of {id: {"vertices": set, **attrs}}
        faces: dict of {id: {"boundary": list, **attrs}}
        orphans: list of (element_id, property, value) for elements NOT in complex
    """
    # Find complex membership
    members = set()
    for _, _, elem in g.triples((None, KC.hasElement, None)):
        members.add(str(elem))

    # Classify elements by type
    type_of = {}
    for elem, _, typ in g.triples((None, RDF.type, None)):
        typ_str = str(typ)
        if typ_str in TYPE_MAP:
            type_of[str(elem)] = TYPE_MAP[typ_str]

    # Extract boundaries
    boundaries = {}  # iri → list of boundary iris
    for elem, _, boundary in g.triples((None, KC.boundedBy, None)):
        elem_str = str(elem)
        if elem_str not in boundaries:
            boundaries[elem_str] = []
        boundaries[elem_str].append(str(boundary))

    # Extract mtg: attributes per element
    attrs = {}  # iri → {attr_name: value_or_list}
    mtg_str = str(MTG)
    for s, p, o in g:
        p_str = str(p)
        if not p_str.startswith(mtg_str):
            continue
        if p_str in KC_PROPS:
            continue
        s_str = str(s)
        attr_name = _local_id(p_str)
        if s_str not in attrs:
            attrs[s_str] = {}
        val = str(o)
        if attr_name in attrs[s_str]:
            existing = attrs[s_str][attr_name]
            if isinstance(existing, list):
                existing.append(val)
            else:
                attrs[s_str][attr_name] = [existing, val]
        else:
            attrs[s_str][attr_name] = val

    # Build structured output
    vertices = {}
    edges = {}
    faces = {}

    for iri in members:
        local = _local_id(iri)
        typ = type_of.get(iri)
        elem_attrs = {k: v for k, v in attrs.get(iri, {}).items()}

        if typ == "Color":
            vertices[local] = elem_attrs
        elif typ == "ColorPair":
            boundary_ids = [_local_id(b) for b in boundaries.get(iri, [])]
            edges[local] = {"vertices": set(boundary_ids), **elem_attrs}
        elif typ == "ColorTriple":
            boundary_ids = [_local_id(b) for b in boundaries.get(iri, [])]
            faces[local] = {"boundary": boundary_ids, **elem_attrs}

    # Detect orphans: mtg: subjects with properties but NOT in complex
    member_set = members
    complex_iri = None
    for s, _, _ in g.triples((None, KC.hasElement, None)):
        complex_iri = str(s)
        break

    orphans = []
    for iri, elem_attrs in attrs.items():
        if iri in member_set:
            continue
        if iri == complex_iri:
            continue
        # Skip OWL class/property declarations
        if type_of.get(iri) is None and iri not in member_set:
            # Check if this is an instance (has a domain type) vs schema declaration
            for _, _, t in g.triples((None, None, None)):
                pass  # We just check attrs
            for attr_name, val in elem_attrs.items():
                if isinstance(val, list):
                    for v in val:
                        orphans.append((_local_id(iri), attr_name, v))
                else:
                    orphans.append((_local_id(iri), attr_name, val))

    return members, vertices, edges, faces, orphans


def reconstruct_and_verify(vertices, edges, faces):
    """Reconstruct the complex using the KC API. Returns (success, errors, kc)."""
    schema = build_mtg_schema()
    kc = KnowledgeComplex(schema=schema, query_dirs=[QUERIES_DIR])
    errors = []

    # Add vertices
    for vid, attrs in sorted(vertices.items()):
        try:
            kc.add_vertex(vid, type="Color", **attrs)
        except ValidationError as e:
            errors.append(("Color", vid, str(e)))
        except Exception as e:
            errors.append(("Color", vid, str(e)))

    # Add edges
    for eid, data in sorted(edges.items()):
        verts = data.pop("vertices")
        try:
            kc.add_edge(eid, type="ColorPair", vertices=verts, **data)
        except ValidationError as e:
            errors.append(("ColorPair", eid, str(e)))
        except Exception as e:
            errors.append(("ColorPair", eid, str(e)))

    # Add faces
    for fid, data in sorted(faces.items()):
        boundary = data.pop("boundary")
        try:
            kc.add_face(fid, type="ColorTriple", boundary=boundary, **data)
        except ValidationError as e:
            errors.append(("ColorTriple", fid, str(e)))
        except Exception as e:
            errors.append(("ColorTriple", fid, str(e)))

    return len(errors) == 0, errors, kc


def main():
    parser = argparse.ArgumentParser(description="Verification Service — KC Python API")
    parser.add_argument("branch", help="Flexo branch name to verify")
    parser.add_argument("--base-url", default=os.environ.get("FLEXO_BASE_URL", DEFAULT_BASE))
    parser.add_argument("--org", default=os.environ.get("FLEXO_ORG", DEFAULT_ORG))
    parser.add_argument("--repo", default=os.environ.get("FLEXO_REPO", ""))
    parser.add_argument("--token", default=os.environ.get("FLEXO_TOKEN", ""))
    args = parser.parse_args()

    if not args.token:
        print("  [verify.py] ERROR: No token provided", file=sys.stderr)
        sys.exit(2)

    # --- Step 1: Fetch from storage ---
    print(f"  [verify.py] Fetching state from Flexo: {args.branch}")
    turtle_data = fetch_triples(args.base_url, args.token, args.org, args.repo, args.branch)
    if not turtle_data.strip():
        print("  [verify.py] ERROR: Empty response from Flexo", file=sys.stderr)
        sys.exit(2)

    g = parse_flexo_graph(turtle_data)
    print(f"  [verify.py] Loaded {len(g)} triples from storage")

    # --- Step 2: Extract structured data ---
    members, vertices, edges, faces, orphans = extract_elements(g)
    print(f"  [verify.py] Complex membership: {len(vertices)} Color, {len(edges)} ColorPair, {len(faces)} ColorTriple")

    # --- Step 3: Reconstruct via KC API ---
    print("  [verify.py] Reconstructing complex via KC Python API...")
    print(f"  [verify.py]   Schema: build_mtg_schema()")
    success, errors, kc = reconstruct_and_verify(vertices, edges, faces)

    if success:
        print(f"  [verify.py]   Reconstruction: PASSED — all {len(vertices) + len(edges) + len(faces)} elements valid")
    else:
        print(f"  [verify.py]   Reconstruction: FAILED — {len(errors)} error(s)")
        for typ, eid, msg in errors[:10]:
            print(f"  [verify.py]     {typ} '{eid}': {msg}")

    # --- Step 4: Detect orphans ---
    if orphans:
        print(f"  [verify.py]   Orphaned data: FOUND ({len(orphans)} triple(s) outside complex)")
        for elem, prop, val in orphans[:10]:
            val_short = val[:60] + "..." if len(val) > 60 else val
            print(f"  [verify.py]     {elem}.{prop} = {val_short}")
    else:
        print("  [verify.py]   Orphaned data: NONE")

    # --- Step 5: Named queries ---
    if success:
        print("  [verify.py] Running domain queries...")
        try:
            verts_df = kc.query("vertices")
            print(f"  [verify.py]   vertices: {len(verts_df)} results")
        except Exception:
            pass
        try:
            edges_df = kc.query("edges_by_disposition")
            adj = len(edges_df[edges_df["disposition"] == "adjacent"]) if "disposition" in edges_df.columns else "?"
            opp = len(edges_df[edges_df["disposition"] == "opposite"]) if "disposition" in edges_df.columns else "?"
            print(f"  [verify.py]   edges_by_disposition: {adj} adjacent, {opp} opposite")
        except Exception:
            pass
        try:
            faces_df = kc.query("faces_by_edge_pattern")
            print(f"  [verify.py]   faces_by_edge_pattern: {len(faces_df)} results")
        except Exception:
            pass

    # --- Step 6: Verdict ---
    passed = success and len(orphans) == 0
    verdict = "PASS" if passed else "FAIL"
    print(f"  [verify.py] VERDICT: {verdict}")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
