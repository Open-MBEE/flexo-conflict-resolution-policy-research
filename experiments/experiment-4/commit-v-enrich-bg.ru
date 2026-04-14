# Commit v — "Enrich BG (Golgari) edge and BRG (Jund) face" (applied on branch-b)
# Curator B independently adds new descriptive properties to the BG edge
# and BRG face, enriching the model with gameplay information.

PREFIX kc: <https://example.org/kc#>
PREFIX mtg: <https://example.org/mtg#>

INSERT DATA {
  mtg:BG mtg:playstyle "graveyard-recursion" .
  mtg:BG mtg:example_decks "Golgari Midrange" .

  mtg:BRG mtg:playstyle "aggressive-midrange" .
  mtg:BRG mtg:example_decks "Jund Sacrifice" .
}
