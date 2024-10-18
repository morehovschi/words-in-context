import unittest

# sys path manipulation necessary for importing function defined in parent dir
import os, sys 
sys.path.insert( 0, os.getcwd() )

from extract_words import (
    analyze_file_new,
    detect_corpus_languages,
    SPACY_MODEL_NAME,
    srt_subtitles
)

import spacy

class TestPunctRemoval( unittest.TestCase ):
    """
    tests that punctuation is removed from lemmas before adding to word-sentence-id
    dictionary
    """
    def test_separate( self ):

        fname = "faust_1.srt"
        lang_dict = detect_corpus_languages( "data" )
        lang = lang_dict[ fname ]
        model_name = SPACY_MODEL_NAME[ lang ]
        model = spacy.load( model_name )

        analysis = analyze_file_new( "data/" + fname, model )

        # Check 1: any word containing apostrophe as vowel replacement are processed
        # as a single word
        # Example sentences:
        #   "Wenn aller Wesen unharmon'sche Menge"
        #   "Wenn nach dem heft'gen Wirbeltanz"

        self.assertIn( "unharmon'sche", analysis[ "wsid" ] )
        self.assertIn( "heft'gen", analysis[ "wsid" ] )

        # Check 2: hyphenated words are split and the words are processed
        # individually
        # Example sentences:
        #   "Hast du noch keinen Mann, nicht Mannes-Wort gekannt?"
        #   "Es wechselt Paradieses-Helle"
        self.assertIn( "mann",  analysis[ "wsid" ] )
        self.assertIn( "wort",  analysis[ "wsid" ] )
        self.assertIn( "paradiese",  analysis[ "wsid" ] )
        self.assertIn( "hell",  analysis[ "wsid" ] )
        
        

if __name__ == "__main__":
    unittest.main()
