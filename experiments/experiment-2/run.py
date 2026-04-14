#!/usr/bin/env python3
"""
Experiment 2 — Satellite Power Subsystem Conflict Resolution (Remote Flexo)

Same scenario as Experiment 1, but run against the remote OpenMBEE Flexo
SysML v2 service using the REST API instead of raw SPARQL.

Experiment 1 uses:
  - Flexo MMS Layer 1 SPARQL API  (/orgs/.../repos/.../branches/.../update|query)
  - RDF/Turtle model files + SPARQL UPDATE for commits
  - SPARQL SELECT queries for constraint evaluation

Experiment 2 uses:
  - SysML v2 REST API  (/projects, /branches, /commits, /elements)
  - JSON element payloads for model and commits
  - Python functions for constraint evaluation (client-side)

The experiment produces identical results, demonstrating that the conflicts
are inherent to the model, not an artifact of the API layer.

Usage:
    export FLEXO_BEARER_TOKEN="eyJhbGci..."
    python3 run.py [--cleanup]
"""

import argparse
import os
import sys

import requests

from model import (
    ANCESTOR_ELEMENTS,
    COMMIT_U_DELTAS,
    COMMIT_V_DELTAS,
    apply_deltas,
    compute_full_elements,
)
from oracle import run_oracle

BASE_URL = os.environ.get("FLEXO_BASE_URL", "https://experimental.starforge.app").rstrip("/")
BEARER_TOKEN = os.environ.get("FLEXO_BEARER_TOKEN", "")
PROJECT_NAME = "satellite-scenario-2"


class FlexoClient:
    """Minimal SysML v2 REST API client for the experiment."""

    def __init__(self, base_url, token):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        self.session.timeout = 60

    def _url(self, path):
        return f"{self.base_url}{path}"

    def _check(self, resp, context=""):
        if not resp.ok:
            print(f"  ERROR: HTTP {resp.status_code} on {context}")
            print(f"  {resp.text[:500]}")
            sys.exit(1)
        return resp

    # --- Projects ---

    def list_projects(self):
        r = self._check(self.session.get(self._url("/projects")), "GET /projects")
        return r.json()

    def create_project(self, name):
        r = self._check(
            self.session.post(self._url("/projects"), json={"name": name, "@type": "Project"}),
            f"POST /projects ({name})",
        )
        return r.json()

    def delete_project(self, project_id):
        r = self._check(
            self.session.delete(self._url(f"/projects/{project_id}")),
            f"DELETE /projects/{project_id}",
        )
        return r.json()

    # --- Branches ---

    def list_branches(self, project_id):
        r = self._check(
            self.session.get(self._url(f"/projects/{project_id}/branches")),
            "GET branches",
        )
        return r.json()

    def get_branch(self, project_id, branch_id):
        r = self._check(
            self.session.get(self._url(f"/projects/{project_id}/branches/{branch_id}")),
            f"GET branch {branch_id}",
        )
        return r.json()

    def create_branch(self, project_id, name, commit_id):
        r = self._check(
            self.session.post(
                self._url(f"/projects/{project_id}/branches"),
                json={"@type": "Branch", "name": name, "head": {"@id": commit_id}},
            ),
            f"POST branch ({name})",
        )
        return r.json()

    # --- Commits ---

    def create_commit(self, project_id, branch_id, elements, description=""):
        change = [{"@type": "DataVersion", "payload": e} for e in elements]
        r = self._check(
            self.session.post(
                self._url(f"/projects/{project_id}/commits?branchId={branch_id}"),
                json={"@type": "Commit", "description": description, "change": change},
            ),
            f"POST commit to branch {branch_id}",
        )
        return r.json()

    # --- Elements ---

    def get_elements(self, project_id, commit_id):
        r = self._check(
            self.session.get(self._url(f"/projects/{project_id}/commits/{commit_id}/elements")),
            f"GET elements at {commit_id[:8]}...",
        )
        return r.json()


def branch_head(client, project_id, branch_id):
    """Get the current head commit ID of a branch."""
    b = client.get_branch(project_id, branch_id)
    return b["head"]["@id"]


def main():
    parser = argparse.ArgumentParser(description="Experiment 2 — Remote Flexo satellite scenario")
    parser.add_argument("--cleanup", action="store_true", help="Delete the project after the experiment")
    args = parser.parse_args()

    # --- Validate environment ---

    if not BEARER_TOKEN:
        print("ERROR: FLEXO_BEARER_TOKEN environment variable is not set.")
        print('Usage: export FLEXO_BEARER_TOKEN="eyJhbGci..." && python3 run.py')
        sys.exit(1)

    client = FlexoClient(BASE_URL, BEARER_TOKEN)

    # --- Step 1: Verify connectivity ---

    print(f"Step 1: Verifying connectivity to {BASE_URL}...")
    projects = client.list_projects()
    print(f"  Connected. {len(projects)} existing project(s) on server.")

    # --- Step 2: Create project ---

    print(f"\nStep 2: Creating project '{PROJECT_NAME}'...")
    project = client.create_project(PROJECT_NAME)
    project_id = project["@id"]
    print(f"  Project created: {project_id}")

    branches = client.list_branches(project_id)
    master = branches[0]
    master_id = master["@id"]
    print(f"  Default branch: '{master['name']}' ({master_id})")

    # --- Step 3: Load ancestor model ---

    print("\nStep 3: Loading ancestor model onto Master...")
    commit = client.create_commit(project_id, master_id, ANCESTOR_ELEMENTS, "Load ancestor state X")
    ancestor_commit_id = commit["@id"]
    print(f"  Ancestor commit: {ancestor_commit_id}")

    # --- Step 4: Verify ancestor constraints ---

    print("\nStep 4: Verifying ancestor constraints...")
    master_head = branch_head(client, project_id, master_id)
    elements = client.get_elements(project_id, master_head)
    print(f"  {len(elements)} elements loaded.")
    run_oracle(elements, "master")

    # --- Step 5: Create branches ---

    print("\nStep 5: Creating branch-a and branch-b from Master...")
    branch_a = client.create_branch(project_id, "branch-a", master_head)
    branch_a_id = branch_a["@id"]
    print(f"  branch-a: {branch_a_id}")

    branch_b = client.create_branch(project_id, "branch-b", master_head)
    branch_b_id = branch_b["@id"]
    print(f"  branch-b: {branch_b_id}")

    # --- Step 6: Apply commits ---

    # Compute full element sets for each commit (API replaces whole elements)
    print("\nStep 6: Applying commits...")
    u_elements = compute_full_elements(elements, COMMIT_U_DELTAS)
    commit_u = client.create_commit(project_id, branch_a_id, u_elements, "Commit u: upgrade comms (Team Alpha)")
    print(f"  commit u on branch-a: {commit_u['@id']}")

    v_elements = compute_full_elements(elements, COMMIT_V_DELTAS)
    commit_v = client.create_commit(project_id, branch_b_id, v_elements, "Commit v: upgrade thermal (Team Beta)")
    print(f"  commit v on branch-b: {commit_v['@id']}")

    # --- Step 7: Verify individual validity ---

    print("\nStep 7: Verifying individual validity...")
    elements_a = client.get_elements(project_id, branch_head(client, project_id, branch_a_id))
    run_oracle(elements_a, "branch-a")

    elements_b = client.get_elements(project_id, branch_head(client, project_id, branch_b_id))
    run_oracle(elements_b, "branch-b")

    # --- Step 8: Construct cross-application states ---
    #
    # branch-uv = f(f(X, u), v)  —  start from branch-a's state, apply commit v's deltas
    # branch-vu = f(f(X, v), u)  —  start from branch-b's state, apply commit u's deltas
    #
    # apply_deltas() mirrors SPARQL DELETE/INSERT semantics: it only modifies
    # the specific properties each commit touches, leaving other properties
    # (set by the prior commit) intact. This correctly produces conflicts when
    # both commits modify the same property to different values.

    print("\nStep 8: Constructing cross-application states...")

    # branch-uv: branch from branch-a, apply v's deltas
    branch_a_head = branch_head(client, project_id, branch_a_id)
    branch_uv = client.create_branch(project_id, "branch-uv", branch_a_head)
    branch_uv_id = branch_uv["@id"]
    uv_state = apply_deltas(elements_a, COMMIT_V_DELTAS)
    commit_uv = client.create_commit(project_id, branch_uv_id, uv_state, "Apply v on top of u")
    print(f"  branch-uv: {branch_uv_id} (commit {commit_uv['@id']})")

    # branch-vu: branch from branch-b, apply u's deltas
    branch_b_head = branch_head(client, project_id, branch_b_id)
    branch_vu = client.create_branch(project_id, "branch-vu", branch_b_head)
    branch_vu_id = branch_vu["@id"]
    vu_state = apply_deltas(elements_b, COMMIT_U_DELTAS)
    commit_vu = client.create_commit(project_id, branch_vu_id, vu_state, "Apply u on top of v")
    print(f"  branch-vu: {branch_vu_id} (commit {commit_vu['@id']})")

    # --- Step 9: Evaluate oracle on cross-application states ---

    print("\nStep 9: Evaluating oracle on cross-application states...")
    elements_uv = client.get_elements(project_id, branch_head(client, project_id, branch_uv_id))
    run_oracle(elements_uv, "branch-uv")

    elements_vu = client.get_elements(project_id, branch_head(client, project_id, branch_vu_id))
    run_oracle(elements_vu, "branch-vu")

    # --- Summary ---

    print("\n============================================")
    print("  Experiment 2 complete.")
    print("  Compare branch-uv and branch-vu results.")
    print("  Expected violations: C2 (+5), C3 (+5),")
    print("  C6 (2 owners), name (2 values).")
    print("============================================")

    # --- Cleanup ---

    if args.cleanup:
        print(f"\nCleaning up: deleting project {project_id}...")
        client.delete_project(project_id)
        print("  Deleted.")
    else:
        print(f"\nProject '{PROJECT_NAME}' retained (id: {project_id}).")
        print("  Re-run with --cleanup to delete, or delete manually.")


if __name__ == "__main__":
    main()
