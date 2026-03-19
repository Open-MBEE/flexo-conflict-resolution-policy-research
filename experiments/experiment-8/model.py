"""
MTG Knowledge Complex model for Experiment 8.

Same model as Experiment 5, but commit u now uses identity-only deletion
to actually remove elements from the commit (rather than just removing
them from the Complex.members list).
"""

import copy
import importlib.util
import os

# Import ANCESTOR_ELEMENTS from experiment-5 without name collision
_spec = importlib.util.spec_from_file_location(
    "exp5_model",
    os.path.join(os.path.dirname(__file__), "..", "experiment-5", "model.py"),
)
_exp5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_exp5)

ANCESTOR_ELEMENTS = _exp5.ANCESTOR_ELEMENTS

COMMIT_V_ENRICHMENTS = {
    "mtg:BG": {"playstyle": "graveyard-recursion", "example_decks": "Golgari Midrange"},
    "mtg:BRG": {"playstyle": "aggressive-midrange", "example_decks": "Jund Sacrifice"},
}

# Elements to delete via identity-only commit
COMMIT_U_DELETE_IDS = ["BG", "WBG", "UBG", "BRG"]


def build_commit_u_membership_update(elements):
    """Build the updated Complex element with removed members."""
    for e in elements:
        if e["@id"] in ("mtg:_complex", "_complex"):
            updated = copy.deepcopy(e)
            remove_set = {"mtg:BG", "mtg:WBG", "mtg:UBG", "mtg:BRG", "BG", "WBG", "UBG", "BRG"}
            updated["members"] = [m for m in updated["members"] if m not in remove_set]
            return updated
    return None


def _strip(s):
    return s[4:] if s.startswith("mtg:") else s


def apply_commit_v(elements):
    """Enrich BG and BRG with new properties."""
    enrichment_keys = {_strip(k): v for k, v in COMMIT_V_ENRICHMENTS.items()}
    result = []
    for e in elements:
        e = copy.deepcopy(e)
        bare = _strip(e["@id"])
        if bare in enrichment_keys:
            e.update(enrichment_keys[bare])
        result.append(e)
    return result
