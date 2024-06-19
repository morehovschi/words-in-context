"""
This command line app looks through a set of subtitle files (.srt files in data/)
and, for a chosen document (corresponding to a movie or an episode), displays the
top N words ranked by TF-IDF. Once a word is chosen, contextual examples of the word
from the given document are displayed.

The app is intended for language learners who want learn a set of words (as well as
their associated contexts) ahead of watching the movie or episode.
"""

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
    nlp = spacy.load( "en_core_web_sm" )
except OSError as e:
    if "Can't find model" in str( e ):
        spacy.cli.download( "en_core_web_sm" )
        nlp = spacy.load( "en_core_web_sm" )
    else:
        raise e

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

def srt_sentences( fpath ):
    """
    helper that reads an srt file and returns a list of srt senteces where each
    item's index matches the srt line number
    """

    sentences = []
    with open( fpath, "r", encoding="utf-8", errors="ignore" ) as f:
        counting = False
        num = None
        timestamp = None  # timestamp is only used for validating format
        sentence = ""

        line = f.readline()
        while line:
            if not counting:
                # potentially remove utf 65279, found once at the beginning of the
                # file and any newline characters or spaces
                line = line.replace( chr( 65279 ), "" ).strip()
                if line.isnumeric():
                    counting = True
                    num = int( line )
                    # add $num empty items at the beginning so that sentence indices
                    # in the list match sentence numbers in the file
                    sentences += [ "" ] * num

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

def word_sentence_ids( fpath ):
    """
    takes a file path pointing to an srt file and returns a dictionary where words
    are keys and the values are lists with the numbers of sentences where each key
    word was encountered
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
    """
    tries to open a serialized dictionary of words and the sentence numbers where
    they occur; if unsuccessful, creates that dictionary and saves it
    """

    fname = fpath[ fpath.rfind( '/' )+1:fpath.find( '.' ) ]

    try:
        with open( cache_path + fname + '.json' ) as json_file:
            counts = json.load( json_file )

    except FileNotFoundError:
        wsid = word_sentence_ids( fpath )

        # if cache path provided, store the counter dictionary
        if cache_path:
            with open( cache_path + fname + '.json' , 'w' ) as json_file:
                json.dump( wsid, json_file )

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
    Parallel( n_jobs=1 )( delayed( analyze_file_sentence_ids )( dirpath + fname , 'data/' )
                        for fname in Bar( 'Counting words in files' ).iter( analyzables ) )
    print( 'elapsed:', time.time() - time0, "\n" )

    # dictionary of word count dictionaries for all files in dirpath dir
    corpus_counts = {}

    dir_filenames = []
    for fname in os.listdir( dirpath ):
        if not fname.endswith( ".json" ):
            continue

        with open( dirpath + fname ) as json_file:
            corpus_counts[ separate_fpath( fname )[ 1 ] ] = \
                json.load( json_file )

    return corpus_counts

def get_doc_word_stats( data_path, file ):
    """
    given a path to a data directory and the name of a file in it, loads data about
    word occurrences in all files (or, if unavailable, computes and saves it), and
    calculates TF-IDF for eaach word in the given file, in relation to all other
    files.

    the returned object is a list of tuples where [ 0 ] is the word and [ 1 ] is a
    dictionary of various statistics about this word in the given doc, like TF-IDF,
    how often the word occurs in this doc, how many other docs it occurs in etc.
    """
    # dictionary of word count dictionaries for all files in data_path dir
    corpus_counts = process_dir( data_path )

    doc_word_stats = []
    doc = corpus_counts[ file ]

    for word in doc:
        if word == "__total__":
            continue

        word_stats = {}

        word_stats[ 'count' ] = len( doc[ word ] )
        word_stats[ 'words_in_doc' ] = doc[ '__total__']
        word_stats[ 'frequency' ] = word_stats[ 'count' ] /\
                                        word_stats[ 'words_in_doc' ]
        word_stats[ 'word_occs_in_docs' ] = 0
        word_stats[ 'word_occ_ids' ] = doc[ word ]

        for other_doc_name, other_doc in corpus_counts.items():
            if word in other_doc:
                word_stats[ 'word_occs_in_docs' ] += 1

        word_stats[ 'tf-idf' ] = word_stats[ 'frequency' ] *\
            math.log( len( corpus_counts ) / word_stats[ 'word_occs_in_docs' ] )

        # replace word count in doc with dictionary of more detailed statistics
        doc_word_stats.append(  ( word, word_stats ) )

    # sort words in doc by tf-idf and prepend None so that indexing starts at 1
    doc_word_stats = [ None ] +\
        sorted( doc_word_stats, key=lambda tup: tup[ 1 ][ 'tf-idf' ], reverse=True )
    return doc_word_stats

def word_occurrence_menu( word, occ_ids, sentences ):
    """
    this just shows all the occurrences of given $word in the given $sentences, as
    determined by the list of sentence ids $occ_ids

    implemented as an additional menu/function because its functionality pertaining
    to a particular word will be expanded soon
    """
    print( f"Displaying occurrences of \"{word}\":" )
    for i, idx in enumerate( occ_ids ):
        print( f"{ i + 1 }. \"{ sentences[ idx ] }\"" )
    print( "\n-Back: b" )

    while True:
        action = input().strip()

        if action.lower() == "b":
            return
        else:
            print( "Selection not understood – please try again" )

def main_menu( num_words, fname, sentences, doc_word_stats ):
    """
    Shows the top $num_words words in the file, as well as associated statistics
    and gives the user the option to print contextual example sentences for any one
    of the displayed words.
    """

    def print_words():
        for i in range( 1, ( min( num_words, len( doc_word_stats ) ) + 1 ) ):
            print( '%d. "%s". count in doc: %d. docs containing word: %d.' % (
                    i, doc_word_stats[ i ][ 0 ],
                    doc_word_stats[ i ][ 1 ][ 'count' ],
                    doc_word_stats[ i ][ 1 ][ 'word_occs_in_docs' ] ),
                'tf-idf:', '{:.2E}'.format( doc_word_stats[ i ][ 1 ][ 'tf-idf' ] ) )
    def print_instructions():
        print( f"\nOptions:\n-Select a word [1-{num_words}] to see contextual"\
                " examples\n-Change number of displayed words: n\n-Display word "\
                "list: l\n-Quit: q\n" )

    print_words()
    print_instructions()

    while True:
        action = input().strip()

        if action.isnumeric() and int( action ) > 0 and int( action ) <= num_words:
            idx = int( action )
            word_occurrence_menu( doc_word_stats[ idx ][ 0 ],
                                  doc_word_stats[ idx ][ 1 ][ "word_occ_ids"],
                                  sentences )
            print_instructions()

        elif action.isnumeric():
            print( "Invalid number. Please try again\n" )
        elif action.lower() == "n":
            print( "Changing the number of words to display is unavailable, "\
                   "but coming soon. Thanks for your patience!" )
        elif action.lower() == "l":
            print_words()
        elif action.lower() == "q":
            print( "Bye now!" )
            return
        else:
            print( "Selection not understood – please try again\n(type a word's "\
                   "number in the list above, not the word itself)" )

def main( argv ):
    if len( argv ) < 2:
        # expected format for name of subtitle files
        fname_srt = 'its-a-wonderful-life-1946.srt'
    else:
        fname_srt = argv[ 1 ]
        
    if len( argv ) < 3:
        num_words = 20
    else:
        num_words = int( argv[ 2 ] )

    if "--help" in argv:
        print( f"USAGE: python3 { argv[ 0 ] }" +
    		   " <name of .srt file in data/> <num words>" )
        exit( 0 )

    data_dir_path = 'data/'
    fname = separate_fpath( fname_srt )[ 1 ]

    sentences = srt_sentences( data_dir_path + fname_srt )

    # extract stats for the current doc and sort by tf-idf descendingly
    doc_word_stats = get_doc_word_stats( data_dir_path, fname )

    main_menu( num_words, fname, sentences, doc_word_stats )

if __name__ == "__main__":
    main( sys.argv )

