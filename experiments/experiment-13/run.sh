#!/usr/bin/env bash
set -euo pipefail

# Experiment 13 — KC Python API as Verification Service
#
# Same three service concerns as Experiment 12, but the verification concern
# is now served by the mtg-kc Python API instead of raw pyshacl + SPARQL.
#
# This is a better proxy for future KerML/SysML v2 verification services:
# the domain-typed Python API (build_mtg_schema, KnowledgeComplex, named
# queries) abstracts SHACL/SPARQL as implementation details — the same
# pattern a KerML compiler check service would follow.
#
# Usage:
#   export FLEXO_TOKEN="eyJhbGci..."
#   ./run.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BASE="${FLEXO_BASE_URL:-https://try-layer1.starforge.app}"
ORG="research"
REPO="kc-api-demo-$(date +%s)"
TIMEOUT=120

if [[ -z "${FLEXO_TOKEN:-}" ]]; then
  echo "ERROR: FLEXO_TOKEN environment variable is not set."
  echo 'Usage: export FLEXO_TOKEN="eyJhbGci..." && ./run.sh'
  exit 1
fi
TOKEN="$FLEXO_TOKEN"

# --- Helpers ---

flexo_put() {
  local url="$1" body="$2"
  curl -s -m "$TIMEOUT" -o /dev/null -w "%{http_code}" \
    -X PUT "$url" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: text/turtle" \
    -d "$body"
}

flexo_update() {
  local url="$1" body="$2"
  curl -s -m "$TIMEOUT" -o /dev/null -w "%{http_code}" \
    -X POST "$url" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/sparql-update" \
    -d "$body"
}

flexo_update_file() {
  local url="$1" file="$2"
  curl -s -m "$TIMEOUT" -o /dev/null -w "%{http_code}" \
    -X POST "$url" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/sparql-update" \
    --data-binary @"$file"
}

expect_ok_or_exists() {
  local code="$1" label="$2"
  if [[ "$code" =~ ^2 ]]; then
    echo "  $label: HTTP $code"
  elif [[ "$code" == "409" ]]; then
    echo "  $label: HTTP $code (already exists — OK)"
  else
    echo "  $label: HTTP $code — UNEXPECTED (aborting)"
    exit 1
  fi
}

load_ttl_as_insert() {
  local branch="$1" file="$2" label="$3"
  local TRIPLES
  TRIPLES=$(grep -v '^@prefix' "$file" | grep -v '^$' | grep -v '^#')
  CODE=$(flexo_update "$BASE/orgs/$ORG/repos/$REPO/branches/$branch/update" \
    "$PREFIXES
INSERT DATA {
$TRIPLES
}")
  echo "  $label: HTTP $CODE"
}

verify_gate() {
  local branch="$1"
  python3 verify.py "$branch" \
    --base-url "$BASE" \
    --org "$ORG" --repo "$REPO" \
    --token "$TOKEN"
  return $?
}

PREFIXES="PREFIX kc: <https://example.org/kc#>
PREFIX kcs: <https://example.org/kc/shape#>
PREFIX mtg: <https://example.org/mtg#>
PREFIX mtgs: <https://example.org/mtg/shape#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX sh: <http://www.w3.org/ns/shacl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>"

echo "═══════════════════════════════════════════════════════════"
echo "  Experiment 13 — KC Python API as Verification Service"
echo "═══════════════════════════════════════════════════════════"
echo ""

# --- Phase 0: Service Readiness ---

echo "Phase 0: Checking remote Flexo service..."
echo "  Target: $BASE"
echo "  Repo:   $REPO (unique per run)"

MAX_WAIT=30
WAITED=0
while true; do
  HTTP=$(curl -s -m 5 -o /dev/null -w "%{http_code}" "$BASE/" 2>/dev/null) || HTTP="000"
  if [[ "$HTTP" != "000" && "$HTTP" != "502" && "$HTTP" != "503" ]]; then
    break
  fi
  if (( WAITED >= MAX_WAIT )); then
    echo "  ERROR: Flexo not responding after ${MAX_WAIT}s."
    exit 1
  fi
  sleep 3
  WAITED=$((WAITED + 3))
  echo "  waiting... (${WAITED}s)"
done
echo "  Flexo responding (HTTP $HTTP)."

# ┌─────────────────────────────────────────────────────────┐
# │  STORAGE — Version-controlled RDF persistence            │
# └─────────────────────────────────────────────────────────┘

echo ""
echo "┌─────────────────────────────────────────────────────────┐"
echo "│  STORAGE — Version-controlled RDF persistence            │"
echo "│  Flexo Layer 0 (Quadstore) + Layer 1 (MMS core).        │"
echo "│  Accepts any valid RDF. Indifferent to interpretation.   │"
echo "└─────────────────────────────────────────────────────────┘"

echo ""
echo "Step 1.1: [Storage] Creating org '$ORG' and repo '$REPO'..."
CODE=$(flexo_put "$BASE/orgs/$ORG" "<> <http://purl.org/dc/terms/title> \"$ORG\"@en .")
expect_ok_or_exists "$CODE" "org"

CODE=$(flexo_put "$BASE/orgs/$ORG/repos/$REPO" "<> <http://purl.org/dc/terms/title> \"$REPO\"@en .")
expect_ok_or_exists "$CODE" "repo"

echo ""
echo "Step 1.2: [Storage] Loading instance data onto master..."
load_ttl_as_insert master instance/ancestor-model.ttl "instance data"

# ┌─────────────────────────────────────────────────────────┐
# │  SCHEMA — Modular ontology packages                      │
# └─────────────────────────────────────────────────────────┘

echo ""
echo "┌─────────────────────────────────────────────────────────┐"
echo "│  SCHEMA — Modular ontology packages                      │"
echo "│  Defines vocabulary, types, and well-formedness rules.   │"
echo "│  Composable like package management.                     │"
echo "└─────────────────────────────────────────────────────────┘"

echo ""
echo "Step 2.1: [Schema] Loading ontology package [kc-core] (1 of 2)..."
echo "  Package: Knowledge Complex Core"
load_ttl_as_insert master ontology/kc-core/ontology.ttl "kc-core ontology"
load_ttl_as_insert master ontology/kc-core/shapes.ttl "kc-core shapes"

echo ""
echo "Step 2.2: [Schema] Loading ontology package [mtg-domain] (2 of 2)..."
echo "  Package: MTG Color Philosophy Domain Extension"
echo "  Depends on: kc-core"
load_ttl_as_insert master ontology/mtg-domain/ontology.ttl "mtg-domain ontology"
load_ttl_as_insert master ontology/mtg-domain/shapes.ttl "mtg-domain shapes"

echo ""
echo "Step 2.3: [Schema] Package loading summary"
echo "  2 ontology packages loaded (kc-core + mtg-domain)"
echo "  Note: the verification service gets its schema from build_mtg_schema(),"
echo "  not from these stored triples. The .ttl files are loaded into Flexo for"
echo "  completeness — a production deployment would serve schema from the API."

# ┌─────────────────────────────────────────────────────────┐
# │  VERIFICATION — KC Python API as constraint service      │
# └─────────────────────────────────────────────────────────┘

echo ""
echo "┌─────────────────────────────────────────────────────────┐"
echo "│  VERIFICATION — KC Python API as constraint service      │"
echo "│  Uses mtg-kc: domain-typed validation + named queries.   │"
echo "│  Proxy for future KerML/SysML v2 verification services.  │"
echo "└─────────────────────────────────────────────────────────┘"

echo ""
echo "Step 3.1: [Verification] Gate check — ancestor state on master..."
if verify_gate master; then
  echo "  Verification gate: PASSED"
else
  echo "  Verification gate: FAILED (unexpected — ancestor should be valid)"
  echo "  Continuing anyway to demonstrate the full scenario..."
fi

# ┌─────────────────────────────────────────────────────────┐
# │  CONFLICT SCENARIO                                       │
# └─────────────────────────────────────────────────────────┘

echo ""
echo "┌─────────────────────────────────────────────────────────┐"
echo "│  CONFLICT SCENARIO                                       │"
echo "│  Two independently valid commits that produce invalid    │"
echo "│  merged states. All three concerns are exercised.        │"
echo "└─────────────────────────────────────────────────────────┘"

echo ""
echo "Step 4.1: [Storage] Creating branch-a and branch-b from master..."
for branch in branch-a branch-b; do
  CODE=$(flexo_put "$BASE/orgs/$ORG/repos/$REPO/branches/$branch" \
    "<> <http://purl.org/dc/terms/title> \"$branch\"@en .
<> <https://mms.openmbee.org/rdf/ontology/ref> <./master> .")
  echo "  $branch: HTTP $CODE"
done

echo ""
echo "Step 4.2: [Storage] Applying commit u (remove BG) on branch-a..."
CODE=$(flexo_update_file "$BASE/orgs/$ORG/repos/$REPO/branches/branch-a/update" commits/commit-u-remove-bg.ru)
echo "  commit u on branch-a: HTTP $CODE"

echo ""
echo "Step 4.2: [Verification] Gate check — branch-a after commit u..."
if verify_gate branch-a; then
  echo "  Verification gate: PASSED — commit u accepted"
else
  echo "  Verification gate: FAILED"
fi

echo ""
echo "Step 4.3: [Storage] Applying commit v (enrich BG) on branch-b..."
CODE=$(flexo_update_file "$BASE/orgs/$ORG/repos/$REPO/branches/branch-b/update" commits/commit-v-enrich-bg.ru)
echo "  commit v on branch-b: HTTP $CODE"

echo ""
echo "Step 4.3: [Verification] Gate check — branch-b after commit v..."
if verify_gate branch-b; then
  echo "  Verification gate: PASSED — commit v accepted"
else
  echo "  Verification gate: FAILED"
fi

echo ""
echo "Step 4.4: [Storage] Constructing cross-application states..."

CODE=$(flexo_put "$BASE/orgs/$ORG/repos/$REPO/branches/branch-uv" \
  '<> <http://purl.org/dc/terms/title> "branch-uv"@en .
<> <https://mms.openmbee.org/rdf/ontology/ref> <./branch-a> .')
echo "  branch-uv created: HTTP $CODE"
CODE=$(flexo_update_file "$BASE/orgs/$ORG/repos/$REPO/branches/branch-uv/update" commits/commit-v-enrich-bg.ru)
echo "  apply v to branch-uv: HTTP $CODE"

CODE=$(flexo_put "$BASE/orgs/$ORG/repos/$REPO/branches/branch-vu" \
  '<> <http://purl.org/dc/terms/title> "branch-vu"@en .
<> <https://mms.openmbee.org/rdf/ontology/ref> <./branch-b> .')
echo "  branch-vu created: HTTP $CODE"
CODE=$(flexo_update_file "$BASE/orgs/$ORG/repos/$REPO/branches/branch-vu/update" commits/commit-u-remove-bg.ru)
echo "  apply u to branch-vu: HTTP $CODE"

echo ""
echo "Step 4.5: [Verification] Gate check — cross-application states..."
echo "  Storage accepted both. Does the KC API?"

echo ""
echo "  --- branch-uv (u then v): ---"
if verify_gate branch-uv; then
  echo "  Verification gate: PASSED"
else
  echo "  Verification gate: FAILED"
  echo "  -> Storage accepted this state. KC API rejects it."
fi

echo ""
echo "  --- branch-vu (v then u): ---"
if verify_gate branch-vu; then
  echo "  Verification gate: PASSED"
else
  echo "  Verification gate: FAILED"
  echo "  -> Storage accepted this state. KC API rejects it."
fi

# ═══════════════════════════════════════════════════════════

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  RESULTS — KC Python API as Verification Service"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  Storage (Flexo Layer 0 + Layer 1):"
echo "    Accepted ALL operations. Indifferent to semantics."
echo ""
echo "  Schema (Ontology Packages):"
echo "    kc-core + mtg-domain loaded into Flexo."
echo "    Verification service gets schema from build_mtg_schema()."
echo ""
echo "  Verification (KC Python API):"
echo "    Reconstructed each branch state via the KC API:"
echo "      add_vertex(), add_edge(), add_face() — domain-typed validation."
echo "    Orphan detection via reconstruction gap."
echo "    Named queries for domain analysis."
echo ""
echo "  This is the pattern a KerML/SysML v2 verification service"
echo "  would follow: domain-typed API, SHACL/SPARQL abstracted away."
echo ""
echo "  Compare branch-uv vs branch-vu for non-commutativity."
echo "═══════════════════════════════════════════════════════════"
