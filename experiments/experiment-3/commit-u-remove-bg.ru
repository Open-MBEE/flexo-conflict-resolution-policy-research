# Commit u — "Remove BG (Golgari) edge and dependent faces" (applied on branch-a)
# Curator A decides the Black-Green color pair is philosophically incoherent
# and removes it, along with all faces that depend on it (WBG/Abzan,
# UBG/Sultai, BRG/Jund), to maintain boundary-closure.

PREFIX kc: <https://example.org/kc#>
PREFIX mtg: <https://example.org/mtg#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

# Remove BG edge, dependent faces, and their complex membership
DELETE {
  # Remove from complex
  mtg:_complex kc:hasElement mtg:BG .
  mtg:_complex kc:hasElement mtg:WBG .
  mtg:_complex kc:hasElement mtg:UBG .
  mtg:_complex kc:hasElement mtg:BRG .

  # Remove BG edge and all its properties
  mtg:BG ?bg_p ?bg_o .

  # Remove WBG (Abzan) face and all its properties
  mtg:WBG ?wbg_p ?wbg_o .

  # Remove UBG (Sultai) face and all its properties
  mtg:UBG ?ubg_p ?ubg_o .

  # Remove BRG (Jund) face and all its properties
  mtg:BRG ?brg_p ?brg_o .
}
WHERE {
  OPTIONAL { mtg:BG ?bg_p ?bg_o . }
  OPTIONAL { mtg:WBG ?wbg_p ?wbg_o . }
  OPTIONAL { mtg:UBG ?ubg_p ?ubg_o . }
  OPTIONAL { mtg:BRG ?brg_p ?brg_o . }
}
