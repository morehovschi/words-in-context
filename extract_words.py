import os
import sys
import spacy
import json
import time
import math

from progress.bar import Bar
from joblib import Parallel, delayed

# load English language model

# here you may get an error like:
# '''
# [E050] Can't find model 'en_core_web_sm'. It doesn't seem to be a Python
# package or a valid path to a data directory.
# '''

# which simply means you haven't yet downloaded the necessary spaCy model yet;
# download the model with 'python -m spacy download en_core_web_sm'
nlp = spacy.load("en_core_web_sm")

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

    with open(fname, "r") as f:
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
        if token.lemma_.lower() not in word_counter:
            word_counter[ token.lemma_.lower() ] = 1
        else:
            word_counter[ token.lemma_.lower() ] =\
            word_counter[ token.lemma_.lower() ] + 1
    
        total_words += 1
        
    return word_counter, total_words

def analyze_file( fpath, cache_path='' ):
    """ uses helper methods to count words in an input file
    
    input: path to file to be analyzed
    output: dictionary of words (keys) and each unique word's number of occurrences (values)
    """
    counts, total_words = None, None
    
    fname = fpath[ fpath.rfind( '/' )+1:fpath.find( '.' )]
    
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
    
if __name__ == "__main__":
    if len( sys.argv ) < 2:
        # expected format for name of subtitle files
        file = 'S01E01.srt'
    else:
        file = sys.argv[ 1 ]
        
    if len( sys.argv ) < 3:
        WORDS_TO_PRINT = 20
    else:
        WORDS_TO_PRINT = int( sys.argv[ 2 ] )
        
    data_path = 'data/'

    time0 = time.time()

    # count words in each srt file in parallel and output results to json files
    analyzables = []
    for fname in os.listdir( data_path ):
        if fname.endswith( '.srt' ):
            analyzables.append( fname )
    Parallel( n_jobs=1 )( delayed( analyze_file )( data_path + fname , 'data/' )
                        for fname in Bar( 'Counting words in files' ).iter( analyzables ) )
    print( 'elapsed:', time.time() - time0 )
    
    print()
        
    # dictionary of word count dictionaries for all files in data_path dir
    corpus_counts = {}
    wordcount_fnames = []
    for fname in os.listdir( data_path ):
        if fname.endswith( '.json' ):
            with open( data_path + fname ) as json_file:
                corpus_counts[ separate_fpath( fname )[ 1 ] ] = json.load( json_file )

    # iterate through each word in each doc and calculate statistics
    doc_names = list( corpus_counts.keys() )
    for i in range( len( doc_names ) ):
        doc = corpus_counts[ doc_names[ i ] ]
        
        for word in doc:
            if word == "__total__":
                continue
            
            word_stats = {}
            
            word_stats[ 'count' ] = doc[ word ]
            word_stats[ 'words_in_doc' ] = doc[ '__total__']
            word_stats[ 'frequency' ] = word_stats[ 'count' ] /\
                                            word_stats[ 'words_in_doc' ]
            word_stats[ 'word_occs_in_docs' ] = 1
            
            for j in range( len( doc_names ) ):
                if j == i:
                    continue
                elif word in corpus_counts[ doc_names[ j ] ]:
                    word_stats[ 'word_occs_in_docs' ] += 1
                    
            word_stats[ 'tf-idf' ] = word_stats[ 'frequency' ] *\
            math.log( len( doc_names ) / word_stats[ 'word_occs_in_docs' ] )
            
            # replace word count in doc with dictionary of more detailed statistics
            corpus_counts[ doc_names[ i ] ][ word ] =  word_stats

    # extract the stats for the current doc
    file = separate_fpath( file )[ 1 ]
    doc_word_stats = []
    for word in corpus_counts[ file]:
        if word == "__total__":
            continue
        
        doc_word_stats.append( ( word, corpus_counts[ file ][ word ] ) )
        
    # sort words in doc by tf-idf descendingly
    doc_word_stats = sorted( doc_word_stats,
                             key=lambda tup: tup[ 1 ][ 'tf-idf' ],
                             reverse=True )

    for i in range( ( min( WORDS_TO_PRINT, len( doc_word_stats ) ) ) ):
        print( '%d. "%s". count in doc: %d. docs containing word: %d.' % ( i + 1 , 
                                                doc_word_stats[ i ][ 0 ], 
                                                doc_word_stats[ i ][ 1 ][ 'count' ], 
                                                doc_word_stats[ i ][ 1 ][ 'word_occs_in_docs' ] ),
             'tf-idf:', '{:.2E}'.format( doc_word_stats[ i ][ 1 ][ 'tf-idf' ] ) )
