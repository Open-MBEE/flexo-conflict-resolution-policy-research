"""
Oracle constraint evaluators for the satellite scenario.

Direct translation of the SPARQL queries in Experiment 1's oracle/ directory:
  c1-mass-budget.rq     →  c1_mass_budget()
  c2-power-budget.rq    →  c2_power_budget()
  c3-bus-load.rq        →  c3_bus_load()
  c4-nonneg-mass.rq     →  c4_nonneg_mass()
  c5-thermal-coupling.rq→  c5_thermal_coupling()
  c6-owner-cardinality.rq→ c6_owner_cardinality()
  name-multiplicity.rq  →  name_multiplicity()

Each function takes a list of element dicts (as returned by the SysML v2 API)
and returns a result dict describing whether the constraint is satisfied.
"""


def _find(elements, element_id):
    """Find an element by @id."""
    for e in elements:
        if e["@id"] == element_id:
            return e
    return None


def _subsystems(elements):
    """Return elements that have a 'mass' property (i.e. subsystems)."""
    return [e for e in elements if "mass" in e]


def _bus_connected(elements):
    """Return elements connected to the PowerBus."""
    return [e for e in elements if e.get("connectedTo") == "PowerBus"]


def c1_mass_budget(elements):
    """C1: total subsystem mass ≤ satellite massBudget."""
    sat = _find(elements, "SatelliteSystem")
    total = sum(s["mass"] for s in _subsystems(elements))
    budget = sat["massBudget"]
    return {"totalMass": total, "massBudget": budget, "violation": total - budget}


def c2_power_budget(elements):
    """C2: total subsystem power ≤ satellite powerBudget."""
    sat = _find(elements, "SatelliteSystem")
    total = sum(s["power"] for s in _subsystems(elements))
    budget = sat["powerBudget"]
    return {"totalPower": total, "powerBudget": budget, "violation": total - budget}


def c3_bus_load(elements):
    """C3: total bus-connected power ≤ PowerBus maxLoad."""
    bus = _find(elements, "PowerBus")
    total = sum(s["power"] for s in _bus_connected(elements))
    max_load = bus["maxLoad"]
    return {"busPower": total, "maxLoad": max_load, "violation": total - max_load}


def c4_nonneg_mass(elements):
    """C4: all subsystem masses ≥ 0."""
    violators = [s["@id"] for s in _subsystems(elements) if s["mass"] < 0]
    if violators:
        return {"satisfied": False, "violators": violators}
    return {"satisfied": True}


def c5_thermal_coupling(elements):
    """C5: ThermalSubsystem capacity ≥ CommSubsystem power × 0.3."""
    comm = _find(elements, "CommSubsystem")
    thermal = _find(elements, "ThermalSubsystem")
    threshold = comm["power"] * 0.3
    capacity = thermal["capacity"]
    return {"threshold": threshold, "capacity": capacity, "violation": threshold - capacity}


def c6_owner_cardinality(elements):
    """C6: each subsystem has at most 1 owner."""
    results = []
    for s in _subsystems(elements):
        owners = s.get("owner", [])
        if isinstance(owners, str):
            owners = [owners]
        if len(owners) > 1:
            results.append({"element": s["@id"], "ownerCount": len(owners), "owners": owners})
    if results:
        return {"satisfied": False, "violations": results}
    return {"satisfied": True}


def name_multiplicity(elements):
    """Name multiplicity: each element has at most 1 name value."""
    results = []
    for e in elements:
        names = e.get("name", None)
        if isinstance(names, list) and len(names) > 1:
            results.append({"element": e["@id"], "nameCount": len(names), "names": names})
    if results:
        return {"satisfied": False, "violations": results}
    return {"satisfied": True}


# Ordered list matching experiment-1's oracle/*.rq alphabetical order
ALL_CONSTRAINTS = [
    ("c1-mass-budget", c1_mass_budget),
    ("c2-power-budget", c2_power_budget),
    ("c3-bus-load", c3_bus_load),
    ("c4-nonneg-mass", c4_nonneg_mass),
    ("c5-thermal-coupling", c5_thermal_coupling),
    ("c6-owner-cardinality", c6_owner_cardinality),
    ("name-multiplicity", name_multiplicity),
]


def run_oracle(elements, label):
    """Run all constraints and print results, mirroring experiment-1 output."""
    print(f"\n=== Oracle evaluation: {label} ===")
    for name, fn in ALL_CONSTRAINTS:
        print(f"--- {name} ---")
        result = fn(elements)
        if "violation" in result:
            print(f"   {result}")
        elif result.get("satisfied", True):
            print("   (no results — constraint satisfied)")
        else:
            for v in result.get("violations", []):
                print(f"   {v}")
