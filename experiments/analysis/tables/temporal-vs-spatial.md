# Temporal vs. Spatial Signal Matrix

Core thesis: RDF excels at the spatial dimension (how things relate),
Git excels at the temporal dimension (how things evolve).

| Finding | Exp | Temporal (Git) | Spatial (RDF/SHACL) | Requires Both? |
|---------|:---:|----------------|---------------------|----------------|
| Cross-file coupling conflicts (power budget) | 14 | no — Git merges cleanly (different files) | YES — oracle detects budget violation | Spatial alone sufficient for detection; Git identifies who diverged |
| Serialization-order false positives | 14 | YES — Git conflicts on reordered text | no — graphs are semantically identical | Both needed: Git flags it, RDF confirms it's spurious |
| Ontology composition conflicts (property rename) | 15 | no — different files | YES — composed SHACL detects missing property | Spatial alone sufficient; Git shows who renamed |
| Schema + data composition conflicts | 15 | no — different files | YES — composed SHACL detects new violation | Spatial alone sufficient; Git shows which team added what |
| Lifecycle gate regression | 16 | no — Git merges cleanly (different files) | YES — lifecycle SHACL shape detects broken gate | Spatial detects regression; Git branch topology shows lifecycle ordering |
| Four-way conflict classification | 17 | partial — distinguishes 2 classes (clean/conflict) | partial — distinguishes ordering but not textual | YES — only combination distinguishes all 4 classes |
| Non-commutative ordering artifacts | 17 | YES — identifies which branch was applied when | YES — shows which ordering violates constraints | YES — both needed to detect and explain |
| Evidence staleness after model evolution | 18 | partial — shows what changed between commits | YES — SHACL detects hash mismatch | YES — RDF identifies affected requirements; Git identifies the change |
