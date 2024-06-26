"""
Basic unit test that simulates some user input and checks that the expected
lines are present (based on data file "its-a-wonderful-life-1946.srt").
"""

import unittest
from unittest.mock import patch
from io import StringIO
import sys

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
    @patch( "builtins.input", side_effect=[ "", "q" ] )
    def test_quit( self, mock_input, mock_stdout ):
        expected_lines =[
    '1. "george". count in doc: 217. docs containing word: 4. tf-idf: 1.12E-02',
    '10. "sam". count in doc: 25. docs containing word: 2. tf-idf: 2.28E-03',
    '20. "zuzu". count in doc: 13. docs containing word: 1. tf-idf: 1.69E-03',
    'Options:',
    '-Select a word [1-20] to see contextual examples',
    '-Change number of displayed words: n',
    '-Display word list: l',
    '-Quit: q',
    'Bye now!'
        ]

        self._run_test( mock_stdout, expected_lines )

    @patch( "sys.stdout", new_callable=StringIO )
    @patch( "builtins.input", side_effect=[ "", "15", "b", "q"] )
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
    @patch( "builtins.input", side_effect=[ "",  "BLABLA", "q"] )
    def test_bad_input( self, mock_input, mock_stdout ):
        expected_lines =[
    'Selection not understood – please try again',
    "(type a word's number in the list above, not the word itself)"
        ]

        self._run_test( mock_stdout, expected_lines )

    @patch( "sys.stdout", new_callable=StringIO )
    @patch( "builtins.input", side_effect=[ "", "n", "-1", "30", "q"] )
    def test_change_num( self, mock_input, mock_stdout ):
        expected_lines =[
    'New number of displayed words: ',
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

if __name__ == "__main__":
    unittest.main()
