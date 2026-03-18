# Experiment 3 — MTG Knowledge Complex: Structural Conflict (Local Flexo)

## What is being tested

Can Flexo's SPARQL-based version control handle **arbitrary RDF** (not SysML), branch it, and detect **structural conflicts** (orphaned triples after topology deletion)?

This is the first experiment using a non-SysML model. The MTG Knowledge Complex is a simplicial complex built with OWL/SHACL/SPARQL — a fundamentally different model structure from the satellite engineering model in Experiments 1–2.

## How

Load the MTG color wheel (25 simplices) into a **local** Flexo instance via SPARQL INSERT DATA. Two curators independently modify the model:

- **Curator A** (commit u, branch-a): Removes the BG (Golgari) edge and all three faces that depend on it (WBG/Abzan, UBG/Sultai, BRG/Jund), maintaining boundary-closure.
- **Curator B** (commit v, branch-b): Enriches the BG edge and BRG face with new gameplay properties (playstyle, example_decks).

Each commit is individually valid. Cross-application states (branch-uv, branch-vu) reveal **orphaned properties** — triples that reference elements no longer in the complex.

## The Model

The MTG Knowledge Complex represents the Magic: The Gathering color wheel as a simplicial complex:

| Dimension | Type | Count | Examples |
| --- | --- | --- | --- |
| 0 (vertices) | Color | 5 | White, Blue, Black, Red, Green |
| 1 (edges) | ColorPair | 10 | WU (Azorius), BR (Rakdos), BG (Golgari) |
| 2 (faces) | ColorTriple | 10 | WUB (Esper), BRG (Jund), WBG (Abzan) |

Key structural constraint: **boundary-closure** — if an element is in the complex, all its boundary elements must also be in the complex. Faces are bounded by 3 edges; edges are bounded by 2 vertices.

Source: [mtg-kc](https://github.com/Open-MBEE/mtg-kc) repository.

## The Conflict Scenario

### Why this scenario is interesting

Unlike Experiments 1–2 (numeric budget violations), this tests **referential integrity** in a graph model. The conflict arises from a fundamental tension: one curator **removes structure** while another **enriches** that same structure. Neither is wrong in isolation, but together they create orphaned data — properties floating in the graph with no corresponding element in the complex.

### Commit u — Remove BG edge and dependent faces

Curator A decides the Black-Green (Golgari) color pair is philosophically incoherent and removes it. To maintain boundary-closure, all faces bounded by BG must also be removed:

- **Deleted:** BG (Golgari), WBG (Abzan), UBG (Sultai), BRG (Jund)
- **Result:** 5 vertices, 9 edges, 7 faces — boundary-closure satisfied

### Commit v — Enrich BG and BRG with new properties

Curator B independently adds gameplay descriptions:

- `mtg:BG mtg:playstyle "graveyard-recursion"`
- `mtg:BG mtg:example_decks "Golgari Midrange"`
- `mtg:BRG mtg:playstyle "aggressive-midrange"`
- `mtg:BRG mtg:example_decks "Jund Sacrifice"`

Individually valid — BG and BRG exist on branch-b.

### Cross-application conflicts

On branch-uv (u then v): commit u deletes BG/BRG, then commit v inserts properties on those deleted elements. The INSERT DATA succeeds (SPARQL doesn't check existence), creating **orphaned triples**.

On branch-vu (v then u): commit v enriches BG/BRG, then commit u deletes their original properties but the `DELETE WHERE` pattern may not match v's newly-added triples, leaving them as **orphaned triples**.

## Directory Contents

```
experiment-3/
├── README.md                        ← this file
├── ancestor-model.ttl               ← full MTG-KC instance (25 elements)
├── commit-u-remove-bg.ru            ← SPARQL UPDATE: delete BG + dependent faces
├── commit-v-enrich-bg.ru            ← SPARQL UPDATE: add properties to BG + BRG
├── oracle/
│   ├── c1-orphaned-properties.rq   ← properties on elements not in complex
│   ├── c2-boundary-closure.rq      ← faces with missing boundary edges
│   ├── c3-complex-membership.rq    ← element count by type
│   └── c4-edge-count.rq            ← total edge count
└── run.sh                           ← full experiment script
```

## Prerequisites

- Local Flexo MMS instance running (see [Experiment 1 README](../experiment-1/README.md))
- `curl` and `python3` on PATH

## Quick Start

```bash
chmod +x run.sh
./run.sh
```

## Expected Results

| Stage | C1 orphaned | C2 closure | C3 membership | C4 edges |
| --- | --- | --- | --- | --- |
| master | satisfied | satisfied | 5 Color, 10 ColorPair, 10 ColorTriple | 10 |
| branch-a | satisfied | satisfied | 5 Color, 9 ColorPair, 7 ColorTriple | 9 |
| branch-b | satisfied | satisfied | 5 Color, 10 ColorPair, 10 ColorTriple | 10 |
| branch-uv | **BG: 2, BRG: 2 orphaned** | satisfied | 5 Color, 9 ColorPair, 7 ColorTriple | 9 |
| branch-vu | satisfied | satisfied | 5 Color, 9 ColorPair, 7 ColorTriple | 9 |

### Non-commutativity: a key finding

Unlike Experiments 1–2 (where both orderings produced identical violations), Experiment 3 reveals **non-commutative** behavior:

- **branch-uv** (delete then enrich): Commit u deletes BG/BRG elements. Commit v's `INSERT DATA` then creates 4 orphaned triples (properties on elements no longer in the complex). SPARQL `INSERT DATA` does not check whether the subject exists.
- **branch-vu** (enrich then delete): Commit v adds properties to BG/BRG. Commit u's `DELETE WHERE { OPTIONAL { mtg:BG ?p ?o } }` catches **all** triples on BG — including v's newly-added ones — wiping them cleanly. No orphans remain.

Both orderings produce the same **structural state** (5/9/7 membership, 9 edges), but the **data residue** differs. The non-commutativity is itself a conflict signal: the order of application matters for data integrity, even when the topology converges.

## What We Learn

1. **Flexo handles arbitrary RDF** — not limited to SysML models. The branch/commit pattern works for OWL knowledge graphs.
2. **SPARQL DELETE/INSERT operations work on non-SysML data** — including `DELETE WHERE` with `OPTIONAL` patterns for bulk deletion.
3. **Structural conflicts are detectable** — orphaned triples can be found via SPARQL queries checking complex membership against the `kc:hasElement` relation.
4. **Non-commutativity as a conflict signal** — unlike the satellite scenario (where both orderings produce identical numeric violations), structural delete-vs-enrich conflicts produce **order-dependent data residue**. This is a richer conflict signature than simple value disagreement.
5. **New conflict type** — referential integrity violations in a graph model, fundamentally different from the aggregate budget violations in Experiments 1–2.

## Comparison with Experiments 1–2

| Aspect | Experiments 1–2 (Satellite) | Experiment 3 (MTG-KC) |
| --- | --- | --- |
| Model type | Engineering (numeric properties) | Knowledge graph (topological) |
| Conflict type | Aggregate constraint violation | Referential integrity violation |
| Detection method | Budget arithmetic (sum > limit) | Complex membership check |
| Commutativity | Yes (identical violations) | **No** (orphaned triples in one order only) |
| Structural convergence | Same final state | Same topology, different data residue |
| Data format | Custom RDF properties | OWL simplicial complex |
