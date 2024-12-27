"""
Utilities for saving the GUI's front and back text as flashcards and writing
flashcards to .apkg files for all target Anki deck names
"""

import os
import pickle
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

def write_flashcard_to_backup( backup_fname, flashcard, target_subtitle_fname,
                               target_lang, native_lang, deck_name_to_id ):
    """
    write the current flash card to a temporary backup file that is used to recover
    the session in case the app crashes or is closed without exporting

    Params:
        backup_fname (str): name of the backup file
        flashcard (Flashcard): an instance of Flashcard (defined in this file)
        target_subtitle_fname (str): name of the subtitle file being analyzed by
                                     main app
        target_lang (str): target language in the session (ISO 639 code)
        native_lang (str): native languag in the session (ISO 639 code)
        deck_name_to_id (dict): dictionary keeping track of Anki deck ID by name
    """
    create_backup_file = False
    if not os.path.isfile( backup_fname ):
        # if backup file does not yet exist, create one with basic info
        create_backup_file = True

    with open( backup_fname, "ab" ) as file:
        if create_backup_file:
            pickle.dump( ( "target_subtitle_fname", target_subtitle_fname ),
                         file )
            pickle.dump( ( "target_lang", target_lang ), file )
            pickle.dump( ( "native_lang", native_lang ), file )
            pickle.dump( ( "deck_name_to_id", deck_name_to_id ), file )

        pickle.dump( flashcard, file )

def read_flashcard_backup( backup_fname ):
    """
    read the backup file to recover the interrupted session

    Returns:
        target_subtitle_fname (str): name of the subtitle file being analyzed by
                                     main app
        target_lang (str): target language in the session (ISO 639 code)
        native_lang (str): native languag in the session (ISO 639 code)
        deck_name_to_id (dict): dictionary keeping track of Anki deck ID by name
        flashcards (list): a list of instances of Flashcard (defined in this file)
    """
    target_subtitle_fname = None
    target_lang = None
    native_lang = None
    deck_name_to_id = None

    flashcards = []

    with open( backup_fname, "rb" ) as file:
        while True:
            try:
                obj = pickle.load( file )

                if isinstance( obj, tuple ):
                    if obj[ 0 ] == "target_subtitle_fname":
                        target_subtitle_fname = obj[ 1 ]
                    elif obj[ 0 ] == "target_lang":
                        target_lang = obj[ 1 ]
                    elif obj[ 0 ] == "native_lang":
                        native_lang = obj[ 1 ]
                    elif obj[ 0 ] == "deck_name_to_id":
                        deck_name_to_id = obj[ 1 ]
                    else:
                        assert False, "Backup file format does not match expected. "\
                                      f"Read object: {obj}"

                # else line is not tuple, thus it is a Flashcard instance
                else:
                    flashcards.append( obj )

            except EOFError:  # end of file reached
                break

    assert target_subtitle_fname
    assert target_lang
    assert native_lang
    assert deck_name_to_id
    assert flashcards

    return ( target_subtitle_fname, target_lang, native_lang, deck_name_to_id,
           flashcards )

def export_to_anki( card_list, deck_name_to_id, fname ):
    """
    write the Flashcard instances in card_list to all the decks defined in
    deck_name_to_id;

    out file name format:
        if only one target deck: "<fname>.apkg"
        if multiple target decks: "<fname> (<deck name>).apkg"

    Params:
        card_list (list): list of Flashcard instances
        deck_name_to_id (dict): a collection mapping deck names to unique ids to
                               ensure that a specific name will always match with
                               the same deck id (to avoid creating duplicate decks
                               with existing names)
        fname (str): name of source file (no extension)
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

    # MISSING-TEST
    if len( decks ) == 1:
        genanki.Package( decks[ 0 ] ).write_to_file( f"{fname}.apkg" )
    else:
        for i, deck in enumerate( decks ):
            genanki.Package( deck ).write_to_file( f"{fname} ({deck.name}).apkg" )

