# Experiments — Conflict Resolution in Flexo MMS

This directory contains 13 experiments that progressively investigate how Flexo MMS handles merge conflicts across different API layers, model types, and architectural patterns. The experiments start with a concrete engineering scenario, generalize to arbitrary knowledge graphs, discover API-layer limitations, and culminate in a three-layer service architecture that separates storage, schema, and verification concerns.

## Experiment Index

| # | Name | API | Model | Key Question | Log |
| --- | --- | --- | --- | --- | --- |
| 1 | [Satellite (local SPARQL)](experiment-1/) | Local Layer 1 | Satellite (SysML) | Baseline: can Flexo detect merge conflicts? | [log](experiment-1/run-output-20260303.log) |
| 2 | [Satellite (remote REST)](experiment-2/) | Remote SysML v2 REST | Satellite (SysML) | Same conflicts via REST API? | [log](experiment-2/run-output-20260318.log) |
| 3 | [MTG-KC instance (local SPARQL)](experiment-3/) | Local Layer 1 | MTG-KC (OWL) | Can Flexo handle non-SysML RDF? | [log](experiment-3/run-output-20260318.log) |
| 4 | [MTG-KC + schema (local SPARQL)](experiment-4/) | Local Layer 1 | MTG-KC + OWL/SHACL | Does Flexo preserve schema triples? | [log](experiment-4/run-output-20260318.log) |
| 5 | [MTG-KC (remote REST)](experiment-5/) | Remote SysML v2 REST | MTG-KC (JSON) | REST API with non-SysML types? | [log](experiment-5/run-output-20260318.log) |
| 6 | [MTG-KC (REST + RDF bridge)](experiment-6/) | Remote REST + pyshacl | MTG-KC (JSON↔RDF) | Can we bridge RDF validation onto REST? | [log](experiment-6/run-output-20260318.log) |
| 7 | [Deletion validation (SysML)](experiment-7/) | Remote SysML v2 REST | Satellite (SysML) | Does identity-only deletion work? | [log](experiment-7/run-output-20260318.log) |
| 8 | [Deletion validation (non-SysML)](experiment-8/) | Remote SysML v2 REST | MTG-KC (non-SysML) | Is deletion type-dependent? | [log](experiment-8/run-output-20260318.log) |
| 9 | [Satellite (remote SPARQL)](experiment-9/) | Remote Layer 1 | Satellite (SysML) | Remote SPARQL matches local? | [log](experiment-9/run-output-20260318.log) |
| 10 | [MTG-KC instance (remote SPARQL)](experiment-10/) | Remote Layer 1 | MTG-KC (OWL) | Remote SPARQL matches local for non-SysML? | [log](experiment-10/run-output-20260318.log) |
| 11 | [MTG-KC + schema (remote SPARQL)](experiment-11/) | Remote Layer 1 | MTG-KC + OWL/SHACL | Remote SPARQL preserves schema? | [log](experiment-11/run-output-20260318.log) |
| 12 | [Three-layer architecture](experiment-12/) | Local Layer 1 | MTG-KC | Where does each concern live? | [log](experiment-12/run-output-20260318.log) |
| 13 | [KC Python API verification](experiment-13/) | Remote Layer 1 | MTG-KC via KC API | Can domain APIs abstract verification? | [log](experiment-13/run-output-20260318.log) |

## Narrative Arc

### Stage 1: Baseline — Satellite Power Subsystem (Experiments 1–2)

Two teams independently modify a satellite's communications and thermal subsystems. Each change is individually valid, but combined they violate power budgets, bus load limits, and ownership constraints. Experiment 1 runs this on a local Flexo SPARQL instance; Experiment 2 repeats it on a remote SysML v2 REST API.

**Finding:** Both APIs detect identical conflicts (C2 power +5, C3 bus +5, C6 dual owners, name multiplicity). Conflicts are **commutative** — both application orderings produce the same violations. The conflict is inherent to the model, not the API.

### Stage 2: Generalization — Non-SysML Models (Experiments 3–4)

The satellite model uses SysML-style properties. Can Flexo handle arbitrary RDF? We load the MTG Knowledge Complex — an OWL simplicial complex with 25 elements (5 colors, 10 color pairs, 10 color triples) and topological constraints (boundary-closure, cardinality).

The conflict scenario: one curator removes the Black-Green (Golgari) edge and its dependent faces; another curator enriches that same edge with new properties. Individually valid; combined, the enrichment creates **orphaned triples** — properties on elements that no longer exist in the complex.

**Finding:** Flexo handles arbitrary RDF. But unlike the satellite scenario, this conflict is **non-commutative**: applying delete-then-enrich produces orphans, while enrich-then-delete is clean (SPARQL's wildcard DELETE catches everything). Non-commutativity is itself a conflict signal — the order of application matters.

Experiment 4 adds OWL ontology and SHACL shapes alongside instance data. Flexo preserves them, and schema-aware queries (type consistency, shape target coverage) track structural changes correctly. However, Flexo does **not** run an OWL reasoner — `rdfs:subClassOf` inference doesn't happen server-side.

### Stage 3: API Layer Comparison (Experiments 5–6)

The same MTG-KC structural conflict on the SysML v2 REST API reveals fundamental differences from SPARQL.

**Experiment 5 findings:**
- The REST API is **type-agnostic** — it stores any `@type` and any properties without validation. It functions as a generic versioned JSON document store.
- The REST API has **no native element deletion** — elements persist through commits via inheritance. At the time of this experiment, we had not yet discovered the identity-only commit workaround (see Experiments 7–8). Without deletion, both orderings produce orphans (unlike SPARQL where only one does).
- All constraint checking happens **client-side** — the server contributes nothing to validation.
- The API silently strips namespace prefixes from `@id` values, creating a mismatch between stored IDs and references.

**Experiment 6** layers RDF-native validation (pyshacl + rdflib) on top of the REST API via a JSON↔RDF bridge. The bridge works — SPARQL queries produce identical results client-side — but SHACL baseline violations (from incomplete JSON models) mask conflict-specific signals.

### Stage 4: Deletion Semantics (Experiments 7–8)

We discovered that element deletion IS possible via **identity-only commits** — a pattern from the `flexo_syside` library where a commit's `change` array contains `{"identity": {"@id": "elem-id"}}` with no `payload` key.

**Experiment 7:** Deletion works for SysML v2 types (`PartDefinition`). Deletion is reversible — a subsequent commit can re-create the element.

**Experiment 8:** Initially appeared to fail for non-SysML types, leading to a (wrong) conclusion that deletion was type-dependent. Root cause analysis revealed an **`@id` prefix mismatch**: the API strips `mtg:` from IDs on storage but requires the original prefix for deletion. After fixing the client code, deletion works for all types. With proper deletion, the REST API produces the **same non-commutative conflict signature as SPARQL** (Experiment 3).

### Stage 5: Remote Infrastructure Validation (Experiments 9–11)

Experiments 1, 3, and 4 ran against a local Flexo instance under QEMU emulation. Experiments 9–11 repeat them against a hosted Layer 1 SPARQL endpoint at `try-layer1.starforge.app`.

**Finding:** Results are identical to their local counterparts. The remote service experienced a transient outage (HTTP 504) during testing but recovered. When operational, the remote Layer 1 is functionally equivalent to the local instance — and significantly faster without QEMU overhead.

### Stage 6: Three-Layer Architecture (Experiments 12–13)

The preceding experiments implicitly separated three concerns. Experiment 12 makes the pattern explicit:

```
Layer 3 — VERIFICATION (closed-world constraint checking)
  What is admissible to express. SHACL shapes + SPARQL oracle
  restrict the space of valid states — reject what violates constraints.

Layer 2 — SEMANTIC (open-world ontology packages)
  What can be expressed. OWL classes, properties, and restrictions
  define the vocabulary — anything not contradicted is permitted.

Layer 1 — SYNTACTIC (quadstore)
  What is well-formed. Accepts any valid RDF triples regardless
  of interpretation.
```

Layer 1 accepts any syntactically valid RDF — well-formed triples with valid URIs, literals, and blank nodes. It enforces RDF syntax but is indifferent to semantic interpretation: orphaned properties, violated cardinality constraints, and broken boundary-closure are all syntactically valid RDF that Layer 1 stores without complaint. Only Layer 3, which loads the ontology packages and runs SHACL validation and SPARQL constraint queries, can determine whether a state is semantically valid according to the domain model. The ontology is split into composable packages (kc-core + mtg-domain) that mirror how KerML and SysML v2 domain extensions would be structured.

**Experiment 13** replaces raw pyshacl/SPARQL with the [mtg-kc Python API](https://github.com/mzargham/mtg-kc), which abstracts SHACL and SPARQL behind domain-typed operations (`add_vertex`, `add_edge`, `add_face`, `ValidationError`). This previews how a KerML/SysML v2 verification service would work: the constraint machinery is hidden behind a public API that exposes domain concepts, not violation reports.

## Cross-Cutting Findings

### Commutativity

| Scenario | API | Commutative? | Notes |
| --- | --- | --- | --- |
| Satellite (Exp 1, 2, 9) | SPARQL, REST | **Yes** | Both orderings produce identical numeric violations |
| MTG-KC (Exp 3, 4, 10, 11) | SPARQL | **No** | delete→enrich has orphans; enrich→delete is clean |
| MTG-KC (Exp 5) | REST (no deletion) | **No** | Both orderings have orphans (API limitation) |
| MTG-KC (Exp 8) | REST (with deletion) | **No** | Matches SPARQL behavior after @id bugfix |

Non-commutativity is a richer conflict signal than simple value disagreement. It indicates that the merge result depends on application order — a property that conflict resolution policies must account for.

### API Comparison

| Capability | Layer 1 SPARQL | SysML v2 REST |
| --- | --- | --- |
| Type validation | None (stores any RDF) | None (stores any JSON) |
| Constraint evaluation | Server-side (SPARQL SELECT) | Client-side only |
| Element deletion | `DELETE WHERE` (native, thorough) | Identity-only commit (not native — workaround discovered in Exp 7–8) |
| Query capabilities | Full SPARQL | None (fetch all, filter client-side) |
| Schema storage | Preserves OWL/SHACL triples | Not applicable (JSON) |
| `@id` handling | Preserves URIs | Strips namespace prefixes |
| OWL reasoning | No | No |

### Key Discoveries

1. **Conflicts are model-semantic, not API-dependent** — the same model produces the same conflicts regardless of whether SPARQL or REST is used for storage and querying. But the API *does* change the conflict signature (orphan residue patterns differ).

2. **The SysML v2 REST API is a generic JSON document store** — it accepts any `@type`, any properties, no validation. The "SysML v2" in its name describes its REST conventions, not its type enforcement.

3. **Deletion is possible but not native** — the REST API has no DELETE endpoint for elements. Deletion is achieved via a workaround: identity-only commits (no `payload` key, just `identity`), discovered by reading the `flexo_syside` library source code. Works for all types, but requires the original `@id` (before prefix stripping). Not documented in the API surface.

4. **The `@id` prefix asymmetry** — the API silently strips namespace prefixes on storage but matches against originals for deletion. This caused a bug that initially appeared type-dependent (Exp 8 changelog).

5. **Three-layer separation is natural** — storage (any valid RDF), schema (modular ontology packages), and verification (SHACL + SPARQL) can be cleanly separated. Layer 1 accepts invalid states; only Layer 3 rejects them.

6. **Domain APIs can abstract verification** — the KC Python API hides SHACL/SPARQL behind typed operations, previewing how a production KerML/SysML v2 verification service would work.

## How to Reproduce

### Prerequisites

- **Local experiments (1, 3, 4, 12):** Docker/Colima with 12+ GB RAM, local [flexo-mms-deployment](https://github.com/Open-MBEE/flexo-mms-deployment) running
- **Remote REST experiments (2, 5, 6, 7, 8):** `FLEXO_BEARER_TOKEN` env var with token for `experimental.starforge.app`
- **Remote SPARQL experiments (9, 10, 11, 13):** `FLEXO_TOKEN` env var with token for `try-layer1.starforge.app`
- **Python experiments (2, 5, 6, 7, 8, 12, 13):** Python 3.8+, `pip install requests rdflib pyshacl`
- **All bash experiments:** `curl` and `python3` on PATH

### Environment Variables

```bash
# For remote SysML v2 REST API (experimental.starforge.app)
export FLEXO_BEARER_TOKEN="eyJhbGci..."

# For remote Layer 1 SPARQL API (try-layer1.starforge.app)
export FLEXO_TOKEN="eyJhbGci..."
```

### Suggested Run Order

Local SPARQL experiments require restarting the Flexo stack between runs for clean state:

```bash
cd ~/Documents/GitHub/flexo-mms-deployment/docker-compose
docker compose down && docker compose up -d
# Wait ~60s for Fuseki to initialize
```

1. **Exp 1** → baseline satellite (local SPARQL)
2. **Exp 2** → same scenario, remote REST
3. **Exp 3** → MTG-KC structural conflict (restart Flexo first)
4. **Exp 4** → same + schema (restart Flexo first)
5. **Exp 5–6** → REST API comparison (no restart needed)
6. **Exp 7–8** → deletion validation (no restart needed)
7. **Exp 9–11** → remote SPARQL validation
8. **Exp 12** → three-layer architecture (restart Flexo first)
9. **Exp 13** → KC API verification

## Note on the Knowledge Complex Model

The MTG Knowledge Complex used in Experiments 3–13 is a **toy model** built on a general-purpose [Knowledge Complex (KC) framework](https://github.com/mzargham/mtg-kc). The KC framework enforces canonical mathematical definitions of simplicial complexes — vertices, edges, and faces with boundary operators, cardinality constraints, and closure properties — then extends these abstract topological objects with domain-specific types and attributes. The MTG color wheel (5 colors, 10 color pairs, 10 color triples) serves as a small, self-contained instance for testing.

The KC model family itself (distinct from the MTG toy ontology) is used for scaffolding large knowledge graphs for use with LLMs, where explicit query languages (SPARQL) and constraint enforcement (SHACL) increase auditability and determinism in knowledge retrieval and reasoning. A paper on this approach is forthcoming at INCOSE IS 2026.
