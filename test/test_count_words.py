import unittest

# sys path manipulation necessary for importing function defined in parent dir
import os, sys
sys.path.insert( 0, os.getcwd() )

from extract_words import count_words

class TestCountWords( unittest.TestCase ):
    """
    test that <i></i> tags are not mistakenly concatenated with other words like:
    "<i>(umpire) Safe!</i>" -> "iumpire"
    "there!</i>" -> "therei"
    """
    def test_tag_removal( self ):
        words = count_words( "data/the-jackie-robinson-story-1950.srt" )[ "wsid" ]

        self.assertIn( "umpire", words )
        self.assertNotIn( "iumpire", words )

        self.assertIn( "man", words )
        self.assertNotIn( "iman", words )

        self.assertIn( "catcher", words )
        self.assertNotIn( "icatcher", words )

        self.assertIn( "there", words )
        self.assertNotIn( "therei", words )

        self.assertIn( "sir", words )
        self.assertNotIn( "siri", words )


if __name__ == "__main__":
    unittest.main()
