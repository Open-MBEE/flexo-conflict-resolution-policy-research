#!/usr/bin/env python3
"""
Experiment 7 — Satellite Model: Deletion Validation (SysML v2 types)

Tests whether identity-only commit deletion works for elements with
SysML v2 @type values (PartDefinition). Then re-runs the satellite
conflict scenario from Experiment 2, using deletion to test what happens
when a cross-application commit modifies a deleted element.

Usage:
    export FLEXO_BEARER_TOKEN="eyJhbGci..."
    python3 run.py [--cleanup]
"""

import argparse
import os
import sys

import requests

from model import ANCESTOR_ELEMENTS, COMMIT_U_DELTAS, COMMIT_V_DELTAS, apply_deltas, compute_full_elements
from oracle import run_oracle

BASE_URL = os.environ.get("FLEXO_BASE_URL", "https://experimental.starforge.app").rstrip("/")
BEARER_TOKEN = os.environ.get("FLEXO_BEARER_TOKEN", "")


class FlexoClient:
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

    def delete_elements(self, project_id, branch_id, element_ids, description=""):
        """Delete elements via identity-only commit (no payload key)."""
        change = [{"identity": {"@id": eid}} for eid in element_ids]
        return self._check(
            self.session.post(
                self._url(f"/projects/{project_id}/commits?branchId={branch_id}"),
                json={"@type": "Commit", "description": description, "change": change},
            ),
            f"POST delete commit ({len(element_ids)} elements)",
        ).json()

    def get_elements(self, project_id, commit_id):
        return self._check(
            self.session.get(self._url(f"/projects/{project_id}/commits/{commit_id}/elements")),
            f"GET elements at {commit_id[:8]}...",
        ).json()


def branch_head(client, project_id, branch_id):
    return client.get_branch(project_id, branch_id)["head"]["@id"]


def main():
    parser = argparse.ArgumentParser(description="Experiment 7 — Satellite deletion validation")
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()

    if not BEARER_TOKEN:
        print("ERROR: FLEXO_BEARER_TOKEN not set.")
        sys.exit(1)

    client = FlexoClient(BASE_URL, BEARER_TOKEN)

    # ================================================================
    # PHASE 1: Validate deletion with SysML v2 types
    # ================================================================
    print("=" * 60)
    print("PHASE 1: Validate identity-only deletion (SysML v2 types)")
    print("=" * 60)

    print("\nStep 1.1: Creating test project...")
    project = client.create_project("exp7-deletion-test")
    pid = project["@id"]
    branches = client.list_branches(pid)
    bid = branches[0]["@id"]

    print("Step 1.2: Committing satellite ancestor elements...")
    client.create_commit(pid, bid, ANCESTOR_ELEMENTS, "Load ancestor")
    head = branch_head(client, pid, bid)
    before = client.get_elements(pid, head)
    before_ids = {e["@id"] for e in before}
    print(f"  Elements before: {sorted(before_ids)}")

    print("Step 1.3: Deleting CommSubsystem via identity-only commit...")
    client.delete_elements(pid, bid, ["CommSubsystem"], "Delete CommSubsystem")
    head = branch_head(client, pid, bid)
    after = client.get_elements(pid, head)
    after_ids = {e["@id"] for e in after}
    print(f"  Elements after:  {sorted(after_ids)}")

    deleted = before_ids - after_ids
    remaining = after_ids
    if "CommSubsystem" in deleted and "SatelliteSystem" in remaining and "ThermalSubsystem" in remaining:
        print("\n  ✓ PASS: CommSubsystem deleted, others retained")
        deletion_works = True
    else:
        print(f"\n  ✗ FAIL: deleted={deleted}, remaining={remaining}")
        deletion_works = False

    # Cleanup test project
    client.delete_project(pid)

    if not deletion_works:
        print("\nDeletion does not work for SysML v2 types. Aborting Phase 2.")
        return

    # ================================================================
    # PHASE 2: Satellite conflict scenario with deletion
    # ================================================================
    print("\n" + "=" * 60)
    print("PHASE 2: Satellite conflict scenario (same as Exp 2)")
    print("=" * 60)

    print(f"\nStep 2.1: Creating project...")
    project = client.create_project("satellite-scenario-deletion")
    project_id = project["@id"]
    branches = client.list_branches(project_id)
    master_id = branches[0]["@id"]

    print("Step 2.2: Loading ancestor model...")
    client.create_commit(project_id, master_id, ANCESTOR_ELEMENTS, "Load ancestor state X")

    print("Step 2.3: Verifying ancestor constraints...")
    master_head = branch_head(client, project_id, master_id)
    elements = client.get_elements(project_id, master_head)
    print(f"  {len(elements)} elements loaded.")
    run_oracle(elements, "master")

    print("\nStep 2.4: Creating branches...")
    branch_a = client.create_branch(project_id, "branch-a", master_head)
    branch_a_id = branch_a["@id"]
    branch_b = client.create_branch(project_id, "branch-b", master_head)
    branch_b_id = branch_b["@id"]

    print("\nStep 2.5: Applying commits...")
    u_elements = compute_full_elements(elements, COMMIT_U_DELTAS)
    client.create_commit(project_id, branch_a_id, u_elements, "Commit u: upgrade comms")
    v_elements = compute_full_elements(elements, COMMIT_V_DELTAS)
    client.create_commit(project_id, branch_b_id, v_elements, "Commit v: upgrade thermal")

    print("\nStep 2.6: Verifying individual validity...")
    elements_a = client.get_elements(project_id, branch_head(client, project_id, branch_a_id))
    run_oracle(elements_a, "branch-a")
    elements_b = client.get_elements(project_id, branch_head(client, project_id, branch_b_id))
    run_oracle(elements_b, "branch-b")

    print("\nStep 2.7: Constructing cross-application states...")
    # branch-uv: from branch-a, apply v's deltas
    branch_a_head = branch_head(client, project_id, branch_a_id)
    branch_uv = client.create_branch(project_id, "branch-uv", branch_a_head)
    branch_uv_id = branch_uv["@id"]
    uv_state = apply_deltas(elements_a, COMMIT_V_DELTAS)
    client.create_commit(project_id, branch_uv_id, uv_state, "Apply v on top of u")

    # branch-vu: from branch-b, apply u's deltas
    branch_b_head = branch_head(client, project_id, branch_b_id)
    branch_vu = client.create_branch(project_id, "branch-vu", branch_b_head)
    branch_vu_id = branch_vu["@id"]
    vu_state = apply_deltas(elements_b, COMMIT_U_DELTAS)
    client.create_commit(project_id, branch_vu_id, vu_state, "Apply u on top of v")

    print("\nStep 2.8: Evaluating oracle on cross-application states...")
    elements_uv = client.get_elements(project_id, branch_head(client, project_id, branch_uv_id))
    run_oracle(elements_uv, "branch-uv")
    elements_vu = client.get_elements(project_id, branch_head(client, project_id, branch_vu_id))
    run_oracle(elements_vu, "branch-vu")

    # --- Phase 2b: Test deletion in conflict scenario ---
    print("\n" + "-" * 60)
    print("PHASE 2b: Test what happens when deletion meets modification")
    print("-" * 60)
    print("\nCreating branch-del from master, deleting CommSubsystem...")
    branch_del = client.create_branch(project_id, "branch-del", master_head)
    branch_del_id = branch_del["@id"]
    client.delete_elements(project_id, branch_del_id, ["CommSubsystem"], "Delete CommSubsystem")

    print("Evaluating after deletion:")
    elements_del = client.get_elements(project_id, branch_head(client, project_id, branch_del_id))
    run_oracle(elements_del, "branch-del")

    print("\nCreating branch-del-then-u from branch-del, applying commit u (modifies CommSubsystem)...")
    branch_del_head = branch_head(client, project_id, branch_del_id)
    branch_del_u = client.create_branch(project_id, "branch-del-then-u", branch_del_head)
    branch_del_u_id = branch_del_u["@id"]
    # u modifies CommSubsystem — but it's been deleted. What happens?
    client.create_commit(project_id, branch_del_u_id, u_elements, "Apply u on deleted state")
    elements_del_u = client.get_elements(project_id, branch_head(client, project_id, branch_del_u_id))
    run_oracle(elements_del_u, "branch-del-then-u (CommSubsystem was deleted, then u re-adds it)")

    print("\n============================================")
    print("  Experiment 7 complete.")
    print("  Phase 1: Deletion validation")
    print("  Phase 2: Satellite conflict (same as Exp 2)")
    print("  Phase 2b: Deletion + modification interaction")
    print("============================================")

    if args.cleanup:
        print(f"\nCleaning up...")
        client.delete_project(project_id)
        print("  Deleted.")


if __name__ == "__main__":
    main()
