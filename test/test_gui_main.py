import sys
import os
import unittest

from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest, QSignalSpy
from PyQt5.QtCore import Qt

# sys path manipulation necessary for importing class defined in parent dir
sys.path.insert( 0, os.getcwd() )
from gui import MainWindow

class TestTranslationBase():
    def setUp( self ):
        """
        initialize the main window with a test subtitle file path
        """
        self.app = QApplication( sys.argv )
        self.main_window = MainWindow( sub_fpath=self.sub_fpath,
                                       target_lang=self.target_lang,
                                       native_lang=self.native_lang,
                                       deck_name_to_id={ "Test": 1 } )
        self.main_window.show()

    def tearDown( self ):
        self.main_window.close()
        self.app = None

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

        self.assertEqual( self.main_window.front_text_edit.toPlainText(),
                          self.expected_front_text )
        self.assertEqual( self.main_window.back_text_edit.toPlainText(),
                          self.expected_back_text )

        # verify that when a different example is clicked, the translation box is
        # cleared
        QTest.mouseClick(
            example_list.viewport(),
            Qt.LeftButton,
            pos=example_list.visualItemRect( example_list.item( 2 ) ).center() )
        self.assertEqual( self.main_window.back_text_edit.toPlainText(), "" )

class TestTranslationEnglish( TestTranslationBase, unittest.TestCase ):
    """
    test English translation and basic main window functionality
    """
    sub_fpath = "data/detour-1945.srt"
    target_lang = "en"
    native_lang = "ro"
    expected_front_text = "scar\n\nI also pointed out that the real Haskell"\
                          " had a scar on his forearm."
    expected_back_text = "cicatrice\n\nAm mai subliniat că adevăratul "\
                         "Haskell avea o cicatrice pe antebraț."


class TestTranslationGerman( unittest.TestCase ):
    """
    test German translation and basic main window functionality
    """
    sub_fpath = "data/faust_1.srt"
    target_lang = "de"
    native_lang = "en"
    expected_front_text = "pudel\n\nFaust mit dem Pudel hereintretend."
    expected_back_text = "poodle\n\nFaust enters with the poodle."

class TestNameFiltering( unittest.TestCase ):
    """
    test the name filtering toggle in the GUI
    """

    def setUp( self ):
        """
        initialize the main window with a test subtitle file path
        """
        self.app = QApplication( sys.argv )
        self.main_window = MainWindow(
            sub_fpath="data/its-a-wonderful-life-1946.srt",
            target_lang="en",
            native_lang="ro",
            deck_name_to_id={ "Test": 1 } )
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

if __name__ == "__main__":
    unittest.main()
