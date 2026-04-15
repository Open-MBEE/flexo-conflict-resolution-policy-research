"""SHACL validation wrapper returning structured results.

Wraps pyshacl to produce machine-readable validation outputs
alongside human-readable reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pyshacl
from rdflib import Graph


@dataclass
class ShaclViolation:
    """A single SHACL constraint violation."""
    shape: str
    focus_node: str
    message: str
    path: Optional[str] = None
    value: Optional[str] = None

    def to_dict(self) -> dict:
        d = {"shape": self.shape, "focus_node": self.focus_node, "message": self.message}
        if self.path:
            d["path"] = self.path
        if self.value:
            d["value"] = self.value
        return d


@dataclass
class ShaclResult:
    """Structured result of a SHACL validation run."""
    conforms: bool
    violation_count: int
    violations: list[ShaclViolation] = field(default_factory=list)
    report_text: str = ""

    def to_dict(self) -> dict:
        return {
            "conforms": self.conforms,
            "violation_count": self.violation_count,
            "violations": [v.to_dict() for v in self.violations],
        }


def run_shacl(
    data_graph: Graph,
    shapes_graph: Graph,
    ont_graph: Optional[Graph] = None,
    inference: str = "rdfs",
) -> ShaclResult:
    """Run SHACL validation and return structured results.

    Args:
        data_graph: The RDF data to validate.
        shapes_graph: The SHACL shapes graph.
        ont_graph: Optional ontology graph for inference.
        inference: Inference mode ('rdfs', 'owlrl', or 'none').
    """
    conforms, results_graph, report_text = pyshacl.validate(
        data_graph=data_graph,
        shacl_graph=shapes_graph,
        ont_graph=ont_graph,
        inference=inference,
        abort_on_first=False,
    )

    violations = _parse_violations(report_text)

    return ShaclResult(
        conforms=conforms,
        violation_count=len(violations),
        violations=violations,
        report_text=report_text,
    )


def _parse_violations(report_text: str) -> list[ShaclViolation]:
    """Parse SHACL text report into structured violations."""
    violations = []
    current: dict = {}

    for line in report_text.split("\n"):
        line = line.strip()
        if line.startswith("Constraint Violation"):
            if current:
                violations.append(ShaclViolation(**current))
            current = {"shape": "", "focus_node": "", "message": ""}
        elif line.startswith("Source Shape:"):
            current["shape"] = line.split(":", 1)[1].strip()
        elif line.startswith("Focus Node:"):
            current["focus_node"] = line.split(":", 1)[1].strip()
        elif line.startswith("Message:"):
            current["message"] = line.split(":", 1)[1].strip()
        elif line.startswith("Result Path:"):
            current["path"] = line.split(":", 1)[1].strip()
        elif line.startswith("Value Node:"):
            current["value"] = line.split(":", 1)[1].strip()

    if current and current.get("shape"):
        violations.append(ShaclViolation(**current))

    return violations


def load_shapes(*paths: Path | str) -> Graph:
    """Load SHACL shapes from one or more Turtle files."""
    g = Graph()
    for p in paths:
        g.parse(str(p), format="turtle")
    return g
