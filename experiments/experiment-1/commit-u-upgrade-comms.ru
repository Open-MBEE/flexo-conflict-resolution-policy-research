# Commit u — "Upgrade Comms" (applied on branch-a)
# Team Alpha upgrades the communications subsystem for high-bandwidth operations.

PREFIX sat: <http://example.org/satellite/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

DELETE {
  sat:CommSubsystem sat:mass "30"^^xsd:integer .
  sat:CommSubsystem sat:power "15"^^xsd:integer .
  sat:CommSubsystem sat:dataRate "100"^^xsd:integer .
  sat:CommSubsystem sat:name "CommSubsystem" .
}
INSERT {
  sat:CommSubsystem sat:mass "45"^^xsd:integer .
  sat:CommSubsystem sat:power "30"^^xsd:integer .
  sat:CommSubsystem sat:dataRate "250"^^xsd:integer .
  sat:CommSubsystem sat:name "HighBandwidthComm" .
  sat:CommSubsystem sat:owner sat:TeamAlpha .
}
WHERE {}
