import unittest
import spacy

# sys path manipulation necessary for importing function defined in parent dir
import os, sys
sys.path.insert( 0, os.getcwd() )

from extract_words import (
    analyze_file,
    get_doc_word_stats
)

class TestDeprioritize( unittest.TestCase ):

    def test_detect_in_sound_desc( self ):
        """
        test that words are marked correctly as within or without sound description
        """

        model = spacy.load( "en_core_web_sm" )
        file_stats = analyze_file( "data/a-bucket-of-blood-1959.srt",
                                    model )

        # "louis" appears only in "[Officer] Louis Raby."
        # -> "in_sound_desc" should have a single value of "False"
        self.assertEqual( file_stats[ "in_sound_desc" ][ "louis" ], [ False ] )

        # "officer" appears in:
        #       "Police officer."
        #       "[Officer] Louis Raby."
        # -> "in_sound_desc" should have a False and a True
        self.assertEqual( file_stats[ "in_sound_desc" ][ "officer" ], [ False, True ] )

    def test_deprioritize_sound_desc( self ):
        """
        checks that a word that occurrs at least once outside a sound description
        gets its score multiplied by 10,000 when deprioritize==True, while one that
        is only found in a sound description has the same score.
        """
        fname = "riders-of-destiny-1933.srt"
        word_stats_no_dep = get_doc_word_stats( "data/", fname )

        # word_stats_no_dep is a list of tuples; convert to dict (skipping the first
        # element, because it is None by design)
        no_dep_dict = {}
        for k, v in word_stats_no_dep[ 1: ]:
            no_dep_dict[ k ] = v

        word_stats_dep = get_doc_word_stats( "data/", fname,
                                                 deprioritize_sound_desc=True )
        dep_dict = {}
        for k, v in word_stats_dep[ 1: ]:
            dep_dict[ k ] = v

        # "outlaw" only occurs in subtitle file outside sound descriptions
        #   -> score should be 10,000 times higher in dep scenario
        self.assertEqual( int( dep_dict[ "outlaw" ][ "tf-idf" ] /
                               no_dep_dict[ "outlaw" ][ "tf-idf" ] ), 10000 )

        # "gun" occurs both inside and outside sound descriptions
        #   -> score should be 10,000 times higher in dep scenario
        self.assertEqual( int( dep_dict[ "gun" ][ "tf-idf" ] /
                               no_dep_dict[ "gun" ][ "tf-idf" ] ), 10000 )

        # "bang" only occurs inside sound descriptions
        #   -> score should be the same in the two scenarios
        self.assertEqual( dep_dict[ "bang" ][ "tf-idf" ],
                          no_dep_dict[ "bang" ][ "tf-idf" ] )

    def test_deprioritize_tight_bracket_bug( self ):
        """
        in the initial version of the feature, square brackets were always assumed
        to be parsed as individual tokens by the spaCy language model;

        however, they would sometimes occur in sequences like "-[flüstert", and
        the sound description detection algorithm would not work correctly;

        test that a problematic example is processed correctly by analyze_file
        """
        model = spacy.load( "de_core_news_sm" )
        file_stats = analyze_file( "data/faust_3.srt",
                                    model )

        # in the mockup example, "entführer" occurs within square brackets, but
        # before the bug fix, the parser classifies it as outside square brackets;
        # the only item in the list indexed below should be True
        self.assertTrue( file_stats[ "in_sound_desc" ][ "entführer" ][ 0 ] )

if __name__ == "__main__":
    unittest.main()
