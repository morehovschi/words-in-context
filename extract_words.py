import os
import sys
import spacy
import json
import time
import math
import re

from progress.bar import Bar
from joblib import Parallel, delayed

TIMESTAMP_REGEX = "[0-9]{2}:[0-9]{2}:[0-9]{2},[0-9]{3} --> [0-9]{2}:[0-9]{2}:[0-9]{2},[0-9]{3}"
NON_ALPHABET_REGEX = "[^a-zA-Z']"

# load English language model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError as e:
    if "Can't find model" in str( e ):
        spacy.cli.download( "en_core_web_sm" )
        nlp = spacy.load("en_core_web_sm")
    else:
        raise e

def srt_sentences( fpath ):
    """
    helper that reads an srt file and returns a list of srt senteces where each
    item's index matches the srt line number
    """

    sentences = [ "" ]  # first item empty so that indices match srt line numbers
    with open( fpath, "r", encoding="utf-8", errors="ignore" ) as f:
        counting = False
        num = None
        timestamp = None  # timestamp is only used for validating format
        sentence = ""

        line = f.readline()
        while line:
            if not counting:
                # potentially remove utf 65279, found once at the beginning of file
                line = line.replace( chr( 65279 ), "" )
                if line.strip() == "1":
                    counting = True
                    num = 1

                line = f.readline()
                continue

            line = line.strip()

            if line.isnumeric() and int( line ) == num + 1:
                sentences.append( sentence.strip() )

                num +=1
                timestamp = None
                sentence = ""
            elif re.search( TIMESTAMP_REGEX, line ):
                timestamp = line
            else:
                if has_alpha( line ) and timestamp:
                    sentence += line.strip() + " "

            line = f.readline()

        # if timestamp not None, there is still the last sentence in the file that
        # has not yet been added to the list
        if timestamp:
            sentences.append( sentence.strip() )

    return sentences


def has_alpha( string ):
    for char in string:
        if char.isalpha():
            return True
    return False    

def separate_fpath( fpath ):
    """ convenience method to separate directory name, file name and extension """
    
    dir_path = fpath[ :fpath.rfind( '/' ) + 1 ]
    fname = fpath[ fpath.rfind( '/' ) + 1:fpath.find( '.' ) ]
    extension = fpath[ fpath.find( '.' ): ]
    
    return dir_path, fname, extension

def tokenize( fname ):
    """ extract words without punctuation and other symbols """
    
    parsed_words = []

    with open(fname, "r", encoding="utf-8", errors="ignore" ) as f:
        text = f.read()
    lines = text.split( "\n" )
    alpha_lines = []

    # filter out lines with no alphabets
    for line in lines:
        if has_alpha( line ):
            alpha_lines.append( line)
    alpha_lines = "\n".join( alpha_lines )
     
    doc = nlp( alpha_lines )
    
    for token in doc:
        if ( token.is_punct ) or ( token is None ) or ( token.text == ' ') or\
           ( token.text == "\n" ):
            continue
        
        parsed_words.append( token )
    
    return parsed_words

def count( wordlist ):
    """ count the occurrence of each word in the wordlist """
    total_words = 0
    word_counter = {}
    for token in wordlist:
        # lemmatize, filter out things like attached dashes, change to lowercase
        lemma = re.sub( NON_ALPHABET_REGEX, "", token.lemma_.lower() )

        if lemma not in word_counter:
            word_counter[ lemma ] = 1
        else:
            word_counter[ lemma ] =\
            word_counter[ lemma ] + 1
    
        total_words += 1
        
    return word_counter, total_words

def analyze_file( fpath, cache_path='' ):
    """ uses helper methods to count words in an input file
    
    input: path to file to be analyzed
    output: dictionary of words (keys) and each unique word's number of occurrences (values)
    """
    counts, total_words = None, None
    
    fname = fpath[ fpath.rfind( '/' )+1:fpath.find( '.' ) ]
    
    try:
        with open( cache_path + fname + '.json' ) as json_file:
            counts = json.load( json_file )

    except FileNotFoundError:
        tokens = tokenize( fpath )
        counts, total_words = count( tokens )

        counts[ '__total__' ] = total_words
        
        # if cache path provided, store the counter dictionary
        if cache_path:
            with open( cache_path + fname + '.json' , 'w' ) as json_file:
                json.dump( counts, json_file )
            
    return counts

def process_dir( dirpath ):
    """
    Looks at data directory and counts occurrences of all words in all files and
    stores the counts for each source file as json. If json already available, skips
    the counting step.
    """
    time0 = time.time()

    # count words in each srt file in parallel and output results to json files
    analyzables = []
    for fname in os.listdir( dirpath ):
        if fname.endswith( '.srt' ):
            analyzables.append( fname )
    Parallel( n_jobs=1 )( delayed( analyze_file )( dirpath + fname , 'data/' )
                        for fname in Bar( 'Counting words in files' ).iter( analyzables ) )
    print( 'elapsed:', time.time() - time0, "\n" )

    # dictionary of word count dictionaries for all files in dirpath dir
    corpus_counts = {}
    for fname in os.listdir( dirpath ):
        if fname.endswith( '.json' ):
            with open( dirpath + fname ) as json_file:
                corpus_counts[ separate_fpath( fname )[ 1 ] ] = json.load( json_file )

    return corpus_counts

def get_doc_word_stats( corpus_counts, file ):
    """
    TODO:
    """
    doc_word_stats = []
    doc = corpus_counts[ file ]

    for word in doc:
        if word == "__total__":
            continue

        word_stats = {}

        word_stats[ 'count' ] = doc[ word ]
        word_stats[ 'words_in_doc' ] = doc[ '__total__']
        word_stats[ 'frequency' ] = word_stats[ 'count' ] /\
                                        word_stats[ 'words_in_doc' ]
        word_stats[ 'word_occs_in_docs' ] = 1

        for other_doc_name, other_doc in corpus_counts.items():
            if other_doc_name == file:
                continue
            elif word in other_doc:
                word_stats[ 'word_occs_in_docs' ] += 1

        word_stats[ 'tf-idf' ] = word_stats[ 'frequency' ] *\
            math.log( len( corpus_counts ) / word_stats[ 'word_occs_in_docs' ] )

        # replace word count in doc with dictionary of more detailed statistics
        doc_word_stats.append(  ( word, word_stats ) )

    # sort words in doc by tf-idf descendingly
    return sorted( doc_word_stats, key=lambda tup: tup[ 1 ][ 'tf-idf' ],
                   reverse=True )

def word_sentence_ids( fpath, cache_path="" ):
    """
    TODO:
    """
    word_sentence_ids = {}
    sentences = srt_sentences( fpath )

    total_words = 0

    for i, sentence in enumerate( sentences ):
        if not sentence:
            continue

        doc = nlp( sentence )

        for token in doc:
            if ( token.is_punct ) or ( token is None ) or ( token.text == ' ') or\
               ( token.text == "\n" ):
                continue

            # lemmatize, filter out things like attached dashes, change to lowercase
            lemma = re.sub( NON_ALPHABET_REGEX, "", token.lemma_.lower() )

            if lemma in word_sentence_ids:
                word_sentence_ids[ lemma ].append( i )
            else:
                 word_sentence_ids[ lemma ] = [ i ]
            total_words += 1

    # the total number of words in the file has special key
    word_sentence_ids[ "__total__" ] = total_words

    return word_sentence_ids

def analyze_file_sentence_ids( fpath, cache_path="" ):

    fname = fpath[ fpath.rfind( '/' )+1:fpath.find( '.' ) ]

    try:
        with open( cache_path + fname + '_wsid.json' ) as json_file:
            counts = json.load( json_file )

    except FileNotFoundError:
        wsid = word_sentence_ids( fpath )

        # if cache path provided, store the counter dictionary
        if cache_path:
            with open( cache_path + fname + '_wsid.json' , 'w' ) as json_file:
                json.dump( wsid, json_file )

    
if __name__ == "__main__":
    if len( sys.argv ) < 2:
        # expected format for name of subtitle files
        file = 'its-a-wonderful-life-1946.srt'
    else:
        file = sys.argv[ 1 ]
        
    if len( sys.argv ) < 3:
        WORDS_TO_PRINT = 20
    else:
        WORDS_TO_PRINT = int( sys.argv[ 2 ] )

    if "--help" in sys.argv:
    	print(f"USAGE: python3 { sys.argv[ 0 ] }" +
    		   " <name of .srt file in data/> <num words>" )
    	exit( 0 )
        
    data_path = 'data/'

    # dictionary of word count dictionaries for all files in data_path dir
    corpus_counts = process_dir( data_path )

    # extract stats for the current doc and sort by tf-idf descendingly
    file = separate_fpath( file )[ 1 ]
    doc_word_stats = get_doc_word_stats( corpus_counts, file )

    for i in range( ( min( WORDS_TO_PRINT, len( doc_word_stats ) ) ) ):
        print( '%d. "%s". count in doc: %d. docs containing word: %d.' % ( i + 1 , 
                                                doc_word_stats[ i ][ 0 ], 
                                                doc_word_stats[ i ][ 1 ][ 'count' ], 
                                                doc_word_stats[ i ][ 1 ][ 'word_occs_in_docs' ] ),
             'tf-idf:', '{:.2E}'.format( doc_word_stats[ i ][ 1 ][ 'tf-idf' ] ) )
