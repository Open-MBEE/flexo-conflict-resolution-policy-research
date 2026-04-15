3 Ways to do it: 
1. something
2. Ansys step recording
3. EMF compare / lieberlieber
# Flexo - Diff / Merge Mind Melt

RecordingMar 17, 8:00am–9:00am

Daniel demonstrated LemonTree’s Git-based model versioning, showing Diff/Merge of EA models, GitLab CI validation (JUnit), and a web review flow. Michael presented a Flexo experiment using SPARQL updates to create conflicts and test constraint checks on the triple store. The group aligned on focusing at the quad-store layer, decoupling serialization, and supporting SysML v2 and other ontologies. Actions: reproduce the Flexo demo on the instance with docs, draft a minimal command-line Diff/Merge prototype, and refine requirements and user stories.

Key topics:

- **LemonTree Diff/Merge demo and CI integration:** Daniel showed storing full EA models in Git (SQLite or text), using LemonTree to produce readable Diffs and resolve Merge conflicts (including diagram merges as SVG), and running LemonTree Automation in GitLab/GitHub CI for model validation (JUnit) and web-based review—demonstrating a mature, reproducible workflow.
    
- **Flexo experiment reproducibility:** Michael built a minimal Flexo example (ancestor TTL + two SPARQL updates) that converge to the same state yet trigger constraint conflicts, and asked others to reproduce it; he will rerun it against the shared Flexo instance and update documentation/scripts.
    
- **Scope and layering:** The group aligned on keeping the top-level goal (semantically valid, engineer-approved merges) while building from the lowest layer (named-graph/Quad store) using Git low-level APIs, with unopinionated open-source protocols below and opinionated application behavior left to commercial tools.
    
- **Serialization and SysML v2/KerML kernel:** The team favors separating semantics from serialization and pursuing a simpler, possibly static KerML/SysML v2 kernel with a canonical serialization to avoid bloated exports (e.g., Cameo/MDK JSON), while still supporting industry formats and aiming for a de facto open-source standard.
    
- **OpenMBE MMS4 interop lessons:** Daniel noted MMS4 already provided reliable common ancestors and fast retrieval, but heavy, tool-specific serializations forced custom mapping, underscoring the need for a lighter, easier-to-interpret serialization layer.
    
- **Reference Diff/Merge prototype:** Johannes proposed a minimal command-line Diff/Merge skeleton operating on triples to run Michael’s example; Richard said LemonTree already separates atomic changes from semantic resolution, but extracting a reusable CLI will require investigation.
    
- **Testing Flexo beyond SysML:** Michael will test Flexo’s generality by committing a non-SysML ontology (an OWL/SHACL/SPARQL simplicial-complex model, e.g., the Magic: The Gathering color-wheel example) to show the Quad store is less opinionated than an MMS data store.
    
- **Mind Melt compiler:** The group reiterated interest in an open-source SysML v2 “Mind Melt” compiler; prior community code may be legally encumbered, so a fresh effort may be required.
    
- **Next steps:** Michael will reproduce the Flexo experiment on the shared instance and update docs/scripts; Johannes and Richard will sync before Reston; the team will refine the problem statement, use cases, user stories, and requirements, and draft a cross-layer user journey.
    

## Actions for Michael Zargham

- Redo the Flexo experiment using the public Flexo instance and update the documentation/scripts for remote usage, documenting results
    
- Close the GitHub issue after completing the remote Flexo reproduction
    
- Attempt to commit the simplicial-complex ontology model (Magic: The Gathering color wheel) to the Flexo instance to validate non-SysML support and document the outcome
    

## Actions for Richard Deininger (LieberLieber)

- Create a simple command-line Diff/Merge prototype (or assess feasibility) for the example to compare and Merge changes
    
- Meet in Reston to review details of the Diff/Merge approach and the example
    

## Actions for Johannes Gross

- Meet in Reston to review details of the Diff/Merge approach and the example
    
- Try the experiment using the updated remote instructions and provide feedback
    

## Actions for Daniel Siegl

- Share a YouTube link demonstrating the GitHub integration similar to the GitLab example

