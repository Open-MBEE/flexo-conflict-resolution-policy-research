# Experiment 8 — MTG-KC Model: Deletion Validation (non-SysML types)

## What is being tested

Does identity-only commit deletion work for elements with **non-SysML `@type` values** (Color, ColorPair, Complex)? This is the counterpart to Experiment 7 (which tested SysML v2 types).

## How

**Phase 1:** Validate deletion by committing 4 MTG-KC elements (`@type: Color`, `@type: ColorPair`, `@type: Complex`), then deleting one via identity-only commit.

**Phase 2:** (Only runs if Phase 1 passes) Re-run the MTG-KC structural conflict scenario with proper deletion.

## Initial Result: Deletion appeared to fail

```
Before: [BG, Black, White, _complex]
After:  [BG, Black, White, _complex]
✗ FAIL: BG (ColorPair) was NOT deleted
```

Phase 2 was skipped.

## Root Cause Analysis: @id Prefix Mismatch (NOT type-dependent)

Follow-up testing revealed the failure was **not caused by `@type`**. It was caused by an **`@id` prefix mismatch**:

| @id submitted | @id stored (API strips prefix) | @id used for deletion | Result |
| --- | --- | --- | --- |
| `"mtg:BG"` | `"BG"` | `"BG"` (stripped) | **FAIL** — no match |
| `"mtg:BG"` | `"BG"` | `"mtg:BG"` (original) | **SUCCESS** — deleted |
| `"CommSubsystem"` (no prefix) | `"CommSubsystem"` | `"CommSubsystem"` | **SUCCESS** (Exp 7) |

The API silently strips namespace prefixes from `@id` on storage, but the deletion mechanism matches against the **original** `@id` (before stripping). Our experiment code used the stripped version, which didn't match.

### Confirmed: deletion is type-agnostic

Additional testing with a mix of SysML and non-SysML types proved that **deletion works for all types** when the correct `@id` is used:

```
Before: [sysml-1 (PartDefinition), sysml-2 (Package), custom-1 (Color), custom-2 (UnicornDefinition)]
After:  (empty — all 4 deleted)
```

The Flexo server is fully type-agnostic for both storage and deletion.

### The @id prefix problem

The SysML v2 REST API has asymmetric `@id` handling:

1. **On INSERT:** `@id: "mtg:BG"` is accepted and stored
2. **On GET:** the prefix is stripped → returned as `@id: "BG"`
3. **On DELETE (identity-only):** requires the ORIGINAL `@id: "mtg:BG"` — the stripped version `"BG"` silently fails

This asymmetry means client code must remember the original `@id` values, since the API returns stripped versions that can't be used for deletion.

### Code references

The `@id` is processed in [CommitApi.kt](https://github.com/Open-MBEE/flexo-mms-sysmlv2/blob/main/src/main/kotlin/org/openmbee/flexo/sysmlv2/apis/CommitApi.kt). All `@type` values are mapped to the SysML namespace via `SYSMLV2.type()` in [Namespaces.kt](https://github.com/Open-MBEE/flexo-mms-sysmlv2/blob/main/src/main/kotlin/org/openmbee/flexo/sysmlv2/Namespaces.kt):

```kotlin
val VOCABULARY = "https://www.omg.org/spec/SysML#"
fun type(type: String): Resource = ResourceFactory.createResource("$VOCABULARY$type")
```

This forces `Color` → `<https://www.omg.org/spec/SysML#Color>` in the RDF store, regardless of whether it's a real SysML type. Storage and deletion both use this mapping consistently — the issue is purely in `@id` prefix handling.

## Corrected Finding

| Aspect | Initial conclusion | Corrected conclusion |
| --- | --- | --- |
| Deletion type-dependent? | Yes — only SysML types | **No** — type-agnostic |
| Root cause of failure | Semantic layer gates deletion | **@id prefix mismatch** |
| Silent failure? | Yes — HTTP 200 on no-op | **Yes** — this is still a real problem |

## Phase 2 Results (after bugfix)

With proper deletion using original `@id` values, the results now match Experiment 3 (SPARQL):

| Stage | C1 orphaned | C2 closure | C3 membership | C4 edges |
| --- | --- | --- | --- | --- |
| master | satisfied | satisfied | 5/10/10 | 10 |
| branch-a | satisfied | satisfied | 5/9/7 | 9 |
| branch-b | satisfied | satisfied | 5/10/10 | 10 |
| branch-uv | **BG, BRG orphaned** | satisfied | 5/9/7 | 9 |
| branch-vu | satisfied | satisfied | 5/9/7 | 9 |

Non-commutativity: branch-uv has orphans (v re-creates deleted elements), branch-vu is clean (u deletes everything including v's enrichments). This matches Experiment 3's SPARQL behavior exactly.

## Implications

1. **Experiment 5's orphan problem is solvable** — deletion works for non-SysML types; we just need to use the original `@id` (with prefix)
2. **The API's `@id` stripping is dangerous** — it creates a mismatch between what you store and what you get back, and deletion silently fails when using the stripped version
3. **Client code must preserve original IDs** — cannot rely on `GET /elements` to return IDs usable for deletion
4. **REST API matches SPARQL behavior** — with proper deletion, the conflict signatures are identical across API layers

## Changelog

### v2 (2026-03-18) — Bugfix: @id prefix mismatch

**Bug:** Phase 1 deletion failed silently because the code used the API-stripped `@id` (`"BG"`) instead of the original `@id` (`"mtg:BG"`) for the identity-only deletion commit. The API strips namespace prefixes on GET but matches on the original for DELETE. HTTP 200 is returned even when deletion has no effect, masking the error.

**Root cause:** The comment in the original code said `"API strips mtg: prefix, so delete 'BG' not 'mtg:BG'"` — this was exactly backwards. The deletion endpoint needs the original pre-strip `@id`.

**Fix:** Changed `COMMIT_U_DELETE_IDS` from `["BG", "WBG", "UBG", "BRG"]` to `["mtg:BG", "mtg:WBG", "mtg:UBG", "mtg:BRG"]`, and Phase 1 test from `"BG"` to `"mtg:BG"`.

**Impact:** Phase 1 now passes. Phase 2 runs and produces results matching Experiment 3 (SPARQL). The original conclusion that "deletion is type-dependent" was **wrong** — deletion is type-agnostic; the failure was purely an `@id` mismatch.

### v1 (2026-03-18) — Initial run

Phase 1 failed. Incorrectly concluded that deletion doesn't work for non-SysML `@type` values. Phase 2 was skipped.
