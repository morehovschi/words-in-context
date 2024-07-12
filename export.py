"""
TODO:
"""

import genanki
from genanki.util import guid_for
from user_data import USER_DECKS

MODEL = genanki.Model(
  241193077,
  'Simple Model',
  fields=[
    {'name': 'Question'},
    {'name': 'Answer'},
  ],
  templates=[
    {
      'name': 'Card 1',
      'qfmt': '{{Question}}',
      'afmt': '{{FrontSide}}<hr id="answer">{{Answer}}',
    },
  ])

class Flashcard:
    """
    TODO:
    """
    def __init__(self, front, back):
        self.front = front
        self.back = back

def export_to_anki( card_list, decks ):
    """
    TODO:
    """

    for j, card in enumerate( card_list ):
        for i, deck in enumerate( decks ):
            note =\
                genanki.Note( model=MODEL,
                              fields=[ card.front, card.back ] )

            # Anki doesn't like duplicate notes, even if they go into separate
            # decks.
            #
            # So change the note identifier to include hashes for extra
            # empty strings in order to make it think that duplicate notes
            # destined to different decks are different notes
            note.guid = guid_for( note.fields + [ "" ] * i )
            deck.add_note( note )

    for i, deck in enumerate( decks ):
        genanki.Package( deck ).write_to_file( deck.name + ".apkg" )

if __name__ == "__main__":
    # test code
    card_list = [ Flashcard( "i", "j" ), Flashcard( "k", "l" ) ]

    export_to_anki( card_list, USER_DECKS )
