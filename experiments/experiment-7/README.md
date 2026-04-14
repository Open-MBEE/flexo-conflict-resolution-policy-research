# Experiment 7 — Satellite Model: Deletion Validation (SysML v2 types)

## What is being tested

Does identity-only commit deletion work for elements with **SysML v2 `@type` values** (PartDefinition)? What happens when a subsequent commit modifies a deleted element?

## How

**Phase 1:** Validate deletion by committing 4 satellite elements (all `@type: PartDefinition`), then deleting one via identity-only commit.

**Phase 2:** Re-run the satellite conflict scenario from Experiment 2 (identical results expected since this scenario doesn't use deletion).

**Phase 2b:** Test deletion-meets-modification: delete CommSubsystem, then apply commit u which modifies CommSubsystem.

## Results

### Phase 1: Deletion works for SysML v2 types

```
Before: [CommSubsystem, PowerBus, SatelliteSystem, ThermalSubsystem]
After:  [PowerBus, SatelliteSystem, ThermalSubsystem]
✓ PASS: CommSubsystem deleted, others retained
```

Identity-only commits successfully delete elements with `@type: PartDefinition`.

### Phase 2: Satellite conflict — identical to Experiment 2

All constraint results match Experiment 2 exactly. Commutativity confirmed (both orderings produce C2=+5, C3=+5, C6=2 owners, name=2 values).

### Phase 2b: Deletion + modification interaction

After deleting CommSubsystem from master:
- Only ThermalSubsystem remains (mass=20, power=10)
- C1: violation=-80 (20 of 100 budget), C2: violation=-40 (10 of 50)

After applying commit u (which modifies CommSubsystem) on the deleted state:
- **CommSubsystem is RE-CREATED** with commit u's values (mass=45, power=30, dataRate=250)
- C1: violation=-35 (65 of 100), matching branch-a in Phase 2
- Deletion is **reversible**: a subsequent commit that includes the deleted element's `@id` in a `DataVersion` payload brings it back

## Key Findings

1. **Deletion works for SysML v2 types** — `@type: PartDefinition` elements can be deleted via identity-only commits.
2. **Deletion is reversible** — A subsequent commit that includes the deleted element (via `DataVersion` payload) re-creates it with the new properties.
3. **No server-side deletion validation** — The server doesn't prevent committing properties for a deleted element. It simply re-creates the element.

## Comparison with Experiment 8

Experiment 8 tests the same deletion mechanism with non-SysML types (`Color`, `ColorPair`). The comparison reveals whether deletion is type-dependent.
