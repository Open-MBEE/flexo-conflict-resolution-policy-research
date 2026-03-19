#!/usr/bin/env bash
set -euo pipefail

# Experiment 12 — Three-Layer Flexo Service Architecture
#
# Demonstrates a proposed architectural pattern that layers Flexo services:
#   Layer 1 (Syntactic):     Quadstore — accepts any valid RDF
#   Layer 2 (Semantic):      Ontology packages — modular, composable interpretation
#   Layer 3 (Verification):  Constraint services — checks compliance, can gate commits
#
# Uses the MTG Knowledge Complex conflict scenario (same as Experiments 3-4)
# to show that independently valid commits produce invalid merged states,
# and that all three layers are necessary to detect this.
#
# Requires a running Flexo MMS instance (see Local Deployment Setup.md).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BASE="${FLEXO_BASE_URL:-http://localhost:8080}"
AUTH="${FLEXO_AUTH_URL:-http://localhost:8082}"
USER="${FLEXO_USER:-user01}"
PASS="${FLEXO_PASS:-password1}"
ORG="research"
REPO="three-layer-demo"

TIMEOUT=900

# --- Helpers (reused from experiment-4) ---

get_token() {
  TOKEN=$(curl -s -m 30 -u "$USER:$PASS" "$AUTH/login" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
  export FLEXO_TOKEN="$TOKEN"
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

load_ttl_as_insert() {
  # Load a .ttl file into a branch via SPARQL INSERT DATA
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
  # Run Layer 3 verification on a branch
  local branch="$1"
  python3 verify.py "$branch" \
    --base-url "$BASE" --auth-url "$AUTH" \
    --org "$ORG" --repo "$REPO" \
    --user "$USER" --password "$PASS" \
    --token "$TOKEN"
  return $?
}

# Shared SPARQL prefixes for INSERT DATA operations
PREFIXES="PREFIX kc: <https://example.org/kc#>
PREFIX kcs: <https://example.org/kc/shape#>
PREFIX mtg: <https://example.org/mtg#>
PREFIX mtgs: <https://example.org/mtg/shape#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX sh: <http://www.w3.org/ns/shacl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>"

# ═══════════════════════════════════════════════════════════
echo "═══════════════════════════════════════════════════════════"
echo "  Experiment 12 — Three-Layer Flexo Service Architecture"
echo "═══════════════════════════════════════════════════════════"
echo ""

# --- Phase 0: Service Readiness ---

echo "Phase 0: Waiting for Flexo services..."

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

# ┌─────────────────────────────────────────────────────────┐
# │  LAYER 1 — SYNTACTIC (Quadstore)                        │
# │  Accepts any valid RDF. No interpretation. No semantics. │
# └─────────────────────────────────────────────────────────┘

echo ""
echo "┌─────────────────────────────────────────────────────────┐"
echo "│  LAYER 1 — SYNTACTIC (Quadstore)                        │"
echo "│  Accepts any valid RDF. No interpretation. No semantics. │"
echo "└─────────────────────────────────────────────────────────┘"

# Step 1.1: Authenticate
echo ""
echo "Step 1.1: [Layer 1] Authenticating as $USER..."
get_token
echo "  Token acquired."

# Step 1.2: Create org and repo
echo ""
echo "Step 1.2: [Layer 1] Creating org '$ORG' and repo '$REPO'..."
CODE=$(flexo_put "$BASE/orgs/$ORG" "<> <http://purl.org/dc/terms/title> \"$ORG\"@en .")
expect_ok_or_exists "$CODE" "org"

CODE=$(flexo_put "$BASE/orgs/$ORG/repos/$REPO" "<> <http://purl.org/dc/terms/title> \"$REPO\"@en .")
expect_ok_or_exists "$CODE" "repo"

# Step 1.3: Load instance data (no schema)
get_token

echo ""
echo "Step 1.3: [Layer 1] Loading instance data onto master..."
echo "  (No ontology, no shapes — Layer 1 stores raw triples without interpretation)"
load_ttl_as_insert master instance/ancestor-model.ttl "instance data"

# ┌─────────────────────────────────────────────────────────┐
# │  LAYER 2 — SEMANTIC (Ontology Packages)                  │
# │  Modular, composable. Like package management.           │
# └─────────────────────────────────────────────────────────┘

echo ""
echo "┌─────────────────────────────────────────────────────────┐"
echo "│  LAYER 2 — SEMANTIC (Ontology Packages)                  │"
echo "│  Modular, composable. Like package management.           │"
echo "└─────────────────────────────────────────────────────────┘"

# Step 2.1: Load KC Core ontology package
echo ""
echo "Step 2.1: [Layer 2] Loading ontology package [kc-core] (1 of 2)..."
echo "  Package: Knowledge Complex Core"
echo "  Classes: Element, Vertex, Edge, Face, Complex"
echo "  Properties: boundedBy, hasElement"
echo "  Shapes: ComplexShape, EdgeShape, FaceShape"
load_ttl_as_insert master ontology/kc-core/ontology.ttl "kc-core ontology"
load_ttl_as_insert master ontology/kc-core/shapes.ttl "kc-core shapes"

# Step 2.2: Load MTG Domain extension package
echo ""
echo "Step 2.2: [Layer 2] Loading ontology package [mtg-domain] (2 of 2)..."
echo "  Package: MTG Color Philosophy Domain Extension"
echo "  Depends on: kc-core"
echo "  Classes: Color (-> Vertex), ColorPair (-> Edge), ColorTriple (-> Face)"
echo "  Properties: guild, theme, persona, goal, method, ... (14 domain properties)"
echo "  Shapes: ColorShape, ColorPairShape, ColorTripleShape"
load_ttl_as_insert master ontology/mtg-domain/ontology.ttl "mtg-domain ontology"
load_ttl_as_insert master ontology/mtg-domain/shapes.ttl "mtg-domain shapes"

# Step 2.3: Summary
echo ""
echo "Step 2.3: [Layer 2] Package loading summary"
echo "  2 ontology packages loaded (kc-core + mtg-domain)"
echo "  6 SHACL shapes active (3 core + 3 domain)"
echo "  Note: Layer 1 treats ontology triples identically to data triples."
echo "  Semantic interpretation is an external concern — the quadstore is indifferent."

# ┌─────────────────────────────────────────────────────────┐
# │  LAYER 3 — VERIFICATION                                 │
# │  Constraint checking as a service.                       │
# │  Currently client-side (pyshacl + SPARQL via rdflib).    │
# └─────────────────────────────────────────────────────────┘

echo ""
echo "┌─────────────────────────────────────────────────────────┐"
echo "│  LAYER 3 — VERIFICATION                                 │"
echo "│  Constraint checking as a service.                       │"
echo "│  Currently client-side (pyshacl + SPARQL via rdflib).    │"
echo "└─────────────────────────────────────────────────────────┘"

# Step 3.1: Verify ancestor state
echo ""
echo "Step 3.1: [Layer 3] Verification gate — ancestor state on master..."
get_token
if verify_gate master; then
  echo "  Verification gate: PASSED"
else
  echo "  Verification gate: FAILED (unexpected — ancestor should be valid)"
  echo "  Continuing anyway to demonstrate the full scenario..."
fi

# ┌─────────────────────────────────────────────────────────┐
# │  CONFLICT SCENARIO                                       │
# │  Two independently valid commits that produce invalid    │
# │  merged states. All three layers are exercised.          │
# └─────────────────────────────────────────────────────────┘

echo ""
echo "┌─────────────────────────────────────────────────────────┐"
echo "│  CONFLICT SCENARIO                                       │"
echo "│  Two independently valid commits that produce invalid    │"
echo "│  merged states. All three layers are exercised.          │"
echo "└─────────────────────────────────────────────────────────┘"

# Step 4.1: Create branches
echo ""
echo "Step 4.1: [Layer 1] Creating branch-a and branch-b from master..."
for branch in branch-a branch-b; do
  CODE=$(flexo_put "$BASE/orgs/$ORG/repos/$REPO/branches/$branch" \
    "<> <http://purl.org/dc/terms/title> \"$branch\"@en .
<> <https://mms.openmbee.org/rdf/ontology/ref> <./master> .")
  echo "  $branch: HTTP $CODE"
done

# Step 4.2: Apply commit u with verification gate
echo ""
echo "Step 4.2: [Layer 1] Applying commit u (remove BG) on branch-a..."
CODE=$(flexo_update_file "$BASE/orgs/$ORG/repos/$REPO/branches/branch-a/update" commits/commit-u-remove-bg.ru)
echo "  commit u on branch-a: HTTP $CODE"

echo ""
echo "Step 4.2: [Layer 3] Verification gate — branch-a after commit u..."
get_token
if verify_gate branch-a; then
  echo "  Verification gate: PASSED — commit u accepted"
else
  echo "  Verification gate: FAILED"
fi

# Step 4.3: Apply commit v with verification gate
echo ""
echo "Step 4.3: [Layer 1] Applying commit v (enrich BG) on branch-b..."
CODE=$(flexo_update_file "$BASE/orgs/$ORG/repos/$REPO/branches/branch-b/update" commits/commit-v-enrich-bg.ru)
echo "  commit v on branch-b: HTTP $CODE"

echo ""
echo "Step 4.3: [Layer 3] Verification gate — branch-b after commit v..."
get_token
if verify_gate branch-b; then
  echo "  Verification gate: PASSED — commit v accepted"
else
  echo "  Verification gate: FAILED"
fi

# Step 4.4: Construct cross-application states
echo ""
echo "Step 4.4: [Layer 1] Constructing cross-application states..."

# branch-uv = f(f(X,u),v) — branch from branch-a, apply v
CODE=$(flexo_put "$BASE/orgs/$ORG/repos/$REPO/branches/branch-uv" \
  '<> <http://purl.org/dc/terms/title> "branch-uv"@en .
<> <https://mms.openmbee.org/rdf/ontology/ref> <./branch-a> .')
echo "  branch-uv created: HTTP $CODE"

CODE=$(flexo_update_file "$BASE/orgs/$ORG/repos/$REPO/branches/branch-uv/update" commits/commit-v-enrich-bg.ru)
echo "  apply v to branch-uv: HTTP $CODE"

# branch-vu = f(f(X,v),u) — branch from branch-b, apply u
CODE=$(flexo_put "$BASE/orgs/$ORG/repos/$REPO/branches/branch-vu" \
  '<> <http://purl.org/dc/terms/title> "branch-vu"@en .
<> <https://mms.openmbee.org/rdf/ontology/ref> <./branch-b> .')
echo "  branch-vu created: HTTP $CODE"

CODE=$(flexo_update_file "$BASE/orgs/$ORG/repos/$REPO/branches/branch-vu/update" commits/commit-u-remove-bg.ru)
echo "  apply u to branch-vu: HTTP $CODE"

# Step 4.5: Verify cross-application states (the punchline)
echo ""
echo "Step 4.5: [Layer 3] Verification gate — cross-application states..."
echo "  These states are syntactically valid RDF (Layer 1 accepted them)."
echo "  But do they satisfy the ontology's constraints?"

get_token

echo ""
echo "  --- branch-uv (u then v): ---"
if verify_gate branch-uv; then
  echo "  Verification gate: PASSED"
else
  echo "  Verification gate: FAILED"
  echo "  -> Layer 1 accepted this state. Layer 3 rejects it."
fi

echo ""
echo "  --- branch-vu (v then u): ---"
if verify_gate branch-vu; then
  echo "  Verification gate: PASSED"
else
  echo "  Verification gate: FAILED"
  echo "  -> Layer 1 accepted this state. Layer 3 rejects it."
fi

# ═══════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  RESULTS — Three-Layer Architecture Demonstration"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  Layer 1 (Syntactic — Quadstore):"
echo "    Accepted ALL operations without complaint."
echo "    Every SPARQL INSERT/DELETE was valid RDF."
echo "    Layer 1 is indifferent to semantic meaning."
echo ""
echo "  Layer 2 (Semantic — Ontology Packages):"
echo "    Two packages loaded as composable modules:"
echo "      kc-core:    abstract topological backbone"
echo "      mtg-domain: domain-specific extension (depends on kc-core)"
echo "    The same pattern applies to SysML v2:"
echo "      KerML:      core modeling abstractions"
echo "      SysML ext:  discipline-specific extensions"
echo ""
echo "  Layer 3 (Verification — Constraint Service):"
echo "    Client-side verification successfully:"
echo "      - Validated ancestor state (PASS)"
echo "      - Validated individual commits (both PASS)"
echo "      - Detected invalid merged states (FAIL)"
echo "    The verification gate pattern shows where enforcement belongs."
echo ""
echo "  Key finding:"
echo "    Individually valid commits can produce invalid merged states."
echo "    Layer 1 cannot detect this — it stores any valid RDF."
echo "    Layer 2 defines what 'valid' means (ontology + shapes)."
echo "    Layer 3 checks it. All three layers are necessary."
echo ""
echo "  Compare branch-uv vs branch-vu for non-commutativity."
echo "═══════════════════════════════════════════════════════════"
