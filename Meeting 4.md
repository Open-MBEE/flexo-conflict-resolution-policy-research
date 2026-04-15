
# Flexo - Diff / Merge Mind Melt

RecordingApr 14, 8:00am–9:00am

Participants aligned on prioritizing a Git+RDF protocol for Diff/Merge, requirements traceability (RTM), and V&V as an OpenMBE standard, treating SysML v2 as a test case. Zargham outlined experiments, hashing and canonical Turtle serialization, for conflict detection and provenance. Gross demoed a Flexo-connected front end and Starforge/StarKit modular spacecraft design, proposing an ADCS collaboration. They emphasized validation as AI accelerates generation, planned SysML v2 packaging improvements, ecosystem/branding work for OpenMBE, and interoperable artifacts enabling procurement and an orbital marketplace.

Key topics:

- **Research scope: Git+RDF-first Diff and Merge:** Michael queued OpenMBE research issues to run Diff and Merge experiments at the Git+RDF protocol layer, treating SysML v2 as a field test rather than the core. The objective is valid, hash-addressable RDF with canonical serializations and referenced artifacts, enabling conflict taxonomy and resolution independent of any single ontology.
    
- **Requirements traceability and accountability:** Michael is building an open RDF+Git RTM and attestation framework so model changes trigger hash invalidation and selective revalidation, delivering reproducibility, manager-level views, and cross-organizational auditability. He wants this standardized in OpenMBE to avoid proprietary lock-in and make model assets transaction-ready.
    
- **Example and experiments: ADCS with StarKit/Starforge/Flexo:** The team will expand Michael’s ADCS demo into a richer StarKit/Starforge example wired to Flexo’s RDF APIs, then scale toward a full satellite to exercise structural/behavioral/visual views, dependency graphs, and MDO coupling. The goal is to demonstrate top-down and bottom-up aggregation of information with practical Diff/Merge plus traceability across layers.
    
- **SysML v2 modularization and package management:** Johannes plans a SysML v2 API framework around a kernel to break the language into modular packages, reducing all-or-nothing imports and RDF graph bloat. The team will evaluate CSand as a SysML package manager and design UX that behaves like a package manager to improve reuse and validation.
    
- **OpenMBE ecosystem strategy and standards:** Michael will map the OpenMBE commercial ecosystem and help craft a narrative and roadmap—anchored by a Git+RDF interoperability standard—mirroring the NumFOCUS scientific-computing breakout. Aligning with Chris Delp, Robert, and others, the intent is open-core tooling (including Flexo) that interoperates rather than binds users to SysML or any vendor.
    
- **Validation keeping pace with AI generation:** With AI accelerating model generation, the group agrees validation is the bottleneck; the Git+RDF+RTM stack is the regulative “control system” to restore trust and scalability. This directly supports startups and cross-authority procurements by making verification, accountability, and sign-off reproducible and portable.
    
- **Presentation layer and data provenance:** Johannes demoed a live web front end pulling directly from Flexo (via transclusion) to deliver leadership-ready views, while Michael stressed that without access-controlled, versioned traceability across bindings, such views won’t be trusted. The takeaway is to pair flexible presentation with rigorous provenance and controls from the RTM protocol.
    
- **Immediate next steps:** Michael will run the queued Diff and Merge experiments, share results, and continue RDF+Git RTM development; Johannes will advance SysML v2 packaging and the Flexo-backed front end. Both will assess CSand, follow up on VLAs, and consider deeper integration under an MNDA.
    

## Actions for Michael Zargham

- Run the queued Diff Merge experiments in the OpenMBE research repo, log results, and close the related issues
    
- Collaborate with Johannes Gross to create an ADCS example in StarKit that integrates RTM-on-RDF with Flexo-backed SysML v2 models
    
- Send Johannes a curated blog series on Vision-Language-Action (VLA) models
    
- Mine the transcript to extract requirements and action items and share a summarized notes document with Johannes
    
- Map the emerging OpenMBE commercial ecosystem and propose an ecosystem-level product/roadmap view
    
- Discuss OpenMBE direction and the RDF+Git core protocol focus with Robert and Chris and align before drafting public narrative
    
- Draft a narrative explaining OpenMBE’s role in the open-source engineering computing breakout (after alignment with Robert and Chris)
    
- Schedule a business-level follow-up between Michael and Johannes to align on open-core and market strategy
    
- Continue the Diff Merge research focusing on RDF+Git for RTM, conflict taxonomy, and verification workflows, using SysML v2 as the application testbed
    

## Actions for Johannes Gross

- Review the VLA materials Michael sends and assess applicability to StarKit/Starforge autonomy use cases
    
- Send the meeting recording/transcript to Michael Zargham
    
- Evaluate the CSand SysML package manager (by Sansmetry) to determine if it meets requirements and report findings
    
- Finalize the OpenMBE branding color scheme for the new logo
    

## Actions for Vince

- Create a SysML v2 API framework around a kernel and define modular subdivisions of the language