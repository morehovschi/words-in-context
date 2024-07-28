import unittest

# sys path manipulation necessary for importing function defined in parent dir
import os, sys 
sys.path.insert( 0, os.getcwd() )

from extract_words import separate_fpath

class TestSeparateFpath( unittest.TestCase ):
    """
    test that file paths containing periods are separated correctly
    """
    def test_separate( self ):

        fpath = "data/It's.A.Wonderful.Life.1946.WEBRip.Amazon.srt"

        separated = separate_fpath( fpath )

        self.assertEquals( separated[ 0 ], "data/" )
        self.assertEquals( separated[ 1 ],
                           "It's.A.Wonderful.Life.1946.WEBRip.Amazon" )
        self.assertEquals( separated[ 2 ], ".srt" )

if __name__ == "__main__":
    unittest.main()
