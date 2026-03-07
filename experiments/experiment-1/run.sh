#!/usr/bin/env bash
set -euo pipefail

# Experiment 1 — Satellite Power Subsystem Conflict Resolution
# Requires a running Flexo MMS instance (see Local Deployment Setup.md)
#
# Note: On Apple Silicon, Flexo services run under QEMU emulation.
# Individual API calls may take 5-30 seconds. The full experiment
# typically completes in 2-5 minutes.
#
# Known issue: If this script is killed mid-request (Ctrl-C, timeout),
# Fuseki may hold a write transaction lock. Subsequent write requests
# will hang. The only fix is to restart the Flexo stack:
#   cd flexo-mms-deployment/docker-compose && docker compose down && docker compose up -d

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BASE="${FLEXO_BASE_URL:-http://localhost:8080}"
AUTH="${FLEXO_AUTH_URL:-http://localhost:8082}"
USER="${FLEXO_USER:-user01}"
PASS="${FLEXO_PASS:-password1}"
ORG="research"
REPO="scenario-1"

# Timeout per request (seconds). Under QEMU emulation on Apple Silicon,
# repo creation can take 10-15 minutes (involves many Fuseki transactions).
# Other operations typically complete in 5-60 seconds.
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

# Expect a 2xx or 409 (already exists) — fail on anything else
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

# Wait for Layer 1 to respond (depends on Fuseki, the slowest to start)
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

# Wait for auth service (depends on Fuseki + LDAP)
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

# Additional settle time — under QEMU emulation, services may accept
# connections before they're fully ready to process requests
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

# Refresh token — repo creation can take 10-15 min under QEMU,
# long enough for the JWT from Step 1 to expire.
get_token

echo ""
echo "Step 3: Loading ancestor model onto master..."

# Convert Turtle to INSERT DATA (strip prefix lines — they go in the UPDATE header)
TRIPLES=$(grep -v '^@prefix' ancestor-model.ttl | grep -v '^$')

CODE=$(flexo_update "$BASE/orgs/$ORG/repos/$REPO/branches/master/update" \
  "PREFIX sat: <http://example.org/satellite/>
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
CODE=$(flexo_update_file "$BASE/orgs/$ORG/repos/$REPO/branches/branch-a/update" commit-u-upgrade-comms.ru)
echo "  commit u on branch-a: HTTP $CODE"

CODE=$(flexo_update_file "$BASE/orgs/$ORG/repos/$REPO/branches/branch-b/update" commit-v-upgrade-thermal.ru)
echo "  commit v on branch-b: HTTP $CODE"

# --- Step 7: Verify Individual Validity ---

echo ""
echo "Step 7: Verifying individual validity..."
# Refresh token in case earlier steps were slow
get_token
run_oracle branch-a
run_oracle branch-b

# --- Step 8: Construct Cross-Application States ---

echo ""
echo "Step 8: Constructing cross-application states..."

# branch-uv = f(f(X,u),v)
CODE=$(flexo_put "$BASE/orgs/$ORG/repos/$REPO/branches/branch-uv" \
  '<> <http://purl.org/dc/terms/title> "branch-uv"@en .
<> <https://mms.openmbee.org/rdf/ontology/ref> <./branch-a> .')
echo "  branch-uv create: HTTP $CODE"

CODE=$(flexo_update_file "$BASE/orgs/$ORG/repos/$REPO/branches/branch-uv/update" commit-v-upgrade-thermal.ru)
echo "  apply v to branch-uv: HTTP $CODE"

# branch-vu = f(f(X,v),u)
CODE=$(flexo_put "$BASE/orgs/$ORG/repos/$REPO/branches/branch-vu" \
  '<> <http://purl.org/dc/terms/title> "branch-vu"@en .
<> <https://mms.openmbee.org/rdf/ontology/ref> <./branch-b> .')
echo "  branch-vu create: HTTP $CODE"

CODE=$(flexo_update_file "$BASE/orgs/$ORG/repos/$REPO/branches/branch-vu/update" commit-u-upgrade-comms.ru)
echo "  apply u to branch-vu: HTTP $CODE"

# --- Step 9: Evaluate Oracle on Cross-Application States ---

echo ""
echo "Step 9: Evaluating oracle on cross-application states..."
# Refresh token in case earlier steps were slow
get_token
run_oracle branch-uv
run_oracle branch-vu

# --- Summary ---

echo ""
echo "============================================"
echo "  Experiment 1 complete."
echo "  Compare branch-uv and branch-vu results."
echo "  Expected violations: C2 (+5), C3 (+5),"
echo "  C6 (2 owners), name (2 values)."
echo "============================================"
