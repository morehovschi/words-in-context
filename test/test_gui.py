import sys
import os
import unittest

from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest, QSignalSpy
from PyQt5.QtCore import Qt

# sys path manipulation necessary for importing class defined in parent dir
sys.path.insert( 0, os.getcwd() )
from gui import MainWindow

class TestMainWindow( unittest.TestCase ):
    @classmethod
    def setUpClass( cls ):
        cls.app = QApplication( sys.argv )

    def setUp( self ):
        """
        initialize the main window with a test subtitle file path
        """
        self.main_window = MainWindow( sub_fpath="data/detour-1945.srt" )
        self.main_window.show()

    def tearDown( self ):
        self.main_window.close()

    def test_interactions( self ):
        """
        simulate the user clicking a top word in the left section, and then an
        example containing the word in the middle section, and then clicking
        the "Translate" button

        verify that the translation matches what is expected for that particular
        example
        """

        top_word_list = self.main_window.left_section
        example_list = self.main_window.middle_section
        translate_button = self.main_window.translate_button

        # Select the fifth item in the top word list
        QTest.mouseClick(
            top_word_list.viewport(),
            Qt.LeftButton,
            pos=top_word_list.visualItemRect( top_word_list.item( 4 ) ).center() )

        # Select the fourth example in the example list
        QTest.mouseClick(
            example_list.viewport(),
            Qt.LeftButton,
            pos=example_list.visualItemRect( example_list.item( 3 ) ).center() )

        # set up a spy to listen to the "translation complete" signal
        spy = QSignalSpy( self.main_window.translation_complete )

        QTest.mouseClick( translate_button, Qt.LeftButton )

        # Wait for the translation to complete (up to 60 seconds)
        spy.wait( 60000 )

        expected_front_text = "scar\n\nI also pointed out that the real Haskell"\
                              " had a scar on his forearm."
        expected_back_text = "cicatrice\n\nDe asemenea, am subliniat că "\
                             "adevăratul Haskell avea o cicatrice pe antebraţ."

        self.assertEqual( self.main_window.front_text_edit.toPlainText(), expected_front_text )
        self.assertEqual( self.main_window.back_text_edit.toPlainText(), expected_back_text )

        # verify that when a different example is clicked, the translation box is
        # cleared
        QTest.mouseClick(
            example_list.viewport(),
            Qt.LeftButton,
            pos=example_list.visualItemRect( example_list.item( 2 ) ).center() )
        self.assertEqual( self.main_window.back_text_edit.toPlainText(), "" )

if __name__ == "__main__":
    unittest.main()
