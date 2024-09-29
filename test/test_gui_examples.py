import sys
import os
import unittest
import random
import spacy
import argparse

from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest, QSignalSpy
from PyQt5.QtCore import Qt

# sys path manipulation necessary for importing class defined in parent dir
sys.path.insert( 0, os.getcwd() )
from gui import MainWindow

from extract_words import detect_corpus_languages, SPACY_MODEL_NAME

class TestWordExamples( unittest.TestCase ):
    """
    tests that indexing into word examples works properly, i.e. the examples
    for a given word contain the actual word
    """

    def setUp( self ):
        """
        choose a file at random and launch the application with it
        """
        self.target_lang = "en"
        file_to_lang = detect_corpus_languages( "data" )
        candidate_files = []
        for file in file_to_lang:
            if file_to_lang[ file ] == self.target_lang:
                candidate_files.append( file )

        self.assertTrue( candidate_files,
            msg=f"No files found in target language: {self.target_lang}." )

        self.selected_file = random.choice( candidate_files )

        print( "Selected file:", self.selected_file )

        self.app = QApplication( sys.argv )
        self.main_window = MainWindow( sub_fpath="data/detour-1945.srt",
                                       target_lang="en",
                                       native_lang="ro",
                                       deck_name_to_id={ "Test": 1 } )
        self.main_window.show()

    def tearDown( self ):
        self.main_window.close()
        self.app = None

    def test_word_examples( self ):
        """
        simulate the user clicking a random word and then a random example for the
        word

        check that the word exists in the sentence
        """

        top_word_list = self.main_window.word_list
        example_list = self.main_window.example_list
        nlp = spacy.load( SPACY_MODEL_NAME[ self.target_lang ] )

        def check_word_in_sentence( word_index ):
            """
            helper that gets the word at word index from the doc_word_stats
            collection and picks a random example, then lemmatizes the example
            sentence and makes sure that at least one token in the lemmatized
            sentence is an occurence of our word
            """
            QTest.mouseClick(
                top_word_list.viewport(),
                Qt.LeftButton,
                pos=top_word_list.visualItemRect(
                    top_word_list.item( word_index ) ).center() )

            # NB:indexing in the doc_word_stats collection starts at 1
            word = self.main_window.doc_word_stats[ word_index + 1 ][ 0 ]
            example_index = random.randint( 0, example_list.count()-1 )
            example_sentence = example_list.item( example_index ).text()

            doc = nlp( example_sentence )
            found = False
            for token in doc:
                if token.lemma_.lower() == word:
                    found = True
                    break

            self.assertTrue( found,
                             msg=f'File: {self.selected_file}, not found word '
                                 f'"{word}" in sentence "{example_sentence}"' )

        # shuffle list indices and pick 10 at random
        indices = list( range( top_word_list.count() ) )
        random.shuffle( indices )
        indices = indices[ :10 ]

        # for each word, pick a random example sentence, lemmatize it, and make sure
        # that in the lemmatized doc there is at least one token whose lemma is
        # equal to the word at word_index
        for word_index in indices:
            check_word_in_sentence( word_index )

def parse_args():
    """
    parse optional command line arguments

    currently only used to take a random seed if specified
    """
    parser = argparse.ArgumentParser(
        description="Run unittests with optional arguments." )
    parser.add_argument( "--seed", type=int, help="random seed" )

    # parse known args, leave unittest args intact
    args, unknown = parser.parse_known_args()
    return args, unknown

if __name__ == "__main__":
    # parse optional arguments
    args, unknown = parse_args()

    # handle random seed
    if args.seed:
        seed = args.seed
    else:
        seed = random.randint( 0, int( 1e+9 ) )

    print( "Random seed is:", seed )
    random.seed( seed )

    # remove parsed arguments from sys.argv
    sys.argv = [ sys.argv[ 0 ] ] + sys.argv[ len( sys.argv ) - len( unknown ): ]

    unittest.main()
