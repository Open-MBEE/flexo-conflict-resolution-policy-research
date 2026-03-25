# A Broader Perspective on Diff and Merge in Engineering

## Abstract

This paper presents the perspective of an OpenMBEE working group focused on the diff and merge problem for engineering models. OpenMBEE’s Model Management System (MMS) provides version control for structured data, and Flexo is the graph-native MMS platform used here as the case study. One of the main drivers for this work is SysML v2, which is both a major use case for Flexo and a major concern of the diff/merge working group. As that ecosystem matures, a gap becomes increasingly visible: most merge thinking still comes from source code, but engineering models are not just text. Model merge has a different failure mode: two changes can be individually valid and still produce an invalid system when combined. This paper uses Flexo as a case study to explain why diff and merge are harder for models than for code, especially when models are stored as graphs rather than files. A small satellite example shows the core issue. One engineer upgrades the communications subsystem, another upgrades the thermal subsystem, and each change passes on its own branch. But when the changes are combined, the merged model violates shared power, bus load, and ownership constraints. The paper then proposes a simple practitioner-oriented merge stack with four layers: syntactic merge, structural checks, constraint evaluation, and simulation or human review. The main argument is that merge for engineering models should be treated as part of an engineering change process, not only as a version control operation. We close with a practical roadmap: start with three-way diff and machine-checkable constraints, then grow toward an oracle-based merge workflow that integrates analysis services, review gates, and organization-specific policy.

## 1. Introduction

Version control has trained practitioners to think about change in terms of files, diffs, and merge conflicts. That mental model works well for source code because code merge is mostly about reconciling textual edits to a shared artifact. Engineering models are different. They are not just files with lines. They are structured representations of systems with typed elements, relationships, budgets, requirements, and analysis assumptions. In modern model repositories, they are often stored internally as graphs.

This matters in the OpenMBEE context. OpenMBEE positions itself as an open source collaborative engineering environment for connected model-based engineering, where engineers can work in different tools and still share authoritative model information across those tools. Its Model Management System (MMS) is described as a version control system for structured data, exposed through RESTful services for operations such as branching and tagging. Flexo should be understood in that context as a graph-native MMS platform, not as a separate idea outside MMS. In that setting, merge is not a side issue. It is one of the control points that determines whether connected engineering information remains trustworthy as changes flow between tools, views, documents, and teams.

This paper is written from that internal community perspective. It reflects the view of an OpenMBEE working group studying how diff and merge should evolve for graph-based engineering models in MMS and Flexo. A major part of that interest comes from SysML v2, both because SysML v2 is one of the main use cases for Flexo and because SysML v2 interchange and textual workflows put new pressure on stable identity, diff quality, and merge robustness. The goal is not to critique the platform from the outside. The goal is to make a practical contribution from within the OpenMBEE ecosystem by clarifying the problem, grounding it in a concrete case, and outlining a path that practitioners can implement incrementally.

That difference matters during merge. A text merge tool can often decide whether two changes conflict by looking at what was edited. A model merge tool cannot stop there. It must also ask what the combined result means. Does the merged model still satisfy cardinality rules? Are references still valid? Do subsystem budgets still close? Does a simulation still pass? Those questions are about the merged state of the model, not just about the recorded edits.

This paper makes a simple practitioner argument: for graph-based engineering models, diff and merge should be treated as a staged engineering evaluation process. Flexo provides a useful case study because it already supports graph-native versioning of models, stores commits as graph updates, and exposes diff operations, but it does not yet implement full merge conflict resolution. That makes the gap visible in a particularly useful way for the OpenMBEE community.

The contribution of this paper is not a new algorithm. It is a practical framing for practitioners:

- why model merge is not code merge
- how to explain the problem with a concrete satellite example
- how to structure merge into layers that organizations can adopt incrementally
- how to embed merge into a broader engineering change process

## 2. Flexo as a Case Study

Flexo should be understood as part of the broader OpenMBEE ecosystem, not as a standalone merge experiment. OpenMBEE combines model repositories, web views, document-oriented access, and tool integrations so that engineering data can be shared across authoring and consumption environments. The official OpenMBEE description emphasizes connected engineering information, multi-tool access, and a model management layer that supports versioning, workflow, and access control. Within that context, Flexo is a graph-native MMS platform.

The official Flexo description is intentionally broad: Flexo MMS provides a graph-native approach to storing and diffing models, and those models are not limited to one enterprise modeling tool because Flexo can store anything expressed as RDF. The Flexo SysML v2 service is then built on that architecture as an implementation of the OMG SysML v2 API Services Specification. That combination is important for this paper because it connects an MBSE audience to a practical repository problem. Flexo is not just about storing SysML data. It is a graph-native MMS platform for managing versioned engineering models while leaving room for multiple tools and model forms. At the same time, SysML v2 is one of the most important practical use cases because it is the API layer many practitioners will actually experience and because its model interchange expectations make diff and merge quality especially visible.

That perspective also explains why this paper is framed the way it is. An OpenMBEE diff-and-merge working group does not need to argue that version control matters. MMS already establishes that. The working group problem is narrower and more practical: once models are versioned as structured, connected, graph-based information, what should merge look like so that it supports real engineering work rather than only repository bookkeeping? For SysML v2 in particular, this question is urgent because engineers expect interoperable APIs, stable identities, meaningful diffs, and merges that survive refactoring without collapsing into file-level ambiguity.

In the configuration studied here, model state is stored as RDF graphs and changes are represented as SPARQL updates. In other words, Flexo already separates two things that are often conflated in source code workflows:

- the model state at a point in time
- the change operation that moves one state to another

This is useful because it exposes the actual shape of the problem inside a connected engineering environment. A commit is not the same thing as the model state it produces. A change that is safe on one state may be unsafe on another. That is a normal condition for graph-based engineering models because validity depends on relationships and constraints that span many elements and may be consumed by other tools, documents, or analysis workflows.

The repository work behind this paper shows that Flexo already has important building blocks:

- versioned model snapshots
- branch-based parallel work
- two-way diff
- graph-native change representation

It also shows what is still missing:

- true three-way merge
- richer conflict classification
- model-state evaluation during merge
- policy-driven escalation to analysis tools or human review

That gap is the focus of this paper. The point is not that OpenMBEE lacks version control. It already has version control primitives for structured data. The point is that as model repositories become more connected and graph-native, merge must evolve from simple change reconciliation into controlled engineering evaluation.

## 3. Running Example: A Satellite Merge That Looks Fine Until It Does Not

The central example is a small satellite power subsystem model with a shared power bus and a few global constraints. The exact numbers are not the point. The important point is that the model contains connected elements and shared budgets.

The example is intentionally simple, but it is representative of the kinds of issues that matter in SysML v2 and MBSE practice. It shows how a repository can successfully store and diff model changes while still lacking the merge behavior engineers actually need when subsystem work converges.

The ancestor model contains a communications subsystem, a thermal subsystem, a power bus, and system-level mass and power budgets. Two teams branch from the same baseline:

- Team Alpha upgrades the communications subsystem for higher bandwidth. The change increases subsystem mass and power and assigns ownership to Team Alpha.
- Team Beta upgrades the thermal subsystem and standardizes naming. The change increases thermal mass and power and assigns ownership to Team Beta.

Each branch is valid on its own. The communications upgrade still fits inside the original budgets when applied alone. The thermal upgrade also fits when applied alone.

The conflict appears only when the changes are combined. In the experiments behind this paper, the combined state violates multiple constraints:

- total power exceeds the satellite power budget
- total bus-connected power exceeds the bus load limit
- the communications subsystem ends up with two owners, violating a cardinality rule
- naming updates collide at the element level

This is the practitioner lesson. Nothing about the individual commits looked obviously wrong. The problem only became visible when the combined model state was evaluated.

That is the core reason model merge is not just graph diff plus patch application. The merge candidate must be checked as a model of a system, not only as a container of edits.

## 4. Why Models Are Harder to Merge Than Code

Practitioners often start with the intuition that a graph is just another data structure, so graph diff and merge should be a manageable extension of file diff and merge. The case study suggests otherwise. Three assumptions from code-centric merge break down for models.

First, merge is not only a function of overlapping edits. In source code, many merge decisions can be made by examining the edited regions. In models, non-overlapping changes can still interact because they touch related elements or shared budgets.

Second, application order matters more often. In text merge, non-overlapping edits often commute. In models, one change can alter the context in which another change should be interpreted. The repository experiments showed this clearly in the non-satellite graph examples, where delete-then-update and update-then-delete produced different outcomes. Even when the satellite case is effectively commutative at the violation level, the more general lesson still holds: graph updates can be order-sensitive.

Third, a clean patch merge is not self-certifying. A merge can succeed at the storage layer and still fail at the engineering layer. A graph database may accept the triples. An element API may accept the payload. Neither result proves that the merged model is usable.

For practitioners, the right takeaway is simple: model merge has to combine version control with model evaluation.

## 5. A Simple Merge Stack for Practitioners

To make this problem usable in practice, it helps to separate merge into layers. The layers below are intentionally simple. They are meant to guide implementation roadmaps and tool responsibilities, not to be mathematically complete.

### Layer 1: Syntactic Merge

This is the familiar diff-and-patch layer. It answers questions such as:

- Did both branches modify the same property?
- Did one branch delete an element that the other updated?
- Can the two change sets be applied without direct overlap?

In Flexo, this is where graph diff, element diff, and eventual three-way merge logic belong. This layer is necessary, but it is not enough.

### Layer 2: Structural Merge

This layer checks whether the merged model is still well-formed as a model. Typical issues include:

- broken references
- invalid types
- multiplicity violations
- containment problems

This is the first point where merge must inspect the merged state rather than only the edits. For many teams, this is also the first high-value improvement beyond basic diff.

### Layer 3: Constraint and Analysis Merge

This layer checks domain rules that reach across the model:

- mass and power budgets
- interface compatibility
- requirement satisfaction rules
- parametric or equation-based checks

This is where the paper uses the term oracle. The oracle is simply the evaluation mechanism that tells the merge process whether the candidate state is acceptable. The implementation can vary. It might be a SPARQL query, a rule engine, a solver, or another analysis service. The important concept is that merge asks an external question about the candidate model state and uses the answer before accepting the merge.

### Layer 4: Simulation and Human Review

Some questions cannot be fully reduced to a deterministic check:

- does the merged controller still behave correctly in simulation?
- is the new decomposition still the right architectural choice?
- is the design acceptable for the program context?

These are still part of merge in a practical engineering sense, but they belong to a review and decision layer rather than a fully automatic one. A good merge process should surface these issues, package the evidence, and route them to the right reviewer instead of pretending they are the same as syntactic conflicts.

## 6. From Merge Tool to Engineering Change Process

Once merge is viewed through these layers, it becomes clear that the real target is not only a better merge command. It is a better engineering change process.

In many organizations, engineering change already involves more than combining edits. It involves checking impacts, running analyses, collecting approvals, and preserving traceability. In the OpenMBEE setting, that broader process already exists around connected model information, document generation, and tool integration. Model repositories can support that process directly if merge is treated as the gateway.

Using the Flexo case study, a practical future workflow looks like this:

1. An engineer proposes a merge from a branch into a target branch.
2. The repository computes a three-way diff and applies the non-conflicting changes.
3. The system constructs one or more candidate merged states.
4. The oracle runs the machine-checkable evaluations for the active policy of that repository or branch.
5. The system classifies findings into:
   - directly mergeable
   - auto-fixable with explicit rule support
   - blocked pending engineer choice
   - blocked pending simulation or domain review
6. Reviewers receive a merge package, not just a red or green status:
   - what changed
   - what failed
   - which constraints or analyses were involved
   - what candidate resolutions are available
7. Once the required evaluations and reviews are complete, the repository records the accepted merged state and the rationale for why it was accepted.

This is important because engineering teams do not only need a merged artifact. They need confidence, traceability, and a defensible record of change.

## 7. Low-Hanging Fruit First

The long-term vision is a full constraint-aware merge process, but practitioners do not need to wait for the whole stack before getting value. The case study suggests a practical adoption sequence.

### Step 1: Implement Real Three-Way Merge

Many model platforms still stop at branch and diff. The first requirement is a true three-way merge that can identify direct overlaps relative to a common ancestor.

### Step 2: Add Structural Checks to the Merge Gate

The next step is to reject merged states that are structurally invalid. This includes reference integrity, multiplicity, and type checks. These checks are often easy to justify organizationally because they are deterministic and tool-friendly.

### Step 3: Add Repository-Specific Constraint Checks

Once structural checks are in place, teams can add the domain checks that matter most for their repository. In the satellite example, obvious starting points are budget-style aggregate checks and ownership rules. These checks are where merge starts to become an engineering-quality gate rather than only a data-management gate.

### Step 4: Make Findings Explainable

A useful merge workflow should tell engineers more than pass or fail. At minimum, it should report:

- which checks failed
- which elements were involved
- whether the problem came from direct overlap or from the combined state
- whether human action or additional analysis is required

Even this basic level of explanation is a major improvement over a generic conflict response.

### Step 5: Integrate Analysis Services and Review Paths

The mature stage is to connect simulation, solver, or domain-specific analysis services so that merge can orchestrate a real engineering review loop. Not every issue should be auto-resolved. Some should be escalated with the right evidence package.

## 8. What Flexo Suggests About the Future

The Flexo case study points toward a useful architecture for future model repositories.

At the organization level, policy determines which checks are required for which branches and repositories. At the team level, workflow determines when those checks run and who must review them. At the individual level, engineers interact with merge as the point where design intent meets system constraints. In an OpenMBEE-style environment, these levels also map naturally onto platform governance, project workflows, and user-facing tool integrations such as model authoring clients, web views, and downstream consumers of model-backed documents.

This means that merge policy should be configurable. A low-risk sandbox branch might allow simple syntactic merge with advisory warnings. A program baseline branch might require structural checks, budget checks, and formal reviewer signoff. A safety-critical branch might additionally require simulation evidence before acceptance.

The same repository can therefore support different merge rigor for different contexts. That is a practical advantage of a layered, oracle-based model merge approach.

## 9. Conclusion

The main lesson from this work is straightforward: models are graphs of related engineering meaning, not just files with a different syntax. Because of that, merge for models cannot stop at diff correlation. It must evaluate the merged model state.

The satellite case study makes the issue easy to see. Two independently valid changes can create an invalid system when combined. That is not a rare edge case. It is the normal reason engineering teams need disciplined model merge in the first place.

For practitioners, the path forward does not require jumping directly to a fully autonomous merge engine. A sensible roadmap is available now: build real three-way merge, add structural and constraint checks, classify findings clearly, and then grow toward a merge-centered engineering change process with analysis services and human review.

Flexo is a useful case study because it already exposes the right problem shape inside a broader connected engineering environment. The remaining opportunity is to turn merge from a storage operation into a controlled engineering decision point.

## Suggested Presentation Framing

If this paper is used as the basis for an MCSS or CUSA presentation, the talk can be organized around four practitioner messages:

- model merge is different from code merge because validity lives in the merged state
- graph-native repositories need more than diff; they need evaluation
- the first wins are practical and implementable now
- the long-term value is a better engineering change process, not just a smarter merge button
