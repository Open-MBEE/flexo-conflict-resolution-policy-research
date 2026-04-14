#!/usr/bin/env bash
set -euo pipefail

# Experiment 3 — MTG Knowledge Complex: Structural Conflict (Local Flexo)
#
# What is being tested:
#   Can Flexo's SPARQL-based version control handle arbitrary RDF (not SysML),
#   branch it, and detect structural conflicts (orphaned triples after
#   topology deletion)?
#
# How:
#   Load the MTG color wheel (25 simplices) into Flexo via SPARQL INSERT DATA.
#   Curator A removes the BG edge + dependent faces (commit u on branch-a).
#   Curator B enriches BG + BRG with new properties (commit v on branch-b).
#   Cross-application states reveal orphaned properties (triples on deleted elements).
#
# Requires a running Flexo MMS instance (see experiments/experiment-1/README.md).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BASE="${FLEXO_BASE_URL:-http://localhost:8080}"
AUTH="${FLEXO_AUTH_URL:-http://localhost:8082}"
USER="${FLEXO_USER:-user01}"
PASS="${FLEXO_PASS:-password1}"
ORG="research"
REPO="mtg-kc-scenario-1"

TIMEOUT=900

# --- Helpers ---

get_token() {
  TOKEN=$(curl -s -m 30 -u "$USER:$PASS" "$AUTH/login" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
}

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

# --- Step 0: Wait for services ---

echo "Step 0: Waiting for Flexo services to be ready..."

MAX_WAIT=180
WAITED=0
while true; do
  HTTP=$(curl -s -m 5 -o /dev/null -w "%{http_code}" "$BASE/" 2>/dev/null) || HTTP="000"
  if [[ "$HTTP" != "000" && "$HTTP" != "502" && "$HTTP" != "503" ]]; then
    break
  fi
  if (( WAITED >= MAX_WAIT )); then
    echo "  ERROR: Layer 1 not responding after ${MAX_WAIT}s. Is Flexo running?"
    exit 1
  fi
  sleep 5
  WAITED=$((WAITED + 5))
  echo "  waiting for Layer 1... (${WAITED}s)"
done
echo "  Layer 1 responding (HTTP $HTTP)."

WAITED=0
while true; do
  HTTP=$(curl -s -m 5 -o /dev/null -w "%{http_code}" -u "$USER:$PASS" "$AUTH/login" 2>/dev/null) || HTTP="000"
  if [[ "$HTTP" =~ ^2 ]]; then
    break
  fi
  if (( WAITED >= MAX_WAIT )); then
    echo "  ERROR: Auth service not responding after ${MAX_WAIT}s."
    exit 1
  fi
  sleep 5
  WAITED=$((WAITED + 5))
  echo "  waiting for Auth... (${WAITED}s, HTTP $HTTP)"
done
echo "  Auth service ready."

echo "  Waiting 10s for services to settle..."
sleep 10

# --- Step 1: Authenticate ---

echo ""
echo "Step 1: Authenticating as $USER..."
get_token
echo "  Token acquired."

# --- Step 2: Create Org and Repo ---

echo ""
echo "Step 2: Creating org '$ORG' and repo '$REPO'..."
CODE=$(flexo_put "$BASE/orgs/$ORG" "<> <http://purl.org/dc/terms/title> \"$ORG\"@en .")
expect_ok_or_exists "$CODE" "org"

CODE=$(flexo_put "$BASE/orgs/$ORG/repos/$REPO" "<> <http://purl.org/dc/terms/title> \"$REPO\"@en .")
expect_ok_or_exists "$CODE" "repo"

# --- Step 3: Load Ancestor Model ---

get_token

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
get_token
run_oracle branch-a
run_oracle branch-b

# --- Step 8: Construct Cross-Application States ---

echo ""
echo "Step 8: Constructing cross-application states..."

# branch-uv = f(f(X,u),v) — branch from branch-a, apply v
CODE=$(flexo_put "$BASE/orgs/$ORG/repos/$REPO/branches/branch-uv" \
  '<> <http://purl.org/dc/terms/title> "branch-uv"@en .
<> <https://mms.openmbee.org/rdf/ontology/ref> <./branch-a> .')
echo "  branch-uv create: HTTP $CODE"

CODE=$(flexo_update_file "$BASE/orgs/$ORG/repos/$REPO/branches/branch-uv/update" commit-v-enrich-bg.ru)
echo "  apply v to branch-uv: HTTP $CODE"

# branch-vu = f(f(X,v),u) — branch from branch-b, apply u
CODE=$(flexo_put "$BASE/orgs/$ORG/repos/$REPO/branches/branch-vu" \
  '<> <http://purl.org/dc/terms/title> "branch-vu"@en .
<> <https://mms.openmbee.org/rdf/ontology/ref> <./branch-b> .')
echo "  branch-vu create: HTTP $CODE"

CODE=$(flexo_update_file "$BASE/orgs/$ORG/repos/$REPO/branches/branch-vu/update" commit-u-remove-bg.ru)
echo "  apply u to branch-vu: HTTP $CODE"

# --- Step 9: Evaluate Oracle on Cross-Application States ---

echo ""
echo "Step 9: Evaluating oracle on cross-application states..."
get_token
run_oracle branch-uv
run_oracle branch-vu

# --- Summary ---

echo ""
echo "============================================"
echo "  Experiment 3 complete."
echo "  Compare branch-uv and branch-vu results."
echo "  Expected: orphaned properties on BG/BRG"
echo "  (properties on elements no longer in the"
echo "   complex after commit u deletes them)."
echo "============================================"
