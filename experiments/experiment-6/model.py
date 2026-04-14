"""
MTG Knowledge Complex model for Experiment 5.

Mirrors the RDF instance from experiments 3–4, flattened to JSON elements
for the SysML v2 REST API. Each simplicial element (Color, ColorPair,
ColorTriple) becomes a JSON object with custom properties.

Commits are defined as property-level deltas matching the SPARQL
DELETE/INSERT semantics in experiments 3–4.
"""

import copy

# --- Ancestor State (X): Full 25-element MTG color wheel ---

ANCESTOR_ELEMENTS = [
    # Complex container (tracks membership)
    {
        "@id": "mtg:_complex",
        "@type": "Complex",
        "members": [
            "mtg:White", "mtg:Blue", "mtg:Black", "mtg:Red", "mtg:Green",
            "mtg:WU", "mtg:UB", "mtg:BR", "mtg:RG", "mtg:GW",
            "mtg:WB", "mtg:WR", "mtg:UG", "mtg:UR", "mtg:BG",
            "mtg:WUB", "mtg:UBR", "mtg:BRG", "mtg:WRG", "mtg:WUG",
            "mtg:WBG", "mtg:UBG", "mtg:URG", "mtg:WBR", "mtg:WUR",
        ],
    },
    # --- Vertices (Colors) ---
    {"@id": "mtg:White", "@type": "Color", "name": "White", "goal": "peace", "method": "order"},
    {"@id": "mtg:Blue", "@type": "Color", "name": "Blue", "goal": "perfection", "method": "knowledge"},
    {"@id": "mtg:Black", "@type": "Color", "name": "Black", "goal": "satisfaction", "method": "ruthlessness"},
    {"@id": "mtg:Red", "@type": "Color", "name": "Red", "goal": "freedom", "method": "action"},
    {"@id": "mtg:Green", "@type": "Color", "name": "Green", "goal": "harmony", "method": "acceptance"},
    # --- Edges (ColorPairs) ---
    {"@id": "mtg:WU", "@type": "ColorPair", "name": "Azorius", "guild": "azorius", "disposition": "adjacent", "theme": "design", "boundedBy": ["mtg:White", "mtg:Blue"]},
    {"@id": "mtg:UB", "@type": "ColorPair", "name": "Dimir", "guild": "dimir", "disposition": "adjacent", "theme": "growth_mindset", "boundedBy": ["mtg:Blue", "mtg:Black"]},
    {"@id": "mtg:BR", "@type": "ColorPair", "name": "Rakdos", "guild": "rakdos", "disposition": "adjacent", "theme": "independence", "boundedBy": ["mtg:Black", "mtg:Red"]},
    {"@id": "mtg:RG", "@type": "ColorPair", "name": "Gruul", "guild": "gruul", "disposition": "adjacent", "theme": "authenticity", "boundedBy": ["mtg:Red", "mtg:Green"]},
    {"@id": "mtg:GW", "@type": "ColorPair", "name": "Selesnya", "guild": "selesnya", "disposition": "adjacent", "theme": "community", "boundedBy": ["mtg:Green", "mtg:White"]},
    {"@id": "mtg:WB", "@type": "ColorPair", "name": "Orzhov", "guild": "orzhov", "disposition": "opposite", "theme": "tribalism", "boundedBy": ["mtg:White", "mtg:Black"]},
    {"@id": "mtg:WR", "@type": "ColorPair", "name": "Boros", "guild": "boros", "disposition": "opposite", "theme": "heroism", "boundedBy": ["mtg:White", "mtg:Red"]},
    {"@id": "mtg:UG", "@type": "ColorPair", "name": "Simic", "guild": "simic", "disposition": "opposite", "theme": "truth_seeking", "boundedBy": ["mtg:Blue", "mtg:Green"]},
    {"@id": "mtg:UR", "@type": "ColorPair", "name": "Izzet", "guild": "izzet", "disposition": "opposite", "theme": "creativity", "boundedBy": ["mtg:Blue", "mtg:Red"]},
    {"@id": "mtg:BG", "@type": "ColorPair", "name": "Golgari", "guild": "golgari", "disposition": "opposite", "theme": "profanity", "boundedBy": ["mtg:Black", "mtg:Green"]},
    # --- Faces (ColorTriples) ---
    {"@id": "mtg:WUB", "@type": "ColorTriple", "name": "Esper", "clan": "esper", "boundedBy": ["mtg:WU", "mtg:UB", "mtg:WB"], "thematic_triad": ["design", "growth_mindset", "tribalism"]},
    {"@id": "mtg:UBR", "@type": "ColorTriple", "name": "Grixis", "clan": "grixis", "boundedBy": ["mtg:UB", "mtg:BR", "mtg:UR"], "thematic_triad": ["growth_mindset", "independence", "creativity"]},
    {"@id": "mtg:BRG", "@type": "ColorTriple", "name": "Jund", "clan": "jund", "boundedBy": ["mtg:BR", "mtg:RG", "mtg:BG"], "thematic_triad": ["independence", "authenticity", "profanity"]},
    {"@id": "mtg:WRG", "@type": "ColorTriple", "name": "Naya", "clan": "naya", "boundedBy": ["mtg:WR", "mtg:RG", "mtg:GW"], "thematic_triad": ["heroism", "authenticity", "community"]},
    {"@id": "mtg:WUG", "@type": "ColorTriple", "name": "Bant", "clan": "bant", "boundedBy": ["mtg:WU", "mtg:UG", "mtg:GW"], "thematic_triad": ["design", "truth_seeking", "community"]},
    {"@id": "mtg:WBG", "@type": "ColorTriple", "name": "Abzan", "clan": "abzan", "boundedBy": ["mtg:WB", "mtg:GW", "mtg:BG"], "thematic_triad": ["tribalism", "community", "profanity"]},
    {"@id": "mtg:UBG", "@type": "ColorTriple", "name": "Sultai", "clan": "sultai", "boundedBy": ["mtg:UB", "mtg:UG", "mtg:BG"], "thematic_triad": ["growth_mindset", "truth_seeking", "profanity"]},
    {"@id": "mtg:URG", "@type": "ColorTriple", "name": "Temur", "clan": "temur", "boundedBy": ["mtg:UR", "mtg:RG", "mtg:UG"], "thematic_triad": ["creativity", "authenticity", "truth_seeking"]},
    {"@id": "mtg:WBR", "@type": "ColorTriple", "name": "Mardu", "clan": "mardu", "boundedBy": ["mtg:WB", "mtg:BR", "mtg:WR"], "thematic_triad": ["tribalism", "independence", "heroism"]},
    {"@id": "mtg:WUR", "@type": "ColorTriple", "name": "Jeskai", "clan": "jeskai", "boundedBy": ["mtg:WU", "mtg:UR", "mtg:WR"], "thematic_triad": ["design", "creativity", "heroism"]},
]

def _strip(s):
    """Strip 'mtg:' prefix if present."""
    return s[4:] if s.startswith("mtg:") else s


# Elements removed by commit u (for deletion tracking)
COMMIT_U_REMOVED_IDS = {"mtg:BG", "mtg:WBG", "mtg:UBG", "mtg:BRG"}
_REMOVED_BARE = {_strip(x) for x in COMMIT_U_REMOVED_IDS}

# Elements enriched by commit v
COMMIT_V_ENRICHMENTS = {
    "mtg:BG": {"playstyle": "graveyard-recursion", "example_decks": "Golgari Midrange"},
    "mtg:BRG": {"playstyle": "aggressive-midrange", "example_decks": "Jund Sacrifice"},
}


def _is_removed(eid):
    return eid in COMMIT_U_REMOVED_IDS or eid in _REMOVED_BARE


def _is_complex(eid):
    return eid in ("mtg:_complex", "_complex")


def apply_commit_u(elements):
    """Remove BG edge + dependent faces (WBG, UBG, BRG) from elements and complex membership."""
    result = []
    for e in elements:
        e = copy.deepcopy(e)
        if _is_removed(e["@id"]):
            continue
        if _is_complex(e["@id"]):
            e["members"] = [m for m in e["members"] if not _is_removed(m)]
        result.append(e)
    return result


def apply_commit_v(elements):
    """Enrich BG and BRG with new properties."""
    result = []
    enrichment_keys = {_strip(k): v for k, v in COMMIT_V_ENRICHMENTS.items()}
    for e in elements:
        e = copy.deepcopy(e)
        bare = _strip(e["@id"])
        if bare in enrichment_keys:
            e.update(enrichment_keys[bare])
        result.append(e)
    return result


def apply_commit_u_on_v_state(elements):
    """
    Apply commit u on top of commit v's state.
    Removes BG/WBG/UBG/BRG entirely — including v's enrichments.
    This mirrors the SPARQL wildcard DELETE behavior.
    """
    return apply_commit_u(elements)


def apply_commit_v_on_u_state(elements):
    """
    Apply commit v on top of commit u's state.
    BG and BRG no longer exist in the element list, so v's enrichments
    create NEW orphaned elements (properties on elements not in the complex).
    """
    result = copy.deepcopy(elements)
    enrichment_keys = {_strip(k): v for k, v in COMMIT_V_ENRICHMENTS.items()}
    for bare_eid, props in enrichment_keys.items():
        existing = next((e for e in result if _strip(e["@id"]) == bare_eid), None)
        if existing:
            existing.update(props)
        else:
            result.append({"@id": bare_eid, "@type": "Orphaned", **props})
    return result
