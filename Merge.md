# Merge

Integrating changes from one branch into another. In Flexo MMS, merge is the operation where concurrent modifications must be reconciled — and where the [[Flexo Conflict Resolution Mapping|conflict resolution formalism]] applies.

## Current State of Implementation

### Layer 1: No Merge Endpoint

The Layer 1 service does **not** have an explicit merge endpoint. The primitive operations are:

- **Commit** (`POST .../branches/{branchId}/update`) — applies a SPARQL UPDATE to the branch head, creating a new commit with the branch's current head as parent
- **Branch creation** (`PUT .../branches/{branchId}`) — creates a new branch from any ref or commit, materializing a snapshot if necessary

Branch creation handles snapshot reconstruction (replaying deltas from an ancestor snapshot), but it does not perform three-way merge or conflict detection between divergent histories.

### SysML v2 PSM: Merge Endpoint (Stub)

The SysML v2 service defines a merge endpoint per the OMG specification:

**`POST /projects/{projectId}/branches/{targetBranchId}/merge`**

| Parameter | Type | Description |
|-----------|------|-------------|
| `sourceCommitId` | query, required | Comma-separated UUIDs of source commits |
| `description` | query, optional | Merge commit description |
| Request body | `Data[]` or null | Conflict resolutions provided by client |

**Responses**:
- **201 Created** — merge commit (no conflicts)
- **409 Conflict** — array of `DataIdentity` objects identifying conflicting elements
- **404 Not Found** — project, branch, or commit not found

**Current status**: The implementation in `DiffMergeApi.kt` is auto-generated scaffolding that returns placeholder data. The actual merge logic — finding a common ancestor, computing a three-way diff, detecting conflicts, and applying resolutions — is **not yet implemented**.

## What a Merge Would Need to Do

Based on the data model documented in [[Quadstore]] and [[Diff and Delta]]:

1. **Find common ancestor** — the most recent commit reachable from both the source and target branch heads (the merge base)
2. **Compute two diffs** — source vs ancestor and target vs ancestor
3. **Detect conflicts** — triples (or elements) modified in both diffs
4. **Apply non-conflicting changes** — combine the two diffs where they don't overlap
5. **Resolve or surface conflicts** — either apply a resolution [[Policy]] or return conflicts to the client
6. **Create merge commit** — a new commit on the target branch with (at minimum) two parents

### Structural Gaps

Several aspects of this process are not yet addressed by the existing architecture:

- **Commit DAG**: The current commit model uses a single `mms:parent` property (a linked list). Merge commits require multiple parents to preserve lineage. The data model would need to support this.
- **Three-way diff**: The existing diff is a two-way set difference between named graphs. A three-way diff (ancestor, source, target) requires computing two diffs and correlating them — this algorithm is not documented or implemented.
- **Conflict representation**: The SysML v2 API returns conflicting element identities but no conflict type or context. A merge implementation would need richer conflict descriptions.
- **Snapshot during merge**: It is unclear how snapshot materialization interacts with merge. Both the source commit and the ancestor commit must be materialized to compute diffs.

## Concurrency Control

The Layer 1 service uses **optimistic concurrency control** to prevent lost updates on a single branch:

- **ETags**: Every branch has an `mms:etag`. Clients send `If-Match` headers; mismatches return 412 Precondition Failed.
- **Transaction mutex**: `createBranchModifyingTransaction()` prevents concurrent modifications to the same branch via a mutex lock (409 Conflict if blocked).
- **Guarded patches**: The `guardedPatch()` function supports WHERE-clause preconditions — if the state the client assumed no longer holds, the patch fails with 412.

This prevents concurrent *writes to the same branch* but does not address the *merge of divergent branches* — which is the domain of the [[Flexo Conflict Resolution Mapping|conflict resolution formalism]].

## State Transition Semantics

The merge operation can be specified as a state transition with pre- and post-conditions (the [[Key Insight]] develops why this framing — commits as control inputs, model states as state variables — is necessary for structured models):

**Pre-conditions:**

- Branch $B_{\text{target}}$ points to $\text{commit}_t$ with snapshot $G_t$ materialized
- Source commit $\text{commit}_s$ is identified (on source branch or by ID)
- A common ancestor $\text{commit}_{\text{base}} = \text{LCA}(\text{commit}_t, \text{commit}_s)$ exists

**Post-conditions (success):**

- Branch $B_{\text{target}}$ points to $\text{commit}_{\text{merge}}$
- $\text{commit}_{\text{merge}}.\text{parents} = \{\text{commit}_t, \text{commit}_s\}$
- $\text{snapshot}(\text{commit}_{\text{merge}}) = \text{merge}(G_t, G_s, G_{\text{base}})$
- $\text{snapshot}(\text{commit}_{\text{merge}})$ is materialized

**Post-conditions (conflict):**

- Branch $B_{\text{target}}$ is unchanged
- A set of conflicting element identities is returned to the client

**Invariant:** The target branch always has a materialized snapshot — whether merge succeeds or fails.

## Open Questions

- **Merge commit parents**: How should multiple parents be represented in the metadata graph? Extend `mms:parent` to allow multiple values, or introduce a separate predicate?
- **Merge base algorithm**: How is the common ancestor found in a DAG? Standard algorithms (e.g., lowest common ancestor) apply, but the current linked-list commit model must first support branching history.
- **Delta composition**: Can two deltas from a common ancestor be composed? The current delta format (SPARQL UPDATE strings) is procedural — composing two arbitrary SPARQL UPDATEs is non-trivial.
- **Atomicity**: Must the entire merge succeed or fail atomically? What happens if the merge commit is partially applied? 
	- Or could the unit be a custom defined entity. E.g. a part definition consists of hundreds of triples. 
- **Resolution as input**: The SysML v2 API allows the client to supply `Data[]` as conflict resolutions. How does this interact with automated [[Policy]]-based resolution?

## References

- [flexo-mms-layer1-service](https://github.com/Open-MBEE/flexo-mms-layer1-service) — `BranchWrite.kt`, `ModelCommit.kt`
- [flexo-mms-sysmlv2 OpenAPI](https://github.com/Open-MBEE/flexo-mms-sysmlv2) — merge endpoint schema
- [Commits, Refs and Snapshots](https://openmbee.atlassian.net/wiki/spaces/OPENMBEE/pages/613613569) — OpenMBEE Confluence

---
← [[Model]] · [[Diff and Delta]] · [[Conflict Classification]] · [[Flexo Conflict Resolution Mapping]] · [[Key Insight]]
