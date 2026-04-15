"""Git utilities for programmatic repo creation, branching, and merging.

Wraps gitpython for experiment use: create repos, branches, commits,
and merges, then extract structured metadata about the results.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from git import Repo


@dataclass
class MergeResult:
    """Structured result of a git merge attempt."""
    source_branch: str
    target_branch: str
    has_conflict: bool
    merged_commit: Optional[str] = None
    conflict_files: list[str] = field(default_factory=list)
    merge_base: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "source_branch": self.source_branch,
            "target_branch": self.target_branch,
            "has_conflict": self.has_conflict,
            "merged_commit": self.merged_commit,
            "conflict_files": self.conflict_files,
            "merge_base": self.merge_base,
        }


def init_repo(path: Path) -> Repo:
    """Initialize a new git repo at the given path with an initial commit."""
    path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(path)
    repo.config_writer().set_value("user", "name", "Experiment").release()
    repo.config_writer().set_value("user", "email", "exp@example.com").release()
    # Create initial empty commit so we have a HEAD
    repo.index.commit("initial commit (empty)")
    return repo


def commit_file(repo: Repo, filepath: str, content: str, message: str) -> str:
    """Write content to a file in the repo, stage it, and commit.

    Returns the commit SHA.
    """
    full_path = Path(repo.working_dir) / filepath
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content)
    repo.index.add([filepath])
    commit = repo.index.commit(message)
    return commit.hexsha


def commit_files(repo: Repo, files: dict[str, str], message: str) -> str:
    """Write multiple files, stage all, and commit.

    files: {relative_path: content}
    Returns the commit SHA.
    """
    for filepath, content in files.items():
        full_path = Path(repo.working_dir) / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
    repo.index.add(list(files.keys()))
    commit = repo.index.commit(message)
    return commit.hexsha


def create_branch(repo: Repo, name: str, start_point: str = "HEAD") -> None:
    """Create a new branch and check it out."""
    repo.create_head(name, start_point)
    repo.heads[name].checkout()


def checkout(repo: Repo, branch_name: str) -> None:
    """Check out an existing branch."""
    repo.heads[branch_name].checkout()


def attempt_merge(repo: Repo, source_branch: str) -> MergeResult:
    """Attempt to merge source_branch into the current branch.

    Uses subprocess for the actual merge to capture conflict state,
    since gitpython doesn't expose merge conflict details well.

    Returns a MergeResult with conflict information.
    """
    target_branch = repo.active_branch.name
    work_dir = repo.working_dir

    # Find merge base
    try:
        merge_base = repo.merge_base(target_branch, source_branch)
        merge_base_sha = merge_base[0].hexsha if merge_base else None
    except Exception:
        merge_base_sha = None

    # Attempt the merge
    result = subprocess.run(
        ["git", "merge", source_branch, "--no-edit"],
        cwd=work_dir,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        # Clean merge
        return MergeResult(
            source_branch=source_branch,
            target_branch=target_branch,
            has_conflict=False,
            merged_commit=repo.head.commit.hexsha,
            merge_base=merge_base_sha,
        )
    else:
        # Conflict — find which files
        status = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=U"],
            cwd=work_dir,
            capture_output=True,
            text=True,
        )
        conflict_files = [f for f in status.stdout.strip().split("\n") if f]
        return MergeResult(
            source_branch=source_branch,
            target_branch=target_branch,
            has_conflict=True,
            conflict_files=conflict_files,
            merge_base=merge_base_sha,
        )


def abort_merge(repo: Repo) -> None:
    """Abort an in-progress merge."""
    subprocess.run(
        ["git", "merge", "--abort"],
        cwd=repo.working_dir,
        capture_output=True,
    )


def get_git_log(repo: Repo) -> str:
    """Return a human-readable git log --graph --oneline --all."""
    result = subprocess.run(
        ["git", "log", "--graph", "--oneline", "--all", "--decorate"],
        cwd=repo.working_dir,
        capture_output=True,
        text=True,
    )
    return result.stdout


def get_diff(repo: Repo, commit_a: str, commit_b: str) -> str:
    """Return the diff between two commits."""
    result = subprocess.run(
        ["git", "diff", commit_a, commit_b],
        cwd=repo.working_dir,
        capture_output=True,
        text=True,
    )
    return result.stdout
