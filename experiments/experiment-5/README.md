# Experiment 5 — MTG Knowledge Complex: Structural Conflict (Remote Flexo REST API)

## What is being tested

Can the SysML v2 REST API store **non-SysML (MTG) elements** as JSON and detect the same structural conflicts as the SPARQL-based Experiments 3–4?

This bridges two dimensions: non-SysML model (from Experiments 3–4) and remote REST API (from Experiment 2).

## How

Same structural conflict scenario as Experiments 3–4:
- **Curator A** (commit u): Removes BG (Golgari) edge + dependent faces (WBG, UBG, BRG)
- **Curator B** (commit v): Enriches BG and BRG with new gameplay properties

Model elements are flattened to JSON and stored via the SysML v2 REST API. Constraints are evaluated in Python (client-side), mirroring Experiment 2's approach.

## Directory Contents

```
experiment-5/
├── README.md
├── run.py                 ← main experiment script
├── model.py               ← MTG elements as JSON + commit operations
├── oracle.py              ← constraint checks in Python
└── requirements.txt
```

### File Mapping Across Experiments

| Experiment 3 (SPARQL) | Experiment 5 (REST) | Purpose |
| --- | --- | --- |
| `run.sh` (bash/curl) | `run.py` (Python/requests) | Orchestration |
| `ancestor-model.ttl` | `model.py: ANCESTOR_ELEMENTS` | Initial state |
| `commit-u-remove-bg.ru` | `model.py: apply_commit_u()` | Curator A's changes |
| `commit-v-enrich-bg.ru` | `model.py: apply_commit_v()` | Curator B's changes |
| `oracle/*.rq` | `oracle.py` | Constraint evaluation |

## Prerequisites

- Python 3.8+, `requests` library
- `FLEXO_BEARER_TOKEN` environment variable

## Quick Start

```bash
pip install requests
export FLEXO_BEARER_TOKEN="eyJhbGci..."
python3 run.py --cleanup
```

## Expected Results

Should match Experiments 3–4:

| Stage | C1 orphaned | C2 closure | C3 membership | C4 edges |
| --- | --- | --- | --- | --- |
| master | satisfied | satisfied | 5 Color, 10 ColorPair, 10 ColorTriple | 10 |
| branch-a | satisfied | satisfied | 5 Color, 9 ColorPair, 7 ColorTriple | 9 |
| branch-b | satisfied | satisfied | 5 Color, 10 ColorPair, 10 ColorTriple | 10 |
| branch-uv | **orphaned (BG, BRG)** | satisfied | 5 Color, 9 ColorPair, 7 ColorTriple | 9 |
| branch-vu | satisfied | satisfied | 5 Color, 9 ColorPair, 7 ColorTriple | 9 |

Non-commutativity: branch-uv has orphans, branch-vu does not (same as Experiments 3–4).

## Actual Results

The REST API reveals a fundamentally different behavior than SPARQL:

| Stage | C1 orphaned | C2 closure | C3 membership | C4 edges |
| --- | --- | --- | --- | --- |
| master | satisfied | satisfied | 5/10/10 | 10 |
| branch-a | **BG, WBG, UBG, BRG orphaned** | satisfied | 5/9/7 | 9 |
| branch-b | satisfied | satisfied | 5/10/10 | 10 |
| branch-uv | **BG, WBG, UBG, BRG + v's stubs** | satisfied | 5/9/7 | 9 |
| branch-vu | **BG, WBG, UBG, BRG (with v's enrichments)** | satisfied | 5/9/7 | 9 |

### Key difference from Experiments 3–4

The SysML v2 REST API **does not support element deletion** — it only supports element replacement. When commit u removes BG/WBG/UBG/BRG from the complex membership list, the elements themselves still exist in the commit history. The API's element inheritance means elements persist across commits unless explicitly overwritten.

This means:
- **branch-a already has orphans** — the elements exist but aren't in the membership list
- **Both orderings show orphans** — unlike the SPARQL experiment where branch-vu was clean
- **branch-uv** has duplicate orphaned BG/BRG entries (original + v's stubs)
- **branch-vu** has enriched orphans (v's properties merged into the original elements)

### Non-commutativity

The non-commutativity is still present but manifests differently: both orderings have orphans, but with different property sets. In SPARQL (Experiment 3), the v-then-u ordering produced a clean state because `DELETE WHERE` could remove all triples. In REST, there's no equivalent of DELETE — orphans persist regardless of order.

## Non-SysML Model on a SysML v2 API: Evaluation

The MTG Knowledge Complex is not a SysML v2 model. It uses custom `@type` values (`Color`, `ColorPair`, `ColorTriple`, `Complex`) and custom properties (`goal`, `guild`, `boundedBy`, `members`, `thematic_triad`, etc.) that have no counterpart in the SysML v2 metamodel. This experiment directly tests how the API handles that mismatch.

### How the API handles non-SysML types

We tested storing elements with a range of `@type` values:

| `@type` value | Category | Stored? | Properties preserved? |
| --- | --- | --- | --- |
| `PartDefinition` | Standard SysML v2 | Yes | Yes |
| `Color`, `ColorPair`, `Complex` | KC domain types | Yes | Yes |
| `UnicornDefinition` | Completely fabricated | Yes | Yes (including `hornLength: 42`) |
| *(omitted)* | No `@type` at all | Yes (`@type: null`) | Yes |

### Key finding: the API is type-agnostic

The SysML v2 REST API on this Flexo instance performs **no schema validation** whatsoever on element `@type` or properties. It is functionally a **generic versioned JSON document store** that uses SysML v2 REST conventions (projects, branches, commits) for version management. Specifically:

- **No type enforcement** — Any string (or null) is accepted for `@type`. There is no SysML v2 metamodel validation.
- **No property validation** — Custom properties of any name, type, or structure are stored and returned as-is. Arrays, strings, numbers all work.
- **No `@id` prefix handling** — The `@id` field is treated as a plain string, but the `mtg:` prefix is stripped (stored as `White` not `mtg:White`). This is the only transformation applied.
- **No relationship enforcement** — Properties like `boundedBy` (lists of element references) are stored as plain arrays of strings with no referential integrity checking.

### Implications for non-SysML models on Flexo

This type-agnostic behavior means the SysML v2 REST API can serve as a **general-purpose versioned knowledge store** for arbitrary models — not just SysML. However, the tradeoff is significant:

1. **No server-side semantic validation** — All constraint checking must happen client-side. The API won't reject an invalid model state.
2. **No element deletion** (confirmed via 5 different approaches — see above) — This makes structural removal operations impossible at the API level. The only workaround is application-level membership tracking (as we do with `mtg:_complex.members`).
3. **No query capabilities** — No SPARQL, no filtering. You must fetch all elements and filter client-side.
4. **`@id` prefix stripping** — The API silently removes namespace prefixes from `@id` values, which can cause mismatches between stored IDs and references in other properties (e.g., `members` list retains `mtg:` but `@id` does not).

### Where does validation actually run?

In this experiment, **all constraint checking happens client-side**. The server contributes nothing to validation:

| Concern | Experiments 1, 3, 4 (SPARQL) | Experiments 2, 5 (REST) |
| --- | --- | --- |
| Data storage | Server (Fuseki quadstore) | Server (Flexo element store) |
| Version control | Server (branches, commits) | Server (branches, commits) |
| **Constraint evaluation** | **Server** (SPARQL SELECT queries execute inside Fuseki) | **Client** (Python fetches all elements, evaluates locally) |
| **Query filtering** | **Server** (SPARQL WHERE clauses) | **Client** (Python loops over full element list) |

This is a meaningful architectural difference. In the SPARQL experiments, the oracle queries are pushed to the server and only violations are returned — the server is doing semantic work. In the REST experiments, the server is a dumb versioned store and all intelligence lives in the client. The `Complex.members` list, the orphan checks, the boundary closure validation — all of that is our application-level logic, not anything the Flexo REST API provides or enforces.

In summary: the API is **permissive enough** to store any model, but **too limited** to enforce or query that model's semantics. The SysML v2 API layer adds version control (branching, commits, element inheritance) but not schema awareness.

## What We Learned

1. **The SysML v2 REST API is type-agnostic** — It stores any `@type` and any properties without validation. It is effectively a generic versioned JSON document store with SysML v2 REST conventions.
2. **No element deletion** — Confirmed via 5 different approaches (`DELETE` endpoint, empty payload, null payload, `delete` flag, omission). Elements persist through all subsequent commits via inheritance. This is a fundamental limitation for modeling structural removal.
3. **Orphan behavior differs from SPARQL** — SPARQL's wildcard `DELETE WHERE` can remove all triples for a subject; REST element replacement cannot. This changes the conflict signature: both orderings produce orphans (unlike Experiment 3 where only one ordering did).
4. **`@id` prefix stripping** — The API silently strips namespace prefixes from `@id`, creating a mismatch with references in other properties. Client code must normalize both sides.
5. **Membership-based constraint checking works** — Despite the deletion limitation, tracking membership in a container element (`Complex.members`) enables conflict detection at the application level.
6. **Accessibility preserved** — Non-SysML conflict detection works without Docker, SPARQL, or RDF knowledge, though results are not identical to the SPARQL-based experiments due to the API's limitations.
