#!/usr/bin/env python3
"""
Experiment 6 — MTG Knowledge Complex: KC Python API Bridge (Remote Flexo)

Same structural conflict scenario as Experiments 3–5, but with a hybrid
validation approach: the REST API serves as a versioned store, while the
KC Python APIs (rdflib, pyshacl) provide RDF-native semantic validation.

What is being tested:
  Can the KC Python APIs bridge between RDF-native models and JSON REST
  storage, preserving SHACL validation and SPARQL query capabilities?

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
    apply_commit_u,
    apply_commit_v,
    apply_commit_u_on_v_state,
    apply_commit_v_on_u_state,
)
from oracle import run_oracle

BASE_URL = os.environ.get("FLEXO_BASE_URL", "https://experimental.starforge.app").rstrip("/")
BEARER_TOKEN = os.environ.get("FLEXO_BEARER_TOKEN", "")
PROJECT_NAME = "mtg-kc-scenario-bridge"


class FlexoClient:
    """Minimal SysML v2 REST API client."""

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

    def list_projects(self):
        return self._check(self.session.get(self._url("/projects")), "GET /projects").json()

    def create_project(self, name):
        return self._check(
            self.session.post(self._url("/projects"), json={"name": name, "@type": "Project"}),
            f"POST /projects ({name})",
        ).json()

    def delete_project(self, project_id):
        return self._check(
            self.session.delete(self._url(f"/projects/{project_id}")),
            f"DELETE /projects/{project_id}",
        ).json()

    def list_branches(self, project_id):
        return self._check(
            self.session.get(self._url(f"/projects/{project_id}/branches")),
            "GET branches",
        ).json()

    def get_branch(self, project_id, branch_id):
        return self._check(
            self.session.get(self._url(f"/projects/{project_id}/branches/{branch_id}")),
            f"GET branch {branch_id}",
        ).json()

    def create_branch(self, project_id, name, commit_id):
        return self._check(
            self.session.post(
                self._url(f"/projects/{project_id}/branches"),
                json={"@type": "Branch", "name": name, "head": {"@id": commit_id}},
            ),
            f"POST branch ({name})",
        ).json()

    def create_commit(self, project_id, branch_id, elements, description=""):
        change = [{"@type": "DataVersion", "payload": e} for e in elements]
        return self._check(
            self.session.post(
                self._url(f"/projects/{project_id}/commits?branchId={branch_id}"),
                json={"@type": "Commit", "description": description, "change": change},
            ),
            f"POST commit to branch {branch_id}",
        ).json()

    def get_elements(self, project_id, commit_id):
        return self._check(
            self.session.get(self._url(f"/projects/{project_id}/commits/{commit_id}/elements")),
            f"GET elements at {commit_id[:8]}...",
        ).json()


def branch_head(client, project_id, branch_id):
    return client.get_branch(project_id, branch_id)["head"]["@id"]


def main():
    parser = argparse.ArgumentParser(description="Experiment 6 — KC bridge + Remote Flexo")
    parser.add_argument("--cleanup", action="store_true", help="Delete the project after the experiment")
    args = parser.parse_args()

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
    print("\nStep 3: Loading MTG-KC ancestor model onto Master...")
    commit = client.create_commit(project_id, master_id, ANCESTOR_ELEMENTS, "Load ancestor state X")
    print(f"  Ancestor commit: {commit['@id']}")

    # --- Step 4: Verify ancestor constraints ---
    print("\nStep 4: Verifying ancestor constraints (Python + SHACL + SPARQL)...")
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
    print("\nStep 6: Applying commits...")
    u_elements = apply_commit_u(ANCESTOR_ELEMENTS)
    commit_u = client.create_commit(project_id, branch_a_id, u_elements, "Commit u: remove BG + dependent faces")
    print(f"  commit u on branch-a: {commit_u['@id']}")

    v_elements = apply_commit_v(ANCESTOR_ELEMENTS)
    commit_v = client.create_commit(project_id, branch_b_id, v_elements, "Commit v: enrich BG + BRG")
    print(f"  commit v on branch-b: {commit_v['@id']}")

    # --- Step 7: Verify individual validity ---
    print("\nStep 7: Verifying individual validity...")
    elements_a = client.get_elements(project_id, branch_head(client, project_id, branch_a_id))
    run_oracle(elements_a, "branch-a")

    elements_b = client.get_elements(project_id, branch_head(client, project_id, branch_b_id))
    run_oracle(elements_b, "branch-b")

    # --- Step 8: Construct cross-application states ---
    print("\nStep 8: Constructing cross-application states...")

    branch_a_head = branch_head(client, project_id, branch_a_id)
    branch_uv = client.create_branch(project_id, "branch-uv", branch_a_head)
    branch_uv_id = branch_uv["@id"]
    uv_elements = apply_commit_v_on_u_state(u_elements)
    commit_uv = client.create_commit(project_id, branch_uv_id, uv_elements, "Apply v on top of u")
    print(f"  branch-uv: {branch_uv_id} (commit {commit_uv['@id']})")

    branch_b_head = branch_head(client, project_id, branch_b_id)
    branch_vu = client.create_branch(project_id, "branch-vu", branch_b_head)
    branch_vu_id = branch_vu["@id"]
    vu_elements = apply_commit_u_on_v_state(v_elements)
    commit_vu = client.create_commit(project_id, branch_vu_id, vu_elements, "Apply u on top of v")
    print(f"  branch-vu: {branch_vu_id} (commit {commit_vu['@id']})")

    # --- Step 9: Evaluate oracle on cross-application states ---
    print("\nStep 9: Evaluating oracle on cross-application states...")
    elements_uv = client.get_elements(project_id, branch_head(client, project_id, branch_uv_id))
    run_oracle(elements_uv, "branch-uv")

    elements_vu = client.get_elements(project_id, branch_head(client, project_id, branch_vu_id))
    run_oracle(elements_vu, "branch-vu")

    # --- Summary ---
    print("\n============================================")
    print("  Experiment 6 complete.")
    print("  C1-C4: Python checks (same as Exp 5)")
    print("  C5: SHACL validation via pyshacl bridge")
    print("  C6: SPARQL query via rdflib bridge")
    print("============================================")

    if args.cleanup:
        print(f"\nCleaning up: deleting project {project_id}...")
        client.delete_project(project_id)
        print("  Deleted.")
    else:
        print(f"\nProject '{PROJECT_NAME}' retained (id: {project_id}).")


if __name__ == "__main__":
    main()
