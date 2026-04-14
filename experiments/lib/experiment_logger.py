"""Dual-output experiment logger.

Writes human-readable output to stdout (for capture to log files)
and structured JSON to output/results.json.

Human output follows the Experiment 12 visual style with Unicode
box-drawing characters.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _get_package_version(name: str) -> str:
    """Get installed package version, or 'not installed'."""
    try:
        from importlib.metadata import version
        return version(name)
    except Exception:
        return "not installed"


def _get_repo_commit() -> str:
    """Get the current git commit SHA of the research repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


@dataclass
class StepRecord:
    """Record of a single experiment step."""
    step: int
    name: str
    description: str
    timestamp: str
    duration_seconds: float
    outcome: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "name": self.name,
            "description": self.description,
            "timestamp": self.timestamp,
            "duration_seconds": round(self.duration_seconds, 3),
            "outcome": self.outcome,
            "details": self.details,
        }


class ExperimentLogger:
    """Dual-output logger for experiments.

    Usage:
        logger = ExperimentLogger(14, "Git as RDF Conflict Detector")
        logger.begin()

        with logger.step("init_repo", "Initialize Git repo with ancestor model") as s:
            # ... do work ...
            s.detail("triple_count", 75)

        logger.set_findings({"confusion_matrix": {...}})
        logger.end("MIXED")
    """

    def __init__(
        self,
        experiment_number: int,
        title: str,
        output_dir: Path | str = "output",
        parameters: dict[str, Any] | None = None,
    ):
        self.experiment_number = experiment_number
        self.title = title
        self.output_dir = Path(output_dir)
        self.parameters = parameters or {}
        self.steps: list[StepRecord] = []
        self.findings: dict[str, Any] = {}
        self._step_counter = 0
        self._start_time: Optional[float] = None
        self._environment = {
            "python_version": platform.python_version(),
            "rdflib_version": _get_package_version("rdflib"),
            "pyshacl_version": _get_package_version("pyshacl"),
            "gitpython_version": _get_package_version("GitPython"),
            "platform": platform.system().lower(),
            "git_commit": _get_repo_commit(),
        }

    def begin(self) -> None:
        """Print header and record start time."""
        self._start_time = time.time()
        width = 59
        print("=" * width)
        print(f"  Experiment {self.experiment_number} — {self.title}")
        print("=" * width)
        print()
        print("Environment:")
        for key, val in self._environment.items():
            label = key.replace("_", " ").replace("version", "").strip()
            print(f"  {label:12s} {val}")
        print()

    def step(self, name: str, description: str) -> StepContext:
        """Create a step context manager."""
        self._step_counter += 1
        return StepContext(self, self._step_counter, name, description)

    def _record_step(self, record: StepRecord) -> None:
        self.steps.append(record)

    def log(self, message: str, indent: int = 2) -> None:
        """Print an indented log line."""
        print(" " * indent + message)

    def set_findings(self, findings: dict[str, Any]) -> None:
        """Set the experiment findings."""
        self.findings = findings

    def set_parameters(self, parameters: dict[str, Any]) -> None:
        """Set/update experiment parameters."""
        self.parameters.update(parameters)

    def end(self, verdict: str) -> dict:
        """Print footer, write results.json, and return the results dict."""
        duration = time.time() - (self._start_time or time.time())

        results = {
            "experiment": self.experiment_number,
            "title": self.title,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(duration, 3),
            "environment": self._environment,
            "parameters": self.parameters,
            "steps": [s.to_dict() for s in self.steps],
            "findings": self.findings,
            "verdict": verdict,
        }

        # Write structured output
        self.output_dir.mkdir(parents=True, exist_ok=True)
        results_path = self.output_dir / "results.json"
        results_path.write_text(json.dumps(results, indent=2, default=str))

        # Print footer
        width = 59
        print()
        print(f"  -> results.json written to {results_path}")
        print()
        print("=" * width)
        print(f"  VERDICT: {verdict}")
        print(f"  Duration: {duration:.1f}s")
        print("=" * width)

        return results


class StepContext:
    """Context manager for a single experiment step."""

    def __init__(self, logger: ExperimentLogger, step_num: int, name: str, description: str):
        self._logger = logger
        self._step_num = step_num
        self._name = name
        self._description = description
        self._details: dict[str, Any] = {}
        self._start: float = 0
        self._outcome = "success"

    def __enter__(self) -> StepContext:
        self._start = time.time()
        # Print step header
        header = f"  Step {self._step_num}: {self._description}"
        border = "+" + "-" * 57 + "+"
        print(border)
        print(f"| {header:<56s}|")
        print(border)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        duration = time.time() - self._start
        if exc_type is not None:
            self._outcome = f"error: {exc_val}"
        ts = datetime.now(timezone.utc).isoformat()
        record = StepRecord(
            step=self._step_num,
            name=self._name,
            description=self._description,
            timestamp=ts,
            duration_seconds=duration,
            outcome=self._outcome,
            details=self._details,
        )
        self._logger._record_step(record)
        print()
        return False  # don't suppress exceptions

    def detail(self, key: str, value: Any) -> None:
        """Record a detail about this step."""
        self._details[key] = value

    def log(self, message: str) -> None:
        """Print an indented log line within this step."""
        self._logger.log(message)
