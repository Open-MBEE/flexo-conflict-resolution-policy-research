# Experiment 6 — MTG Knowledge Complex: KC Python API Bridge (Remote Flexo)

## What is being tested

Can the KC Python APIs (rdflib, pyshacl) **bridge between RDF-native models and JSON REST storage**, preserving SHACL validation and SPARQL query capabilities?

This is the most architecturally ambitious experiment. The REST API is a dumb versioned JSON store (as established in Experiment 5). The question is whether we can layer RDF-native semantic validation on top by:

1. Fetching JSON elements from the REST API
2. Converting them to an rdflib RDF graph (the "bridge")
3. Running pyshacl validation against the KC schema
4. Executing SPARQL queries against the client-side RDF graph

## How

Same structural conflict scenario as Experiments 3–5. The oracle runs six checks:

| Check | Method | What it tests |
| --- | --- | --- |
| C1: Orphaned properties | Python | Same as Experiment 5 |
| C2: Boundary closure | Python | Same as Experiment 5 |
| C3: Complex membership | Python | Same as Experiment 5 |
| C4: Edge count | Python | Same as Experiment 5 |
| **C5: SHACL validation** | **pyshacl via bridge** | Full KC schema validation on REST-stored data |
| **C6: SPARQL boundary closure** | **rdflib via bridge** | Same SPARQL query as Experiments 3–4, on client-side RDF |

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Remote Flexo (SysML v2 REST API)               │
│  - Stores JSON elements                         │
│  - Manages branches/commits                     │
│  - No validation, no queries                    │
└──────────────────┬──────────────────────────────┘
                   │ GET /elements (JSON)
                   ▼
┌─────────────────────────────────────────────────┐
│  Bridge (bridge.py)                             │
│  - JSON → rdflib Graph conversion               │
│  - Maps @type to OWL classes                    │
│  - Maps properties to RDF predicates            │
│  - Maps members to kc:hasElement                │
│  - Maps boundedBy to kc:boundedBy               │
└──────────┬──────────────────┬───────────────────┘
           │                  │
           ▼                  ▼
┌──────────────────┐ ┌───────────────────────────┐
│  pyshacl          │ │  rdflib SPARQL             │
│  (C5: SHACL)      │ │  (C6: boundary closure)    │
│  Uses KC schema:  │ │  Same .rq queries as       │
│  ontology.ttl     │ │  Experiments 3–4           │
│  shapes.ttl       │ │                            │
└──────────────────┘ └───────────────────────────┘
```

The bridge is the key innovation: it reconstitutes RDF semantics from flat JSON, enabling the full KC validation stack to run on data stored in a non-RDF API.

## Directory Contents

```
experiment-6/
├── README.md
├── run.py                 ← main experiment script
├── model.py               ← MTG elements as JSON + commit operations
├── oracle.py              ← C1-C4 (Python) + C5 (SHACL) + C6 (SPARQL)
├── bridge.py              ← JSON ↔ RDF conversion + validation
├── schema/
│   ├── ontology.ttl       ← KC OWL ontology
│   └── shapes.ttl         ← KC SHACL shapes
└── requirements.txt       ← requests, rdflib, pyshacl
```

## Prerequisites

- Python 3.8+
- `requests`, `rdflib`, `pyshacl` (`pip install -r requirements.txt`)
- `FLEXO_BEARER_TOKEN` environment variable

## Quick Start

```bash
pip install -r requirements.txt
export FLEXO_BEARER_TOKEN="eyJhbGci..."
python3 run.py --cleanup
```

## Results

### C1–C4 (Python): Identical to Experiment 5

Same orphan behavior, same non-commutativity. The bridge doesn't change the Python-level constraint results.

### C5 (SHACL via bridge): 130 violations on ALL branches

pyshacl reports 130 MinCount violations on every branch — including the ancestor. These are **not conflict-related**: they reflect missing required properties (`at_best`, `at_worst`, `persona`, `example_behaviors`) that the KC SHACL shapes mandate but our simplified JSON model omits.

This reveals an important **bridge fidelity issue**: the JSON model used in Experiments 5–6 carries only the structural properties (goal, guild, theme, boundedBy, members) and omits the rich-text attributes (persona essays, example behaviors). SHACL correctly catches this gap. The violation count is constant across branches because the conflict scenario doesn't change which properties are present — it changes membership and adds new properties, but the missing ones stay missing.

To get SHACL violations that vary by branch (and thus detect conflicts), the bridge would need to either: (a) include all required properties in the JSON model, or (b) use a relaxed SHACL shapes file that only validates structural constraints.

### C6 (SPARQL via bridge): Works perfectly

The same boundary-closure SPARQL query from Experiments 3–4 runs correctly client-side via rdflib. It correctly reports "satisfied" on all branches (boundary closure is maintained by commit u's design). This confirms that the JSON→RDF bridge produces a graph that is query-compatible with the server-side SPARQL experiments.

## What We Learned

1. **The bridge works** — JSON elements from the REST API can be converted to RDF and validated with pyshacl/rdflib. The round-trip is functional.
2. **SPARQL queries are portable** — The same `.rq` queries from Experiments 3–4 produce identical results on the client-side rdflib graph. This is a strong portability result.
3. **SHACL catches bridge fidelity gaps** — pyshacl validation immediately surfaces properties that the JSON model omits. This is useful: it tells you exactly what information is lost in the JSON↔RDF bridge.
4. **Constant SHACL violations mask conflict signals** — When the baseline SHACL state already has violations (from incomplete data), conflict-specific violations are drowned out. A production bridge would need either full-fidelity JSON models or conflict-specific SHACL shapes.
5. **Architecture is viable but needs refinement** — The pattern of "REST API for versioning + client-side RDF for validation" works in principle. The gap is in data fidelity: the JSON model must carry enough information for SHACL to produce meaningful differential signals between branches.

## Comparison Across All Experiments

| Concern | Exp 1–2 (Satellite) | Exp 3–4 (SPARQL) | Exp 5 (REST) | Exp 6 (Bridge) |
| --- | --- | --- | --- | --- |
| Storage | Flexo SPARQL / REST | Flexo SPARQL | Flexo REST | Flexo REST |
| Validation | Server SPARQL / Client Python | Server SPARQL | Client Python | **Client RDF (pyshacl + rdflib)** |
| Schema awareness | None | None / OWL+SHACL stored | None | **OWL+SHACL loaded client-side** |
| Query language | SPARQL / Python | SPARQL | Python | **Both (Python + client SPARQL)** |
