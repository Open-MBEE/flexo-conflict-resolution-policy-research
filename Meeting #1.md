

# Flexo - Diff / Merge Mind Melt

Mar 3, 9:00am–10:00am

The group aligned on tackling Diff/Merge in Flexo/OpenMBE and will stand up a sandbox, move a repo to OpenMBE, and capture problem statement, demo, and success criteria in Confluence. Daniel stressed three-way Diff/Merge with a common‑ancestor API and warned that splitting models across files complicates Merge; single‑file/LFS works commercially. They flagged SysML v2 textual notation’s lack of stable IDs as a Merge risk. They set a biweekly cadence (one hour earlier); Daniel will demo, and GitHub issues will track actions.

Key topics: [[Basics]]
- **Problem framing for model Diff/Merge:** The group is forming a working group to tackle Diff and Merge for graph-based models in Flexo MMS, focusing on a layered approach: protocol-level changes (alternative high-level commands over Git’s low-level APIs), recommended best practices, and development norms, plus a public sandbox to materialize and test real problems.
    
- **Vendor requirements and Merge strategy:** Daniel stressed three-way Diff/Merge with a reliable common-ancestor API as a hard requirement and strongly advised treating the full model as the merge unit; splitting models across files makes Merge complexity explode, whereas single-file (e.g., SQLite via Git LFS) workflows have proven tractable with customers.
    
- **Open source vs. commercial layering:** Consensus: keep OpenMBE/Flexo unopinionated at lower layers to support diverse patterns, while vendors can build opinionated, commercial layers (e.g., single-file models) on top—preserving moats yet collaborating on shared infrastructure.
    
- **Working group logistics and immediate actions:** Biweekly cadence agreed; Michael will transfer and seed a research repo under OpenMBE and commit initial Flexo experiments; a concise problem statement, success criteria, and demonstration will be captured in Confluence; GitHub Issues will track tasks; Daniel will present a 20‑minute demo next meeting; a shared Flexo sandbox server is targeted in ~2 weeks.
    
- **SysML v2 textual notation limitations:** Lack of persistent IDs in the SysML v2 textual notation breaks round‑tripping and makes refactor-heavy Merges brittle; “debugger file” style mappings don’t scale, underscoring the need for stable identifiers to enable robust Diff/Merge and interchange.
    
- **AI-assisted querying over models:** Doris’s MCP server experiment aims to translate natural language into SPARQL over the graph, but ontology size makes query generation hard; Michael recommends purpose–persona–protocol prompting and using OWL/SHACL topology to narrow context to relevant subgraphs in Flexo, potentially with query‑builder tools—leveraging Mind Melt where applicable.
    
- **Flexo Layer 1 scope:** Doris confirmed Flexo MMS Layer 1 is ontology‑agnostic and operates at the RDF layer, so any Diff/Merge or querying solution cannot assume a specific SysML ontology.
    

## Actions for Daniel Siegl

- Prepare a 20-minute curated demo of the commercial Diff/Merge product and workflows for the next session
    

## Actions for Michael Zargham

- Commit initial Flexo MMS local-instance experimentation notes/tests to the transferred research repo (open a PR if needed)
    
- Incorporate low-level Git API considerations (e.g., alternative high-level commands; three-way Merge constraints) into the research repo notes
    

## Actions for Johannes Gross

- Set up a shared public sandbox Flexo MMS server for experimentation (target ~two weeks)
    
- Draft and publish a short problem statement, problem demonstration outline, and success criteria in Confluence
    
- Create and use GitHub issues in the transferred repo to track action items (e.g., demo, shared server, Confluence docs, common-ancestor API)
    
- Adjust and schedule biweekly working group meetings on Tuesdays one hour earlier; send updated invites
    

## Actions for All participants

- Confirm attendance by accepting the Google Meet invite
    

## Actions

- Specify and implement an API to find the common ancestor commit between two commits to enable three-way Merge in MMS
    

## Actions for Doris Lam

- Load the SysML V2 ontology into Flexo, interpret it as a graph, and experiment with using graph topology (e.g., via NetworkX) to narrow context for SPARQL query generation