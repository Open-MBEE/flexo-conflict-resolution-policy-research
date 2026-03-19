#!/usr/bin/env python3
"""
Experiment 8 — MTG-KC Model: Deletion Validation (non-SysML types)

Tests whether identity-only commit deletion works for elements with
non-SysML @type values (Color, ColorPair, ColorTriple). Then re-runs
the MTG-KC structural conflict scenario using proper deletion.

Usage:
    export FLEXO_BEARER_TOKEN="eyJhbGci..."
    python3 run.py [--cleanup]
"""

import argparse
import copy
import os
import sys

import requests

from model import (
    ANCESTOR_ELEMENTS,
    COMMIT_U_DELETE_IDS,
    COMMIT_V_ENRICHMENTS,
    build_commit_u_membership_update,
    apply_commit_v,
)
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
        """Delete elements via identity-only commit."""
        change = [{"identity": {"@id": eid}} for eid in element_ids]
        return self._check(
            self.session.post(
                self._url(f"/projects/{project_id}/commits?branchId={branch_id}"),
                json={"@type": "Commit", "description": description, "change": change},
            ),
            f"POST delete commit ({len(element_ids)} elements)",
        ).json()

    def commit_mixed(self, project_id, branch_id, updates=None, deletes=None, description=""):
        """Commit with both updates (DataVersion+payload) and deletes (identity-only)."""
        change = []
        for e in (updates or []):
            change.append({"@type": "DataVersion", "payload": e})
        for eid in (deletes or []):
            change.append({"identity": {"@id": eid}})
        return self._check(
            self.session.post(
                self._url(f"/projects/{project_id}/commits?branchId={branch_id}"),
                json={"@type": "Commit", "description": description, "change": change},
            ),
            f"POST mixed commit",
        ).json()

    def get_elements(self, project_id, commit_id):
        return self._check(
            self.session.get(self._url(f"/projects/{project_id}/commits/{commit_id}/elements")),
            f"GET elements at {commit_id[:8]}...",
        ).json()


def branch_head(client, project_id, branch_id):
    return client.get_branch(project_id, branch_id)["head"]["@id"]


def main():
    parser = argparse.ArgumentParser(description="Experiment 8 — MTG-KC deletion validation")
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()

    if not BEARER_TOKEN:
        print("ERROR: FLEXO_BEARER_TOKEN not set.")
        sys.exit(1)

    client = FlexoClient(BASE_URL, BEARER_TOKEN)

    # ================================================================
    # PHASE 1: Validate deletion with non-SysML types
    # ================================================================
    print("=" * 60)
    print("PHASE 1: Validate identity-only deletion (non-SysML types)")
    print("=" * 60)

    print("\nStep 1.1: Creating test project...")
    project = client.create_project("exp8-deletion-test")
    pid = project["@id"]
    branches = client.list_branches(pid)
    bid = branches[0]["@id"]

    print("Step 1.2: Committing MTG-KC elements (Color, ColorPair types)...")
    test_elements = [
        {"@id": "mtg:White", "@type": "Color", "name": "White", "goal": "peace"},
        {"@id": "mtg:Black", "@type": "Color", "name": "Black", "goal": "satisfaction"},
        {"@id": "mtg:BG", "@type": "ColorPair", "name": "Golgari", "guild": "golgari"},
        {"@id": "mtg:_complex", "@type": "Complex", "members": ["mtg:White", "mtg:Black", "mtg:BG"]},
    ]
    client.create_commit(pid, bid, test_elements, "Load test elements")
    head = branch_head(client, pid, bid)
    before = client.get_elements(pid, head)
    before_ids = {e["@id"] for e in before}
    print(f"  Elements before: {sorted(before_ids)}")

    print("Step 1.3: Deleting BG via identity-only commit...")
    # API strips mtg: prefix, so delete "BG" not "mtg:BG"
    client.delete_elements(pid, bid, ["BG"], "Delete BG")
    head = branch_head(client, pid, bid)
    after = client.get_elements(pid, head)
    after_ids = {e["@id"] for e in after}
    print(f"  Elements after:  {sorted(after_ids)}")

    deleted = before_ids - after_ids
    if "BG" in deleted and "White" in after_ids and "_complex" in after_ids:
        print("\n  ✓ PASS: BG (ColorPair) deleted, others retained")
        deletion_works = True
    else:
        print(f"\n  ✗ FAIL: deleted={deleted}, remaining={after_ids}")
        deletion_works = False

    client.delete_project(pid)

    if not deletion_works:
        print("\nDeletion does not work for non-SysML types. Aborting Phase 2.")
        return

    # ================================================================
    # PHASE 2: MTG-KC conflict scenario with proper deletion
    # ================================================================
    print("\n" + "=" * 60)
    print("PHASE 2: MTG-KC conflict scenario with identity-only deletion")
    print("=" * 60)

    print(f"\nStep 2.1: Creating project...")
    project = client.create_project("mtg-kc-deletion-scenario")
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

    # Commit u: delete BG + dependent faces + update Complex.members
    updated_complex = build_commit_u_membership_update(ANCESTOR_ELEMENTS)
    client.commit_mixed(
        project_id, branch_a_id,
        updates=[updated_complex] if updated_complex else [],
        deletes=COMMIT_U_DELETE_IDS,
        description="Commit u: delete BG + dependent faces",
    )
    print(f"  commit u on branch-a: deleted {COMMIT_U_DELETE_IDS}")

    # Commit v: enrich BG + BRG
    v_elements = apply_commit_v(ANCESTOR_ELEMENTS)
    # Only commit the changed elements
    v_changed = [e for e in v_elements if any(
        e["@id"] == orig["@id"] and e != orig for orig in ANCESTOR_ELEMENTS
    )]
    client.create_commit(project_id, branch_b_id, v_changed, "Commit v: enrich BG + BRG")
    print(f"  commit v on branch-b: enriched BG + BRG")

    print("\nStep 2.6: Verifying individual validity...")
    elements_a = client.get_elements(project_id, branch_head(client, project_id, branch_a_id))
    run_oracle(elements_a, "branch-a")
    elements_b = client.get_elements(project_id, branch_head(client, project_id, branch_b_id))
    run_oracle(elements_b, "branch-b")

    print("\nStep 2.7: Constructing cross-application states...")

    # branch-uv: from branch-a (BG deleted), apply v (enriches BG)
    branch_a_head = branch_head(client, project_id, branch_a_id)
    branch_uv = client.create_branch(project_id, "branch-uv", branch_a_head)
    branch_uv_id = branch_uv["@id"]
    # v enriches BG/BRG — but they've been deleted. Committing them re-creates them.
    client.create_commit(project_id, branch_uv_id, v_changed, "Apply v on top of u (re-creates deleted elements?)")
    print(f"  branch-uv created")

    # branch-vu: from branch-b (BG enriched), delete BG + faces
    branch_b_head = branch_head(client, project_id, branch_b_id)
    branch_vu = client.create_branch(project_id, "branch-vu", branch_b_head)
    branch_vu_id = branch_vu["@id"]
    updated_complex_b = build_commit_u_membership_update(elements_b)
    client.commit_mixed(
        project_id, branch_vu_id,
        updates=[updated_complex_b] if updated_complex_b else [],
        deletes=COMMIT_U_DELETE_IDS,
        description="Apply u on top of v (deletes enriched elements)",
    )
    print(f"  branch-vu created")

    print("\nStep 2.8: Evaluating oracle on cross-application states...")
    elements_uv = client.get_elements(project_id, branch_head(client, project_id, branch_uv_id))
    run_oracle(elements_uv, "branch-uv")
    elements_vu = client.get_elements(project_id, branch_head(client, project_id, branch_vu_id))
    run_oracle(elements_vu, "branch-vu")

    print("\n============================================")
    print("  Experiment 8 complete.")
    print("  Phase 1: Non-SysML deletion validation")
    print("  Phase 2: MTG-KC conflict with real deletion")
    print("  Compare with Exp 5 (no deletion) and")
    print("  Exp 3 (SPARQL deletion).")
    print("============================================")

    if args.cleanup:
        print(f"\nCleaning up...")
        client.delete_project(project_id)
        print("  Deleted.")


if __name__ == "__main__":
    main()
