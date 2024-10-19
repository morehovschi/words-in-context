import unittest
import spacy

# sys path manipulation necessary for importing function defined in parent dir
import os, sys
sys.path.insert( 0, os.getcwd() )

from extract_words import analyze_file_new

class TestLikelyNames( unittest.TestCase ):
    def test_likely_names( self ):
        expected_output = {
            'west': [ 0, 5 ],
            'york': [ 4, 1, 1, 1, 1, 9, 1, 5, 7 ],
            'sue': [ 0, 2, 0, 0, 1, 5, 6, 5, 11, 4, 6, 0, 2 ],
            'mr': [ 0, 0, 0, 0, 0, 0, 13, 0 ],
            'paradisical': [ 8, 4],
            'al': [ 0, 0, 0, 0, 0, 2, 1 ],
            'california': [ 5, 14, 3, 8 ],
            'hollywood': [ 7, 4, 3, 4, 3, 8, 6, 8 ],
            'roberts': [ 1, 12, 0, 0, 0, 0, 2, 0, 8, 0, 0, 0, 0, 2 ],
            'los': [ 9, 3, 3, 0, 4, 6 ],
            'angeles': [ 10, 4, 4, 1, 5, 7 ],
            'harvey': [ 1, 1 ],
            'view': [ 1, 1 ],
            'arizona': [ 3, 10, 0, 5 ],
            'haskell': [ 0, 1, 1, 1, 1, 1, 1, 1, 13, 2, 1, 3, 1, 1, 1, 7, 7, 14,
                         8, 2, 6, 6, 13, 7, 1, 1, 8, 5, 1, 3, 9, 0, 2, 4, 3, 0,
                         1, 6, 1, 1, 1, 3, 12, 8, 6, 7, 0, 2, 5, 7, 0, 1, 4 ],
            'wednesday': [ 8, 1 ],
            'santa': [ 6, 3 ],
            'anita': [ 7, 4 ],
            'miami': [ 9, 4, 6 ],
            'charles': [ 0, 2, 6, 6, 0, 2, 5 ],
            'jr': [ 2, 4 ],
            'san': [ 8, 2 ],
            'bernardino': [ 9, 3 ],
            'vera': [ 4, 0, 0, 0, 0, 0, 2, 6, 1, 1, 0, 1, 0, 8, 0, 0, 0, 0, 0, 1,
                      0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 4 ],
            'phoenix': [ 0, 5, 4 ],
            'charlie': [ 7, 8, 11 ],
            'crest': [ 2, 0],
            'siamese': [ 6, 0 ],
            'mrs': [ 1, 0 ]
        }

        model = spacy.load( "en_core_web_sm" )
        likely_names = analyze_file_new( "data/detour-1945.srt", model )[ "likely_names" ]

        self.assertCountEqual( likely_names, expected_output )


if __name__ == "__main__":
    unittest.main()
