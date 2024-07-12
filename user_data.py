"""
This module contains data for my individual use case. Replace DECK_LILIA and
DECK_SERGIU with as many decks as you need, and the same flashcards will be written
to all.

Most likely you'll  need a user deck list with just one deck – give it a name and
a unique integer as its id.
"""

from genanki import Deck

DECK_LILIA = Deck( 542411, "English Lilia" )
DECK_SERGIU = Deck( 542412, "English Sergiu" )
USER_DECKS = [ DECK_LILIA, DECK_SERGIU ]
