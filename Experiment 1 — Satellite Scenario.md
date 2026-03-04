# Experiment 1 — Satellite Scenario

A concrete experiment exercising the [[Conflict Resolution Problem Statement|conflict resolution formalism]] on a running [[Flexo MMS]] instance. The scenario constructs a small constraint-rich systems engineering model, produces two independently valid commits on divergent branches, and demonstrates that their cross-application violates constraints at all three levels of the [[Conflict Classification|conflict taxonomy]]: syntactic, structural, and semantic.

Since Flexo v0.2.2 does not implement three-way merge or conflict detection, we implement the [[Predicate Compliance Oracle]] externally as SPARQL queries and construct cross-application states manually via the branch/update API.

**Reproducibility**: All model files, SPARQL queries, and an executable script are in [`experiments/experiment-1/`](experiments/experiment-1/). See the [reproducibility guide](experiments/experiment-1/README.md).

---

## Model: Satellite Power Subsystem

A satellite with two subsystems connected to a shared power bus. The model uses namespace `sat: <http://example.org/satellite/>` with `xsd:integer` typed literals.

### Elements

| Element | Type | Properties |
|---------|------|------------|
| `sat:Satellite` | `sat:System` | `massBudget=100`, `powerBudget=50` |
| `sat:CommSubsystem` | `sat:Subsystem` | `mass=30`, `power=15`, `dataRate=100`, `name="CommSubsystem"` |
| `sat:ThermalSubsystem` | `sat:Subsystem` | `mass=20`, `power=10`, `capacity=15`, `name="ThermalSubsystem"` |
| `sat:PowerBus` | `sat:Bus` | `maxLoad=50`, `name="PowerBus"` |

Both subsystems are `connectedTo` the power bus.

### Ancestor State as Turtle

```turtle
@prefix sat: <http://example.org/satellite/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

sat:Satellite a sat:System ;
    sat:massBudget "100"^^xsd:integer ;
    sat:powerBudget "50"^^xsd:integer .

sat:CommSubsystem a sat:Subsystem ;
    sat:mass "30"^^xsd:integer ;
    sat:power "15"^^xsd:integer ;
    sat:dataRate "100"^^xsd:integer ;
    sat:name "CommSubsystem" ;
    sat:connectedTo sat:PowerBus .

sat:ThermalSubsystem a sat:Subsystem ;
    sat:mass "20"^^xsd:integer ;
    sat:power "10"^^xsd:integer ;
    sat:capacity "15"^^xsd:integer ;
    sat:name "ThermalSubsystem" ;
    sat:connectedTo sat:PowerBus .

sat:PowerBus a sat:Bus ;
    sat:maxLoad "50"^^xsd:integer ;
    sat:name "PowerBus" .
```

---

## Constraints (Oracle Predicates)

Six constraints implemented as SPARQL queries against the model graph. Each constraint $c_i(X) \leq 0$ evaluates to a scalar: negative values indicate slack (satisfied with margin), zero indicates binding, positive indicates violation.

| ID | Type | Predicate | Formula | Ancestor Value |
|----|------|-----------|---------|---------------|
| C1 | Aggregate | Total mass ≤ mass budget | $\sum m_i - B_m$ | $-50$ (slack) |
| C2 | Aggregate | Total power ≤ power budget | $\sum p_i - B_p$ | $-25$ (slack) |
| C3 | Relational | Total bus-connected power ≤ max load | $\sum p_{\text{bus}} - L_{\max}$ | $-25$ (slack) |
| C4 | Local | Mass ≥ 0 for each subsystem | $-m_i$ | satisfied |
| C5 | Coupling | Thermal capacity ≥ comm power × 0.3 | $0.3 \cdot p_{\text{comm}} - \text{cap}_{\text{thermal}}$ | $-10.5$ (slack) |
| C6 | Structural | Max 1 `sat:owner` per subsystem | $\text{count}(\text{owner}) - 1$ | satisfied (0 owners) |

### SPARQL Oracle Queries

**C1 — Mass Budget:**
```sparql
PREFIX sat: <http://example.org/satellite/>
SELECT ?totalMass ?massBudget ((?totalMass - ?massBudget) AS ?violation) WHERE {
  { SELECT (SUM(?m) AS ?totalMass) WHERE { ?s a sat:Subsystem . ?s sat:mass ?m . } }
  sat:Satellite sat:massBudget ?massBudget .
}
```

**C2 — Power Budget:**
```sparql
PREFIX sat: <http://example.org/satellite/>
SELECT ?totalPower ?powerBudget ((?totalPower - ?powerBudget) AS ?violation) WHERE {
  { SELECT (SUM(?p) AS ?totalPower) WHERE { ?s a sat:Subsystem . ?s sat:power ?p . } }
  sat:Satellite sat:powerBudget ?powerBudget .
}
```

**C3 — Bus Load:**
```sparql
PREFIX sat: <http://example.org/satellite/>
SELECT ?totalPower ?maxLoad ((?totalPower - ?maxLoad) AS ?violation) WHERE {
  { SELECT (SUM(?p) AS ?totalPower) WHERE { ?s sat:connectedTo sat:PowerBus . ?s sat:power ?p . } }
  sat:PowerBus sat:maxLoad ?maxLoad .
}
```

**C4 — Non-negative Mass:**
```sparql
PREFIX sat: <http://example.org/satellite/>
SELECT ?s ?mass WHERE {
  ?s a sat:Subsystem . ?s sat:mass ?mass .
  FILTER (?mass < 0)
}
```

**C5 — Thermal Coupling:**
```sparql
PREFIX sat: <http://example.org/satellite/>
SELECT ?capacity ?commPower ?threshold ((?threshold - ?capacity) AS ?violation) WHERE {
  sat:ThermalSubsystem sat:capacity ?capacity .
  sat:CommSubsystem sat:power ?commPower .
  BIND (?commPower * 0.3 AS ?threshold)
}
```

**C6 — Owner Cardinality:**
```sparql
PREFIX sat: <http://example.org/satellite/>
SELECT ?s (COUNT(?owner) AS ?ownerCount) WHERE {
  ?s a sat:Subsystem . ?s sat:owner ?owner .
} GROUP BY ?s HAVING (COUNT(?owner) > 1)
```

**Syntactic — Name Multiplicity:**
```sparql
PREFIX sat: <http://example.org/satellite/>
SELECT ?s (GROUP_CONCAT(?name; separator=", ") AS ?names) (COUNT(?name) AS ?nameCount) WHERE {
  ?s sat:name ?name .
} GROUP BY ?s HAVING (COUNT(?name) > 1)
```

---

## Commits

### Commit $u$ — "Upgrade Comms" (branch-a)

Team Alpha upgrades the communications subsystem for high-bandwidth operations.

```sparql
PREFIX sat: <http://example.org/satellite/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

DELETE {
  sat:CommSubsystem sat:mass "30"^^xsd:integer .
  sat:CommSubsystem sat:power "15"^^xsd:integer .
  sat:CommSubsystem sat:dataRate "100"^^xsd:integer .
  sat:CommSubsystem sat:name "CommSubsystem" .
}
INSERT {
  sat:CommSubsystem sat:mass "45"^^xsd:integer .
  sat:CommSubsystem sat:power "30"^^xsd:integer .
  sat:CommSubsystem sat:dataRate "250"^^xsd:integer .
  sat:CommSubsystem sat:name "HighBandwidthComm" .
  sat:CommSubsystem sat:owner sat:TeamAlpha .
}
WHERE {}
```

### Commit $v$ — "Upgrade Thermal + Rename" (branch-b)

Team Beta upgrades the thermal subsystem and standardizes naming.

```sparql
PREFIX sat: <http://example.org/satellite/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

DELETE {
  sat:ThermalSubsystem sat:mass "20"^^xsd:integer .
  sat:ThermalSubsystem sat:power "10"^^xsd:integer .
  sat:CommSubsystem sat:name "CommSubsystem" .
}
INSERT {
  sat:ThermalSubsystem sat:mass "40"^^xsd:integer .
  sat:ThermalSubsystem sat:power "25"^^xsd:integer .
  sat:CommSubsystem sat:name "CommunicationsSubsystem" .
  sat:CommSubsystem sat:owner sat:TeamBeta .
}
WHERE {}
```

---

## Individual Validity

Each commit is independently valid — all constraints pass when applied to the ancestor in isolation.

### Branch-a (after commit $u$)

| Constraint | Value | Status |
|------------|-------|--------|
| C1 mass | $65 - 100 = -35$ | Slack |
| C2 power | $40 - 50 = -10$ | Slack |
| C3 bus | $40 - 50 = -10$ | Slack |
| C4 local | all $\geq 0$ | Satisfied |
| C5 coupling | $9.0 - 15 = -6.0$ | Slack |
| C6 owner | 1 owner on CommSubsystem | Satisfied |

### Branch-b (after commit $v$)

| Constraint | Value | Status |
|------------|-------|--------|
| C1 mass | $70 - 100 = -30$ | Slack |
| C2 power | $40 - 50 = -10$ | Slack |
| C3 bus | $40 - 50 = -10$ | Slack |
| C4 local | all $\geq 0$ | Satisfied |
| C5 coupling | $4.5 - 15 = -10.5$ | Slack |
| C6 owner | 1 owner on CommSubsystem | Satisfied |

---

## Cross-Application States

We construct both orderings:

- $X_{uv} = f(f(X, u), v)$ — apply $u$ first, then $v$
- $X_{vu} = f(f(X, v), u)$ — apply $v$ first, then $u$

### Construction

Created `branch-uv` from `branch-a` and applied commit $v$. Created `branch-vu` from `branch-b` and applied commit $u$.

### Observation: Commutativity

**The two cross-application states are identical**: $X_{uv} = X_{vu}$.

This is because the commits' DELETE/INSERT patterns operate on disjoint primary elements (CommSubsystem vs ThermalSubsystem for the numeric properties) and the shared element (CommSubsystem's `sat:name`) exhibits a specific interaction: commit $u$ deletes `"CommSubsystem"` and inserts `"HighBandwidthComm"`, so when commit $v$ subsequently tries to delete `"CommSubsystem"` on `branch-uv`, the DELETE has no match (the value is already gone). The INSERT of `"CommunicationsSubsystem"` proceeds regardless, producing two name values. The reverse ordering produces the same outcome symmetrically.

This commutativity is not guaranteed in general — it depends on the structure of the SPARQL UPDATE patterns. If commits had WHERE clauses with preconditions, or if INSERT and DELETE patterns overlapped on the same triples, the orderings could produce different states.

### Resulting Model State ($X_{uv} = X_{vu}$)

| Element | Property | Value |
|---------|----------|-------|
| `sat:CommSubsystem` | `sat:mass` | `45` |
| `sat:CommSubsystem` | `sat:power` | `30` |
| `sat:CommSubsystem` | `sat:dataRate` | `250` |
| `sat:CommSubsystem` | `sat:name` | `"HighBandwidthComm"` **and** `"CommunicationsSubsystem"` |
| `sat:CommSubsystem` | `sat:owner` | `sat:TeamAlpha` **and** `sat:TeamBeta` |
| `sat:ThermalSubsystem` | `sat:mass` | `40` |
| `sat:ThermalSubsystem` | `sat:power` | `25` |
| `sat:ThermalSubsystem` | `sat:capacity` | `15` |
| `sat:PowerBus` | `sat:maxLoad` | `50` |

---

## Constraint Violation Vectors

### Oracle Results on $X_{uv}$ (= $X_{vu}$)

| Constraint | Type | $c_i(X_{uv})$ | Status |
|------------|------|---------------|--------|
| C1 mass budget | Aggregate | $85 - 100 = -15$ | **Slack** |
| C2 power budget | Aggregate | $55 - 50 = +5$ | **VIOLATED** |
| C3 bus load | Relational | $55 - 50 = +5$ | **VIOLATED** |
| C4 non-neg mass | Local | all $\geq 0$ | **Satisfied** |
| C5 thermal coupling | Coupling | $9.0 - 15 = -6.0$ | **Slack** |
| C6 owner cardinality | Structural | $2 > 1$ | **VIOLATED** |
| Name multiplicity | Syntactic | 2 names on CommSubsystem | **CONFLICT** |

### Violation Vector

$$\lambda_{uv} = \lambda_{vu} = \begin{pmatrix} 0 \\ 5 \\ 5 \\ 0 \\ 0 \\ 1 \end{pmatrix}$$

Where $\lambda_i = \max(0, c_i(X_{uv}))$ for constraints C1–C6, plus the syntactic name conflict detected separately.

---

## Conflict Classification

The conflicting constraint set $\mathcal{C}_{\text{conflict}} = \{C2, C3, C6, \text{name}\}$ spans all three levels of the [[Conflict Classification|taxonomy]]:

### Syntactic Conflict

**`sat:name` update-update**: Both commits modify `CommSubsystem`'s name to different values.

- Commit $u$: `"CommSubsystem"` → `"HighBandwidthComm"`
- Commit $v$: `"CommSubsystem"` → `"CommunicationsSubsystem"`

Result: two `sat:name` triples on the same subject. This is detectable by comparing diffs — both diffs delete the same triple (`sat:CommSubsystem sat:name "CommSubsystem"`) and insert different replacements.

**Resolution options**: Source-wins, target-wins, or human selection. This is a pure [[Verification and Validation|verification]]-scope conflict.

### Structural Conflict

**C6 — Owner cardinality**: Both commits add `sat:owner` to `CommSubsystem` with different values.

- Commit $u$: adds `sat:owner sat:TeamAlpha`
- Commit $v$: adds `sat:owner sat:TeamBeta`

Result: two owners on a subsystem constrained to have at most one. Neither diff individually creates a problem (the ancestor had zero owners), but their union violates the metamodel constraint.

This is an **insert-insert structural conflict** — invisible in the individual diffs, detectable only by evaluating the merged state against the metamodel.

**Resolution options**: Choose one owner, reject both, or relax the cardinality constraint. Requires policy input.

### Semantic Conflicts

**C2 — Power budget violation** ($c_2 = +5$): Combined power draw (30 + 25 = 55) exceeds the satellite's power budget of 50 by 5 units.

**C3 — Bus load violation** ($c_3 = +5$): The same combined power draw exceeds the power bus's max load of 50 by 5 units.

Both commits are individually within budget. The violation emerges only from their combination — a classic example of a semantic conflict invisible at the syntactic level.

**Note**: C2 and C3 are coupled — they share the same underlying cause (total power = 55). A resolution that reduces total power to ≤ 50 resolves both simultaneously. This coupling is structurally significant: the shadow prices $\mu^*_2$ and $\mu^*_3$ are not independent.

---

## Impacted Resource Set

$$\mathcal{R}_{\text{impacted}} = \{\ \texttt{sat:CommSubsystem},\ \texttt{sat:ThermalSubsystem},\ \texttt{sat:PowerBus}\ \}$$

- **CommSubsystem** is directly involved in all four conflicts (name, owner, power contribution to C2/C3)
- **ThermalSubsystem** contributes to C2/C3 through its power draw
- **PowerBus** is the constraint anchor for C3 (its `maxLoad` defines the bound)
- **Satellite** is the constraint anchor for C2 (its `powerBudget` defines the bound) but is not itself modified

---

## Discussion

### Shadow Prices and Policy Implications

In the formalism from [[Conflict Resolution Problem Statement]], the resolution $w^*$ minimizes intent loss subject to constraints:

$$\min_{w} \; L_{\text{intent}}(w;\, u, v) \quad \text{s.t.} \quad C(f(X, w)) \leq \mathbf{0}$$

The Lagrange multipliers $\mu^*$ at the optimum reveal which constraints shaped the resolution:

- **$\mu^*_2, \mu^*_3 > 0$** — the power constraints are binding. Any resolution must reduce total power by at least 5. The shadow price quantifies how much additional power budget (C2) or bus capacity (C3) would reduce the intent loss.
- **$\mu^*_6 > 0$** — the cardinality constraint is binding. One owner must be removed.
- **$\mu^*_1 = \mu^*_4 = \mu^*_5 = 0$** — these constraints are slack and do not influence the resolution.

### What $w^*$ Would Look Like

A resolution commit $w^*$ must:

1. **Reduce total power by ≥ 5** — either reduce CommSubsystem power below 30, reduce ThermalSubsystem power below 25, or some combination. Each option trades off against the original intent (both teams wanted more power for their subsystem).

2. **Choose one owner** for CommSubsystem — `sat:TeamAlpha` or `sat:TeamBeta`. This is a discrete choice, not a continuous optimization. The resolution policy must encode precedence (e.g., the commit author whose branch is the merge target wins).

3. **Choose one name** for CommSubsystem — `"HighBandwidthComm"` or `"CommunicationsSubsystem"`. Again discrete.

The power reduction (semantic) is the most interesting component because it involves a genuine tradeoff. Reducing comm power preserves thermal performance but degrades data rate capability. Reducing thermal power preserves communications but may create thermal coupling issues if C5's margin shrinks. The shadow prices on C2 and C3 would quantify this tradeoff.

### C2/C3 Coupling

Constraints C2 and C3 are structurally coupled — they share the same variable (total power of bus-connected subsystems) and in this model, all subsystems are bus-connected, so they are identical in value. This means:

- They are violated by the same amount (+5)
- They are resolved by the same action (reduce total power)
- Their shadow prices are linked: at the optimum, $\mu^*_2 + \mu^*_3$ reflects the total marginal cost of power

In a richer model with subsystems not connected to the bus, C2 and C3 would decouple — C2 would constrain global power while C3 would constrain only bus-connected power.

### Commutativity and Its Limits

The commutativity $X_{uv} = X_{vu}$ observed here is a consequence of the commits' structure: their SPARQL UPDATE patterns use empty WHERE clauses (unconditional application) and their DELETE/INSERT patterns are largely disjoint. In general:

- **WHERE-clause preconditions** would break commutativity if one commit's changes invalidate the other's preconditions
- **Overlapping DELETE patterns** would break commutativity if the first commit removes triples the second expects to find
- **Computed values** (using BIND or expressions in INSERT) would break commutativity if they depend on state that the other commit modifies

The commutativity here simplifies the analysis — the conflict set $\mathcal{C}_{\text{conflict}}$ is the same regardless of ordering. Non-commutative cases require evaluating both $X_{uv}$ and $X_{vu}$ and taking the union of violated constraints.

### The Verification Boundary

Every constraint in this experiment is directly computable from the model graph via SPARQL. Even the "semantic" conflicts (C2, C3) are arithmetic aggregations over property values — they require no external tools, no simulation, and no human judgment to evaluate. This places the entire experiment within the [[Verification and Validation|verification]] scope of the [[Predicate Compliance Oracle]].

This is by design for a first experiment, but it is important to acknowledge what it does *not* cover. In practice, the more consequential and more common constraints in systems engineering are **behavioral** and **validation-scope**: they cannot be checked or inferred from the model graph alone but require disciplinary models, external solvers, and domain expert analysis to evaluate and attest to.

Examples of what a richer satellite scenario would include:

| Constraint | Evaluation mechanism | Why it's harder |
| --- | --- | --- |
| "The thermal subsystem maintains component temperatures within operating limits under worst-case orbital conditions" | Thermal simulation (e.g., Thermal Desktop, OpenModelica) | Requires running a disciplinary model against the merged state — the RDF graph encodes parameters, but compliance depends on physics |
| "The communication link closes with ≥ 3 dB margin at maximum range" | Link budget analysis tool | Depends on antenna gain, transmit power, orbit geometry — multiple model elements interact through equations not encoded in RDF |
| "The power system sustains operations through eclipse without battery depth-of-discharge exceeding 30%" | Power/energy simulation | Time-domain behavior not representable as a static triple-level predicate |
| "The design satisfies requirement R-42: system shall be operable by a single technician" | Human expert review | Non-assertable — no computable predicate exists |

In the formalism, these are still constraints $c_i(X) \leq 0$ with associated shadow prices $\mu^*_i$. The [[Predicate Compliance Oracle]] treats them uniformly at the interface level. But their evaluation is fundamentally different:

- **Verification-scope** constraints (this experiment): the oracle is a SPARQL query; evaluation is deterministic, fast, and automatable. Shadow prices are computable.
- **Validation-scope** constraints (real systems): the oracle dispatches to external tools or human reviewers; evaluation may be slow, expensive, non-deterministic, or require judgment. Shadow prices are *estimated* or *assigned* by domain experts — the formalism accommodates them but cannot compute them autonomously (see [[Predicate Compliance Oracle#V&V Boundary]]).

The practical implication is that a merge policy cannot wait for all constraints to be evaluated before proceeding — behavioral constraints may take hours (simulation) or days (expert review). The policy framework must support **partial evaluation**: resolve verification-scope conflicts immediately, flag validation-scope constraints for asynchronous review, and define what model state is permissible in the interim. This is the governance challenge that [[Conflict Classification#Logical vs Behavioral Constraints]] identifies and that future experiments should address.

### Experiment Limitations

1. **Verification-scope only**: All constraints are directly computable SPARQL queries. The experiment does not exercise validation-scope predicates requiring external solvers, simulation, or human attestation. See the section above.
2. **No automated resolution**: We identified conflicts and characterized shadow prices conceptually but did not compute $w^*$. The optimization itself is future work.
3. **Manual cross-application**: Flexo does not support merge, so we constructed $X_{uv}$ and $X_{vu}$ by creating additional branches and replaying updates manually.
4. **Simplified ontology**: The `sat:` namespace is ad hoc — a real satellite model would use a formal ontology (SysML v2, MBSE frameworks) with richer type constraints.
5. **Integer arithmetic**: Using `xsd:integer` avoids floating-point issues but limits the expressiveness of constraint evaluation in SPARQL.

---

## Execution Log

All operations executed against a local Flexo MMS v0.2.2 instance (see [[Local Deployment Setup]]).

| Step | Operation | Endpoint | Result |
|------|-----------|----------|--------|
| 1 | Authenticate | `GET localhost:8082/login` | JWT token |
| 2 | Create repo `scenario-1` | `PUT /orgs/research/repos/scenario-1` | 201 |
| 3 | Load ancestor model | `POST .../branches/master/update` | 201 |
| 4 | Verify ancestor constraints | `POST .../branches/master/query` × 6 | C1=-50, C2=-25, C5=-10.5, all pass |
| 5 | Create `branch-a` from master | `PUT .../branches/branch-a` | 201 |
| 6 | Create `branch-b` from master | `PUT .../branches/branch-b` | 201 |
| 7 | Apply commit $u$ on `branch-a` | `POST .../branches/branch-a/update` | 201 |
| 8 | Apply commit $v$ on `branch-b` | `POST .../branches/branch-b/update` | 201 |
| 9 | Verify `branch-a` constraints | `POST .../branches/branch-a/query` × 6 | All pass |
| 10 | Verify `branch-b` constraints | `POST .../branches/branch-b/query` × 6 | All pass |
| 11 | Create `branch-uv` from `branch-a` | `PUT .../branches/branch-uv` | 201 |
| 12 | Create `branch-vu` from `branch-b` | `PUT .../branches/branch-vu` | 201 |
| 13 | Apply commit $v$ on `branch-uv` | `POST .../branches/branch-uv/update` | 201 |
| 14 | Apply commit $u$ on `branch-vu` | `POST .../branches/branch-vu/update` | 201 |
| 15 | Verify $X_{uv} = X_{vu}$ | `POST .../query` on both | Identical model states |
| 16 | Evaluate C1–C6 on $X_{uv}$ | `POST .../branches/branch-uv/query` × 7 | C2=+5, C3=+5, C6 violated, name conflict |
| 17 | Evaluate C1–C6 on $X_{vu}$ | `POST .../branches/branch-vu/query` × 5 | Same results (commutativity confirmed) |

### Gotcha: PUT Graph vs SPARQL UPDATE

Loading the ancestor model via `PUT .../branches/master/graph` with inline Turtle returned HTTP 200 but subsequent queries returned empty results. Loading via `POST .../branches/master/update` with `INSERT DATA { ... }` worked correctly. This may be related to content negotiation or snapshot materialization behavior in Layer 1.

---

## References

- [[Conflict Resolution Problem Statement]] — the full mathematical formalism
- [[Conflict Classification]] — taxonomy of conflict types
- [[Predicate Compliance Oracle]] — abstract constraint evaluator
- [[Flexo Conflict Resolution Mapping]] — mapping formalism to Flexo operations
- [[Diff and Delta]] — how Flexo computes and stores differences
- [[Local Deployment Setup]] — local Flexo instance setup guide

---
← [[Flexo MMS]] · [[Local Deployment Setup]] · [[Conflict Resolution Problem Statement]]
