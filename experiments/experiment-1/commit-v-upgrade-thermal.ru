# Commit v — "Upgrade Thermal + Rename" (applied on branch-b)
# Team Beta upgrades the thermal subsystem and standardizes naming.

PREFIX sat: <http://example.org/satellite/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

DELETE {
  sat:ThermalSubsystem sat:mass "20"^^xsd:integer .
  sat:ThermalSubsystem sat:power "10"^^xsd:integer .
  sat:CommSubsystem sat:name "CommSubsystem" .
}
INSERT {
  sat:ThermalSubsystem sat:mass "40"^^xsd:integer .
  sat:ThermalSubsystem sat:power "25"^^xsd:integer .
  sat:CommSubsystem sat:name "CommunicationsSubsystem" .
  sat:CommSubsystem sat:owner sat:TeamBeta .
}
WHERE {}
