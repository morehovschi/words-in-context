import unittest
import spacy

# sys path manipulation necessary for importing function defined in parent dir
import os, sys
sys.path.insert( 0, os.getcwd() )

from extract_words import analyze_file

class TestDetect( unittest.TestCase ):
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


if __name__ == "__main__":
    unittest.main()
