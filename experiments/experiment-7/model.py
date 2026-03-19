"""
Satellite model definitions for Experiment 2.

Mirrors the RDF/Turtle data from Experiment 1:
  - ancestor-model.ttl  →  ANCESTOR_ELEMENTS
  - commit-u-upgrade-comms.ru  →  COMMIT_U_DELTAS
  - commit-v-upgrade-thermal.ru  →  COMMIT_V_DELTAS

Commits are defined as property-level deltas (delete/insert pairs), matching
the SPARQL DELETE/INSERT semantics in Experiment 1. The function
apply_deltas() merges these onto a base element set to produce the new state.

Element @id values are plain strings (e.g., "CommSubsystem"). The SysML v2
API stores them as-is. The corresponding RDF URIs in Experiment 1 use the
"sat:" prefix (e.g., "sat:CommSubsystem").
"""

import copy

# --- Ancestor State (X) ---
# Satellite system with two subsystems and a power bus.
# Total: 50 kg mass, 25 W power (both well within budgets).

ANCESTOR_ELEMENTS = [
    {
        "@id": "SatelliteSystem",
        "@type": "PartDefinition",
        "name": "SatelliteSystem",
        "massBudget": 100,
        "powerBudget": 50,
    },
    {
        "@id": "CommSubsystem",
        "@type": "PartDefinition",
        "name": "CommSubsystem",
        "mass": 30,
        "power": 15,
        "dataRate": 100,
        "connectedTo": "PowerBus",
    },
    {
        "@id": "ThermalSubsystem",
        "@type": "PartDefinition",
        "name": "ThermalSubsystem",
        "mass": 20,
        "power": 10,
        "capacity": 15,
        "connectedTo": "PowerBus",
    },
    {
        "@id": "PowerBus",
        "@type": "PartDefinition",
        "name": "PowerBus",
        "maxLoad": 50,
    },
]

# --- Commit u: Team Alpha — Communications Upgrade (branch-a) ---
#
# SPARQL equivalent (from commit-u-upgrade-comms.ru):
#   DELETE { CommSubsystem mass 30; power 15; dataRate 100; name "CommSubsystem" }
#   INSERT { CommSubsystem mass 45; power 30; dataRate 250; name "HighBandwidthComm"; owner TeamAlpha }
#
# Each delta: (element_id, property, delete_value_or_None, insert_value_or_None)
# For list-valued properties like "owner", insert appends rather than replaces.

COMMIT_U_DELTAS = [
    ("CommSubsystem", "mass", 30, 45),
    ("CommSubsystem", "power", 15, 30),
    ("CommSubsystem", "dataRate", 100, 250),
    ("CommSubsystem", "name", "CommSubsystem", "HighBandwidthComm"),
    ("CommSubsystem", "owner", None, "TeamAlpha"),  # INSERT only (no prior owner)
]

# --- Commit v: Team Beta — Thermal Upgrade (branch-b) ---
#
# SPARQL equivalent (from commit-v-upgrade-thermal.ru):
#   DELETE { ThermalSubsystem mass 20; power 10; CommSubsystem name "CommSubsystem" }
#   INSERT { ThermalSubsystem mass 40; power 25; CommSubsystem name "CommunicationsSubsystem"; owner TeamBeta }

COMMIT_V_DELTAS = [
    ("ThermalSubsystem", "mass", 20, 40),
    ("ThermalSubsystem", "power", 10, 25),
    ("CommSubsystem", "name", "CommSubsystem", "CommunicationsSubsystem"),
    ("CommSubsystem", "owner", None, "TeamBeta"),  # INSERT only (no prior owner)
]


def apply_deltas(base_elements, deltas):
    """
    Apply property-level deltas to a set of elements, producing a new state.

    This mirrors SPARQL DELETE/INSERT semantics:
    - DELETE removes a specific value from a property (if it matches).
    - INSERT adds a value.
    - For scalar properties: DELETE old value, INSERT new value = replace.
    - For "owner": INSERT appends to a list (RDF allows multiple triples).
    - If DELETE value doesn't match current value (because a prior commit
      changed it), the delete is a no-op and the insert adds a second value,
      producing a conflict (e.g., two names).

    Returns a new list of elements (does not mutate the input).
    """
    # Index by @id for fast lookup
    result = {e["@id"]: copy.deepcopy(e) for e in base_elements}

    for element_id, prop, delete_val, insert_val in deltas:
        elem = result[element_id]
        current = elem.get(prop)

        if prop == "owner":
            # Owner is always list-valued (RDF allows multiple triples)
            owners = elem.get("owner", [])
            if isinstance(owners, str):
                owners = [owners]
            if delete_val is not None and delete_val in owners:
                owners = [o for o in owners if o != delete_val]
            if insert_val is not None:
                owners.append(insert_val)
            elem["owner"] = owners
        elif delete_val is not None and current == delete_val:
            # Scalar: value matches DELETE → replace with INSERT
            elem[prop] = insert_val
        elif delete_val is not None and current != delete_val:
            # Scalar: value does NOT match DELETE (changed by another commit).
            # The DELETE is a no-op; INSERT adds a second value → conflict.
            # Represent as a list of values (mirrors multiple RDF triples).
            if isinstance(current, list):
                if insert_val not in current:
                    elem[prop] = current + [insert_val]
            else:
                elem[prop] = [current, insert_val]
        elif delete_val is None and insert_val is not None:
            # Pure INSERT (no delete) — set value
            elem[prop] = insert_val

    return list(result.values())


def compute_full_elements(base_elements, deltas):
    """
    Compute the full element set after applying deltas.

    Used for committing to the SysML v2 API (which replaces whole elements).
    Returns only the elements that changed.
    """
    new_state = apply_deltas(base_elements, deltas)
    base_index = {e["@id"]: e for e in base_elements}
    # Return only changed elements
    changed = [e for e in new_state if e != base_index.get(e["@id"])]
    return changed
