import unittest

# sys path manipulation necessary for importing function defined in parent dir
import os, sys 
sys.path.insert( 0, os.getcwd() )

from export import (
    Flashcard,
    write_flashcard_to_backup,
    read_flashcard_backup
)

TMP_FNAME = "test_backup_pickle"

class TestBackupFile( unittest.TestCase ):
    """
    TODO:
    """
    def setUp( self ):
        # clean up if left over for some reason (e.g. interrupted run of this test)
        if os.path.isfile( TMP_FNAME ):
            os.unlink( TMP_FNAME )

    def test_backup_pickle( self ):
        # mock up some data for 2 flash cards
        front1 = """
<html>
<body>
    <p>example</p><br>
    <p>This is an <b>example</b>.</p>
</body>
</html>
"""

        back1 = """
<html>
<body>
    <p>exemplu</p><br>
    <p>Acesta este un <b>exemplu</b>.</p>
</body>
</html>
"""

        front2 = """
<html>
<body>
    <p>beispiel</p><br>
    <p>Dies ist ein <b>Beispiel</b>.</p>
</body>
</html>
"""

        back2 = """
<html>
<body>
    <p>example</p><br>
    <p>This is an <b>example</b>.</p>
</body>
</html>
"""

        flashcards = [ Flashcard( front1, back1 ), Flashcard( front2, back2 ) ]

        target_subtitle_fname = "FAKE_SUBTITLE_FILE"
        target_lang = "en"
        native_lang = "ro"
        deck_name_to_id = { "a": 1, "b": 2 }

        for flashcard in flashcards:
            write_flashcard_to_backup( TMP_FNAME, flashcard, target_subtitle_fname,
                                       target_lang, native_lang, deck_name_to_id )

        read_data = read_flashcard_backup( TMP_FNAME )

        read_target_subtitle_fname = read_data[ 0 ]
        read_target_lang = read_data[ 1 ]
        read_native_lang = read_data[ 2 ]
        read_deck_name_to_id = read_data[ 3 ]
        read_flashcards = read_data[ 4 ]

        # first check the metadata
        expected = [ target_subtitle_fname,
                     target_lang,
                     native_lang,
                     deck_name_to_id ]

        got = [ read_target_subtitle_fname,
                read_target_lang,
                read_native_lang,
                read_deck_name_to_id ]

        for i in range( len( expected ) ):
            assert expected[ i ] == got[ i ], f"Expected: {expected[i]}, got: {got[i]}."

        # now check flashcard content is the same:
        for i in range( len( flashcards ) ):
            expected = flashcards[ i ].front
            got = read_flashcards[ i ].front
            assert expected == got, f"Expected: {expected}, got: {got}."

            expected = flashcards[ i ].back
            got = read_flashcards[ i ].back
            assert expected == got, f"Expected: {expected}, got: {got}."

    def tearDown( self ):
        os.unlink( TMP_FNAME )

if __name__ == "__main__":
    unittest.main()
