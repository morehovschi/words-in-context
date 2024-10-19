"""
Utilities for saving the GUI's front and back text as flashcards and writing
flashcards to .apkg files for all target Anki deck names
"""

import genanki
from genanki.util import guid_for

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
    custom class holding the text for the front and the back of a flashcard
    """
    def __init__( self, front, back ):
        self.front = front
        self.back = back

def export_to_anki( card_list, deck_name_to_id ):
    """
    write the Flashcard instances in card_list to all the decks defined in
    deck_name_to_id;

    the output consists of as many .apkg files as there are names in deck_name_to_id
    and the file names are "<deck name>.apkg"

    nb: deck_name_to_id is a collection mapping deck names to unique id and it helps
    ensure that a specific name will always match with the same deck id (to avoid
    creating duplicate decks with existing names)
    """
    decks = []
    for deck_name, deck_id in deck_name_to_id.items():
        decks.append( genanki.Deck( deck_id, deck_name ) )

    for j, card in enumerate( card_list ):
        for i, deck in enumerate( decks ):
            front = card.front
            back = card.back

            # add styles to the HTML content
            styled_front = f"""
            <html>
            <head>
            <style>
            body {{ text-align: center; font-size: 16px; }}
            </style>
            </head>
            <body>
            {front}
            </body>
            </html>
            """

            styled_back = f"""
            <html>
            <head>
            <style>
            body {{ text-align: center; font-size: 16px; }}
            </style>
            </head>
            <body>
            {back}
            </body>
            </html>
            """

            note =\
                genanki.Note( model=MODEL,
                              fields=[ styled_front, styled_back ] )

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

