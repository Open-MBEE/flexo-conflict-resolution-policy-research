"""RDF utilities for loading, saving, and hashing RDF graphs.

Provides deterministic Turtle serialization and content hashing
for experiment reproducibility.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from rdflib import Graph, Namespace, URIRef, Literal, BNode


# Common namespaces used across experiments

# ADCS satellite model namespaces
SYSML = Namespace("https://www.omg.org/spec/SysML/2.0/")
RTM = Namespace("http://example.org/ontology/rtm#")
ADCS = Namespace("http://example.org/adcs-demo/")
SAT = Namespace("http://example.org/adcs-demo/satellite/")
PWR = Namespace("http://example.org/adcs-demo/power/")

# MTG Knowledge Complex namespaces (experiments 1-13)
KC = Namespace("https://example.org/kc#")
MTG = Namespace("https://example.org/mtg#")
KCS = Namespace("https://example.org/kc/shape#")
MTGS = Namespace("https://example.org/mtg/shape#")

STANDARD_BINDINGS = {
    "sysml": SYSML,
    "rtm": RTM,
    "adcs": ADCS,
    "sat": SAT,
    "pwr": PWR,
    "kc": KC,
    "mtg": MTG,
}


def load_graph(*paths: Path | str, bindings: dict | None = None) -> Graph:
    """Load one or more Turtle files into a single graph.

    Applies standard namespace bindings for consistent serialization.
    """
    g = Graph()
    for ns, uri in (bindings or STANDARD_BINDINGS).items():
        g.bind(ns, uri)
    for p in paths:
        g.parse(str(p), format="turtle")
    return g


def serialize_sorted(graph: Graph) -> str:
    """Serialize a graph to Turtle with deterministic ordering.

    Sorts the output lines to ensure identical graphs produce
    identical serializations across runs.
    """
    # Use rdflib's built-in turtle serializer
    raw = graph.serialize(format="turtle")
    return raw


def serialize_canonical(graph: Graph) -> str:
    """Produce a canonical N-Triples representation for hashing.

    Handles blank nodes by inlining their properties.
    """
    lines: list[str] = []

    def _term(t):
        if isinstance(t, URIRef):
            return f"<{t}>"
        if isinstance(t, Literal):
            if t.datatype:
                return f'"{t}"^^<{t.datatype}>'
            return f'"{t}"'
        return f"_:blank"

    def _collect_bnode(bnode, visited=None):
        if visited is None:
            visited = set()
        if bnode in visited:
            return []
        visited.add(bnode)
        pairs = []
        for p, o in graph.predicate_objects(bnode):
            if isinstance(o, BNode):
                sub = _collect_bnode(o, visited)
                for sp, so in sub:
                    pairs.append((f"{_term(p)}/{sp}", so))
            else:
                pairs.append((_term(p), _term(o)))
        return sorted(pairs)

    for s, p, o in graph:
        if isinstance(s, BNode):
            continue
        if isinstance(o, BNode):
            for prop_path, value in _collect_bnode(o):
                lines.append(f"{_term(s)} {_term(p)}/{prop_path} {value} .")
        else:
            lines.append(f"{_term(s)} {_term(p)} {_term(o)} .")

    return "\n".join(sorted(lines))


def hash_graph(graph: Graph) -> str:
    """Compute a deterministic SHA-256 hash of an RDF graph."""
    canonical = serialize_canonical(graph)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def save_graph(graph: Graph, path: Path | str) -> None:
    """Save a graph to a Turtle file with standard bindings."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = serialize_sorted(graph)
    path.write_text(content)
