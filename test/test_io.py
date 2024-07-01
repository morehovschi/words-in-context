"""
Basic unit test that simulates some user input and checks that the expected
lines are present (based on data file "its-a-wonderful-life-1946.srt").
"""

import unittest
from unittest.mock import patch
from io import StringIO

# sys path manipulation necessary for importing function defined in parent dir
import os, sys 
sys.path.insert( 0, os.getcwd() )
from extract_words import main 

class TestMainMenuIO( unittest.TestCase ):

    # common steps in all tests
    def _run_test( self, mock_stdout, expected_lines ):
        main( [ "", "its-a-wonderful-life-1946.srt", "20" ] )
        output = mock_stdout.getvalue()

        for line in expected_lines:
            self.assertIn( line, output )

    @patch( "sys.stdout", new_callable=StringIO )
    @patch( "builtins.input", side_effect=[ "", "f", "q" ] )
    def test_quit( self, mock_input, mock_stdout ):
        expected_lines =[
    '1. "george". count in doc: 217. docs containing word: 4. tf-idf: 1.12E-02',
    '10. "sam". count in doc: 25. docs containing word: 2. tf-idf: 2.28E-03',
    '20. "zuzu". count in doc: 13. docs containing word: 1. tf-idf: 1.69E-03',
    'Options:',
    '-Select a word [1-20] to see contextual examples',
    '-Change number of displayed words: w',
    '-Display current word list again: l',
    '-Quit: q',
    'Bye now!'
        ]

        self._run_test( mock_stdout, expected_lines )

    @patch( "sys.stdout", new_callable=StringIO )
    @patch( "builtins.input", side_effect=[ "", "f", "15", "q"] )
    def test_good_input( self, mock_input, mock_stdout ):
        expected_lines =[
    'Displaying occurrences of "loan":',
    '1. "You see, Harry will take my job at the Building and Loan,"',
    '10. "All right, Mother, old Building and Loan pal,"',
    '20. "Well, how about the Building and Loan?"',
    '-Back: b'
        ]

        self._run_test( mock_stdout, expected_lines )

    @patch( "sys.stdout", new_callable=StringIO )
    @patch( "builtins.input", side_effect=[ "", "BLABLA", "21", "q"] )
    def test_bad_input( self, mock_input, mock_stdout ):
        expected_lines =[
    'Selection not understood – please try again. Make sure to type the',
    'word exactly as it appears above, or simply introduce its number.',
    'Number out of range. Please try again.'
        ]

        self._run_test( mock_stdout, expected_lines )

    @patch( "sys.stdout", new_callable=StringIO )
    @patch( "builtins.input", side_effect=[ "", "f", "w", "-1", "30", "q"] )
    def test_change_num( self, mock_input, mock_stdout ):
        expected_lines =[
    'New word window size:',
    'Please enter a valid number (integer >= 1)',
    '30. "wing". count in doc: 17. docs containing word: 3. tf-idf: 1.16E-03'
        ]

        self._run_test( mock_stdout, expected_lines )

    @patch( "sys.stdout", new_callable=StringIO )
    @patch( "builtins.input", side_effect=[ "", "f", "q"] )
    def test_name_filtering_integration( self, mock_input, mock_stdout ):
        expected_lines =[
    '1. "george". count in doc: 217. docs containing word: 4. tf-idf: 1.12E-02',
    '10. "sam". count in doc: 25. docs containing word: 2. tf-idf: 2.28E-03',
    '20. "zuzu". count in doc: 13. docs containing word: 1. tf-idf: 1.69E-03',
    'Note: name filtering is currently disabled.',
    '1. "building". count in doc: 27. docs containing word: 2. tf-idf: 2.46E-03',
    '10. "auld". count in doc: 8. docs containing word: 1. tf-idf: 1.04E-03',
    '20. "rent". count in doc: 6. docs containing word: 2. tf-idf: 5.46E-04',
    'Note: name filtering is currently enabled.',
    '-Disable name filtering: f'
        ]
        self._run_test( mock_stdout, expected_lines )

    @patch( "sys.stdout", new_callable=StringIO )
    @patch( "builtins.input", side_effect=[ "", "f", "w", "1200", "n", "q" ] )
    def test_next_words( self, mock_input, mock_stdout ):
        # sets window size to 1,200 and then hits next once, which should reach
        # the last word in the file, at 1,601
        expected_lines =[
    '1601. "ahead". count in doc: 1. docs containing word: 10. tf-idf: 0.00E+00',
        ]
        self._run_test( mock_stdout, expected_lines )

    @patch( "sys.stdout", new_callable=StringIO )
    @patch( "builtins.input", side_effect=[ "", "f", "n", "p", "q" ] )
    def test_previous_words( self, mock_input, mock_stdout ):
        main( [ "", "its-a-wonderful-life-1946.srt", "20" ] )
        output = mock_stdout.getvalue()

        first_line =\
    '1. "george". count in doc: 217. docs containing word: 4. tf-idf: 1.12E-02'
        
        # testing that the line appears twice effectively tests the "previous"
        # functionality, as the line was first printed by default, and then a
        # second time when the user navigated from words 21-40 back to 1-20
        self.assertEqual( output.count( first_line ), 2 )

    @patch( "sys.stdout", new_callable=StringIO )
    @patch( "builtins.input", side_effect=[ "", "rent", "q" ] )
    def test_word_typing( self, mock_input, mock_stdout ):
        # checks correct result when user types word instead of choosing by number
        expected_lines =[
    'Displaying occurrences of "rent":',
    '6. "You know, they charge for meals and rent up there,"'
        ]
        self._run_test( mock_stdout, expected_lines )

    @patch( "sys.stdout", new_callable=StringIO )
    @patch( "builtins.input", side_effect=[ "", "rent", "5", "b",
                                            "n", "n", "button", "1", "q" ] )
    def test_translation( self, mock_input, mock_stdout ):
        expected_lines =[
    'Selected sentence:',
    ' "90% owned by suckers who used to pay rent to you."',
    'Translating...done!',
    '90% deţinut de fraieri care obişnuiau să-ţi plătească chirie.',
    ' "And did you know that button behind you causes this floor to open up?"',
    'Şi ştiai că acel buton din spatele tău face ca acest etaj să se deschidă?'
        ]
        self._run_test( mock_stdout, expected_lines )

    @patch( "sys.stdout", new_callable=StringIO )
    @patch( "builtins.input", side_effect=[ "", "rent", "l", "q" ] )
    def test_display_examples( self, mock_input, mock_stdout ):
        main( [ "", "its-a-wonderful-life-1946.srt", "20" ] )
        output = mock_stdout.getvalue()

        instruction_line =\
    '-Display all examples again: l'

        example_line =\
    '6. "You know, they charge for meals and rent up there,"'

        self.assertIn( example_line, output )

        # testing that the line appears twice checks that the line was displayed
        # once by default, and then a second time after the user typed "l"
        self.assertEqual( output.count( example_line ), 2 )

if __name__ == "__main__":
    unittest.main()
