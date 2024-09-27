import sys
import os
import unittest

from PyQt5.QtWidgets import QApplication, QDialogButtonBox, QMessageBox
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt, QTimer

# sys path manipulation necessary for importing class defined in parent dir
sys.path.insert( 0, os.getcwd() )
from gui import SessionCreationDialog, SessionSelectionDialog

from user_sessions import load_user_sessions

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
