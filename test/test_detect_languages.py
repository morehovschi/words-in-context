import unittest

# sys path manipulation necessary for importing function defined in parent dir
import os, sys 
sys.path.insert( 0, os.getcwd() )

from extract_words import detect_corpus_languages

class TestLanguageDetection( unittest.TestCase ):
    """
    test that file languages are detected as expected
    """
    def test_detect( self ):
        lang_map = detect_corpus_languages( "data" )

        expected_lang_map = {
            "riders-of-destiny-1933.srt": "en",
            "the-man-with-the-golden-arm-1955.srt": "en",
            "detour-1945.srt": "en",
            "penny-serenade-1941.srt": "en",
            "road-to-bail-1952.srt": "en",
            "faust_1.srt": "de",
            "faust_3.srt": "de",
            "a-bucket-of-blood-1959.srt": "en",
            "faust_2.srt": "de",
            "a-farewell-to-arms-1932.srt": "en",
            "its-a-wonderful-life-1946.srt": "en",
            "the-jackie-robinson-story-1950.srt": "en",
            "life-with-father-1947.srt": "en"
        }

        self.assertCountEqual( lang_map, expected_lang_map )

if __name__ == "__main__":
    unittest.main()
