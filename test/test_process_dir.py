"""
Unit test checking that process_dir_new produces a word stats file which results
in a similar TF-IDF computation (top 10 results are the same) to that produced
by the old function process_dir.
"""

import unittest

# sys path manipulation necessary for importing function defined in parent dir
import os, sys 
sys.path.insert( 0, os.getcwd() )

from extract_words import process_dir, process_dir_new, get_doc_word_stats

class TestProcessDir( unittest.TestCase ):
    def test_process_dir( self ):
        # call the same function that calculates TF-IDF on both results
        old_tf_idf = get_doc_word_stats( "data/", "detour-1945",
                                         name_filtering=True )
        new_tf_idf = get_doc_word_stats( "data/", "detour-1945.srt",
                                         name_filtering=True,
                                         new_process_dir=True )

        # check that the top 10 words by TF-IDF are the same for both methods;

        # there is still lots of similarity between the two rankings beyond the
        # top 10, but as the "frequency in document" and "occurrence in other docs"
        # reach the single digits, there are nosiy reasons why two words that have
        # the same values might be ordered differently in the two rankings
        for i in range( 1, 11 ):
            self.assertEqual( old_tf_idf[ i ][ 0 ], new_tf_idf[ i ][ 0 ] )

        # verify that the two words preprocessing functions determined the same
        # words as likely names
        old_names = process_dir( "data/" )[ "detour-1945" ][ "likely_names" ]
        new_names = process_dir_new( "data/", target_lang="en" )\
            [ "en" ][ "detour-1945.srt" ][ "likely_names" ]

        self.assertCountEqual( old_names, new_names )


if __name__ == "__main__":
    unittest.main()
