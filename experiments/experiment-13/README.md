# Experiment 13 — KC Python API as Verification Service

## Relationship to Experiment 12

Experiment 12 identified three service concerns (Storage, Schema, Verification) and demonstrated them using raw pyshacl + SPARQL for the verification concern. This experiment replaces the raw tooling with the [mtg-kc](https://github.com/mzargham/mtg-kc) Python API, which abstracts SHACL/SPARQL behind domain-typed operations.

The Storage and Schema phases are identical to Experiment 12. Only the Verification concern changes.

## Why This Matters

The mtg-kc Python API is a proxy for how a KerML or SysML v2 verification service would work:

| mtg-kc (this experiment) | KerML/SysML v2 (future) |
| --- | --- |
| `build_mtg_schema()` — constructs schema in Python | KerML compiler — parses and validates metamodel |
| `KnowledgeComplex.add_vertex/add_edge/add_face()` — validates on write | SysML v2 element creation with compiler checks |
| `ValidationError` — domain-typed error | Compiler error with element-level diagnostics |
| `kc.query("faces_by_edge_pattern")` — named domain queries | SysML v2 API queries with domain semantics |
| SHACL/SPARQL hidden behind public API | Compiler internals hidden behind service API |

The key insight: when ontologies are modular and reusable, the SHACL and SPARQL can be **abstracted away**. The verification service exposes domain concepts (Color, ColorPair, ColorTriple), not constraint violation reports. This is the same abstraction boundary a production KerML/SysML v2 service would present.

## How Verification Works

The verify.py script implements a **reconstruct + compare** strategy:

1. **Fetch** all triples from a Flexo branch via SPARQL CONSTRUCT
2. **Extract** structured data: which elements are in the complex, their types, boundaries, and attributes
3. **Reconstruct** using the KC API:
   - `build_mtg_schema()` — get the schema (no .ttl files needed)
   - `KnowledgeComplex(schema)` — create an empty complex
   - `add_vertex()`, `add_edge()`, `add_face()` — add elements in topological order
   - Each add triggers SHACL validation internally; `ValidationError` on failure
4. **Detect orphans**: triples in Flexo for elements NOT in the complex (data residue from conflicts)
5. **Run named queries**: `vertices`, `edges_by_disposition`, `faces_by_edge_pattern`

rdflib is used only for parsing the Flexo HTTP response — all validation and analysis goes through the KC public API.

## Prerequisites

- `mtg-kc` installed: `pip install -e /path/to/mtg-kc`
- A Bearer token for `try-layer1.starforge.app`
- `curl` on PATH

## Running

```bash
export FLEXO_TOKEN="eyJhbGci..."
cd experiments/experiment-13
./run.sh
```

## Expected Results

| Branch | Storage | KC Reconstruction | Orphans | Verdict |
| --- | --- | --- | --- | --- |
| master (ancestor) | Accepted | PASS (25 elements) | NONE | **PASS** |
| branch-a (commit u) | Accepted | PASS (21 elements) | NONE | **PASS** |
| branch-b (commit v) | Accepted | PASS (25 elements) | NONE | **PASS** |
| branch-uv (u then v) | Accepted | PASS (21 elements) | **4 orphans** (BG, BRG) | **FAIL** |
| branch-vu (v then u) | Accepted | PASS (21 elements) | NONE | **PASS** |

The orphans on branch-uv are properties added by commit v to elements (BG, BRG) that commit u already removed from the complex. The KC API reconstructs the complex without these elements — the orphaned triples are detected as the gap between what Flexo stores and what the KC framework accepts.

branch-vu has no orphans because commit u's wildcard DELETE cleaned up commit v's additions.

## File Manifest

| File | Concern | Description |
| --- | --- | --- |
| `run.sh` | Orchestrator | Drives all three concerns |
| `verify.py` | Verification | KC Python API: reconstruct + compare + named queries |
| `ontology/` | Schema | Symlink to exp-12 ontology packages (loaded into Flexo) |
| `instance/ancestor-model.ttl` | Storage | Pure instance data (symlink) |
| `commits/*.ru` | Storage | SPARQL UPDATE patches (symlinks) |
| `requirements.txt` | — | Python dependencies |
