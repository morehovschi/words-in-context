import sys
import os
import unittest

from PyQt5.QtWidgets import QApplication, QDialogButtonBox, QMessageBox
from PyQt5.QtTest import QTest, QSignalSpy
from PyQt5.QtCore import Qt, QTimer

# sys path manipulation necessary for importing class defined in parent dir
sys.path.insert( 0, os.getcwd() )
from gui import MainWindow, SessionCreationDialog, SessionSelectionDialog

from user_sessions import load_user_sessions

class TestTranslation( unittest.TestCase ):
    """
    test translation and basic main window functionality
    """

    def setUp( self ):
        """
        initialize the main window with a test subtitle file path
        """
        self.app = QApplication( sys.argv )
        self.main_window = MainWindow( sub_fpath="data/detour-1945.srt" )
        self.main_window.show()

    def tearDown( self ):
        self.main_window.close()
        self.app = None

        # verify that temporary audio file has been cleaned up
        self.assertFalse( os.path.isfile( "tmp-audio.mp3" ) )

    def test_interactions( self ):
        """
        simulate the user clicking a top word in the left section, and then an
        example containing the word in the middle section, and then clicking
        the "Translate" button

        verify that the translation matches what is expected for that particular
        example
        """

        top_word_list = self.main_window.word_list
        example_list = self.main_window.example_list
        translate_button = self.main_window.translate_button

        # select the fifth item in the top word list
        QTest.mouseClick(
            top_word_list.viewport(),
            Qt.LeftButton,
            pos=top_word_list.visualItemRect( top_word_list.item( 4 ) ).center() )

        # select the fourth example in the example list
        QTest.mouseClick(
            example_list.viewport(),
            Qt.LeftButton,
            pos=example_list.visualItemRect( example_list.item( 3 ) ).center() )

        # set up a spy to listen to the "translation complete" signal
        spy = QSignalSpy( self.main_window.translation_complete )

        QTest.mouseClick( translate_button, Qt.LeftButton )

        # wait for the translation to complete (up to 60 seconds)
        spy.wait( 60000 )

        expected_front_text = "scar\n\nI also pointed out that the real Haskell"\
                              " had a scar on his forearm."
        expected_back_text = "cicatrice\n\nAm mai subliniat că adevăratul "\
                             "Haskell avea o cicatrice pe antebraț."\

        self.assertEqual( self.main_window.front_text_edit.toPlainText(), expected_front_text )
        self.assertEqual( self.main_window.back_text_edit.toPlainText(), expected_back_text )

        # verify that when a different example is clicked, the translation box is
        # cleared
        QTest.mouseClick(
            example_list.viewport(),
            Qt.LeftButton,
            pos=example_list.visualItemRect( example_list.item( 2 ) ).center() )
        self.assertEqual( self.main_window.back_text_edit.toPlainText(), "" )

class TestNameFiltering( unittest.TestCase ):
    """
    test the name filtering toggle in the GUI
    """

    def setUp( self ):
        """
        initialize the main window with a test subtitle file path
        """
        self.app = QApplication( sys.argv )
        self.main_window = MainWindow( sub_fpath="data/its-a-wonderful-life-1946.srt" )
        self.main_window.show()

    def tearDown( self ):
        self.main_window.close()
        self.app = None

    def test_name_filtering( self ):
        """
        test that with the name filtering toggle checked and unchecked the top 20
        words in the word list are the expected ones
        """

        top_word_list = self.main_window.word_list
        example_list = self.main_window.example_list

        # expected content for name filtering enabled (by default)
        name_filtered_top20 = [
            '1.  "building"',
            '2.  "sam"',
            '3.  "martini"',
            '4.  "bank"',
            '5.  "loan"',
            '6.  "hee"',
            '7.  "haw"',
            '8.  "wing"',
            '9.  "examiner"',
            '10.  "auld"',
            '11.  "angel"',
            '12.  "moon"',
            '13.  "lang"',
            '14.  "syne"',
            '15.  "okay"',
            '16.  "reopen"',
            '17.  "tree"',
            '18.  "save"',
            '19.  "gal"',
            '20.  "rent"'
        ]
        for i in range( 20 ):
            self.assertEqual( top_word_list.item( i ).text(),
                              name_filtered_top20[ i ] )

        # for whatever reason, simulating a mouse click does not seem to update the
        # checkbox's state, so a spacebar click simulation is used instead
        QTest.keyClick( self.main_window.nf_button, Qt.Key_Space )

        # expected output for name filtering disabled
        unfiltered_top20 = [
            '1.  "bailey"',
            '2.  "george"',
            '3.  "potter"',
            '4.  "mary"',
            '5.  "harry"',
            '6.  "merry"',
            '7.  "christmas"',
            '8.  "building"',
            '9.  "gower"',
            '10.  "sam"',
            '11.  "uncle"',
            '12.  "martini"',
            '13.  "daddy"',
            '14.  "bank"',
            '15.  "loan"',
            '16.  "hee"',
            '17.  "haw"',
            '18.  "clarence"',
            '19.  "bedford"',
            '20.  "zuzu"'
        ]

        for i in range( 20 ):
            self.assertEqual( top_word_list.item( i ).text(),
                              unfiltered_top20[ i ] )


class TestSessionCreationDialog( unittest.TestCase ):
    """
    very basic unit test for the language selection dialog

    simulates inputting two deck names and selecting target and native languages
    from the drop down menus and verifies that the data is stored into the object
    """
    def setUp( self ):
        # create the application and dialog for testing
        self.app = QApplication( sys.argv )
        self.dialog = SessionCreationDialog()

    def tearDown( self ):
        # clean up the dialog and application after tests
        self.dialog = None
        self.app = None

    def test_session_creation_dialog( self ):
        # simulates inputting session name
        QTest.keyClicks( self.dialog.session_name_edit, "Session A" )

        # simulate entering deck names
        QTest.keyClicks( self.dialog.deck_names_edit, "Deck 1, Deck 2" )

        # simulate selecting target language
        target_language_index =\
            self.dialog.target_language_combo.findText( "Spanish",
                                                        Qt.MatchFixedString )
        self.dialog.target_language_combo.setCurrentIndex( target_language_index )

        # simulate selecting native language
        native_language_index =\
            self.dialog.native_language_combo.findText( "Romanian",
                                                        Qt.MatchFixedString )
        self.dialog.native_language_combo.setCurrentIndex( native_language_index )

        # simulate clicking the OK button
        self.dialog.button_box.button( QDialogButtonBox.Ok ).click()

        # get the selection from the dialog
        session_name, deck_names, target_language, native_language =\
            self.dialog.get_selection()

        # assert that the data matches the input
        self.assertEqual( session_name, "Session A" )
        self.assertEqual( deck_names, [ "Deck 1", "Deck 2" ] )
        self.assertEqual( target_language, "Spanish" )
        self.assertEqual( native_language, "Romanian" )

class TestSessionSelection( unittest.TestCase ):
    """
    test integrating SessionSelectionDialog, SessionCreationDialog, and user session
    loading, creation, deletion, and saving
    """
    user_sessions_filename = "test_user_sessions.json"

    def setUp( self ):
        # clean up test data file if existing
        if os.path.isfile( self.user_sessions_filename ):
            os.unlink( self.user_sessions_filename )

        # create the application and dialog for testing
        self.app = QApplication( sys.argv )
        self.dialog = SessionSelectionDialog( self.user_sessions_filename )

    def tearDown( self ):
        # clean up the dialog, application, and generated data after tests
        self.dialog = None
        self.app = None

        os.unlink( self.user_sessions_filename )

    def test_session_selection( self ):
        def simulate_session_creation_input( session_name, deck_names,
                                             native_lang="Romanian",
                                             target_lang="English" ):
            # called in a separate thread

            # find the SessionCreationDialog
            creation_dialog = None
            for widget in QApplication.topLevelWidgets():
                if isinstance( widget, SessionCreationDialog ):
                    creation_dialog = widget

            assert creation_dialog, "Session creation dialog not found"

            creation_dialog.session_name_edit.setText( session_name )
            creation_dialog.deck_names_edit.setText( deck_names )

            # simulate selecting native language
            native_lang_idx =\
                creation_dialog.native_language_combo.findText( native_lang,
                                                               Qt.MatchFixedString )
            creation_dialog.native_language_combo.setCurrentIndex( native_lang_idx )

            # simulate selecting target language
            target_lang_idx =\
                creation_dialog.target_language_combo.findText( target_lang,
                                                               Qt.MatchFixedString )
            creation_dialog.target_language_combo.setCurrentIndex( target_lang_idx )

            # simulate clicking the OK button
            creation_dialog.button_box.button( QDialogButtonBox.Ok ).click()

        def simulate_session_selection( session_name ):
            matching_items = self.dialog.session_list.findItems( session_name,
                                                                 Qt.MatchExactly )

            if not matching_items:
                return

            # Assuming there's only one matching item
            item = matching_items[ 0 ]

            # Get the item's index and rectangle
            index = self.dialog.session_list.indexFromItem( item )
            item_rect = self.dialog.session_list.visualRect( index )

            center_point = item_rect.center()
            QTest.mouseClick( self.dialog.session_list.viewport(), Qt.LeftButton,
                              pos=center_point )

        def simulate_yes():
            # called in a separate thread

            confirmation_dialog = None
            for widget in QApplication.topLevelWidgets():
                # find the confirmation dialog
                if isinstance( widget, QMessageBox ):
                    confirmation_dialog = widget
                    break

            assert confirmation_dialog, "Confirmation dialog not found"
            confirmation_dialog.button( QMessageBox.Yes ).click()


        # call simulate_session_creation_input within a separate thread
        QTimer.singleShot(
            100, lambda: simulate_session_creation_input( "Session A",
                                                          "Deck 1, Deck 2" ) )
        self.dialog.new_session_button.click()

        # simulate creating another session
        QTimer.singleShot(
            100, lambda: simulate_session_creation_input( "Session B",
                                                          "Deck 3, Deck 4",
                                                          "Portuguese",
                                                          "Ukrainian" ) )
        self.dialog.new_session_button.click()

        # verify that .json file has the expected data
        loaded_sessions = load_user_sessions()[ "sessions" ]
        expected_sessions = {
            "Session A": { "decks": [ "Deck 1", "Deck 2" ],
                           "target_lang": "English",
                           "native_lang": "Romanian" },
            "Session B": { "decks": [ "Deck 3", "Deck 4" ],
                           "target_lang": "Portuguese",
                           "native_lang": "Ukrainian" } }

        self.assertCountEqual( loaded_sessions, expected_sessions )

        # delete session B using the GUI
        simulate_session_selection( "Session B" )
        QTimer.singleShot( 100, simulate_yes )
        self.dialog.delete_session_button.click()

        # verify that .json file reflects session deletion
        loaded_sessions = load_user_sessions()
        deck_name_to_id = loaded_sessions[ "deck_id" ]
        loaded_sessions = loaded_sessions[ "sessions" ]
        expected_sessions = {
            "Session A": { "decks": [ "Deck 1", "Deck 2" ],
                           "target_lang": "English",
                           "native_lang": "Romanian" } }

        self.assertCountEqual( loaded_sessions, expected_sessions )

        # deck name->ID mappings are not deleted, so verify all present
        expected_deck_names = [ "Deck 1", "Deck 2", "Deck 3", "Deck 4" ]
        self.assertCountEqual( list( deck_name_to_id.keys() ), expected_deck_names )

if __name__ == "__main__":
    unittest.main()
