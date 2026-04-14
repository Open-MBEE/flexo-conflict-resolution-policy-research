#!/usr/bin/env bash
set -euo pipefail

# Experiment 10 — MTG-KC Instance Only on Remote Layer 1 SPARQL API
#
# What is being tested:
#   Does the remote Layer 1 SPARQL API produce identical results to the
#   local Flexo instance (Experiment 3) for non-SysML RDF data?
#
# Data files imported from experiment-3:
#   ancestor-model.ttl, commit-u-remove-bg.ru, commit-v-enrich-bg.ru,
#   oracle/*.rq — all identical, linked via symlinks.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BASE="${FLEXO_BASE_URL:-https://try-layer1.starforge.app}"
ORG="research"
REPO="mtg-kc-remote-inst-$(date +%s)"
TIMEOUT=60

if [[ -z "${FLEXO_TOKEN:-}" ]]; then
  echo "ERROR: FLEXO_TOKEN environment variable is not set."
  echo 'Usage: export FLEXO_TOKEN="eyJhbGci..." && ./run.sh'
  exit 1
fi
TOKEN="$FLEXO_TOKEN"

# --- Helpers ---

query_branch() {
  local branch="$1" query_file="$2"
  curl -s -m "$TIMEOUT" -X POST "$BASE/orgs/$ORG/repos/$REPO/branches/$branch/query" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/sparql-query" \
    -H "Accept: application/json" \
    --data-binary @"$query_file"
}

print_results() {
  python3 -c "
import sys, json
data = json.load(sys.stdin)
bindings = data['results']['bindings']
if not bindings:
    print('  (no results — constraint satisfied)')
else:
    for b in bindings:
        print('  ', {k: v['value'] for k, v in b.items()})
"
}

run_oracle() {
  local branch="$1"
  echo ""
  echo "=== Oracle evaluation: $branch ==="
  for q in oracle/*.rq; do
    echo "--- $(basename "$q") ---"
    query_branch "$branch" "$q" | print_results
  done
}

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

# --- Step 1: Verify connectivity ---

echo "Step 1: Verifying connectivity to $BASE..."
HTTP=$(curl -s -m 10 -o /dev/null -w "%{http_code}" "$BASE/" 2>/dev/null) || HTTP="000"
if [[ "$HTTP" == "000" ]]; then
  echo "  ERROR: Cannot reach $BASE."
  exit 1
fi
echo "  Remote Layer 1 responding (HTTP $HTTP). Token pre-set."

# --- Step 2: Create Org and Repo ---

echo ""
echo "Step 2: Creating org '$ORG' and repo '$REPO'..."
CODE=$(flexo_put "$BASE/orgs/$ORG" "<> <http://purl.org/dc/terms/title> \"$ORG\"@en .")
expect_ok_or_exists "$CODE" "org"

CODE=$(flexo_put "$BASE/orgs/$ORG/repos/$REPO" "<> <http://purl.org/dc/terms/title> \"$REPO\"@en .")
expect_ok_or_exists "$CODE" "repo"

# --- Step 3: Load Ancestor Model ---

echo ""
echo "Step 3: Loading MTG-KC ancestor model onto master..."

TRIPLES=$(grep -v '^@prefix' ancestor-model.ttl | grep -v '^$')

CODE=$(flexo_update "$BASE/orgs/$ORG/repos/$REPO/branches/master/update" \
  "PREFIX kc: <https://example.org/kc#>
PREFIX mtg: <https://example.org/mtg#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
INSERT DATA {
$TRIPLES
}")
echo "  load: HTTP $CODE"

# --- Step 4: Verify Ancestor Constraints ---

echo ""
echo "Step 4: Verifying ancestor constraints..."
run_oracle master

# --- Step 5: Create Branches ---

echo ""
echo "Step 5: Creating branch-a and branch-b from master..."
for branch in branch-a branch-b; do
  CODE=$(flexo_put "$BASE/orgs/$ORG/repos/$REPO/branches/$branch" \
    "<> <http://purl.org/dc/terms/title> \"$branch\"@en .
<> <https://mms.openmbee.org/rdf/ontology/ref> <./master> .")
  echo "  $branch: HTTP $CODE"
done

# --- Step 6: Apply Commits ---

echo ""
echo "Step 6: Applying commits..."
CODE=$(flexo_update_file "$BASE/orgs/$ORG/repos/$REPO/branches/branch-a/update" commit-u-remove-bg.ru)
echo "  commit u (remove BG) on branch-a: HTTP $CODE"

CODE=$(flexo_update_file "$BASE/orgs/$ORG/repos/$REPO/branches/branch-b/update" commit-v-enrich-bg.ru)
echo "  commit v (enrich BG) on branch-b: HTTP $CODE"

# --- Step 7: Verify Individual Validity ---

echo ""
echo "Step 7: Verifying individual validity..."
run_oracle branch-a
run_oracle branch-b

# --- Step 8: Construct Cross-Application States ---

echo ""
echo "Step 8: Constructing cross-application states..."

CODE=$(flexo_put "$BASE/orgs/$ORG/repos/$REPO/branches/branch-uv" \
  '<> <http://purl.org/dc/terms/title> "branch-uv"@en .
<> <https://mms.openmbee.org/rdf/ontology/ref> <./branch-a> .')
echo "  branch-uv create: HTTP $CODE"

CODE=$(flexo_update_file "$BASE/orgs/$ORG/repos/$REPO/branches/branch-uv/update" commit-v-enrich-bg.ru)
echo "  apply v to branch-uv: HTTP $CODE"

CODE=$(flexo_put "$BASE/orgs/$ORG/repos/$REPO/branches/branch-vu" \
  '<> <http://purl.org/dc/terms/title> "branch-vu"@en .
<> <https://mms.openmbee.org/rdf/ontology/ref> <./branch-b> .')
echo "  branch-vu create: HTTP $CODE"

CODE=$(flexo_update_file "$BASE/orgs/$ORG/repos/$REPO/branches/branch-vu/update" commit-u-remove-bg.ru)
echo "  apply u to branch-vu: HTTP $CODE"

# --- Step 9: Evaluate Oracle ---

echo ""
echo "Step 9: Evaluating oracle on cross-application states..."
run_oracle branch-uv
run_oracle branch-vu

# --- Summary ---

echo ""
echo "============================================"
echo "  Experiment 10 complete."
echo "  Compare with Experiment 3 (local)."
echo "  Expected: identical results."
echo "============================================"
