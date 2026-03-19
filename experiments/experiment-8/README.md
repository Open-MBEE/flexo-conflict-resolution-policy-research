# Experiment 8 — MTG-KC Model: Deletion Validation (non-SysML types)

## What is being tested

Does identity-only commit deletion work for elements with **non-SysML `@type` values** (Color, ColorPair, Complex)? This is the counterpart to Experiment 7 (which tested SysML v2 types).

## How

**Phase 1:** Validate deletion by committing 4 MTG-KC elements (`@type: Color`, `@type: ColorPair`, `@type: Complex`), then deleting one via identity-only commit.

**Phase 2:** (Only runs if Phase 1 passes) Re-run the MTG-KC structural conflict scenario with proper deletion.

## Results

### Phase 1: Deletion FAILS for non-SysML types

```
Before: [BG, Black, White, _complex]
After:  [BG, Black, White, _complex]
✗ FAIL: BG (ColorPair) was NOT deleted
```

The identity-only commit returned HTTP 200 (success) but the element persists. **Deletion silently fails for non-SysML `@type` values.**

Phase 2 was skipped because Phase 1 failed.

## Key Finding: Deletion is Type-Dependent

| `@type` | Deletion works? | Experiment |
| --- | --- | --- |
| `PartDefinition` (SysML v2) | **Yes** | Experiment 7 |
| `Color` (non-SysML) | **No** | Experiment 8 |
| `ColorPair` (non-SysML) | **No** | Experiment 8 |
| `Complex` (non-SysML) | Not tested (but likely no) | — |

This reveals that the Flexo server's SysML v2 REST API is **not fully type-agnostic** despite storing arbitrary types. The deletion mechanism (identity-only commits) is gated by the SysML v2 semantic layer:

- **Storage** is type-agnostic — any `@type` and properties are accepted and stored
- **Deletion** is type-aware — only recognized SysML v2 types are processed by the deletion logic

The server returns HTTP 200 for the deletion commit even when it has no effect, providing no feedback that the deletion was silently skipped. This is a potential footgun for applications using non-SysML types.

## Implications

1. **Experiment 5's orphan problem is inherent** — For non-SysML models on the REST API, elements cannot be deleted. The membership-based tracking workaround from Experiment 5 is the only option.
2. **The semantic layer selectively engages** — Flexo's SysML v2 layer doesn't validate types on write, but does gate certain operations (deletion) based on type recognition.
3. **Silent failure is dangerous** — HTTP 200 on a no-op deletion gives false confidence. Applications must verify deletion by re-fetching elements.

## Comparison Across Deletion Experiments

| Aspect | Exp 3 (SPARQL) | Exp 5 (REST, no deletion) | Exp 7 (REST, SysML deletion) | Exp 8 (REST, non-SysML deletion) |
| --- | --- | --- | --- | --- |
| Deletion mechanism | `DELETE WHERE` | N/A (membership only) | Identity-only commit | Identity-only commit |
| Works for SysML types | Yes | N/A | **Yes** | N/A |
| Works for non-SysML types | Yes | N/A | N/A | **No** |
| Orphan behavior | Non-commutative | Both orderings have orphans | Deletion is reversible | Falls back to Exp 5 |
