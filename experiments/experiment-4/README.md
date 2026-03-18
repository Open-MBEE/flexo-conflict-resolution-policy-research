# Experiment 4 — MTG Knowledge Complex: Full Schema Loading (Local Flexo)

## What is being tested

Does Flexo **preserve OWL ontology and SHACL shapes** when loaded alongside instance data? Can we run **schema-aware queries** (rdf:type-based, SHACL shape coverage) that produce richer conflict detection than Experiment 3's instance-only approach?

## How

Same conflict scenario as Experiment 3 (Curator A removes BG edge + dependent faces, Curator B enriches BG/BRG with new properties), but with three data layers loaded:

1. **ontology.ttl** — OWL class hierarchy (Color, ColorPair, ColorTriple), property definitions
2. **shapes.ttl** — SHACL shapes (boundary-closure, edge cardinality, face closed-triangle, vocabulary constraints)
3. **ancestor-model.ttl** — Instance data (25 simplicial elements)

Two additional oracle queries leverage the schema:
- **C5: Type consistency** — Elements typed as ColorPair/ColorTriple but not in the complex
- **C6: Shape target coverage** — SHACL shapes and how many valid target instances remain

## Directory Contents

```
experiment-4/
├── README.md
├── run.sh
├── ontology.ttl                   ← OWL ontology (class hierarchy, properties)
├── shapes.ttl                     ← SHACL shapes (topological + vocabulary constraints)
├── ancestor-model.ttl             ← MTG-KC instance (25 elements)
├── commit-u-remove-bg.ru          ← SPARQL UPDATE: delete BG + dependent faces
├── commit-v-enrich-bg.ru          ← SPARQL UPDATE: add properties to BG + BRG
└── oracle/
    ├── c1-orphaned-properties.rq  ← properties on elements not in complex
    ├── c2-boundary-closure.rq     ← faces with missing boundary edges
    ├── c3-complex-membership.rq   ← element count by type
    ├── c4-edge-count.rq           ← total edge count
    ├── c5-type-consistency.rq     ← typed instances not in complex (NEW)
    └── c6-shape-targets.rq        ← SHACL shape target coverage (NEW)
```

## Prerequisites

- Local Flexo MMS instance running (see [Experiment 1 README](../experiment-1/README.md))
- `curl` and `python3` on PATH

## Quick Start

```bash
chmod +x run.sh
./run.sh
```

## Results

### C1–C4: Identical to Experiment 3

Schema loading does not change instance-level conflict behavior:
- **branch-uv**: 4 orphaned triples on BG/BRG (same as Experiment 3)
- **branch-vu**: no orphans (same non-commutativity as Experiment 3)

### C5: Type consistency — no violations

Commit u's wildcard `DELETE WHERE { mtg:BG ?p ?o }` removes the `rdf:type` triple along with everything else. Deleted elements have no type residue, so C5 finds nothing. The orphaned triples from commit v are just data properties, not typed.

### C6: Shape target coverage

SHACL shapes are preserved and queryable. Target instance counts track correctly across branches:

| Shape | master | branch-a | branch-uv/vu |
| --- | --- | --- | --- |
| ColorShape | 5 | 5 | 5 |
| ColorPairShape | 10 | 9 | 9 |
| ColorTripleShape | 10 | 7 | 7 |
| EdgeShape (kc:Edge) | 0 | 0 | 0 |
| FaceShape (kc:Face) | 0 | 0 | 0 |
| ComplexShape (kc:Complex) | 0 | 0 | 0 |

The kc: base shapes show 0 instances because **Flexo does not run an OWL reasoner** — instances are typed as `mtg:ColorPair` (direct type), not `kc:Edge` (via `rdfs:subClassOf`). The mtg: shapes work because they target the concrete types directly.

## What We Learned

1. **Flexo preserves OWL/SHACL triples** — Schema data survives loading, branching, and commits alongside instance data.
2. **Schema-aware queries work** — SHACL shape metadata is queryable and target counts track structural changes correctly.
3. **No OWL reasoning** — Flexo stores but does not reason over OWL axioms. `rdfs:subClassOf` inference does not happen, so queries must target concrete types, not abstract supertypes.
4. **Schema loading doesn't change conflict behavior** — C1–C4 results are identical to Experiment 3. The additional C5/C6 queries provide structural context but don't reveal new conflict types in this scenario.
5. **Type cleanup is thorough** — Wildcard DELETE removes type triples, preventing type-residue conflicts. A more targeted DELETE (specific property patterns) could leave type triples behind, which C5 would then detect.

## Comparison with Experiment 3

| Aspect | Experiment 3 | Experiment 4 |
| --- | --- | --- |
| Data loaded | Instance only | Ontology + shapes + instance |
| Oracle queries | C1–C4 (instance-level) | C1–C6 (+ schema-aware) |
| Type queries | Cannot use rdf:type | Can query by type hierarchy |
| Shape queries | No SHACL data to query | Can inspect shape targets |
| Same conflict scenario | Yes | Yes |
