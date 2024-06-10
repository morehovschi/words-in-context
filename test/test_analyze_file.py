import unittest
import json
import spacy

nlp = spacy.load("en_core_web_sm")

# sys path manipulation necessary for importing function defined in parent dir
import os, sys
sys.path.insert( 0, os.getcwd() ) 
from extract_words import analyze_file, analyze_file_sentence_ids, separate_fpath

class TestAnalyzeFile( unittest.TestCase ):

    def _test_parity_for_file( self, fname ):
        wordcount_path = "data/" + separate_fpath( fname )[ 1 ] + ".json"
        wsid_path = "data/" + separate_fpath( fname )[ 1 ] + "_wsid.json"
        keep_generated_wordcounts = os.path.isfile( wordcount_path )
        keep_generated_wsid = os.path.isfile( wsid_path )

        analyze_file( "data/" +  fname, "data/" )
        analyze_file_sentence_ids( "data/" +  fname, "data/" )
        
        wordcounts = None
        wsid = None
        with open( wordcount_path, "r" ) as f:
            wordcounts = json.load( f )
        with open( wsid_path, "r" ) as f:
            wsid = json.load( f )

        # compute the differences of the two sets of words
        in_first = set( wordcounts.keys() ) - set( wsid.keys() )
        in_second = set( wsid.keys() ) - set( wordcounts.keys() )

        # because of the difference in context size, the two analyzers may sometimes
        # lemmatize the same word differently;
        #
        # clean up any words that actually occur in both sets, but were classified
        # as different because of the differences in lemmatization
        # e.g. "whisper"<->"whispers", "child"<->"children"
        removable = set()
        for word in in_first:
            token = nlp( word )[ 0 ]
            if ( ( token.text in wsid ) or
                 ( token.lemma_ in wsid ) ):
                removable.add( token.text )
                removable.add( token.lemma_ )

        for word in in_second:
            token = nlp( word )[ 0 ]
            if ( ( token.lemma_ in wordcounts ) or
                 ( token.text in wordcounts ) ):
                removable.add( token.text )
                removable.add( token.lemma_ )

        in_first = in_first - removable
        in_second = in_second - removable

        in_first_string = "[" + ", ".join( in_first ) + "]"
        print( "Words only identified by first analyzer: " )
        print( in_first_string )
        print()

        in_second_string = "[" + ", ".join( in_second ) + "]"
        print( "Words only identified by second analyzer: " )
        print( in_second_string )
        print()

        # some of the differences in lemmatization cannot be overcome by the above
        # method of analyzing each word individually, e.g. the second analyzer
        # registers the word "singing" as an instance of the verb "singe", as
        # opposed to the contextually correct "sing"
        #
        # in addition, the first analyzer is likely to pick up srt format artifacts
        # such as "subs.com</font", "color="#fffa00" as words
        #
        # thus the test tolerates a small number of words unique to each analyzer
        # output as long as it is less than 1% of the total unique words identified
        # by the analyzer
        msg = "The words only identified by the first analyzer are >= 1% of the "\
              "total unique words identified by the first analyzer"
        self.assertLess( len( in_first ) / len( wordcounts ), 0.01, msg )

        msg = "The words only identified by the second analyzer are >= 1% of the "\
              "total unique words identified by the second analyzer"
        self.assertLess( len( in_second) / len( wsid ), 0.01, msg )

    def test_parity( self ):
        """
        test that analyze_file and analyze_file_sentence_ids arrive at the same
        number of occurrences in the doc for each word
        """
        self._test_parity_for_file( "S01E01.srt" )


if __name__ == '__main__':
    unittest.main()
