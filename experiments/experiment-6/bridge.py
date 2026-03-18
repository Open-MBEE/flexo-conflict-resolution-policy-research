"""
Bridge between JSON elements (SysML v2 REST API) and RDF/SHACL validation
(KC Python API).

Converts JSON elements from the REST API into an rdflib Graph, then runs
pyshacl validation using the MTG-KC schema (ontology + shapes).

This is the core of Experiment 6: can we use RDF-native validation tools
on data stored in a non-RDF API?
"""

import sys
from pathlib import Path

from rdflib import Graph, Namespace, URIRef, Literal, RDF, XSD

# KC schema files (from the mtg-kc repo)
MTG_KC_ROOT = Path(__file__).parent / "schema"

KC = Namespace("https://example.org/kc#")
MTG = Namespace("https://example.org/mtg#")

# Map JSON @type to RDF class IRIs
TYPE_MAP = {
    "Color": MTG.Color,
    "ColorPair": MTG.ColorPair,
    "ColorTriple": MTG.ColorTriple,
    "Complex": KC.Complex,
}

# Properties that are object references (not literal values)
OBJECT_PROPERTIES = {"boundedBy", "members"}

# Properties that map to KC namespace
KC_PROPERTIES = {"boundedBy": KC.boundedBy, "hasElement": KC.hasElement}


def _strip_prefix(s):
    return s[4:] if s.startswith("mtg:") else s


def json_elements_to_graph(elements):
    """
    Convert a list of JSON elements (as returned by the REST API) into
    an rdflib Graph with proper RDF types and properties.

    The resulting graph can be validated with pyshacl using the KC schema.
    """
    g = Graph()
    g.bind("kc", KC)
    g.bind("mtg", MTG)

    for elem in elements:
        eid = elem.get("@id", "")
        etype = elem.get("@type")

        # Determine the IRI for this element
        bare_id = _strip_prefix(eid)
        if bare_id == "_complex":
            elem_iri = MTG["_complex"]
        else:
            elem_iri = MTG[bare_id]

        # Assert type
        if etype and etype in TYPE_MAP:
            g.add((elem_iri, RDF.type, TYPE_MAP[etype]))

        # Assert properties
        for key, value in elem.items():
            if key in ("@id", "@type"):
                continue

            if key == "members":
                # Complex membership → kc:hasElement
                if isinstance(value, list):
                    for m in value:
                        member_iri = MTG[_strip_prefix(m)]
                        g.add((elem_iri, KC.hasElement, member_iri))
            elif key == "boundedBy":
                # Boundary relations → kc:boundedBy
                if isinstance(value, list):
                    for b in value:
                        boundary_iri = MTG[_strip_prefix(b)]
                        g.add((elem_iri, KC.boundedBy, boundary_iri))
            elif key == "name":
                # Skip 'name' — not a KC/MTG ontology property, just a label
                continue
            else:
                # Domain properties → mtg:propertyName
                prop_iri = MTG[key]
                if isinstance(value, list):
                    for v in value:
                        g.add((elem_iri, prop_iri, Literal(str(v))))
                elif isinstance(value, (int, float)):
                    g.add((elem_iri, prop_iri, Literal(value)))
                else:
                    g.add((elem_iri, prop_iri, Literal(str(value))))

    return g


def validate_with_shacl(elements, shapes_path=None, ontology_path=None):
    """
    Run SHACL validation on JSON elements using the KC schema.

    Returns (conforms, report_text) tuple.
    """
    import pyshacl

    # Build data graph from JSON elements
    data_graph = json_elements_to_graph(elements)

    # Load schema
    ont_graph = Graph()
    shacl_graph = Graph()

    ont_path = ontology_path or (MTG_KC_ROOT / "ontology.ttl")
    shapes_path = shapes_path or (MTG_KC_ROOT / "shapes.ttl")

    if ont_path.exists():
        ont_graph.parse(str(ont_path), format="turtle")
    if shapes_path.exists():
        shacl_graph.parse(str(shapes_path), format="turtle")

    conforms, _, report_text = pyshacl.validate(
        data_graph=data_graph,
        shacl_graph=shacl_graph,
        ont_graph=ont_graph,
        inference="rdfs",
        abort_on_first=False,
    )

    return conforms, report_text


def run_sparql_on_elements(elements, query_text):
    """
    Run a SPARQL SELECT query against JSON elements converted to RDF.

    Returns a list of result dicts.
    """
    g = json_elements_to_graph(elements)
    results = g.query(query_text)
    rows = []
    for row in results:
        rows.append({str(var): str(row[var]) for var in results.vars if row[var] is not None})
    return rows
